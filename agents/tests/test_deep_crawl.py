"""Deep-crawl behavior with a fake fetcher (no network)."""
from __future__ import annotations

from gov_oracle_agents.agents import GovernmentResolverAgent, SourceDiscoveryAgent, SourceMonitorAgent
from gov_oracle_agents.crawling import FetchResult
from gov_oracle_agents.storage import Document, Source, init_db, session_scope

ROOT_HTML = """
<html><head><title>Ministry of Finance</title></head><body>
<p>Welcome to the Ministry of Finance public portal with information on fiscal policy,
budget documents, procurement and public expenditure management for citizens.</p>
<a href="/budget-2026">Budget documents FY2026</a>
<a href="/tender-notices">Procurement tender notices</a>
<a href="/photo-gallery">Photo gallery</a>
</body></html>
"""

BUDGET_HTML = """
<html><head><title>Budget FY2026</title></head><body>
<p>The annual development budget allocation is Tk 500 crore for fiscal year 2026.</p>
</body></html>
"""

TENDER_HTML = """
<html><head><title>Tender notices</title></head><body>
<p>Invitation for bid: e-GP tender for hospital equipment procurement.</p>
</body></html>
"""


class FakeFetcher:
    """Serves a small fake government site; records what was requested."""

    def __init__(self):
        self.requested: list[str] = []

    def fetch(self, url: str) -> FetchResult:
        self.requested.append(url)
        pages = {
            "/budget-2026": BUDGET_HTML,
            "/tender-notices": TENDER_HTML,
        }
        for path, html in pages.items():
            if url.rstrip("/").endswith(path.lstrip("/").rstrip("/")) or url.endswith(path):
                return self._html(url, html)
        if url.endswith("/sitemap.xml"):
            return FetchResult(url=url, ok=False, status_code=404, error="HTTP 404")
        if "photo-gallery" in url:
            raise AssertionError("negative-scored link must not be fetched")
        return self._html(url, ROOT_HTML)

    @staticmethod
    def _html(url: str, html: str) -> FetchResult:
        return FetchResult(
            url=url, ok=True, status_code=200, content_type="text/html",
            text=html, content=html.encode(),
        )

    def close(self) -> None:
        pass


def test_deep_crawl_follows_civic_links(settings):
    settings.crawl_enabled = True
    settings.crawl_depth = 1
    settings.crawl_max_links_per_source = 3
    init_db(settings.database_url)

    with session_scope(settings.database_url) as session:
        government = GovernmentResolverAgent().resolve(session, "Government of Bangladesh")
        SourceDiscoveryAgent().discover(session, government)
        # crawl just one source to keep the test focused
        source = session.query(Source).filter_by(government_id=government.id).first()
        fetcher = FakeFetcher()
        stats = SourceMonitorAgent(settings, fetcher=fetcher).crawl(session, [source])

        assert stats.sources_checked == 1
        assert stats.sources_successful == 1
        assert stats.links_followed == 2  # budget + tender, not the gallery
        assert stats.new_documents_found == 3  # root + 2 children
        assert stats.pages_fetched >= 3

        titles = {d.title for d in session.query(Document).all()}
        assert "Budget FY2026" in titles
        assert "Tender notices" in titles

        # re-crawl: identical content → no duplicate documents
        stats2 = SourceMonitorAgent(settings, fetcher=FakeFetcher()).crawl(session, [source])
        assert stats2.new_documents_found == 0


def test_depth_zero_disables_link_following(settings):
    settings.crawl_enabled = True
    settings.crawl_depth = 0
    init_db(settings.database_url)

    with session_scope(settings.database_url) as session:
        government = GovernmentResolverAgent().resolve(session, "Government of Bangladesh")
        SourceDiscoveryAgent().discover(session, government)
        source = session.query(Source).filter_by(government_id=government.id).first()
        stats = SourceMonitorAgent(settings, fetcher=FakeFetcher()).crawl(session, [source])
        assert stats.links_followed == 0
        assert stats.new_documents_found == 1  # root only


def test_ssl_invalid_pages_recorded_as_findings(settings):
    settings.crawl_enabled = True
    settings.crawl_depth = 0
    init_db(settings.database_url)

    class SslFlaggingFetcher(FakeFetcher):
        def fetch(self, url: str) -> FetchResult:
            result = super().fetch(url)
            result.ssl_invalid = True
            return result

    from gov_oracle_agents.storage import CrawlError, session_scope as scope

    with scope(settings.database_url) as session:
        government = GovernmentResolverAgent().resolve(session, "Government of Bangladesh")
        SourceDiscoveryAgent().discover(session, government)
        source = session.query(Source).filter_by(government_id=government.id).first()
        stats = SourceMonitorAgent(settings, fetcher=SslFlaggingFetcher()).crawl(session, [source])
        assert stats.ssl_invalid_pages == 1
        errors = session.query(CrawlError).filter_by(error_type="tls_invalid").all()
        assert len(errors) == 1


def test_event_confidence_weighted_by_source_reliability(settings):
    from gov_oracle_agents.agents import CivicEventExtractionAgent, DocumentExtractionAgent
    from gov_oracle_agents.llm import RuleBasedAnalyst
    from gov_oracle_agents.storage import CivicEvent

    init_db(settings.database_url)
    with session_scope(settings.database_url) as session:
        government = GovernmentResolverAgent().resolve(session, "Government of Bangladesh")
        SourceDiscoveryAgent().discover(session, government)
        gov_source = (
            session.query(Source)
            .filter_by(government_id=government.id)
            .filter(Source.reliability_score >= 0.85)
            .first()
        )
        news_source = (
            session.query(Source)
            .filter_by(government_id=government.id, source_type="news")
            .first()
        )
        text = "Notification of award: contract awarded to MedSupply Ltd for Tk 40 crore."
        for i, src in enumerate([gov_source, news_source]):
            session.add(
                Document(
                    government_id=government.id,
                    source_id=src.id,
                    title=f"Contract award notice {i}",
                    url=f"https://example{i}.gov.bd/award",
                    document_type="unknown",
                    content_hash=f"rel-hash-{i}",
                    raw_text=text,
                )
            )
        session.flush()
        DocumentExtractionAgent(RuleBasedAnalyst()).process_new_documents(session, government)
        CivicEventExtractionAgent().extract(session, government)

        events = {
            e.document_id: e
            for e in session.query(CivicEvent).filter_by(government_id=government.id)
        }
        docs = session.query(Document).filter(Document.content_hash.like("rel-hash-%")).all()
        gov_doc = next(d for d in docs if d.source_id == gov_source.id)
        news_doc = next(d for d in docs if d.source_id == news_source.id)
        assert events[gov_doc.id].confidence > events[news_doc.id].confidence


def test_institution_sites_registered_as_sources(settings):
    init_db(settings.database_url)
    with session_scope(settings.database_url) as session:
        government = GovernmentResolverAgent().resolve(session, "Government of Bangladesh")
        sources = SourceDiscoveryAgent().discover(session, government)
        names = {s.name for s in sources}
        assert any("Ministry of Health and Family Welfare" in n for n in names)
        # curated list (14) + institution sites — meaningfully broader than before
        assert len(sources) >= 20
