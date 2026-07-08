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
