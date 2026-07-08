"""Crawl-frontier heuristics: which links on a government page are worth
following with a limited page budget?

Scoring is keyword-based and deterministic (auditable, works offline). When
a real LLM is configured, the monitor lets it re-rank the top candidates —
the heuristics then act as a pre-filter, not the final word.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

# Signals that a link leads to substantive civic records. Weights are
# relative; ties are broken by URL brevity (hub pages over deep leaves).
CIVIC_KEYWORDS: dict[str, int] = {
    "budget": 6,
    "tender": 6,
    "procurement": 6,
    "audit": 6,
    "expenditure": 5,
    "contract": 5,
    "award": 5,
    "finance": 4,
    "gazette": 4,
    "law": 4,
    "act": 3,
    "policy": 4,
    "report": 4,
    "statistics": 4,
    "publication": 4,
    "notice": 4,
    "circular": 3,
    "bulletin": 3,
    "survey": 3,
    "dataset": 4,
    "data": 2,
    "project": 3,
    "annual": 3,
    "quarterly": 3,
    "monthly": 2,
    "download": 2,
    "pdf": 2,
    "press": 1,
    "news": 1,
    # --- non-English civic vocabulary (Latin-script official languages of
    # registered governments). Substring-matched like the rest, so only
    # words that are unambiguous as substrings belong here.
    # German
    "haushalt": 6,
    "ausschreibung": 6,
    "vergabe": 5,
    "rechnungshof": 5,
    "finanzen": 4,
    "statistik": 4,
    "gesetz": 4,
    "bericht": 3,
    # French
    "marches-publics": 6,
    "depense": 5,
    "dépense": 5,
    "comptes": 4,
    "rapport": 3,
    "statistique": 4,
    "loi-": 2,
    # Spanish
    "presupuesto": 6,
    "licitacion": 6,
    "licitación": 6,
    "auditoria": 5,
    "auditoría": 5,
    "contrato": 4,
    "estadistica": 4,
    "estadística": 4,
    "informe": 3,
    # Portuguese
    "orcamento": 6,
    "orçamento": 6,
    "licitacao": 6,
    "licitação": 6,
    "despesa": 5,
    "relatorio": 3,
    "relatório": 3,
    # Indonesian
    "anggaran": 6,
    "pengadaan": 6,
    "lelang": 5,
    "keuangan": 4,
    "laporan": 3,
    # Norwegian
    "budsjett": 6,
    "anskaffelse": 6,
    "regnskap": 4,
    "statistikk": 4,
}

# Links that are never worth budget: nav chrome, auth, social, media,
# entertainment sections (where "award"/"policy" keywords false-positive).
NEGATIVE_PATTERNS = (
    "login",
    "signin",
    "sign-in",
    "register",
    "subscribe",
    "advertis",
    "facebook.",
    "twitter.",
    "x.com",
    "youtube.",
    "instagram.",
    "linkedin.",
    "javascript:",
    "mailto:",
    "tel:",
    "/gallery",
    "/photo",
    "/video",
    "/culture",
    "/entertainment",
    "/sports",
    "/lifestyle",
    "tv-film",
    "comment-policy",
    "comment policy",
    "sitemap.xml",
    "accessibility",
    "privacy",
    "terms",
    "faq",
    "contact",
)

SITEMAP_LOC_RE = re.compile(r"<loc>\s*(.*?)\s*</loc>", re.IGNORECASE | re.DOTALL)


def extract_links(html: str, base_url: str) -> list[tuple[str, str]]:
    """Return [(absolute_url, anchor_text)], deduped, fragments stripped."""
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    links: list[tuple[str, str]] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith("#"):
            continue
        absolute = urljoin(base_url, href).split("#")[0]
        if not absolute.startswith(("http://", "https://")):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        links.append((absolute, anchor.get_text(" ", strip=True)[:200]))
    return links


def score_link(url: str, anchor_text: str) -> int:
    haystack = f"{url.lower()} {anchor_text.lower()}"
    if any(pattern in haystack for pattern in NEGATIVE_PATTERNS):
        return -1
    score = sum(weight for keyword, weight in CIVIC_KEYWORDS.items() if keyword in haystack)
    return score


def same_site(url: str, base_url: str) -> bool:
    """Same host — or same government web estate.

    Official portals sprawl across sibling domains (mof.portal.gov.bd,
    bangladesh.gov.bd, ...). If the base host is under a governmental
    second-level zone like `gov.bd`, any host in that zone is in scope.
    """
    host = urlparse(url).netloc.lower()
    base = urlparse(base_url).netloc.lower()
    if not host or not base:
        return False
    if host == base:
        return True
    base_parts = base.split(".")
    if len(base_parts) >= 2 and base_parts[-2] in ("gov", "gob", "gouv", "go"):
        zone = ".".join(base_parts[-2:])
        return host == zone or host.endswith("." + zone)
    return False


def select_frontier(
    links: list[tuple[str, str]], base_url: str, limit: int, min_score: int = 1
) -> list[tuple[str, str, int]]:
    """Top-N civically valuable, in-scope links: [(url, text, score)].

    `min_score` raises the bar for noisy estates (news sites), where weak
    single-keyword matches are mostly editorial content.
    """
    scored = [
        (url, text, score_link(url, text))
        for url, text in links
        if same_site(url, base_url)
    ]
    ranked = sorted(
        (item for item in scored if item[2] >= min_score),
        key=lambda item: (-item[2], len(item[0])),
    )
    return ranked[:limit]


def parse_sitemap(xml_text: str, limit: int = 20) -> list[str]:
    """Extract <loc> URLs from a sitemap or sitemap index (namespace-agnostic)."""
    return [match.strip() for match in SITEMAP_LOC_RE.findall(xml_text)[:limit]]
