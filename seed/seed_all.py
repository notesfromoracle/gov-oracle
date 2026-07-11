"""Seed the database with every government in the curated registry.

Usage (from the repo root, with the agents package installed):

    python seed/seed_all.py

Equivalent to the backend CLI command `flask seed --with-sample-report`.
"""
from __future__ import annotations

from pathlib import Path

from gov_oracle_agents.seeding import insert_sample_report, seed_all_governments

SAMPLE_REPORT_PATH = Path(__file__).parent / "sample_report.json"


def main() -> None:
    for name, source_count in seed_all_governments():
        print(f"Seeded {name}: {source_count} sources")
    if SAMPLE_REPORT_PATH.exists() and insert_sample_report(SAMPLE_REPORT_PATH):
        print("Inserted Bangladesh sample report.")
    else:
        print("Sample report skipped (missing file or reports already exist).")


if __name__ == "__main__":
    main()
