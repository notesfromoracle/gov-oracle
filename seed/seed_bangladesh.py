"""Seed the database with the Government of Bangladesh and a sample report.

Usage (from the repo root, with the agents package installed):

    python seed/seed_bangladesh.py

This gives the frontend something to show immediately — government,
institutions, sources, and one real sample report (captured from an actual
crawl) — without needing network access or an LLM key. Re-running is safe:
the sample report is only inserted if the government has no reports yet.
"""
from __future__ import annotations

import json
from pathlib import Path

from gov_oracle_agents.agents import GovernmentResolverAgent, SourceDiscoveryAgent
from gov_oracle_agents.models import GovernmentReport
from gov_oracle_agents.oracle import GovernmentOracle
from gov_oracle_agents.storage import AgentRun, Report, init_db, session_scope
from sqlalchemy import select

SAMPLE_REPORT_PATH = Path(__file__).parent / "sample_report.json"


def main() -> None:
    init_db()
    with session_scope() as session:
        government = GovernmentResolverAgent().resolve(session, "Government of Bangladesh")
        sources = SourceDiscoveryAgent().discover(session, government)
        print(f"Seeded {government.name}: {len(sources)} sources")

        has_reports = session.scalar(
            select(Report).where(Report.government_id == government.id)
        )
        if has_reports is not None:
            print("Reports already exist; not inserting the sample report.")
            return

        report = GovernmentReport.model_validate(
            json.loads(SAMPLE_REPORT_PATH.read_text())
        )
        run = AgentRun(government_id=government.id, run_type="manual", status="succeeded")
        session.add(run)
        session.flush()
        GovernmentOracle._persist_report(session, government.id, run, report)
        print(f"Inserted sample report (overall {report.transparency_scores.overall}/100)")


if __name__ == "__main__":
    main()
