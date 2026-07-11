"""Scheduled agent runs.

Daily run at 02:00 server time for every government; deeper weekly run every
Sunday at 03:00. Enable with SCHEDULER_ENABLED=true (off by default so dev
servers and tests don't crawl by surprise).
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from . import db, jobs

logger = logging.getLogger(__name__)


def _run_all(run_type: str) -> None:
    for gov in db.list_governments():
        logger.info("Scheduled %s run for %s", run_type, gov["name"])
        jobs.enqueue_run(gov["name"], run_type)


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _run_all, CronTrigger(hour=2, minute=0), args=["daily"], id="daily-runs"
    )
    scheduler.add_job(
        _run_all, CronTrigger(day_of_week="sun", hour=3, minute=0), args=["weekly"], id="weekly-runs"
    )
    scheduler.start()
    logger.info("Scheduler started: daily 02:00, weekly Sunday 03:00")
    return scheduler


def main() -> None:
    """Standalone scheduler process for production.

    Run exactly ONE instance (e.g. under Supervisor):

        python -m src.scheduler

    In production the API runs under gunicorn with SCHEDULER_ENABLED=false —
    embedding the scheduler in gunicorn would start one per worker and
    duplicate every scheduled run.
    """
    import time

    from gov_oracle_agents.config import validate_required_config

    logging.basicConfig(level=logging.INFO)
    validate_required_config()  # abort on missing DATABASE_URL / OPENAI_API_KEY
    db.ensure_schema()
    start_scheduler()
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    main()
