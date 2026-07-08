"""Civic Event Extraction Agent.

Converts classified documents into structured civic events. Document types
map to event families; amounts and institution mentions become event fields.
Confidence is inherited from classification and capped: heuristic events are
never presented as high-confidence facts.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..storage import CivicEvent, Document, Government, Source

DOC_TYPE_TO_EVENT = {
    "budget": "budget_allocation",
    "tender": "procurement_notice",
    "contract": "contract_award",
    "audit": "audit_objection",
    "law": "law_passed",
    "policy": "policy_announcement",
    "statistics": "spending_report",
    "project report": "project_status",
    "press release": "public_service_alert",
}


class CivicEventExtractionAgent:
    def extract(self, session: Session, government: Government) -> int:
        already_processed = {
            event.document_id
            for event in session.scalars(
                select(CivicEvent).where(CivicEvent.government_id == government.id)
            )
            if event.document_id is not None
        }
        documents = session.scalars(
            select(Document).where(
                Document.government_id == government.id,
                Document.document_type.in_(DOC_TYPE_TO_EVENT.keys()),
            )
        ).all()

        source_reliability = {
            source.id: source.reliability_score
            for source in session.scalars(
                select(Source).where(Source.government_id == government.id)
            )
        }

        created = 0
        for document in documents:
            if document.id in already_processed:
                continue
            metadata = document.metadata_json or {}
            amounts = metadata.get("amounts", [])
            top_amount = amounts[0] if amounts else None
            institutions = metadata.get("institutions_mentioned", [])
            # weight by source reliability: a news mention is corroboration,
            # not a primary record — it must never outrank official documents
            reliability = source_reliability.get(document.source_id, 0.5)
            confidence = min(float(metadata.get("classification_confidence", 0.3)), 0.75) * reliability
            if confidence < 0.2:
                continue

            session.add(
                CivicEvent(
                    government_id=government.id,
                    document_id=document.id,
                    event_type=DOC_TYPE_TO_EVENT[document.document_type],
                    title=document.title[:500],
                    summary=(document.raw_text or "")[:600],
                    event_date=document.published_at or document.retrieved_at,
                    amount=top_amount["value"] if top_amount else None,
                    currency=top_amount["currency"] if top_amount else None,
                    institution_name=institutions[0] if institutions else None,
                    entities_json=institutions,
                    locations_json=[],
                    confidence=confidence,
                )
            )
            created += 1
        session.flush()
        return created
