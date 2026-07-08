# gov-oracle-agents

Open-source AI-assisted public-information audit agents. Given a government
name, the library runs a research pipeline over publicly available sources and
produces evidence-backed civic notes, six transparency scores with written
explanations, and a record of civic questions it could not answer.

```python
from gov_oracle_agents import GovernmentOracle

oracle = GovernmentOracle()
report = oracle.run("Government of Bangladesh")
print(report.summary)
print(report.transparency_scores.overall)
```

Or from the CLI:

```bash
python -m gov_oracle_agents.run --government "Government of Bangladesh"
python -m gov_oracle_agents.run --government "Government of Bangladesh" --json
python -m gov_oracle_agents.run --government "Government of Bangladesh" --no-crawl  # offline demo
```

## Pipeline

| Agent | Responsibility |
| --- | --- |
| `GovernmentResolverAgent` | Resolve the canonical government, official domains, major institutions (curated registry of 22 countries across income levels; aliases like "uk", "Brasil", "Republic of Kenya" resolve) |
| `SourceDiscoveryAgent` | Register official/public sources (budget, procurement, audit, statistics, parliament, news) |
| `SourceMonitorAgent` | Deep-crawl sources (root + civically scored links + sitemap entries), detect new/changed/unavailable pages, preserve historical snapshots, extract PDF text |
| `DocumentExtractionAgent` | Extract text, classify document type, extract amounts/dates/institution mentions |
| `CivicEventExtractionAgent` | Convert documents into structured civic events |
| `KnowledgeGraphAgent` | Create evidence-backed edges between budgets, projects, tenders, contracts, vendors |
| `FailedQuestionsAgent` | Attempt a bank of civic transparency questions; record exactly what data was missing |
| `TransparencyScoringAgent` | Score six dimensions deterministically from observed signals, each with an explanation |
| `DailyNotesAgent` | Produce calm, non-partisan, evidence-backed public notes |

## Crawling

The monitor is frontier-based, not homepage-only:

- **Fetching** — httpx first; if a source looks bot-walled or JS-rendered
  (403/429/503, Cloudflare markers, near-empty HTML shells), it retries with
  headless Chromium. Install the browser path with:

  ```bash
  pip install -e ".[full]"
  python -m playwright install chromium
  ```

  Without Playwright the fallback is skipped and the failure is recorded —
  which is itself an accessibility finding. Sources serving broken TLS
  certificate chains (common on government sites) are re-fetched insecurely
  and flagged as `tls_invalid` crawl errors: the content is audited, and the
  broken chain deducts from the accessibility score.
- **Breadth** — links on each source page are scored for civic value
  (budget/tender/audit/report/statistics keywords beat news and nav chrome),
  merged with `sitemap.xml` entries, filtered to the government's web estate,
  checked against robots.txt, and the top links are followed one level deep.
  When a real LLM is configured it re-ranks the frontier (`rank_links` task);
  offline, the deterministic keyword ranking stands.
- **PDFs** — text-based PDFs are extracted with pypdf; scanned image PDFs are
  stored but flagged, and lower the accessibility score.

Tuning (env vars): `CRAWL_DEPTH` (0 = roots only), `CRAWL_MAX_LINKS_PER_SOURCE`,
`CRAWL_MAX_PAGES_TOTAL`, `CRAWL_USE_BROWSER`, `CRAWL_TIMEOUT_SECONDS`.

## LLM abstraction

Any OpenAI-compatible endpoint works (`OPENAI_API_KEY`, `OPENAI_API_BASE`,
`OPENAI_MODEL`). **Without a key the pipeline still runs end to end** using a
deterministic rule-based analyst — useful for development, tests, and
understanding baseline behavior. Scoring is always deterministic and
signal-based; the LLM only writes narrative text and classifies documents.

## Database

The library owns the schema (SQLAlchemy models in
`gov_oracle_agents/storage/orm.py`, Alembic migrations in `migrations/`).
`DATABASE_URL` selects the database — MySQL in production, and a local SQLite
file (`./gov_oracle.db`) as automatic fallback when unset. Tables are
auto-created on first use; production should run `alembic upgrade head`.

Reports are append-only: a new row per run, never overwritten.

## Development

```bash
pip install -e ".[dev]"
pytest
```
