from __future__ import annotations

import hashlib
import re
from datetime import datetime

from bs4 import BeautifulSoup


def content_hash(content: str | bytes) -> str:
    data = content.encode("utf-8", errors="replace") if isinstance(content, str) else content
    return hashlib.sha256(data).hexdigest()


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def html_title(html: str, fallback: str = "Untitled document") -> str:
    soup = BeautifulSoup(html, "html.parser")
    if soup.title and soup.title.string:
        return soup.title.string.strip()[:500]
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)[:500]
    return fallback


# Amounts like "Tk 500 crore", "BDT 1,200 million", "$25 million"
AMOUNT_PATTERN = re.compile(
    r"(?:tk\.?|bdt|taka|usd|\$)\s*([\d,]+(?:\.\d+)?)\s*(crore|lakh|million|billion)?",
    re.IGNORECASE,
)

MULTIPLIERS = {
    "crore": 10_000_000,
    "lakh": 100_000,
    "million": 1_000_000,
    "billion": 1_000_000_000,
    None: 1,
}


def extract_amounts(text: str) -> list[dict]:
    """Extract monetary amounts. Returns [{'raw', 'value', 'currency'}]."""
    results = []
    for match in AMOUNT_PATTERN.finditer(text):
        raw_number = match.group(1).replace(",", "")
        unit = match.group(2).lower() if match.group(2) else None
        try:
            value = float(raw_number) * MULTIPLIERS[unit]
        except (ValueError, KeyError):
            continue
        currency = "USD" if "$" in match.group(0) or "usd" in match.group(0).lower() else "BDT"
        results.append({"raw": match.group(0).strip(), "value": value, "currency": currency})
    return results


DATE_PATTERNS = [
    (re.compile(r"(\d{4})-(\d{2})-(\d{2})"), "%Y-%m-%d"),
    (re.compile(r"(\d{2})/(\d{2})/(\d{4})"), "%d/%m/%Y"),
]


def extract_first_date(text: str) -> datetime | None:
    for pattern, fmt in DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            try:
                return datetime.strptime(match.group(0), fmt)
            except ValueError:
                continue
    return None
