"""Source Monitor Agent.

Deep-crawls known sources within a page budget:

  1. Fetch the source root (httpx, headless-browser rescue for bot walls
     and JS shells) — snapshot it with change detection, as before.
  2. Extract links, merge in sitemap.xml entries, score them for civic
     value (budget/tender/audit/report keywords), keep in-scope links,
     honor robots.txt, and optionally let a configured LLM re-rank.
  3. Follow the top links one level deep; store each page/PDF as a
     document. Text is extracted from PDFs; scanned PDFs are recorded as
     an accessibility finding rather than silently dropped.

Every fetch is recorded: successes as snapshots/documents, failures as
crawl_errors. Failures are data — they feed the accessibility score.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..crawling import (
    FetchResult,
    RobotsCache,
    SmartFetcher,
    extract_links,
    parse_sitemap,
    same_site,
    select_frontier,
)
from ..crawling.pdf import extract_pdf_text
from ..llm import LLMClient
from ..storage import (
    CrawlError,
    Document,
    DocumentVersion,
    Source,
    SourceSnapshot,
)
from ..utils import content_hash, html_title, html_to_text


@dataclass
class CrawlStats:
    sources_checked: int = 0
    sources_successful: int = 0
    sources_failed: int = 0
    new_documents_found: int = 0
    pages_fetched: int = 0
    machine_readable_hits: int = 0  # pages returning HTML/CSV/JSON/XML or text PDFs
    links_followed: int = 0
    browser_rescues: int = 0
    pdf_documents: int = 0
    scanned_pdfs: int = 0
    ssl_invalid_pages: int = 0  # readable only by ignoring a broken TLS chain
    failure_reasons: list[str] = field(default_factory=list)


class SourceMonitorAgent:
    def __init__(
        self,
        settings: Settings | None = None,
        fetcher=None,
        llm: LLMClient | None = None,
    ):
        self.settings = settings or get_settings()
        self._injected_fetcher = fetcher  # tests inject a fake
        self.llm = llm
        self._sitemap_cache: dict[str, list[str]] = {}

    def crawl(self, session: Session, sources: list[Source], run_id: int | None = None) -> CrawlStats:
        stats = CrawlStats()
        if not self.settings.crawl_enabled:
            return stats

        fetcher = self._injected_fetcher or SmartFetcher(self.settings)
        robots = RobotsCache(self.settings.crawl_user_agent)
        seen_urls: set[str] = set()
        try:
            for source in sources[: self.settings.crawl_max_sources]:
                if stats.pages_fetched >= self.settings.crawl_max_pages_total:
                    break
                stats.sources_checked += 1
                self._crawl_source(
                    session, source, fetcher, robots, stats, run_id, seen_urls
                )
        finally:
            if self._injected_fetcher is None:
                fetcher.close()
        session.flush()
        return stats

    # --- root page ------------------------------------------------------

    def _crawl_source(
        self,
        session: Session,
        source: Source,
        fetcher,
        robots: RobotsCache,
        stats: CrawlStats,
        run_id: int | None,
        seen_urls: set[str],
    ) -> None:
        now = datetime.now(timezone.utc)
        source.last_checked_at = now
        seen_urls.add(source.url)
        result = fetcher.fetch(source.url)
        stats.pages_fetched += 1
        if result.via_browser:
            stats.browser_rescues += 1
        if result.ssl_invalid:
            stats.ssl_invalid_pages += 1
            session.add(
                CrawlError(
                    source_id=source.id,
                    run_id=run_id,
                    url=source.url,
                    error_type="tls_invalid",
                    message="Served with an invalid TLS certificate chain; content was "
                    "fetched insecurely for auditing.",
                )
            )

        if not result.ok:
            stats.sources_failed += 1
            reason = result.error or "unknown fetch error"
            stats.failure_reasons.append(f"{source.name}: {reason}")
            source.status = "unreachable" if result.status_code is None else "error"
            session.add(
                CrawlError(
                    source_id=source.id,
                    run_id=run_id,
                    url=source.url,
                    error_type="http_error" if result.status_code else "fetch_error",
                    message=reason[:2000],
                )
            )
            session.add(
                SourceSnapshot(
                    source_id=source.id,
                    http_status=result.status_code,
                    content_type=result.content_type[:128],
                    change_status="unavailable",
                )
            )
            return

        stats.sources_successful += 1
        source.status = "active"
        if result.is_machine_readable:
            stats.machine_readable_hits += 1

        digest = content_hash(result.content)
        previous = session.scalar(
            select(SourceSnapshot)
            .where(SourceSnapshot.source_id == source.id, SourceSnapshot.content_hash.is_not(None))
            .order_by(SourceSnapshot.fetched_at.desc(), SourceSnapshot.id.desc())
        )
        change_status = (
            "new" if previous is None else ("changed" if previous.content_hash != digest else "unchanged")
        )
        session.add(
            SourceSnapshot(
                source_id=source.id,
                http_status=result.status_code,
                content_hash=digest,
                content_type=result.content_type[:128],
                raw_content=result.text[:500_000] if result.text else None,
                change_status=change_status,
            )
        )
        if change_status in ("new", "changed") and result.text:
            self._store_document(session, source, result, stats, fallback_title=source.name)

        # --- breadth: follow civically valuable links ------------------
        if self.settings.crawl_depth >= 1 and result.is_html:
            self._crawl_frontier(session, source, result, fetcher, robots, stats, seen_urls)

    # --- frontier -------------------------------------------------------

    def _crawl_frontier(
        self,
        session: Session,
        source: Source,
        root: FetchResult,
        fetcher,
        robots: RobotsCache,
        stats: CrawlStats,
        seen_urls: set[str],
    ) -> None:
        links = extract_links(root.text, root.url)
        links += [(url, "sitemap entry") for url in self._sitemap_urls(fetcher, root.url)]
        # news estates need a stronger civic signal before spending budget
        min_score = 5 if source.source_type == "news" else 1
        frontier = select_frontier(
            links,
            root.url,
            limit=self.settings.crawl_max_links_per_source * 3,
            min_score=min_score,
        )
        frontier = self._llm_rerank(source, frontier)[: self.settings.crawl_max_links_per_source]

        for url, anchor_text, _score in frontier:
            if stats.pages_fetched >= self.settings.crawl_max_pages_total:
                return
            if url in seen_urls or not robots.allowed(url):
                continue
            seen_urls.add(url)
            child = fetcher.fetch(url)
            stats.pages_fetched += 1
            stats.links_followed += 1
            if child.via_browser:
                stats.browser_rescues += 1
            if child.ssl_invalid:
                stats.ssl_invalid_pages += 1
            if not child.ok:
                session.add(
                    CrawlError(
                        source_id=source.id,
                        url=url,
                        error_type="http_error" if child.status_code else "fetch_error",
                        message=(child.error or "")[:2000],
                    )
                )
                continue
            if child.is_machine_readable:
                stats.machine_readable_hits += 1
            self._store_document(
                session, source, child, stats, fallback_title=anchor_text or url
            )

    def _sitemap_urls(self, fetcher, base_url: str) -> list[str]:
        parsed = urlparse(base_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._sitemap_cache:
            result = fetcher.fetch(f"{origin}/sitemap.xml")
            locs = (
                parse_sitemap(result.text, limit=20)
                if result.ok and result.text and "<loc" in result.text.lower()
                else []
            )
            self._sitemap_cache[origin] = [u for u in locs if same_site(u, base_url)]
        return self._sitemap_cache[origin]

    def _llm_rerank(
        self, source: Source, frontier: list[tuple[str, str, int]]
    ) -> list[tuple[str, str, int]]:
        """Let a configured LLM re-rank the pre-filtered frontier.

        The rule-based analyst returns {} — keyword order stands. A real LLM
        gets the source context and picks the most civically valuable links.
        """
        if self.llm is None or len(frontier) <= 1:
            return frontier
        try:
            response = self.llm.complete_json(
                task="rank_links",
                instructions=(
                    "You are prioritizing a crawl of official public sources for a "
                    "government transparency audit. From `links`, pick the URLs most "
                    "likely to lead to budgets, tenders, contract awards, audit "
                    "reports, statistics, laws, or project reports — prefer document "
                    "listings and machine-readable data over news or navigation. "
                    'Return {"selected_urls": [...]} in priority order.'
                ),
                payload={
                    "source_name": source.name,
                    "source_type": source.source_type,
                    "links": [{"url": url, "text": text} for url, text, _ in frontier],
                },
            )
            selected = response.get("selected_urls")
            if not selected:
                return frontier
            by_url = {url: (url, text, score) for url, text, score in frontier}
            reranked = [by_url[url] for url in selected if url in by_url]
            remaining = [item for item in frontier if item[0] not in set(selected)]
            return reranked + remaining
        except Exception:  # noqa: BLE001 — ranking is best-effort, never fatal
            return frontier

    # --- document storage -------------------------------------------------

    def _store_document(
        self,
        session: Session,
        source: Source,
        result: FetchResult,
        stats: CrawlStats,
        fallback_title: str,
    ) -> None:
        digest = content_hash(result.content)
        existing = session.scalar(
            select(Document).where(
                Document.government_id == source.government_id,
                Document.content_hash == digest,
            )
        )
        if existing is not None:
            return

        metadata: dict = {"content_type": result.content_type, "via_browser": result.via_browser}
        if result.is_pdf:
            text, is_scanned = extract_pdf_text(result.content)
            stats.pdf_documents += 1
            metadata["format"] = "pdf"
            metadata["scanned_pdf"] = is_scanned
            if is_scanned:
                stats.scanned_pdfs += 1
            else:
                stats.machine_readable_hits += 1
            title = fallback_title[:500]
        elif result.is_html:
            text = html_to_text(result.text)
            title = html_title(result.text, fallback=fallback_title[:500])
        elif result.text:
            text = result.text  # CSV/JSON/XML — keep raw
            title = fallback_title[:500]
        else:
            return  # unknown binary; nothing extractable

        document = Document(
            source_id=source.id,
            government_id=source.government_id,
            title=title,
            url=result.url,
            document_type="unknown",
            retrieved_at=datetime.now(timezone.utc),
            content_hash=digest,
            raw_text=text[:500_000],
            metadata_json=metadata,
        )
        session.add(document)
        session.flush()
        session.add(
            DocumentVersion(
                document_id=document.id,
                content_hash=digest,
                raw_text=document.raw_text,
            )
        )
        stats.new_documents_found += 1
