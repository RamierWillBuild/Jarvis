"""Mutable, user-editable settings backed by a JSON file.

Seeded from environment defaults on first run. The Settings page in the
frontend reads and writes these via the /settings endpoints. We keep this out
of the DB so the schema stays limited to articles/briefings/chat_messages.
"""
from __future__ import annotations

import json
import os
import threading

from .config import settings

_lock = threading.Lock()


def _defaults() -> dict:
    return {
        # category -> enabled?
        "categories": {cat: True for cat in settings.NEWS_CATEGORIES},
        "llm_provider": settings.LLM_PROVIDER,
    }


def _ensure_parent_dir() -> None:
    parent = os.path.dirname(os.path.abspath(settings.SETTINGS_PATH))
    os.makedirs(parent, exist_ok=True)


def load() -> dict:
    with _lock:
        if not os.path.exists(settings.SETTINGS_PATH):
            data = _defaults()
            _write_unlocked(data)
            return data
        try:
            with open(settings.SETTINGS_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            data = _defaults()
        # Merge in any newly-configured categories.
        merged = _defaults()
        merged.update(data)
        merged_categories = {cat: True for cat in settings.NEWS_CATEGORIES}
        merged_categories.update(data.get("categories", {}))
        merged["categories"] = merged_categories
        return merged


def _write_unlocked(data: dict) -> None:
    _ensure_parent_dir()
    with open(settings.SETTINGS_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def save(data: dict) -> dict:
    with _lock:
        current = _defaults()
        if os.path.exists(settings.SETTINGS_PATH):
            try:
                with open(settings.SETTINGS_PATH, "r", encoding="utf-8") as fh:
                    current.update(json.load(fh))
            except (json.JSONDecodeError, OSError):
                pass
        if "categories" in data:
            current.setdefault("categories", {})
            current["categories"].update(data["categories"])
        if "llm_provider" in data:
            current["llm_provider"] = data["llm_provider"]
        _write_unlocked(current)
        return current


def enabled_categories() -> list[str]:
    data = load()
    return [cat for cat, on in data.get("categories", {}).items() if on]


def active_provider() -> str:
    return load().get("llm_provider", settings.LLM_PROVIDER)
