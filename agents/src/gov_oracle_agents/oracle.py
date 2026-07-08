"""GovernmentOracle — the public entry point of the agents library.

Orchestrates the full pipeline:
  resolve → discover sources → crawl → extract documents → extract events
  → link knowledge graph → attempt civic questions → score → write notes
  → persist report (append-only; old reports are never overwritten).
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from .agents import (
    CivicEventExtractionAgent,
    DailyNotesAgent,
    DocumentExtractionAgent,
    FailedQuestionsAgent,
    GovernmentResolverAgent,
    KnowledgeGraphAgent,
    SourceDiscoveryAgent,
    SourceMonitorAgent,
    TransparencyScoringAgent,
)
from .config import Settings, get_settings
from .llm import LLMClient, get_llm_client
from .models import GovernmentReport, SourceCoverage
from .storage import (
    AgentRun,
    FailedQuestionRow,
    Report,
    ReportNote,
    TransparencyScoreRow,
    init_db,
    session_scope,
)

logger = logging.getLogger("gov_oracle_agents")


class GovernmentOracle:
    def __init__(self, settings: Settings | None = None, llm: LLMClient | None = None):
        self.settings = settings or get_settings()
        self.llm = llm or get_llm_client(self.settings)
        init_db(self.settings.database_url)

    def run(self, government_name: str, run_type: str = "daily") -> GovernmentReport:
        """Alias matching the README usage: oracle.run("Government of Bangladesh")."""
        return self.run_government_report(government_name=government_name, run_type=run_type)

    def run_government_report(
        self,
        government_name: str,
        run_type: str = "daily",
        country_code: str | None = None,
        jurisdiction_type: str = "national",
        focus_areas: list[str] | None = None,
        language: str = "en",
        max_sources: int | None = None,
        depth: str = "standard",
    ) -> GovernmentReport:
        if max_sources is not None:
            self.settings.crawl_max_sources = max_sources

        with session_scope(self.settings.database_url) as session:
            resolver = GovernmentResolverAgent()
            government = resolver.resolve(
                session, government_name, country_code, jurisdiction_type
            )

            run = AgentRun(government_id=government.id, run_type=run_type, status="running")
            session.add(run)
            session.flush()

            try:
                sources = SourceDiscoveryAgent().discover(session, government)
                logger.info("Discovered %d sources for %s", len(sources), government.name)

                crawl_stats = SourceMonitorAgent(self.settings, llm=self.llm).crawl(
                    session, sources, run_id=run.id
                )
                logger.info(
                    "Crawl: %d checked, %d ok, %d failed, %d new documents",
                    crawl_stats.sources_checked,
                    crawl_stats.sources_successful,
                    crawl_stats.sources_failed,
                    crawl_stats.new_documents_found,
                )

                DocumentExtractionAgent(self.llm).process_new_documents(session, government)
                CivicEventExtractionAgent().extract(session, government)
                KnowledgeGraphAgent().link(session, government)

                question_results = FailedQuestionsAgent(self.llm).attempt_questions(session, government)
                scoring = TransparencyScoringAgent().score(
                    session, government, crawl_stats, question_results
                )
                notes = DailyNotesAgent(self.llm).generate(
                    session, government, crawl_stats, question_results
                )

                executive_summary = self.llm.complete_text(
                    task="executive_summary",
                    instructions=(
                        "Write a 4-6 sentence executive summary of this transparency audit run. "
                        "Calm, non-partisan, evidence-bound. Emphasize what could and could not "
                        "be learned from public information."
                    ),
                    payload={
                        "government": government.name,
                        "source_coverage": crawl_stats.__dict__,
                        "scores": scoring.scores.model_dump(),
                        "failed_question_count": len(question_results.failed),
                        "answered_question_count": len(question_results.answered),
                    },
                )

                report = GovernmentReport(
                    government=government.name,
                    country_code=government.country_code,
                    date=date.today(),
                    run_type=run_type,  # type: ignore[arg-type]
                    executive_summary=executive_summary,
                    today_notes=notes,
                    transparency_scores=scoring.scores,
                    score_explanations=scoring.explanations,
                    failed_questions=question_results.all_attempted,
                    source_coverage=SourceCoverage(
                        sources_checked=crawl_stats.sources_checked,
                        sources_successful=crawl_stats.sources_successful,
                        sources_failed=crawl_stats.sources_failed,
                        new_documents_found=crawl_stats.new_documents_found,
                    ),
                    metadata={
                        "llm_provider": self.llm.name,
                        # cumulative per-process counters (ResilientLLMClient only)
                        "llm_primary_calls": getattr(self.llm, "primary_calls", None),
                        "llm_fallback_calls": getattr(self.llm, "fallback_calls", None),
                        "depth": depth,
                        "language": language,
                        "focus_areas": focus_areas or [],
                        "crawl": {
                            "pages_fetched": crawl_stats.pages_fetched,
                            "links_followed": crawl_stats.links_followed,
                            "browser_rescues": crawl_stats.browser_rescues,
                            "pdf_documents": crawl_stats.pdf_documents,
                            "scanned_pdfs": crawl_stats.scanned_pdfs,
                            "ssl_invalid_pages": crawl_stats.ssl_invalid_pages,
                        },
                    },
                )

                self._persist_report(session, government.id, run, report)
                run.status = "succeeded"
                run.finished_at = datetime.now(timezone.utc)
                run.stats_json = {
                    "sources_checked": crawl_stats.sources_checked,
                    "new_documents": crawl_stats.new_documents_found,
                    "notes": len(notes),
                }
                return report
            except Exception as exc:
                run.status = "failed"
                run.finished_at = datetime.now(timezone.utc)
                run.error = str(exc)[:4000]
                session.flush()
                raise

    @staticmethod
    def _persist_report(session, government_id: int, run: AgentRun, report: GovernmentReport) -> None:
        row = Report(
            government_id=government_id,
            run_id=run.id,
            report_date=report.date,
            run_type=report.run_type,
            executive_summary=report.executive_summary,
            overall_score=report.transparency_scores.overall,
            report_json=report.model_dump(mode="json"),
        )
        session.add(row)
        session.flush()

        for note in report.today_notes:
            session.add(
                ReportNote(
                    report_id=row.id,
                    title=note.title[:500],
                    category=note.category,
                    importance=note.importance,
                    summary=note.summary,
                    analysis=note.analysis,
                    confidence=note.confidence,
                    evidence_json=[e.model_dump(mode="json") for e in note.evidence],
                )
            )
        scores = report.transparency_scores
        session.add(
            TransparencyScoreRow(
                report_id=row.id,
                documentation=scores.documentation,
                timeliness=scores.timeliness,
                accessibility=scores.accessibility,
                completeness=scores.completeness,
                traceability=scores.traceability,
                explainability=scores.explainability,
                overall=scores.overall,
                explanations_json=report.score_explanations.model_dump(),
            )
        )
        for question in report.failed_questions:
            session.add(
                FailedQuestionRow(
                    report_id=row.id,
                    question=question.question,
                    status=question.answerability_status,
                    answer=question.answer,
                    findings_json=[f.model_dump(mode="json") for f in question.findings],
                    evidence_json=[e.model_dump(mode="json") for e in question.evidence],
                    confidence=question.confidence,
                    reason_failed=question.reason_failed or None,
                    missing_data_json=question.missing_data,
                    failed_step=question.failed_step,
                    severity=question.severity,
                    recommendation=question.recommendation,
                )
            )
