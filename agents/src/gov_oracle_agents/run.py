"""CLI entry point.

    python -m gov_oracle_agents.run --government "Government of Bangladesh"
    python -m gov_oracle_agents.run --government "Government of Bangladesh" --run-type weekly --json
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

from .oracle import GovernmentOracle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a government transparency audit.")
    parser.add_argument("--government", required=True, help='e.g. "Government of Bangladesh"')
    parser.add_argument("--run-type", default="daily", choices=["daily", "weekly", "manual"])
    parser.add_argument("--max-sources", type=int, default=None)
    parser.add_argument("--no-crawl", action="store_true", help="Skip network crawling (offline demo)")
    parser.add_argument("--json", action="store_true", help="Print the full report as JSON")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    oracle = GovernmentOracle()
    if args.no_crawl:
        oracle.settings.crawl_enabled = False

    report = oracle.run_government_report(
        government_name=args.government,
        run_type=args.run_type,
        max_sources=args.max_sources,
    )

    if args.json:
        print(json.dumps(report.model_dump(mode="json"), indent=2))
        return 0

    scores = report.transparency_scores
    print(f"\n=== {report.government} — {report.date} ({report.run_type} run) ===\n")
    print(report.executive_summary)
    print("\nTransparency scores (0-100):")
    for dimension in (
        "documentation",
        "timeliness",
        "accessibility",
        "completeness",
        "traceability",
        "explainability",
    ):
        print(f"  {dimension:15s} {getattr(scores, dimension):3d}")
    print(f"  {'overall':15s} {scores.overall:3d}")
    print(f"\nNotes: {len(report.today_notes)}")
    for note in report.today_notes:
        print(f"  [{note.importance}] {note.title}")
    failed = [q for q in report.failed_questions if q.answerability_status == "failed"]
    print(f"\nFailed civic questions: {len(failed)}")
    for question in failed:
        print(f"  - {question.question}")
    coverage = report.source_coverage
    print(
        f"\nSources: {coverage.sources_checked} checked, {coverage.sources_successful} ok, "
        f"{coverage.sources_failed} failed, {coverage.new_documents_found} new documents"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
