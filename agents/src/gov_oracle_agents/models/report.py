"""Public Pydantic models returned by the agents library.

These are the contract between the agents library and any consumer
(the Flask backend, notebooks, other tools). Keep them stable.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

RunType = Literal["daily", "weekly", "manual"]
Importance = Literal["low", "medium", "high"]
Severity = Literal["low", "medium", "high", "critical"]
AnswerabilityStatus = Literal["answered", "partial", "failed"]


class EvidenceSource(BaseModel):
    title: str
    url: str
    source_type: str = "government"
    retrieved_at: datetime | None = None


class GovernmentNote(BaseModel):
    title: str
    category: str
    importance: Importance = "medium"
    summary: str
    analysis: str
    what_is_missing: str | None = None
    open_questions: list[str] = Field(default_factory=list)
    evidence: list[EvidenceSource] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class TransparencyScores(BaseModel):
    documentation: int = Field(ge=0, le=100)
    timeliness: int = Field(ge=0, le=100)
    accessibility: int = Field(ge=0, le=100)
    completeness: int = Field(ge=0, le=100)
    traceability: int = Field(ge=0, le=100)
    explainability: int = Field(ge=0, le=100)
    overall: int = Field(ge=0, le=100)


class ScoreExplanations(BaseModel):
    documentation: str
    timeliness: str
    accessibility: str
    completeness: str
    traceability: str
    explainability: str


class QuestionFinding(BaseModel):
    """One piece of concrete information backing (or partially backing) an answer."""

    title: str
    detail: str | None = None  # institution, event type, or other context
    amount: float | None = None
    currency: str | None = None
    date: datetime | None = None
    source_url: str | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class FailedQuestion(BaseModel):
    """A civic question attempt.

    Not just answerability: the agent produces its best answer with the
    findings behind it, so a human can verify the answer against the cited
    evidence. On partial/failed attempts, `findings` holds whatever partial
    information was found and `missing_data` states exactly what was absent.
    """

    question: str
    answerability_status: AnswerabilityStatus = "failed"
    answer: str | None = None
    findings: list[QuestionFinding] = Field(default_factory=list)
    evidence: list[EvidenceSource] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    reason_failed: str
    missing_data: list[str] = Field(default_factory=list)
    failed_step: str | None = None
    severity: Severity = "medium"
    recommendation: str | None = None


class SourceCoverage(BaseModel):
    sources_checked: int = 0
    sources_successful: int = 0
    sources_failed: int = 0
    new_documents_found: int = 0


class GovernmentReport(BaseModel):
    government: str
    country_code: str | None = None
    date: date
    run_type: RunType = "daily"
    executive_summary: str
    today_notes: list[GovernmentNote] = Field(default_factory=list)
    transparency_scores: TransparencyScores
    score_explanations: ScoreExplanations
    failed_questions: list[FailedQuestion] = Field(default_factory=list)
    source_coverage: SourceCoverage = Field(default_factory=SourceCoverage)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def summary(self) -> str:
        """Convenience alias so `report.summary` reads naturally."""
        return self.executive_summary
