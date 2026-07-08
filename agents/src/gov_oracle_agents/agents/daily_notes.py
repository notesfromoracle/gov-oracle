"""Daily Notes Agent.

Produces public-facing notes: what happened, why it matters, what evidence
supports it, what is missing, what questions remain. Tone rules are enforced
structurally — notes are assembled from observed facts and gaps, then the
narrative analysis is written by the LLM abstraction (or its deterministic
fallback), which is instructed to stay calm, non-partisan, and evidence-bound.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..llm import LLMClient
from ..models import EvidenceSource, GovernmentNote
from ..storage import CivicEvent, Document, Government
from .failed_questions import QuestionResults
from .source_monitor import CrawlStats

EVENT_CATEGORY = {
    "budget_allocation": "budget",
    "budget_revision": "budget",
    "procurement_notice": "procurement",
    "contract_award": "procurement",
    "audit_objection": "audit",
    "law_passed": "legal",
    "policy_announcement": "policy",
    "spending_report": "statistics",
    "project_status": "infrastructure",
    "public_service_alert": "public_services",
}

EVENT_IMPORTANCE = {
    "contract_award": "high",
    "audit_objection": "high",
    "budget_allocation": "medium",
    "procurement_notice": "medium",
    "law_passed": "medium",
}


class DailyNotesAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def generate(
        self,
        session: Session,
        government: Government,
        crawl_stats: CrawlStats,
        question_results: QuestionResults,
        max_notes: int = 8,
    ) -> list[GovernmentNote]:
        notes: list[GovernmentNote] = []
        recent_cutoff = datetime.now(timezone.utc) - timedelta(days=7)

        events = session.scalars(
            select(CivicEvent)
            .where(
                CivicEvent.government_id == government.id,
                CivicEvent.created_at >= recent_cutoff,
            )
            .order_by(CivicEvent.confidence.desc())
            .limit(max_notes)
        ).all()

        for event in events:
            notes.append(self._note_from_event(session, event))

        # Coverage gaps are findings too — surface them even on quiet days.
        if crawl_stats.sources_failed > 0:
            notes.append(self._note_from_failures(crawl_stats))
        critical_failures = [
            q for q in question_results.failed if q.severity in ("high", "critical")
        ]
        if critical_failures:
            notes.append(self._note_from_failed_questions(critical_failures))

        return notes[: max_notes + 2]

    def _note_from_event(self, session: Session, event: CivicEvent) -> GovernmentNote:
        document = (
            session.get(Document, event.document_id) if event.document_id is not None else None
        )
        evidence = []
        if document is not None and document.url:
            evidence.append(
                EvidenceSource(
                    title=document.title,
                    url=document.url,
                    source_type="government",
                    retrieved_at=document.retrieved_at,
                )
            )

        event_label = event.event_type.replace("_", " ")
        what_happened = (
            f"A {event_label} record was captured from monitored public sources: "
            f"{event.title[:200]}."
        )
        if event.amount:
            what_happened += f" An associated amount of {event.amount:,.0f} {event.currency or ''} was detected in the text."
        why_it_matters = (
            "Records of this type are a primary input for tracing public spending and "
            "policy activity."
        )
        what_is_missing = None
        if not evidence:
            what_is_missing = "The record could not be tied to a stable public URL."
        elif event.confidence < 0.6:
            what_is_missing = (
                "Classification confidence is moderate; the document's type and details "
                "have not been confirmed against a second public record."
            )

        analysis = self.llm.complete_text(
            task="note_analysis",
            instructions=(
                "Write a calm, non-partisan, evidence-bound analysis paragraph for a civic "
                "transparency note. State facts, separate inference, never allege wrongdoing. "
                "Note explicitly what is missing from the public record."
            ),
            payload={
                "what_happened": what_happened,
                "why_it_matters": why_it_matters,
                "what_is_missing": what_is_missing,
            },
        )

        return GovernmentNote(
            title=f"{event_label.capitalize()}: {event.title[:120]}",
            category=EVENT_CATEGORY.get(event.event_type, "general"),
            importance=EVENT_IMPORTANCE.get(event.event_type, "medium"),  # type: ignore[arg-type]
            summary=what_happened,
            analysis=analysis,
            what_is_missing=what_is_missing,
            open_questions=[],
            evidence=evidence,
            confidence=event.confidence,
        )

    def _note_from_failures(self, crawl_stats: CrawlStats) -> GovernmentNote:
        failed = crawl_stats.sources_failed
        checked = crawl_stats.sources_checked
        summary = (
            f"{failed} of {checked} monitored official sources were unreachable or returned "
            "errors during this run."
        )
        analysis = self.llm.complete_text(
            task="note_analysis",
            instructions="Calm, factual analysis of source availability for a transparency note.",
            payload={
                "what_happened": summary,
                "why_it_matters": (
                    "When official sources are unavailable, public information cannot be "
                    "independently verified, which lowers the accessibility score."
                ),
                "what_is_missing": "Stable, reliably available official web sources.",
            },
        )
        return GovernmentNote(
            title="Some official sources were unavailable",
            category="accessibility",
            importance="medium",
            summary=summary,
            analysis=analysis,
            what_is_missing="; ".join(crawl_stats.failure_reasons[:5]) or None,
            evidence=[],
            confidence=0.9,  # the failure itself is directly observed
        )

    def _note_from_failed_questions(self, critical_failures) -> GovernmentNote:
        questions = [q.question for q in critical_failures[:4]]
        missing = sorted({item for q in critical_failures for item in q.missing_data})[:6]
        summary = (
            f"{len(critical_failures)} high-priority civic questions could not be answered "
            "from public records in this run."
        )
        analysis = self.llm.complete_text(
            task="note_analysis",
            instructions="Calm, factual analysis of unanswerable civic questions.",
            payload={
                "what_happened": summary,
                "why_it_matters": (
                    "These questions represent things a citizen should be able to learn from "
                    "public information without insider access."
                ),
                "what_is_missing": "; ".join(missing) + ".",
            },
        )
        return GovernmentNote(
            title="High-priority civic questions remain unanswerable",
            category="explainability",
            importance="high",
            summary=summary,
            analysis=analysis,
            what_is_missing="; ".join(missing),
            open_questions=questions,
            evidence=[],
            confidence=0.9,
        )
