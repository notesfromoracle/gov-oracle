"""Transparency Scoring Agent.

Six dimensions, each 0–100, each computed from observable signals collected
during this run, each with a plain-language explanation that cites the
numbers behind it. Scores are deterministic given the same collected data —
no LLM vibes in the scoring path. That keeps the benchmark auditable.

Scores measure information navigability, not government quality.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import ScoreExplanations, TransparencyScores
from ..storage import CivicEvent, Document, Government, KnowledgeEdge
from .failed_questions import QuestionResults
from .source_monitor import CrawlStats

# Document types a national government is expected to publish.
EXPECTED_DOC_TYPES = [
    "budget",
    "tender",
    "contract",
    "audit",
    "law",
    "policy",
    "statistics",
    "project report",
]

# Edges required to trace money end to end.
TRACE_CHAIN_EDGES = [
    "budget_funds_project",
    "project_has_tender",
    "tender_awarded_as_contract",
    "contract_paid_by",
]


def clamp(value: float) -> int:
    return max(0, min(100, round(value)))


@dataclass
class ScoringResult:
    scores: TransparencyScores
    explanations: ScoreExplanations


class TransparencyScoringAgent:
    def score(
        self,
        session: Session,
        government: Government,
        crawl_stats: CrawlStats,
        question_results: QuestionResults,
    ) -> ScoringResult:
        doc_types_found = set(
            session.scalars(
                select(Document.document_type)
                .where(Document.government_id == government.id)
                .distinct()
            )
        )
        total_documents = session.scalar(
            select(func.count(Document.id)).where(Document.government_id == government.id)
        ) or 0
        recent_documents = session.scalar(
            select(func.count(Document.id)).where(
                Document.government_id == government.id,
                Document.retrieved_at >= datetime.now(timezone.utc) - timedelta(days=30),
            )
        ) or 0
        dated_documents = session.scalar(
            select(func.count(Document.id)).where(
                Document.government_id == government.id,
                Document.published_at.is_not(None),
            )
        ) or 0
        edge_types_found = set(
            session.scalars(
                select(KnowledgeEdge.edge_type)
                .where(KnowledgeEdge.government_id == government.id)
                .distinct()
            )
        )
        event_count = session.scalar(
            select(func.count(CivicEvent.id)).where(CivicEvent.government_id == government.id)
        ) or 0

        # --- Documentation: expected doc-type coverage + volume ---------
        expected_found = [t for t in EXPECTED_DOC_TYPES if t in doc_types_found]
        expected_missing = [t for t in EXPECTED_DOC_TYPES if t not in doc_types_found]
        coverage_ratio = len(expected_found) / len(EXPECTED_DOC_TYPES)
        volume_bonus = min(total_documents, 20) / 20 * 20
        documentation = clamp(coverage_ratio * 80 + volume_bonus)
        documentation_expl = (
            f"Of {len(EXPECTED_DOC_TYPES)} expected public document categories, "
            f"{len(expected_found)} were found ({', '.join(expected_found) or 'none'}). "
            f"Missing: {', '.join(expected_missing) or 'none'}. "
            f"{total_documents} documents were collected in total. "
            "The score combines category coverage (80%) with document volume (20%)."
        )

        # --- Timeliness: recency of collected material -------------------
        recency_ratio = recent_documents / total_documents if total_documents else 0.0
        dated_ratio = dated_documents / total_documents if total_documents else 0.0
        timeliness = clamp(recency_ratio * 60 + dated_ratio * 40)
        timeliness_expl = (
            f"{recent_documents} of {total_documents} collected documents were retrieved as new or "
            f"changed within the last 30 days, and {dated_documents} carried an extractable "
            "publication date. Undated documents make publication delay unmeasurable, which "
            "lowers this score."
        )

        # --- Accessibility: can machines actually read the sources? -----
        reachable_ratio = (
            crawl_stats.sources_successful / crawl_stats.sources_checked
            if crawl_stats.sources_checked
            else 0.0
        )
        machine_ratio = (
            min(crawl_stats.machine_readable_hits / crawl_stats.pages_fetched, 1.0)
            if crawl_stats.pages_fetched
            else 0.0
        )
        scanned_ratio = (
            crawl_stats.scanned_pdfs / crawl_stats.pdf_documents
            if crawl_stats.pdf_documents
            else 0.0
        )
        ssl_ratio = (
            crawl_stats.ssl_invalid_pages / crawl_stats.pages_fetched
            if crawl_stats.pages_fetched
            else 0.0
        )
        accessibility = clamp(
            reachable_ratio * 55 + machine_ratio * 35 + (1 - scanned_ratio) * 10 - ssl_ratio * 10
        )
        browser_note = (
            f" {crawl_stats.browser_rescues} pages required a full browser to render "
            "(plain HTTP clients were blocked or served empty shells), which is an "
            "access barrier for automated analysis."
            if crawl_stats.browser_rescues
            else ""
        )
        pdf_note = (
            f" Of {crawl_stats.pdf_documents} PDFs collected, {crawl_stats.scanned_pdfs} "
            "were scanned images with no extractable text."
            if crawl_stats.pdf_documents
            else ""
        )
        ssl_note = (
            f" {crawl_stats.ssl_invalid_pages} pages were served with invalid TLS "
            "certificate chains and could only be read insecurely — a barrier for "
            "standard clients and a small deduction here."
            if crawl_stats.ssl_invalid_pages
            else ""
        )
        accessibility_expl = (
            f"Of {crawl_stats.sources_checked} known public sources checked, "
            f"{crawl_stats.sources_successful} responded successfully; across "
            f"{crawl_stats.pages_fetched} pages fetched (including "
            f"{crawl_stats.links_followed} followed links), "
            f"{crawl_stats.machine_readable_hits} returned machine-readable content "
            f"(HTML/CSV/JSON/XML or text-based PDF). {crawl_stats.sources_failed} sources "
            "were unreachable or returned errors; unreachable official sources are a "
            f"direct accessibility failure.{browser_note}{pdf_note}{ssl_note}"
        )

        # --- Completeness: is spending linked across records? ------------
        linkage_edges = [t for t in TRACE_CHAIN_EDGES if t in edge_types_found]
        linkage_ratio = len(linkage_edges) / len(TRACE_CHAIN_EDGES)
        event_bonus = min(event_count, 10) / 10 * 20
        completeness = clamp(linkage_ratio * 80 + event_bonus)
        completeness_expl = (
            f"Of the {len(TRACE_CHAIN_EDGES)} record linkages needed to connect budgets to "
            f"projects, tenders, contracts, and payments, {len(linkage_edges)} could be "
            f"established from public records ({', '.join(linkage_edges) or 'none'}). "
            f"{event_count} structured civic events were extracted. Missing linkages mean "
            "spending cannot be followed across records."
        )

        # --- Traceability: can money be followed end to end? -------------
        # Stricter than completeness: the full chain matters, not partial credit.
        chain_depth = 0
        for edge_type in TRACE_CHAIN_EDGES:
            if edge_type in edge_types_found:
                chain_depth += 1
            else:
                break
        traceability = clamp((chain_depth / len(TRACE_CHAIN_EDGES)) * 90 + (10 if event_count else 0))
        traced_desc = (
            f"The money trail could be followed {chain_depth} of {len(TRACE_CHAIN_EDGES)} steps "
            "(budget → project → tender → contract → payment) before the public record broke."
        )
        traceability_expl = (
            traced_desc + " Traceability requires an unbroken chain, so a single missing link "
            "(most often contract-to-payment) caps the score regardless of how much is "
            "published upstream."
        )

        # --- Explainability: could civic questions be answered? ----------
        answered = len(question_results.answered)
        partial = len(question_results.partial)
        failed = len(question_results.failed)
        total_questions = answered + partial + failed
        explainability = clamp(question_results.answer_rate * 100)
        explainability_expl = (
            f"The system attempted {total_questions} civic transparency questions. "
            f"It could answer {answered} from public records, partially answer {partial}, "
            f"and failed {failed} due to missing or unlinked public information. "
            "Partial answers count at half weight."
        )

        overall = clamp(
            (documentation + timeliness + accessibility + completeness + traceability + explainability) / 6
        )

        return ScoringResult(
            scores=TransparencyScores(
                documentation=documentation,
                timeliness=timeliness,
                accessibility=accessibility,
                completeness=completeness,
                traceability=traceability,
                explainability=explainability,
                overall=overall,
            ),
            explanations=ScoreExplanations(
                documentation=documentation_expl,
                timeliness=timeliness_expl,
                accessibility=accessibility_expl,
                completeness=completeness_expl,
                traceability=traceability_expl,
                explainability=explainability_expl,
            ),
        )
