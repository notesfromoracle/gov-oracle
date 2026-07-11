"""Flask CLI commands.

Server usage (from app/backend, with .env providing DATABASE_URL):

    FLASK_APP=wsgi flask seed                              # all 22 registry governments
    FLASK_APP=wsgi flask seed --government "Kenya"         # one government (alias ok)
    FLASK_APP=wsgi flask seed --with-sample-report         # + bundled Bangladesh demo report
"""
from __future__ import annotations

from pathlib import Path

import click

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_REPORT = REPO_ROOT / "seed" / "sample_report.json"


@click.command("seed")
@click.option(
    "--government",
    "government_name",
    default=None,
    help="Seed a single government by registry name or alias (default: all).",
)
@click.option(
    "--with-sample-report",
    is_flag=True,
    help="Also insert the bundled Bangladesh sample report if it has no reports yet.",
)
def seed_command(government_name: str | None, with_sample_report: bool) -> None:
    """Seed registry governments, institutions, and sources into the database."""
    from gov_oracle_agents.seeding import (
        insert_sample_report,
        seed_all_governments,
        seed_one_government,
    )

    if government_name:
        name, source_count, known = seed_one_government(government_name)
        if not known:
            click.echo(
                f"warning: '{government_name}' is not in the curated registry; "
                "a minimal record was created without sources."
            )
        click.echo(f"Seeded {name}: {source_count} sources")
    else:
        results = seed_all_governments()
        for name, source_count in results:
            click.echo(f"Seeded {name}: {source_count} sources")
        click.echo(f"{len(results)} governments seeded.")

    if with_sample_report:
        if not SAMPLE_REPORT.exists():
            click.echo(f"sample report not found at {SAMPLE_REPORT}; skipped.")
        elif insert_sample_report(SAMPLE_REPORT):
            click.echo("Inserted Bangladesh sample report.")
        else:
            click.echo("Bangladesh already has reports; sample report skipped.")
