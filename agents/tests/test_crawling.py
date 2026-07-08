"""Unit tests for the crawling layer (no network)."""
from __future__ import annotations

from io import BytesIO

from gov_oracle_agents.crawling import (
    FetchResult,
    extract_links,
    looks_blocked,
    parse_sitemap,
    same_site,
    score_link,
    select_frontier,
)
from gov_oracle_agents.crawling.pdf import extract_pdf_text


def html_result(url: str, text: str, status: int = 200) -> FetchResult:
    return FetchResult(
        url=url, ok=status < 400, status_code=status,
        content_type="text/html", text=text, content=text.encode(),
    )


# --- link extraction & scoring ------------------------------------------

PAGE = """
<html><body>
<a href="/finance/budget-2026.pdf">Annual Budget 2026</a>
<a href="/tender-notices">Tender Notices</a>
<a href="/audit/annual-report">Audit Report</a>
<a href="/photo-gallery">Photo Gallery</a>
<a href="https://facebook.com/govpage">Facebook</a>
<a href="/login">Officer Login</a>
<a href="/about-the-minister">About the Minister</a>
<a href="https://other-ministry.gov.bd/statistics">National Statistics</a>
<a href="https://random-blog.com/budget">Budget blog</a>
</body></html>
"""


def test_extract_links_resolves_and_dedupes():
    links = extract_links(PAGE, "https://mof.gov.bd/home")
    urls = [u for u, _ in links]
    assert "https://mof.gov.bd/finance/budget-2026.pdf" in urls
    assert "https://mof.gov.bd/tender-notices" in urls


def test_score_link_prefers_civic_content():
    assert score_link("https://x.gov.bd/budget-2026.pdf", "Annual Budget") > score_link(
        "https://x.gov.bd/news", "Latest News"
    )
    assert score_link("https://x.gov.bd/login", "Login") == -1
    assert score_link("https://facebook.com/gov", "Follow us") == -1


def test_same_site_allows_gov_estate_but_not_external():
    assert same_site("https://mof.gov.bd/x", "https://mof.gov.bd/")
    assert same_site("https://bbs.gov.bd/stats", "https://mof.gov.bd/")  # same .gov.bd estate
    assert not same_site("https://random-blog.com/budget", "https://mof.gov.bd/")
    assert not same_site("https://en.prothomalo.com/x", "https://www.thedailystar.net/")


def test_select_frontier_ranks_and_filters():
    links = extract_links(PAGE, "https://mof.gov.bd/home")
    frontier = select_frontier(links, "https://mof.gov.bd/home", limit=3)
    urls = [u for u, _, _ in frontier]
    assert len(frontier) == 3
    assert "https://mof.gov.bd/finance/budget-2026.pdf" in urls
    assert all("facebook" not in u and "login" not in u and "gallery" not in u for u in urls)
    assert all("random-blog.com" not in u for u in urls)


def test_parse_sitemap():
    xml = """<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>https://mof.gov.bd/budget</loc></url>
    <url><loc> https://mof.gov.bd/reports </loc></url></urlset>"""
    assert parse_sitemap(xml) == ["https://mof.gov.bd/budget", "https://mof.gov.bd/reports"]


def test_news_chrome_and_entertainment_filtered():
    assert score_link("https://news.example.gov.bd/comment-policy", "Comment Policy") == -1
    assert score_link(
        "https://x.gov.bd/culture/tv-film/news/top-winners-awards-123", "Awards night"
    ) == -1
    assert score_link("https://x.gov.bd/subscribe", "Subscribe now") == -1


def test_min_score_raises_bar_for_weak_links():
    links = [
        ("https://x.gov.bd/news/daily-roundup", "Daily news roundup"),  # weak: news only
        ("https://x.gov.bd/budget-2026", "Budget documents"),  # strong
    ]
    lax = select_frontier(links, "https://x.gov.bd/", limit=10, min_score=1)
    strict = select_frontier(links, "https://x.gov.bd/", limit=10, min_score=5)
    assert len(lax) == 2
    assert [u for u, _, _ in strict] == ["https://x.gov.bd/budget-2026"]


# --- blocked-response detection -------------------------------------------

def test_looks_blocked_on_failure_and_bot_walls():
    assert looks_blocked(FetchResult(url="u", ok=False, error="timeout"))
    assert looks_blocked(html_result("u", "<html>x</html>", status=403))
    long_pad = "<p>" + "word " * 200 + "</p>"
    assert looks_blocked(html_result("u", f"<html>Checking your browser {long_pad}</html>"))
    assert looks_blocked(html_result("u", "<html><body></body></html>"))  # empty JS shell
    assert not looks_blocked(html_result("u", f"<html><body>{long_pad}</body></html>"))


def test_pdf_never_needs_browser():
    result = FetchResult(
        url="https://x.gov.bd/doc.pdf", ok=True, status_code=200,
        content_type="application/pdf", content=b"%PDF-1.4",
    )
    assert result.is_pdf
    assert not result.is_machine_readable


# --- pdf extraction --------------------------------------------------------

def make_pdf(text: str) -> bytes:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_blank_pdf_detected_as_scanned():
    text, is_scanned = extract_pdf_text(make_pdf(""))
    assert is_scanned
    assert text == ""


def test_garbage_pdf_degrades_gracefully():
    text, is_scanned = extract_pdf_text(b"not a pdf at all")
    assert text == ""
    assert is_scanned
