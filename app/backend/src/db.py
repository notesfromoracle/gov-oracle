"""Thin query layer over the shared schema owned by gov_oracle_agents."""
from __future__ import annotations

from sqlalchemy import select

from gov_oracle_agents.storage import (
    AgentRun,
    FailedQuestionRow,
    Government,
    Report,
    Source,
    TransparencyScoreRow,
    init_db,
    session_scope,
)


def ensure_schema() -> None:
    init_db()


def find_government_id(name: str) -> int | None:
    with session_scope() as session:
        gov = session.scalar(select(Government).where(Government.name == name))
        return gov.id if gov else None


def serialize_government(gov: Government, latest: Report | None = None) -> dict:
    data = {
        "id": gov.id,
        "name": gov.name,
        "country_code": gov.country_code,
        "jurisdiction_type": gov.jurisdiction_type,
        "description": gov.description,
    }
    if latest is not None:
        data["latest_report"] = {
            "id": latest.id,
            "report_date": str(latest.report_date),
            "overall_score": latest.overall_score,
            "run_type": latest.run_type,
        }
    return data


def list_governments() -> list[dict]:
    with session_scope() as session:
        governments = session.scalars(select(Government).order_by(Government.name)).all()
        result = []
        for gov in governments:
            latest = session.scalar(
                select(Report)
                .where(Report.government_id == gov.id)
                .order_by(Report.id.desc())
            )
            result.append(serialize_government(gov, latest))
        return result


def get_government(government_id: int) -> dict | None:
    with session_scope() as session:
        gov = session.get(Government, government_id)
        if gov is None:
            return None
        latest = session.scalar(
            select(Report).where(Report.government_id == gov.id).order_by(Report.id.desc())
        )
        return serialize_government(gov, latest)


def get_government_name(government_id: int) -> str | None:
    with session_scope() as session:
        gov = session.get(Government, government_id)
        return gov.name if gov else None


def get_latest_report(government_id: int) -> dict | None:
    """Latest successful report plus a staleness warning if a newer run failed."""
    with session_scope() as session:
        report = session.scalar(
            select(Report).where(Report.government_id == government_id).order_by(Report.id.desc())
        )
        if report is None:
            return None
        payload = dict(report.report_json or {})
        payload["report_id"] = report.id
        payload["stale"] = False
        latest_run = session.scalar(
            select(AgentRun)
            .where(AgentRun.government_id == government_id)
            .order_by(AgentRun.id.desc())
        )
        if latest_run is not None and latest_run.status == "failed" and (
            report.run_id is None or latest_run.id > report.run_id
        ):
            payload["stale"] = True
            payload["warning"] = (
                "The most recent agent run failed; this is the last successful report."
            )
        return payload


def list_reports(government_id: int) -> list[dict]:
    with session_scope() as session:
        reports = session.scalars(
            select(Report).where(Report.government_id == government_id).order_by(Report.id.desc())
        ).all()
        return [
            {
                "id": r.id,
                "report_date": str(r.report_date),
                "run_type": r.run_type,
                "overall_score": r.overall_score,
                "executive_summary": r.executive_summary,
            }
            for r in reports
        ]


def get_report(report_id: int) -> dict | None:
    with session_scope() as session:
        report = session.get(Report, report_id)
        if report is None:
            return None
        payload = dict(report.report_json or {})
        payload["report_id"] = report.id
        payload["government_id"] = report.government_id
        return payload


def score_history(government_id: int) -> list[dict]:
    with session_scope() as session:
        rows = session.execute(
            select(TransparencyScoreRow, Report.report_date)
            .join(Report, TransparencyScoreRow.report_id == Report.id)
            .where(Report.government_id == government_id)
            .order_by(Report.id)
        ).all()
        return [
            {
                "report_id": score.report_id,
                "report_date": str(report_date),
                "documentation": score.documentation,
                "timeliness": score.timeliness,
                "accessibility": score.accessibility,
                "completeness": score.completeness,
                "traceability": score.traceability,
                "explainability": score.explainability,
                "overall": score.overall,
            }
            for score, report_date in rows
        ]


def list_sources(government_id: int) -> list[dict]:
    with session_scope() as session:
        sources = session.scalars(
            select(Source).where(Source.government_id == government_id).order_by(Source.name)
        ).all()
        return [
            {
                "id": s.id,
                "name": s.name,
                "url": s.url,
                "source_type": s.source_type,
                "reliability_score": s.reliability_score,
                "status": s.status,
                "last_checked_at": str(s.last_checked_at) if s.last_checked_at else None,
            }
            for s in sources
        ]


def latest_failed_questions(government_id: int) -> list[dict]:
    with session_scope() as session:
        report = session.scalar(
            select(Report).where(Report.government_id == government_id).order_by(Report.id.desc())
        )
        if report is None:
            return []
        questions = session.scalars(
            select(FailedQuestionRow).where(FailedQuestionRow.report_id == report.id)
        ).all()
        return [
            {
                "question": q.question,
                "status": q.status,
                "answer": q.answer,
                "findings": q.findings_json or [],
                "evidence": q.evidence_json or [],
                "confidence": q.confidence,
                "reason_failed": q.reason_failed,
                "missing_data": q.missing_data_json or [],
                "failed_step": q.failed_step,
                "severity": q.severity,
                "recommendation": q.recommendation,
            }
            for q in questions
        ]
