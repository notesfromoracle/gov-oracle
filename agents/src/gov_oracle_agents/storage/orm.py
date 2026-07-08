"""SQLAlchemy models for the gov-oracle schema.

This module is the single owner of the database schema. The Flask backend
imports these models instead of redefining them. Works on MySQL (production)
and SQLite (local demo / tests).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# raw document text can exceed MySQL TEXT's 64KB; keep SQLite plain Text
LongText = Text().with_variant(LONGTEXT(), "mysql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Government(TimestampMixin, Base):
    __tablename__ = "governments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    country_code: Mapped[str | None] = mapped_column(String(8))
    jurisdiction_type: Mapped[str] = mapped_column(String(32), default="national")
    description: Mapped[str | None] = mapped_column(Text)

    institutions: Mapped[list["Institution"]] = relationship(back_populates="government")
    sources: Mapped[list["Source"]] = relationship(back_populates="government")
    reports: Mapped[list["Report"]] = relationship(back_populates="government")


class Institution(TimestampMixin, Base):
    __tablename__ = "institutions"
    __table_args__ = (UniqueConstraint("government_id", "name", name="uq_institution_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    government_id: Mapped[int] = mapped_column(ForeignKey("governments.id"))
    name: Mapped[str] = mapped_column(String(255))
    institution_type: Mapped[str] = mapped_column(String(64), default="ministry")
    website_url: Mapped[str | None] = mapped_column(String(1024))

    government: Mapped[Government] = relationship(back_populates="institutions")


class Source(TimestampMixin, Base):
    __tablename__ = "sources"
    __table_args__ = (UniqueConstraint("government_id", "url", name="uq_source_url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    government_id: Mapped[int] = mapped_column(ForeignKey("governments.id"))
    institution_id: Mapped[int | None] = mapped_column(ForeignKey("institutions.id"))
    name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(1024))
    source_type: Mapped[str] = mapped_column(String(64), default="government")
    country_code: Mapped[str | None] = mapped_column(String(8))
    reliability_score: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String(32), default="active")
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime)

    government: Mapped[Government] = relationship(back_populates="sources")
    institution: Mapped[Institution | None] = relationship()


class SourceSnapshot(TimestampMixin, Base):
    __tablename__ = "source_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    http_status: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    content_type: Mapped[str | None] = mapped_column(String(128))
    raw_content: Mapped[str | None] = mapped_column(LongText)
    change_status: Mapped[str] = mapped_column(String(32), default="unchanged")  # new|changed|unchanged|unavailable


class Document(TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("government_id", "content_hash", name="uq_doc_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"))
    government_id: Mapped[int] = mapped_column(ForeignKey("governments.id"))
    title: Mapped[str] = mapped_column(String(512))
    url: Mapped[str | None] = mapped_column(String(1024))
    document_type: Mapped[str] = mapped_column(String(64), default="unknown")
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    raw_text: Mapped[str | None] = mapped_column(LongText)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)


class DocumentVersion(TimestampMixin, Base):
    __tablename__ = "document_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    raw_text: Mapped[str | None] = mapped_column(LongText)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Entity(TimestampMixin, Base):
    __tablename__ = "entities"
    __table_args__ = (UniqueConstraint("government_id", "name", "entity_type", name="uq_entity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    government_id: Mapped[int] = mapped_column(ForeignKey("governments.id"))
    name: Mapped[str] = mapped_column(String(255))
    entity_type: Mapped[str] = mapped_column(String(64))  # institution|program|project|vendor|budget|tender|contract|payment|outcome
    metadata_json: Mapped[dict | None] = mapped_column(JSON)


class CivicEvent(TimestampMixin, Base):
    __tablename__ = "civic_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    government_id: Mapped[int] = mapped_column(ForeignKey("governments.id"))
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"))
    event_type: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(512))
    summary: Mapped[str | None] = mapped_column(Text)
    event_date: Mapped[datetime | None] = mapped_column(DateTime)
    amount: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(8))
    institution_name: Mapped[str | None] = mapped_column(String(255))
    entities_json: Mapped[list | None] = mapped_column(JSON)
    locations_json: Mapped[list | None] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)


class KnowledgeEdge(TimestampMixin, Base):
    __tablename__ = "knowledge_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    government_id: Mapped[int] = mapped_column(ForeignKey("governments.id"))
    from_entity_type: Mapped[str] = mapped_column(String(64))
    from_entity_id: Mapped[int] = mapped_column(Integer)
    to_entity_type: Mapped[str] = mapped_column(String(64))
    to_entity_id: Mapped[int] = mapped_column(Integer)
    edge_type: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"))
    explanation: Mapped[str | None] = mapped_column(Text)


class AgentRun(TimestampMixin, Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    government_id: Mapped[int] = mapped_column(ForeignKey("governments.id"))
    run_type: Mapped[str] = mapped_column(String(16), default="daily")
    status: Mapped[str] = mapped_column(String(32), default="running")  # running|succeeded|failed
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    error: Mapped[str | None] = mapped_column(Text)
    stats_json: Mapped[dict | None] = mapped_column(JSON)


class Report(TimestampMixin, Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    government_id: Mapped[int] = mapped_column(ForeignKey("governments.id"))
    run_id: Mapped[int | None] = mapped_column(ForeignKey("agent_runs.id"))
    report_date: Mapped[datetime] = mapped_column(Date)
    run_type: Mapped[str] = mapped_column(String(16), default="daily")
    executive_summary: Mapped[str | None] = mapped_column(Text)
    overall_score: Mapped[int | None] = mapped_column(Integer)
    report_json: Mapped[dict | None] = mapped_column(JSON)

    government: Mapped[Government] = relationship(back_populates="reports")
    notes: Mapped[list["ReportNote"]] = relationship(back_populates="report")
    scores: Mapped["TransparencyScoreRow | None"] = relationship(back_populates="report")
    failed_questions: Mapped[list["FailedQuestionRow"]] = relationship(back_populates="report")


class ReportNote(TimestampMixin, Base):
    __tablename__ = "report_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"))
    title: Mapped[str] = mapped_column(String(512))
    category: Mapped[str] = mapped_column(String(64))
    importance: Mapped[str] = mapped_column(String(16), default="medium")
    summary: Mapped[str | None] = mapped_column(Text)
    analysis: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    evidence_json: Mapped[list | None] = mapped_column(JSON)

    report: Mapped[Report] = relationship(back_populates="notes")


class TransparencyScoreRow(TimestampMixin, Base):
    __tablename__ = "transparency_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"))
    documentation: Mapped[int] = mapped_column(Integer)
    timeliness: Mapped[int] = mapped_column(Integer)
    accessibility: Mapped[int] = mapped_column(Integer)
    completeness: Mapped[int] = mapped_column(Integer)
    traceability: Mapped[int] = mapped_column(Integer)
    explainability: Mapped[int] = mapped_column(Integer)
    overall: Mapped[int] = mapped_column(Integer)
    explanations_json: Mapped[dict | None] = mapped_column(JSON)

    report: Mapped[Report] = relationship(back_populates="scores")


class FailedQuestionRow(TimestampMixin, Base):
    __tablename__ = "failed_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"))
    question: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="failed")  # answered|partial|failed
    answer: Mapped[str | None] = mapped_column(Text)
    findings_json: Mapped[list | None] = mapped_column(JSON)
    evidence_json: Mapped[list | None] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    reason_failed: Mapped[str | None] = mapped_column(Text)
    missing_data_json: Mapped[list | None] = mapped_column(JSON)
    failed_step: Mapped[str | None] = mapped_column(String(128))
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    recommendation: Mapped[str | None] = mapped_column(Text)

    report: Mapped[Report] = relationship(back_populates="failed_questions")


class Citation(TimestampMixin, Base):
    __tablename__ = "citations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int | None] = mapped_column(ForeignKey("reports.id"))
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"))
    title: Mapped[str] = mapped_column(String(512))
    url: Mapped[str] = mapped_column(String(1024))
    source_type: Mapped[str] = mapped_column(String(64), default="government")
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime)


class CrawlError(TimestampMixin, Base):
    __tablename__ = "crawl_errors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"))
    run_id: Mapped[int | None] = mapped_column(ForeignKey("agent_runs.id"))
    url: Mapped[str | None] = mapped_column(String(1024))
    error_type: Mapped[str] = mapped_column(String(64), default="fetch_error")
    message: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
