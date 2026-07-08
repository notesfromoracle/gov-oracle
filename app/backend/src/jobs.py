"""Agent run execution.

Runs are enqueued to RQ when Redis is available (`rq worker gov-oracle` must
be running), otherwise executed in a daemon thread — good enough for the MVP
and for local demos without Redis.
"""
from __future__ import annotations

import logging
import os
import threading

logger = logging.getLogger(__name__)


def execute_run(government_name: str, run_type: str = "daily") -> dict:
    """The actual job body. Importable by RQ workers."""
    from gov_oracle_agents import GovernmentOracle

    from . import cache
    from .db import find_government_id

    oracle = GovernmentOracle()
    report = oracle.run_government_report(government_name=government_name, run_type=run_type)
    government_id = find_government_id(government_name)
    if government_id is not None:
        cache.invalidate(cache.latest_report_key(government_id))
    logger.info("Run finished for %s (overall %d)", government_name, report.transparency_scores.overall)
    return {"government": government_name, "overall": report.transparency_scores.overall}


def enqueue_run(government_name: str, run_type: str = "daily") -> dict:
    """Enqueue via RQ if possible, else run in a background thread."""
    try:
        import redis
        from rq import Queue

        connection = redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"), socket_connect_timeout=1
        )
        connection.ping()
        queue = Queue("gov-oracle", connection=connection)
        job = queue.enqueue(execute_run, government_name, run_type, job_timeout=1800)
        return {"queued": True, "backend": "rq", "job_id": job.id}
    except Exception:
        thread = threading.Thread(
            target=_run_safely, args=(government_name, run_type), daemon=True
        )
        thread.start()
        return {"queued": True, "backend": "thread", "job_id": None}


def _run_safely(government_name: str, run_type: str) -> None:
    try:
        execute_run(government_name, run_type)
    except Exception:
        logger.exception("Agent run failed for %s", government_name)
