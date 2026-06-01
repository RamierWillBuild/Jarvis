"""Central configuration. Every option is sourced from an environment variable.

Defaults are chosen so the app boots and the pipeline runs even with no secrets
configured (LLM calls gracefully fall back to extractive summaries).
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

# Load a local .env if present (no-op in Docker where env is injected).
load_dotenv()


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings:
    """Process-level config, read once from the environment."""

    # --- LLM provider -----------------------------------------------------
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai").lower()
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")

    # Optional, reserved for future NewsAPI integration.
    NEWSAPI_KEY: str = os.getenv("NEWSAPI_KEY", "")

    # --- News sources -----------------------------------------------------
    NEWS_CATEGORIES: list[str] = _csv(
        os.getenv("NEWS_CATEGORIES", "ai,technology,science,business,world")
    )
    HN_STORY_LIMIT: int = int(os.getenv("HN_STORY_LIMIT", "20"))
    # RSS feeds as comma-separated "category::url" pairs.
    RSS_FEEDS_RAW: str = os.getenv(
        "RSS_FEEDS",
        "technology::https://techcrunch.com/feed/,"
        "science::http://feeds.arstechnica.com/arstechnica/index,"
        "world::http://feeds.bbci.co.uk/news/rss.xml",
    )

    # --- Pipeline / scheduler --------------------------------------------
    PIPELINE_INTERVAL_HOURS: int = int(os.getenv("PIPELINE_INTERVAL_HOURS", "6"))
    RUN_PIPELINE_ON_STARTUP: bool = os.getenv("RUN_PIPELINE_ON_STARTUP", "true").lower() == "true"
    SUMMARIZE_LIMIT: int = int(os.getenv("SUMMARIZE_LIMIT", "15"))
    BRIEFING_ARTICLES_PER_CATEGORY: int = int(os.getenv("BRIEFING_ARTICLES_PER_CATEGORY", "5"))

    # --- Storage ----------------------------------------------------------
    DB_PATH: str = os.getenv("DB_PATH", os.path.join("data", "jarvis.db"))
    SETTINGS_PATH: str = os.getenv("SETTINGS_PATH", os.path.join("data", "settings.json"))

    # --- HTTP -------------------------------------------------------------
    HTTP_TIMEOUT_SECONDS: float = float(os.getenv("HTTP_TIMEOUT_SECONDS", "15"))
    CORS_ORIGINS: list[str] = _csv(os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"))

    @property
    def rss_feeds(self) -> list[dict[str, str]]:
        """Parse RSS_FEEDS_RAW into [{category, url}, ...]."""
        feeds: list[dict[str, str]] = []
        for entry in _csv(self.RSS_FEEDS_RAW):
            if "::" in entry:
                category, url = entry.split("::", 1)
            else:
                category, url = "technology", entry
            feeds.append({"category": category.strip(), "url": url.strip()})
        return feeds


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
