import json
from datetime import date

import pytest
from pydantic import ValidationError

from gov_oracle_agents.models import (
    EvidenceSource,
    FailedQuestion,
    GovernmentNote,
    GovernmentReport,
    ScoreExplanations,
    SourceCoverage,
    TransparencyScores,
)


def make_scores(**overrides) -> TransparencyScores:
    values = dict(
        documentation=71,
        timeliness=58,
        accessibility=44,
        completeness=39,
        traceability=31,
        explainability=47,
        overall=48,
    )
    values.update(overrides)
    return TransparencyScores(**values)


def test_report_round_trips_through_json():
    report = GovernmentReport(
        government="Government of Bangladesh",
        country_code="BD",
        date=date(2026, 7, 4),
        run_type="daily",
        executive_summary="Summary.",
        today_notes=[
            GovernmentNote(
                title="New procurement notice found in health sector",
                category="procurement",
                importance="medium",
                summary="s",
                analysis="a",
                evidence=[
                    EvidenceSource(
                        title="Official procurement notice",
                        url="https://example.gov/notice",
                    )
                ],
                confidence=0.82,
            )
        ],
        transparency_scores=make_scores(),
        score_explanations=ScoreExplanations(
            documentation="d", timeliness="t", accessibility="a",
            completeness="c", traceability="tr", explainability="e",
        ),
        failed_questions=[
            FailedQuestion(
                question="Which vendors received payments?",
                reason_failed="Payment records not linked.",
                missing_data=["payment records"],
                severity="high",
            )
        ],
        source_coverage=SourceCoverage(sources_checked=42, sources_successful=31),
    )
    payload = json.loads(json.dumps(report.model_dump(mode="json")))
    restored = GovernmentReport.model_validate(payload)
    assert restored.government == "Government of Bangladesh"
    assert restored.summary == "Summary."
    assert restored.transparency_scores.overall == 48
    assert restored.today_notes[0].evidence[0].url == "https://example.gov/notice"


def test_scores_reject_out_of_range():
    with pytest.raises(ValidationError):
        make_scores(documentation=101)
    with pytest.raises(ValidationError):
        make_scores(traceability=-1)


def test_note_confidence_bounds():
    with pytest.raises(ValidationError):
        GovernmentNote(title="t", category="c", summary="s", analysis="a", confidence=1.5)
