from gov_oracle_agents.utils import content_hash, extract_amounts, html_title, html_to_text


def test_extract_amounts_bdt_crore():
    amounts = extract_amounts("The project was allocated Tk 500 crore for FY2026.")
    assert amounts[0]["value"] == 500 * 10_000_000
    assert amounts[0]["currency"] == "BDT"


def test_extract_amounts_usd_million():
    amounts = extract_amounts("A $25 million loan was approved.")
    assert amounts[0]["value"] == 25_000_000
    assert amounts[0]["currency"] == "USD"


def test_html_to_text_strips_scripts():
    html = "<html><head><script>evil()</script></head><body><p>Budget  report</p></body></html>"
    text = html_to_text(html)
    assert "evil" not in text
    assert "Budget" in text


def test_html_title():
    assert html_title("<html><head><title> Ministry of Finance </title></head></html>") == "Ministry of Finance"
    assert html_title("<html></html>", fallback="fb") == "fb"


def test_content_hash_stable():
    assert content_hash("abc") == content_hash(b"abc")
