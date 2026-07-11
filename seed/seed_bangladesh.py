"""Seed the database with the Government of Bangladesh and a sample report.

Usage (from the repo root, with the agents package installed):

    python seed/seed_bangladesh.py

Equivalent to `flask seed --government "Government of Bangladesh" --with-sample-report`.
"""
from __future__ import annotations

from pathlib import Path

from gov_oracle_agents.seeding import insert_sample_report, seed_one_government

SAMPLE_REPORT_PATH = Path(__file__).parent / "sample_report.json"


def main() -> None:
    name, source_count, _known = seed_one_government("Government of Bangladesh")
    print(f"Seeded {name}: {source_count} sources")
    if insert_sample_report(SAMPLE_REPORT_PATH):
        print(f"Inserted sample report from {SAMPLE_REPORT_PATH.name}")
    else:
        print("Reports already exist; not inserting the sample report.")


if __name__ == "__main__":
    main()
