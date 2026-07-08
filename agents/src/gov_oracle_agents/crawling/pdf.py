"""PDF text extraction.

Text-based PDFs yield searchable civic records; scanned image PDFs yield
almost nothing — which is exactly the accessibility failure the scoring
should capture, so callers distinguish the two cases.
"""
from __future__ import annotations

import logging
from io import BytesIO

logger = logging.getLogger(__name__)

# Below this many characters per page, treat the PDF as scanned/image-only.
SCANNED_THRESHOLD_CHARS_PER_PAGE = 40


def extract_pdf_text(data: bytes, max_pages: int = 50) -> tuple[str, bool]:
    """Return (text, is_scanned)."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        pages = reader.pages[:max_pages]
        chunks = []
        for page in pages:
            try:
                chunks.append(page.extract_text() or "")
            except Exception:  # noqa: BLE001 — malformed pages are common
                chunks.append("")
        text = "\n".join(chunks).strip()
        page_count = max(len(pages), 1)
        is_scanned = len(text) < SCANNED_THRESHOLD_CHARS_PER_PAGE * page_count
        return text, is_scanned
    except Exception as exc:  # noqa: BLE001
        logger.debug("pdf extraction failed: %s", exc)
        return "", True
