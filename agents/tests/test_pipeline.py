"""End-to-end pipeline test, fully offline.

Runs the oracle with crawling disabled, then injects synthetic documents to
verify extraction, events, linking, question answering, and scoring react to
data — and that reports are append-only.
"""
from __future__ import annotations

from gov_oracle_agents.agents import (
    CivicEventExtractionAgent,
    CrawlStats,
    DocumentExtractionAgent,
    FailedQuestionsAgent,
    KnowledgeGraphAgent,
    TransparencyScoringAgent,
)
from gov_oracle_agents.llm import RuleBasedAnalyst
from gov_oracle_agents.oracle import GovernmentOracle
from gov_oracle_agents.storage import (
    CivicEvent,
    Document,
    Government,
    KnowledgeEdge,
    Report,
    Source,
    session_scope,
)


def run_oracle(settings):
    oracle = GovernmentOracle(settings=settings, llm=RuleBasedAnalyst())
    return oracle, oracle.run_government_report("Government of Bangladesh")


def test_offline_run_produces_valid_report(settings):
    _, report = run_oracle(settings)
    assert report.government == "Government of Bangladesh"
    assert report.country_code == "BD"
    assert 0 <= report.transparency_scores.overall <= 100
    # every score has a non-empty explanation
    for dim in ("documentation", "timeliness", "accessibility", "completeness", "traceability", "explainability"):
        assert len(getattr(report.score_explanations, dim)) > 20
    # with no crawl data, the civic question bank should mostly fail — missing data is a finding
    failed = [q for q in report.failed_questions if q.answerability_status == "failed"]
    assert len(failed) > 0
    assert all(q.missing_data for q in failed)
    assert report.metadata["llm_provider"] == "rule-based"


def test_reports_are_append_only(settings):
    oracle, _ = run_oracle(settings)
    oracle.run_government_report("Government of Bangladesh")
    with session_scope(settings.database_url) as session:
        reports = session.query(Report).all()
        assert len(reports) == 2
        assert reports[0].id != reports[1].id


def test_sources_and_institutions_seeded(settings):
    run_oracle(settings)
    with session_scope(settings.database_url) as session:
        gov = session.query(Government).one()
        sources = session.query(Source).filter_by(government_id=gov.id).all()
        assert len(sources) >= 10
        assert any(s.source_type == "procurement" for s in sources)
        assert any(s.source_type == "audit" for s in sources)


def test_documents_flow_into_events_edges_and_scores(settings):
    oracle, baseline = run_oracle(settings)
    analyst = RuleBasedAnalyst()

    with session_scope(settings.database_url) as session:
        gov = session.query(Government).one()
        source = session.query(Source).filter_by(government_id=gov.id).first()
        session.add_all(
            [
                Document(
                    government_id=gov.id,
                    source_id=source.id,
                    title="Annual budget allocation for health sector FY2026",
                    url="https://mof.example.gov.bd/budget-2026",
                    document_type="unknown",
                    content_hash="hash-budget",
                    raw_text=(
                        "The annual development budget allocation for the health sector is "
                        "Tk 500 crore for fiscal year 2026. Ministry of Health and Family "
                        "Welfare will implement the hospital modernization project."
                    ),
                ),
                Document(
                    government_id=gov.id,
                    source_id=source.id,
                    title="Contract award: hospital equipment procurement",
                    url="https://bppa.example.gov.bd/award-77",
                    document_type="unknown",
                    content_hash="hash-contract",
                    raw_text=(
                        "Notification of award: the contract for hospital equipment was "
                        "awarded to MedSupply Ltd for Tk 40 crore. Ministry of Health and "
                        "Family Welfare procurement under the hospital modernization project."
                    ),
                ),
            ]
        )
        session.flush()

        DocumentExtractionAgent(analyst).process_new_documents(session, gov)
        CivicEventExtractionAgent().extract(session, gov)
        KnowledgeGraphAgent().link(session, gov)

        docs = session.query(Document).filter(Document.content_hash.like("hash-%")).all()
        types = {d.document_type for d in docs}
        assert "budget" in types
        assert "contract" in types
        budget_doc = next(d for d in docs if d.document_type == "budget")
        assert budget_doc.metadata_json["amounts"][0]["value"] == 500 * 10_000_000
        assert "Ministry of Health and Family Welfare" in budget_doc.metadata_json["institutions_mentioned"]

        events = session.query(CivicEvent).filter_by(government_id=gov.id).all()
        event_types = {e.event_type for e in events}
        assert "budget_allocation" in event_types
        assert "contract_award" in event_types

        edges = session.query(KnowledgeEdge).filter_by(government_id=gov.id).all()
        assert len(edges) > 0
        assert all(e.explanation for e in edges)
        assert all(e.source_document_id is not None for e in edges)

        results = FailedQuestionsAgent().attempt_questions(session, gov)
        assert len(results.answered) + len(results.partial) > 0

        # answered questions must display a verifiable answer built from findings
        vendor_q = next(
            q for q in results.all_attempted if q.question.startswith("Which vendors won")
        )
        assert vendor_q.answerability_status == "answered"
        assert vendor_q.answer and "hospital equipment" in vendor_q.answer.lower()
        assert vendor_q.findings and vendor_q.findings[0].amount == 40 * 10_000_000
        assert vendor_q.evidence and vendor_q.evidence[0].url.startswith("https://")
        assert 0 < vendor_q.confidence <= 0.6  # rule-based answers are capped

        # partial/failed questions with related records must show them as partial info
        for q in results.partial:
            if q.findings:
                assert q.answer and "partial" in q.answer.lower()
                assert q.confidence <= 0.5
        for q in results.failed:
            if not q.findings:
                assert q.answer is None

        scoring = TransparencyScoringAgent().score(
            session, gov, CrawlStats(sources_checked=10, sources_successful=8, machine_readable_hits=8), results
        )
        assert scoring.scores.documentation > baseline.transparency_scores.documentation
        assert scoring.scores.explainability > baseline.transparency_scores.explainability


def test_run_alias_matches_readme_usage(settings):
    oracle = GovernmentOracle(settings=settings, llm=RuleBasedAnalyst())
    report = oracle.run("Government of Bangladesh")
    assert report.summary  # `.summary` property per README example
