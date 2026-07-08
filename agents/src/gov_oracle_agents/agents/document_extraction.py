"""Document Extraction Agent.

Classifies unclassified documents and extracts structured metadata
(amounts, dates, entity mentions). Classification goes through the LLM
abstraction, which falls back to keyword heuristics offline.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..llm import LLMClient
from ..storage import Document, Government, Institution
from ..utils import extract_amounts, extract_first_date

ALLOWED_DOC_TYPES = {
    "budget", "tender", "contract", "policy", "law", "audit", "press release",
    "statistics", "project report", "speech", "news article", "unknown",
}
# tolerate common LLM phrasings ("budget document", "audit report", ...)
DOC_TYPE_SYNONYMS = {
    "budget document": "budget",
    "audit report": "audit",
    "procurement notice": "tender",
    "tender notice": "tender",
    "contract award": "contract",
    "legislation": "law",
    "statistical report": "statistics",
    "news": "news article",
    "report": "project report",
}


def normalize_doc_type(raw: object) -> str:
    value = str(raw or "unknown").strip().lower()
    value = DOC_TYPE_SYNONYMS.get(value, value)
    return value if value in ALLOWED_DOC_TYPES else "unknown"


def normalize_confidence(raw: object, default: float = 0.3) -> float:
    try:
        return min(max(float(raw), 0.0), 1.0)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


class DocumentExtractionAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def process_new_documents(self, session: Session, government: Government) -> int:
        institution_names = [
            inst.name
            for inst in session.scalars(
                select(Institution).where(Institution.government_id == government.id)
            )
        ]
        documents = session.scalars(
            select(Document).where(
                Document.government_id == government.id,
                Document.document_type == "unknown",
            )
        ).all()

        for document in documents:
            text = document.raw_text or ""
            classification = self.llm.complete_json(
                task="classify_document",
                instructions=(
                    "Classify this public document into one of: budget, tender, contract, "
                    "policy, law, audit, press release, statistics, project report, speech, "
                    "news article, unknown. Return {\"document_type\": ..., \"confidence\": 0-1}."
                ),
                payload={"title": document.title, "text": text[:4000]},
            )
            document.document_type = normalize_doc_type(classification.get("document_type"))

            amounts = extract_amounts(text[:20_000])
            mentioned_institutions = [name for name in institution_names if name.lower() in text.lower()]
            published = extract_first_date(text[:5000])
            if published and document.published_at is None:
                document.published_at = published

            # merge with crawl-time metadata (format, scanned_pdf, via_browser)
            document.metadata_json = {
                **(document.metadata_json or {}),
                "classification_confidence": normalize_confidence(classification.get("confidence")),
                "classification_method": classification.get("method", self.llm.name),
                "amounts": amounts[:20],
                "institutions_mentioned": mentioned_institutions,
            }
        session.flush()
        return len(documents)
