"""News pipeline: fetch -> store -> summarize -> build briefing.

Plain async orchestration of the two agents. Safe to call from an HTTP handler
or the scheduler. A module-level lock prevents overlapping runs.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date

from . import database as db
from . import runtime_settings
from .agents import news_agent, summarization_agent
from .config import settings

logger = logging.getLogger("jarvis.pipeline")

_run_lock = asyncio.Lock()


async def run_pipeline() -> dict:
    """Execute one full pipeline run. Returns a summary dict."""
    if _run_lock.locked():
        logger.info("Pipeline already running; skipping this trigger.")
        return {"status": "skipped", "fetched": 0, "inserted": 0, "summarized": 0, "briefing_id": None}

    async with _run_lock:
        enabled = runtime_settings.enabled_categories()
        logger.info("Pipeline start. Enabled categories: %s", enabled)

        # 1. Fetch
        articles = await news_agent.gather_news(enabled_categories=enabled or None)
        logger.info("Fetched %d articles", len(articles))

        # 2. Store new ones
        inserted = 0
        for article in articles:
            if db.upsert_article(article):
                inserted += 1
        logger.info("Inserted %d new articles", inserted)

        # 3. Summarize articles lacking a summary
        pending = db.articles_missing_summary(settings.SUMMARIZE_LIMIT)
        summarized = 0
        for article in pending:
            try:
                summary = await summarization_agent.summarize_article(
                    article["title"], article.get("content") or ""
                )
                db.set_article_summary(article["id"], summary)
                summarized += 1
            except Exception:  # noqa: BLE001 - never let one article break the run
                logger.exception("Failed to summarize article %s", article["id"])
        logger.info("Summarized %d articles", summarized)

        # 4. Build today's briefing from the freshest, highest-signal articles
        per_cat = settings.BRIEFING_ARTICLES_PER_CATEGORY
        recent = db.recent_articles(limit=200)
        chosen: list[dict] = []
        counts: dict[str, int] = {}
        for article in recent:
            cat = article["category"]
            if counts.get(cat, 0) >= per_cat:
                continue
            counts[cat] = counts.get(cat, 0) + 1
            chosen.append(article)

        briefing_text = await summarization_agent.generate_briefing(chosen)
        briefing_id = db.insert_briefing(
            date=date.today().isoformat(),
            content=briefing_text,
            article_count=len(chosen),
        )
        logger.info("Briefing %d created from %d articles", briefing_id, len(chosen))

        return {
            "status": "ok",
            "fetched": len(articles),
            "inserted": inserted,
            "summarized": summarized,
            "briefing_id": briefing_id,
        }
