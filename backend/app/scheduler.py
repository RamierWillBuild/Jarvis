"""APScheduler integration — runs the pipeline on a fixed interval."""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .config import settings
from .pipeline import run_pipeline

logger = logging.getLogger("jarvis.scheduler")

_scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        run_pipeline,
        trigger=IntervalTrigger(hours=settings.PIPELINE_INTERVAL_HOURS),
        id="news_pipeline",
        name="News pipeline",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("Scheduler started; pipeline runs every %d hours", settings.PIPELINE_INTERVAL_HOURS)
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
    _scheduler = None
