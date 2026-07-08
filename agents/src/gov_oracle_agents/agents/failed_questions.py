"""Civic Questions Agent — the heart of the benchmark.

For each question in a canonical bank the agent does three things:

  1. Checks whether the evidence the question requires exists (document
     types, event types, record linkages) — this determines answerability.
  2. Gathers the concrete findings that bear on the question (events with
     amounts, dates, institutions, and source URLs).
  3. Synthesizes an actual answer from those findings — via the configured
     LLM, or a deterministic enumeration offline — so a human can read the
     answer and verify it against the cited evidence.

Honesty rules:
  - The answer is built ONLY from gathered findings; missing data is stated,
    never papered over.
  - If records of the right type exist but none match the question's
    specific topic (e.g. project reports exist but none mention delays), the
    status is capped at "partial" — related information is displayed, but no
    answer is claimed.
  - Failed questions still display whatever partial findings exist, plus
    exactly what data was missing. That record IS the product.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..llm import LLMClient, RuleBasedAnalyst
from ..models import EvidenceSource, FailedQuestion, QuestionFinding
from ..storage import CivicEvent, Document, Government, KnowledgeEdge


@dataclass
class CivicQuestion:
    question: str
    required_document_types: list[str]
    required_event_types: list[str]
    required_edge_types: list[str]
    missing_data_labels: list[str]
    severity: str
    recommendation: str
    # topical filter: when set, at least one finding must match a keyword
    # for the question to count as fully answered
    keywords: list[str] = field(default_factory=list)


QUESTION_BANK: list[CivicQuestion] = [
    CivicQuestion(
        question="Where did the health ministry's development budget go this quarter?",
        required_document_types=["budget"],
        required_event_types=["budget_allocation"],
        required_edge_types=["budget_funds_project"],
        missing_data_labels=["quarterly budget execution reports", "budget-to-project linkage"],
        severity="high",
        recommendation="Publish quarterly budget execution data linked to named projects in machine-readable form.",
        keywords=["health", "hospital", "medical"],
    ),
    CivicQuestion(
        question="Which vendors won the largest public contracts this month?",
        required_document_types=["contract"],
        required_event_types=["contract_award"],
        required_edge_types=[],
        missing_data_labels=["contract award notices with vendor names and amounts"],
        severity="high",
        recommendation="Publish contract award notices with vendor, amount, and date on a stable public page.",
    ),
    CivicQuestion(
        question="Can procurement awards be linked to actual payments?",
        required_document_types=["contract"],
        required_event_types=["contract_award"],
        required_edge_types=["contract_paid_by"],
        missing_data_labels=["payment records", "contract-to-payment linkage"],
        severity="critical",
        recommendation="Publish payment records referencing contract identifiers so awards can be reconciled with disbursements.",
    ),
    CivicQuestion(
        question="Which infrastructure projects are currently delayed?",
        required_document_types=["project report"],
        required_event_types=["project_status"],
        required_edge_types=[],
        missing_data_labels=["project implementation status reports"],
        severity="medium",
        recommendation="Publish project-level implementation monitoring reports on a regular schedule.",
        keywords=["delay", "delayed", "behind schedule", "time extension", "revised deadline"],
    ),
    CivicQuestion(
        question="Which programs received budget increases in the latest budget?",
        required_document_types=["budget"],
        required_event_types=["budget_allocation"],
        required_edge_types=[],
        missing_data_labels=["program-level budget tables in machine-readable format"],
        severity="medium",
        recommendation="Release budget tables as CSV/Excel with program-level line items and prior-year comparisons.",
        keywords=["increase", "increased", "additional", "supplementary", "revised upward"],
    ),
    CivicQuestion(
        question="What did the auditor general object to in the most recent audit cycle?",
        required_document_types=["audit"],
        required_event_types=["audit_objection"],
        required_edge_types=[],
        missing_data_labels=["published audit reports"],
        severity="high",
        recommendation="Publish full audit reports, including objections and agency responses.",
    ),
    CivicQuestion(
        question="Which agencies have not published required periodic reports recently?",
        required_document_types=["project report", "statistics"],
        required_event_types=[],
        required_edge_types=[],
        missing_data_labels=["publication calendars", "agency reporting compliance data"],
        severity="medium",
        recommendation="Maintain a public publication calendar so missing reports are detectable.",
    ),
    CivicQuestion(
        question="Can a budget allocation be followed to a completed public asset or outcome?",
        required_document_types=["budget", "project report"],
        required_event_types=["budget_allocation", "project_status"],
        required_edge_types=["budget_funds_project", "contract_relates_to_project"],
        missing_data_labels=["outcome reporting", "asset registers", "full spending chain linkage"],
        severity="critical",
        recommendation="Link budget lines, projects, contracts, and completion reports with shared identifiers.",
    ),
]

MAX_FINDINGS = 5


@dataclass
class QuestionResults:
    answered: list[FailedQuestion]
    partial: list[FailedQuestion]
    failed: list[FailedQuestion]

    @property
    def all_attempted(self) -> list[FailedQuestion]:
        return self.answered + self.partial + self.failed

    @property
    def answer_rate(self) -> float:
        total = len(self.all_attempted)
        if total == 0:
            return 0.0
        return (len(self.answered) + 0.5 * len(self.partial)) / total


class FailedQuestionsAgent:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or RuleBasedAnalyst()

    def attempt_questions(self, session: Session, government: Government) -> QuestionResults:
        doc_types = set(
            session.scalars(
                select(Document.document_type).where(Document.government_id == government.id).distinct()
            )
        )
        event_types = set(
            session.scalars(
                select(CivicEvent.event_type).where(CivicEvent.government_id == government.id).distinct()
            )
        )
        edge_types = set(
            session.scalars(
                select(KnowledgeEdge.edge_type).where(KnowledgeEdge.government_id == government.id).distinct()
            )
        )

        results = QuestionResults(answered=[], partial=[], failed=[])
        for q in QUESTION_BANK:
            attempt = self._attempt(session, government, q, doc_types, event_types, edge_types)
            if attempt.answerability_status == "answered":
                results.answered.append(attempt)
            elif attempt.answerability_status == "partial":
                results.partial.append(attempt)
            else:
                results.failed.append(attempt)
        return results

    # --- single question ---------------------------------------------------

    def _attempt(
        self,
        session: Session,
        government: Government,
        q: CivicQuestion,
        doc_types: set[str],
        event_types: set[str],
        edge_types: set[str],
    ) -> FailedQuestion:
        # 1. requirement coverage → provisional status
        missing: list[str] = []
        failed_step = None
        missing_docs = [d for d in q.required_document_types if d not in doc_types]
        if missing_docs:
            missing.extend(f"published {d} documents" for d in missing_docs)
            failed_step = failed_step or "document_collection"
        missing_events = [e for e in q.required_event_types if e not in event_types]
        if missing_events:
            missing.extend(f"{e.replace('_', ' ')} records" for e in missing_events)
            failed_step = failed_step or "event_extraction"
        missing_edges = [e for e in q.required_edge_types if e not in edge_types]
        if missing_edges:
            missing.extend(q.missing_data_labels)
            failed_step = failed_step or "record_linkage"

        requirement_count = (
            len(q.required_document_types) + len(q.required_event_types) + len(q.required_edge_types)
        )
        missing_count = len(missing_docs) + len(missing_events) + len(missing_edges)
        if missing_count == 0:
            status = "answered"
        elif missing_count < requirement_count:
            status = "partial"
        else:
            status = "failed"

        # 2. gather concrete findings (also for partial/failed — partial info matters)
        findings, evidence, keyword_hit = self._gather_findings(session, government, q)

        # 3. topical honesty cap: right record types but wrong topic → partial
        if status == "answered" and q.keywords and not keyword_hit:
            status = "partial"
            missing = list(
                dict.fromkeys(
                    missing
                    + [
                        f"records specifically matching the question topic "
                        f"({', '.join(q.keywords[:3])})"
                    ]
                )
            )
            failed_step = failed_step or "topical_match"

        # 4. synthesize the answer from findings only
        answer, confidence = self._synthesize_answer(q, status, findings, missing)

        # 5. content honesty cap: if the analyst's own answer says the findings
        # lack the asked-for specifics (very low confidence), the question is
        # not answered, whatever the type-level evidence suggested. Synthesis
        # can only downgrade a status, never upgrade one — a model can make
        # the benchmark more conservative but never inflate it.
        if status == "answered" and confidence < 0.35:
            status = "partial"
            missing = list(
                dict.fromkeys(
                    missing + ["records containing the specific details the question asks for"]
                )
            )
            failed_step = failed_step or "content_sufficiency"

        reason_failed = ""
        if status == "partial":
            reason_failed = (
                "Some supporting records were found, but the public record is incomplete: "
                + "; ".join(dict.fromkeys(missing)) + "."
            )
        elif status == "failed":
            reason_failed = (
                "The required public records could not be found or could not be connected: "
                + "; ".join(dict.fromkeys(missing)) + "."
            )

        return FailedQuestion(
            question=q.question,
            answerability_status=status,  # type: ignore[arg-type]
            answer=answer,
            findings=findings,
            evidence=evidence,
            confidence=confidence,
            reason_failed=reason_failed,
            missing_data=list(dict.fromkeys(missing)),
            failed_step=failed_step if status != "answered" else None,
            severity=q.severity,  # type: ignore[arg-type]
            recommendation=q.recommendation if status != "answered" else None,
        )

    def _gather_findings(
        self, session: Session, government: Government, q: CivicQuestion
    ) -> tuple[list[QuestionFinding], list[EvidenceSource], bool]:
        """Collect concrete records bearing on the question.

        Returns (findings, evidence, keyword_hit). Findings prefer events of
        the required types; documents of required types are the fallback so
        even extraction failures leave verifiable partial information.
        """
        candidates: list[QuestionFinding] = []
        doc_ids: list[int] = []

        if q.required_event_types:
            events = session.scalars(
                select(CivicEvent)
                .where(
                    CivicEvent.government_id == government.id,
                    CivicEvent.event_type.in_(q.required_event_types),
                )
                # is_(None) ascending puts amounts first (MySQL lacks NULLS LAST)
                .order_by(CivicEvent.amount.is_(None), CivicEvent.amount.desc(), CivicEvent.confidence.desc())
                .limit(MAX_FINDINGS * 4)
            ).all()
            for event in events:
                candidates.append(
                    QuestionFinding(
                        title=event.title[:300],
                        detail=event.institution_name or event.event_type.replace("_", " "),
                        amount=event.amount,
                        currency=event.currency,
                        date=event.event_date,
                        confidence=event.confidence,
                    )
                )
                doc_ids.append(event.document_id)

        if not candidates and q.required_document_types:
            documents = session.scalars(
                select(Document)
                .where(
                    Document.government_id == government.id,
                    Document.document_type.in_(q.required_document_types),
                )
                .order_by(Document.retrieved_at.desc())
                .limit(MAX_FINDINGS * 4)
            ).all()
            for document in documents:
                candidates.append(
                    QuestionFinding(
                        title=document.title[:300],
                        detail=document.document_type,
                        date=document.published_at or document.retrieved_at,
                        source_url=document.url,
                        confidence=0.4,
                    )
                )
                doc_ids.append(document.id)

        # topical filter: matched findings first
        keyword_hit = False
        if q.keywords:
            matched, unmatched = [], []
            for finding, doc_id in zip(candidates, doc_ids):
                haystack = f"{finding.title} {finding.detail or ''}".lower()
                (matched if any(k in haystack for k in q.keywords) else unmatched).append(
                    (finding, doc_id)
                )
            keyword_hit = bool(matched)
            ordered = matched + unmatched
        else:
            keyword_hit = bool(candidates)
            ordered = list(zip(candidates, doc_ids))

        findings = [f for f, _ in ordered[:MAX_FINDINGS]]
        # attach source URLs + evidence from the backing documents
        evidence: list[EvidenceSource] = []
        seen_urls: set[str] = set()
        for finding, doc_id in ordered[:MAX_FINDINGS]:
            document = session.get(Document, doc_id) if doc_id is not None else None
            if document is None or not document.url:
                continue
            if finding.source_url is None:
                finding.source_url = document.url
            if document.url not in seen_urls:
                seen_urls.add(document.url)
                evidence.append(
                    EvidenceSource(
                        title=document.title[:300],
                        url=document.url,
                        source_type="government",
                        retrieved_at=document.retrieved_at,
                    )
                )
        return findings, evidence, keyword_hit

    def _synthesize_answer(
        self,
        q: CivicQuestion,
        status: str,
        findings: list[QuestionFinding],
        missing: list[str],
    ) -> tuple[str | None, float]:
        if not findings:
            return None, 0.0
        payload = {
            "question": q.question,
            "answerability_status": status,
            "findings": [f.model_dump(mode="json") for f in findings],
            "missing_data": missing,
        }
        response = self.llm.complete_json(
            task="answer_civic_question",
            instructions=(
                "Answer the civic question using ONLY the provided findings — never invent "
                "vendors, amounts, dates, or institutions. If the findings only partially "
                "answer the question, say precisely what can and cannot be concluded and "
                "why (see missing_data). Cite finding titles inline so a human can verify "
                'each claim. Return {"answer": "...", "confidence": 0.0-1.0}.'
            ),
            payload=payload,
        )
        answer = response.get("answer")
        if not answer:
            return None, 0.0
        try:
            confidence = min(max(float(response.get("confidence", 0.3)), 0.0), 1.0)
        except (TypeError, ValueError):
            confidence = 0.3
        if status != "answered":
            confidence = min(confidence, 0.5)  # partial info can never be high-confidence
        return str(answer), confidence
