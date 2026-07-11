"""Registry seeding helpers.

Shared by the standalone scripts in seed/ and the backend's `flask seed`
CLI command. Idempotent: re-running never duplicates governments,
institutions, or sources, and the sample report is only inserted when the
government has no reports yet.
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .agents import GovernmentResolverAgent, SourceDiscoveryAgent
from .models import GovernmentReport
from .seeds import ALL_GOVERNMENTS, lookup
from .storage import AgentRun, Government, Report, init_db, session_scope


def seed_government(session: Session, government_name: str) -> tuple[str, int]:
    """Resolve one government and register its sources. Returns (name, source count)."""
    government = GovernmentResolverAgent().resolve(session, government_name)
    sources = SourceDiscoveryAgent().discover(session, government)
    return government.name, len(sources)


def seed_all_governments(database_url: str | None = None) -> list[tuple[str, int]]:
    """Seed every government in the curated registry."""
    init_db(database_url)
    results = []
    with session_scope(database_url) as session:
        for entry in ALL_GOVERNMENTS:
            results.append(seed_government(session, entry["government_name"]))
    return results


def seed_one_government(government_name: str, database_url: str | None = None) -> tuple[str, int, bool]:
    """Seed a single government by name or alias.

    Returns (canonical name, source count, known_in_registry). Unknown names
    still get a minimal government record (the resolver's fallback), but no
    curated sources.
    """
    init_db(database_url)
    known = lookup(government_name) is not None
    with session_scope(database_url) as session:
        name, source_count = seed_government(session, government_name)
    return name, source_count, known


def insert_sample_report(
    sample_path: Path,
    government_name: str = "Government of Bangladesh",
    database_url: str | None = None,
) -> bool:
    """Insert the bundled demo report if the government has none. Returns True if inserted."""
    from .oracle import GovernmentOracle

    init_db(database_url)
    report = GovernmentReport.model_validate(json.loads(sample_path.read_text()))
    with session_scope(database_url) as session:
        government = GovernmentResolverAgent().resolve(session, government_name)
        exists = session.scalar(select(Report).where(Report.government_id == government.id))
        if exists is not None:
            return False
        run = AgentRun(government_id=government.id, run_type="manual", status="succeeded")
        session.add(run)
        session.flush()
        GovernmentOracle._persist_report(session, government.id, run, report)
        return True
