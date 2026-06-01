"""News Agent — fetches stories from the HackerNews API and configurable RSS feeds.

Pure async functions. Network calls use httpx; feedparser (sync) runs in a
thread so it doesn't block the event loop.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import feedparser
import httpx

from ..config import settings

HN_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{id}.json"

_AI_KEYWORDS = ("ai", "llm", "gpt", "openai", "anthropic", "machine learning", "neural", "model")


def _categorize_hn(title: str) -> str:
    lowered = title.lower()
    if any(kw in lowered for kw in _AI_KEYWORDS):
        return "ai"
    return "technology"


async def fetch_hackernews(client: httpx.AsyncClient, limit: int) -> list[dict]:
    """Fetch the top `limit` HackerNews stories."""
    try:
        resp = await client.get(HN_TOP)
        resp.raise_for_status()
        ids = resp.json()[:limit]
    except (httpx.HTTPError, ValueError):
        return []

    async def _one(story_id: int) -> dict | None:
        try:
            r = await client.get(HN_ITEM.format(id=story_id))
            r.raise_for_status()
            item = r.json()
        except (httpx.HTTPError, ValueError):
            return None
        if not item or item.get("type") != "story" or not item.get("url"):
            return None
        published = None
        if item.get("time"):
            published = datetime.fromtimestamp(item["time"], tz=timezone.utc).isoformat()
        title = item.get("title", "(untitled)")
        return {
            "external_id": f"hn-{item['id']}",
            "source": "hackernews",
            "title": title,
            "url": item["url"],
            "content": item.get("text") or title,
            "category": _categorize_hn(title),
            "score": int(item.get("score") or 0),
            "published_at": published,
        }

    results = await asyncio.gather(*[_one(i) for i in ids])
    return [r for r in results if r]


def _parse_feed_sync(url: str, category: str) -> list[dict]:
    parsed = feedparser.parse(url)
    articles: list[dict] = []
    for entry in parsed.entries[:25]:
        link = entry.get("link")
        if not link:
            continue
        published = None
        if entry.get("published_parsed"):
            try:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
            except (TypeError, ValueError):
                published = None
        summary = entry.get("summary", "") or entry.get("description", "")
        articles.append(
            {
                "external_id": entry.get("id") or link,
                "source": parsed.feed.get("title", "rss") if parsed.feed else "rss",
                "title": entry.get("title", "(untitled)"),
                "url": link,
                "content": summary,
                "category": category,
                "score": 0,
                "published_at": published,
            }
        )
    return articles


async def fetch_rss(feeds: list[dict[str, str]]) -> list[dict]:
    """Fetch all configured RSS feeds concurrently."""
    tasks = [asyncio.to_thread(_parse_feed_sync, f["url"], f["category"]) for f in feeds]
    grouped = await asyncio.gather(*tasks, return_exceptions=True)
    articles: list[dict] = []
    for group in grouped:
        if isinstance(group, Exception):
            continue
        articles.extend(group)
    return articles


async def gather_news(enabled_categories: list[str] | None = None) -> list[dict]:
    """Fetch from all sources, filter by enabled categories, de-duplicate by URL."""
    async with httpx.AsyncClient(
        timeout=settings.HTTP_TIMEOUT_SECONDS,
        headers={"User-Agent": "Jarvis/1.0 (+https://github.com/jarvis)"},
        follow_redirects=True,
    ) as client:
        hn, rss = await asyncio.gather(
            fetch_hackernews(client, settings.HN_STORY_LIMIT),
            fetch_rss(settings.rss_feeds),
        )

    all_articles = hn + rss
    if enabled_categories is not None:
        allowed = set(enabled_categories)
        all_articles = [a for a in all_articles if a["category"] in allowed]

    seen: set[str] = set()
    deduped: list[dict] = []
    for article in all_articles:
        if article["url"] in seen:
            continue
        seen.add(article["url"])
        deduped.append(article)
    return deduped
