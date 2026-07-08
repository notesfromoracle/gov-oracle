"""Knowledge Graph / Linking Agent.

Builds evidence-backed edges between entities extracted from documents and
events. An edge is only created when a single document mentions both
endpoints — the document is the evidence, and the explanation says exactly
what the evidence supports (a mention, not a verified transaction).

The chain we want to be able to trace:
  Institution → Program → Project → Budget → Tender → Contract → Vendor → Payment → Outcome

For most governments large parts of this chain are NOT publicly linkable.
That gap is measured by the completeness/traceability scores rather than
papered over here.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..storage import CivicEvent, Entity, Government, KnowledgeEdge

EVENT_TYPE_TO_ENTITY = {
    "budget_allocation": "budget",
    "procurement_notice": "tender",
    "contract_award": "contract",
    "audit_objection": "audit",
    "project_status": "project",
}

EDGE_RULES = [
    # (from_entity_type, to_entity_type, edge_type)
    ("budget", "project", "budget_funds_project"),
    ("project", "tender", "project_has_tender"),
    ("tender", "contract", "tender_awarded_as_contract"),
    ("contract", "project", "contract_relates_to_project"),
    ("audit", "project", "audit_mentions_project"),
]


class KnowledgeGraphAgent:
    def link(self, session: Session, government: Government) -> int:
        events = session.scalars(
            select(CivicEvent).where(CivicEvent.government_id == government.id)
        ).all()

        # 1. Materialize entities for events and their institution mentions.
        entity_cache: dict[tuple[str, str], Entity] = {
            (e.entity_type, e.name): e
            for e in session.scalars(
                select(Entity).where(Entity.government_id == government.id)
            )
        }

        def get_entity(entity_type: str, name: str) -> Entity:
            key = (entity_type, name[:255])
            if key not in entity_cache:
                entity = Entity(
                    government_id=government.id, name=name[:255], entity_type=entity_type
                )
                session.add(entity)
                session.flush()
                entity_cache[key] = entity
            return entity_cache[key]

        # entity -> (event, institution names mentioned in its source document)
        event_entities: list[tuple[Entity, CivicEvent, set[str]]] = []
        for event in events:
            entity_type = EVENT_TYPE_TO_ENTITY.get(event.event_type)
            if entity_type is None:
                continue
            entity = get_entity(entity_type, event.title)
            mentions = set(event.entities_json or [])
            if event.institution_name:
                mentions.add(event.institution_name)
            event_entities.append((entity, event, mentions))

        existing_edges = {
            (edge.from_entity_id, edge.to_entity_id, edge.edge_type)
            for edge in session.scalars(
                select(KnowledgeEdge).where(KnowledgeEdge.government_id == government.id)
            )
        }

        created = 0
        # 2. Institution → event-entity edges (evidence: the document mentions the institution).
        for entity, event, mentions in event_entities:
            for institution_name in mentions:
                institution_entity = get_entity("institution", institution_name)
                key = (institution_entity.id, entity.id, "institution_mentioned_in")
                if key in existing_edges:
                    continue
                session.add(
                    KnowledgeEdge(
                        government_id=government.id,
                        from_entity_type="institution",
                        from_entity_id=institution_entity.id,
                        to_entity_type=entity.entity_type,
                        to_entity_id=entity.id,
                        edge_type="institution_mentioned_in",
                        confidence=min(event.confidence, 0.7),
                        source_document_id=event.document_id,
                        explanation=(
                            f"The source document for '{event.title[:120]}' mentions "
                            f"{institution_name}. This is a textual mention, not a verified "
                            "administrative relationship."
                        ),
                    )
                )
                existing_edges.add(key)
                created += 1

        # 3. Cross-event edges where two events share an institution mention.
        for i, (entity_a, event_a, mentions_a) in enumerate(event_entities):
            for entity_b, event_b, mentions_b in event_entities[i + 1 :]:
                shared = mentions_a & mentions_b
                if not shared:
                    continue
                for from_type, to_type, edge_type in EDGE_RULES:
                    pair = None
                    if entity_a.entity_type == from_type and entity_b.entity_type == to_type:
                        pair = (entity_a, entity_b, event_b)
                    elif entity_b.entity_type == from_type and entity_a.entity_type == to_type:
                        pair = (entity_b, entity_a, event_a)
                    if pair is None:
                        continue
                    from_entity, to_entity, evidence_event = pair
                    key = (from_entity.id, to_entity.id, edge_type)
                    if key in existing_edges:
                        continue
                    shared_names = ", ".join(sorted(shared))
                    session.add(
                        KnowledgeEdge(
                            government_id=government.id,
                            from_entity_type=from_entity.entity_type,
                            from_entity_id=from_entity.id,
                            to_entity_type=to_entity.entity_type,
                            to_entity_id=to_entity.id,
                            edge_type=edge_type,
                            confidence=min(event_a.confidence, event_b.confidence, 0.6),
                            source_document_id=evidence_event.document_id,
                            explanation=(
                                f"Both records mention {shared_names}. The link is inferred "
                                "from shared institutional context, not from an explicit "
                                "cross-reference in the public record."
                            ),
                        )
                    )
                    existing_edges.add(key)
                    created += 1
        session.flush()
        return created
