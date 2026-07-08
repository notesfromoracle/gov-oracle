#!/usr/bin/env python
"""Run transparency reports for a set of countries and archive the results.

Usage (from the repo root):

    python scripts/run_study.py --countries us,gb,de,jp,no --out research_artifacts/my_study
    python scripts/run_study.py --countries br,in,za,bd,ke --out research_artifacts/my_study

Country identifiers are registry aliases (ISO codes and names both work).
Reports go into the shared database (so the frontend sees them) AND into the
output folder as one JSON file per country, plus a cumulative summary.csv /
summary.md. Re-running with the same --out appends to the summary, so a study
can be executed in batches.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from gov_oracle_agents import GovernmentOracle, __version__
from gov_oracle_agents.seeds import lookup

SUMMARY_FIELDS = [
    "country_code", "government", "run_started_utc", "duration_s",
    "sources_checked", "sources_successful", "sources_failed", "new_documents",
    "pages_fetched", "links_followed", "ssl_invalid_pages", "pdf_documents", "scanned_pdfs",
    "documentation", "timeliness", "accessibility", "completeness",
    "traceability", "explainability", "overall",
    "questions_answered", "questions_partial", "questions_failed",
]


def slugify(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name.lower()).strip("_")


def run_one(oracle: GovernmentOracle, alias: str, out_dir: Path) -> dict | None:
    entry = lookup(alias)
    if entry is None:
        print(f"!! unknown country alias: {alias}", flush=True)
        return None
    name = entry["government_name"]
    started = datetime.now(timezone.utc)
    t0 = time.time()
    print(f"== running {name} ...", flush=True)
    try:
        report = oracle.run_government_report(government_name=name, run_type="manual")
    except Exception:
        print(f"!! run failed for {name}:\n{traceback.format_exc()}", flush=True)
        return None
    duration = round(time.time() - t0, 1)

    payload = report.model_dump(mode="json")
    out_path = out_dir / f"{report.country_code}_{slugify(name)}.json"
    out_path.write_text(json.dumps(payload, indent=2))

    scores = report.transparency_scores
    coverage = report.source_coverage
    crawl = report.metadata.get("crawl", {})
    statuses = [q.answerability_status for q in report.failed_questions]
    row = {
        "country_code": report.country_code,
        "government": name,
        "run_started_utc": started.isoformat(timespec="seconds"),
        "duration_s": duration,
        "sources_checked": coverage.sources_checked,
        "sources_successful": coverage.sources_successful,
        "sources_failed": coverage.sources_failed,
        "new_documents": coverage.new_documents_found,
        "pages_fetched": crawl.get("pages_fetched", 0),
        "links_followed": crawl.get("links_followed", 0),
        "ssl_invalid_pages": crawl.get("ssl_invalid_pages", 0),
        "pdf_documents": crawl.get("pdf_documents", 0),
        "scanned_pdfs": crawl.get("scanned_pdfs", 0),
        "documentation": scores.documentation,
        "timeliness": scores.timeliness,
        "accessibility": scores.accessibility,
        "completeness": scores.completeness,
        "traceability": scores.traceability,
        "explainability": scores.explainability,
        "overall": scores.overall,
        "questions_answered": statuses.count("answered"),
        "questions_partial": statuses.count("partial"),
        "questions_failed": statuses.count("failed"),
    }
    print(
        f"   done in {duration}s: {coverage.sources_successful}/{coverage.sources_checked} "
        f"sources, {coverage.new_documents_found} docs, overall {scores.overall}",
        flush=True,
    )
    return row


def append_summary(out_dir: Path, rows: list[dict]) -> None:
    csv_path = out_dir / "summary.csv"
    existing: list[dict] = []
    if csv_path.exists():
        with csv_path.open() as f:
            existing = list(csv.DictReader(f))
    # replace any previous row for the same country (latest run wins)
    merged = {row["country_code"]: row for row in existing}
    for row in rows:
        merged[row["country_code"]] = {k: str(v) for k, v in row.items()}
    ordered = sorted(merged.values(), key=lambda r: -int(r["overall"]))
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(ordered)

    md_path = out_dir / "summary.md"
    lines = [
        "# Ten-country transparency study — run summary",
        "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} "
        f"by gov-oracle-agents v{__version__}.",
        "",
        "| Country | Overall | Doc | Time | Access | Compl | Trace | Expl | Sources ok | Docs | Q answered/partial/failed |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in ordered:
        lines.append(
            f"| {r['government']} ({r['country_code']}) | **{r['overall']}** "
            f"| {r['documentation']} | {r['timeliness']} | {r['accessibility']} "
            f"| {r['completeness']} | {r['traceability']} | {r['explainability']} "
            f"| {r['sources_successful']}/{r['sources_checked']} | {r['new_documents']} "
            f"| {r['questions_answered']}/{r['questions_partial']}/{r['questions_failed']} |"
        )
    md_path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--countries", required=True, help="comma-separated registry aliases")
    parser.add_argument("--out", required=True, help="artifact output directory")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    oracle = GovernmentOracle()
    meta = {
        "package_version": __version__,
        "llm_provider": oracle.llm.name,
        "crawl_settings": {
            "timeout_s": oracle.settings.crawl_timeout_seconds,
            "depth": oracle.settings.crawl_depth,
            "max_links_per_source": oracle.settings.crawl_max_links_per_source,
            "max_pages_total": oracle.settings.crawl_max_pages_total,
            "browser_fallback": oracle.settings.crawl_use_browser,
        },
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2))

    rows = []
    for alias in [c.strip() for c in args.countries.split(",") if c.strip()]:
        row = run_one(oracle, alias, out_dir)
        if row:
            rows.append(row)
    append_summary(out_dir, rows)
    print(f"\nBatch complete: {len(rows)} reports saved to {out_dir}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
