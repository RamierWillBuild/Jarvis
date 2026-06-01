"""SQLite persistence layer.

Uses the stdlib ``sqlite3`` module with a fresh connection per operation, which
is safe to share across the FastAPI event loop and the APScheduler background
thread. Tables: articles, briefings, chat_messages.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id  TEXT,
    source       TEXT NOT NULL,
    title        TEXT NOT NULL,
    url          TEXT NOT NULL UNIQUE,
    content      TEXT,
    summary      TEXT,
    category     TEXT NOT NULL,
    score        INTEGER DEFAULT 0,
    published_at TEXT,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS briefings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    date          TEXT NOT NULL,
    content       TEXT NOT NULL,
    article_count INTEGER DEFAULT 0,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
CREATE INDEX IF NOT EXISTS idx_articles_created ON articles(created_at);
CREATE INDEX IF NOT EXISTS idx_briefings_date ON briefings(date);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_parent_dir() -> None:
    parent = os.path.dirname(os.path.abspath(settings.DB_PATH))
    os.makedirs(parent, exist_ok=True)


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    _ensure_parent_dir()
    conn = sqlite3.connect(settings.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# --------------------------------------------------------------------------
# Article helpers
# --------------------------------------------------------------------------
def upsert_article(article: dict) -> bool:
    """Insert an article if its URL is new. Returns True if inserted."""
    with get_conn() as conn:
        cur = conn.execute("SELECT id FROM articles WHERE url = ?", (article["url"],))
        if cur.fetchone():
            return False
        conn.execute(
            """
            INSERT INTO articles
                (external_id, source, title, url, content, summary, category, score, published_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                article.get("external_id"),
                article["source"],
                article["title"],
                article["url"],
                article.get("content"),
                article.get("summary"),
                article["category"],
                int(article.get("score") or 0),
                article.get("published_at"),
                now_iso(),
            ),
        )
        return True


def set_article_summary(article_id: int, summary: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE articles SET summary = ? WHERE id = ?", (summary, article_id))


def list_articles(category: str | None = None, limit: int = 100) -> list[dict]:
    query = "SELECT * FROM articles"
    params: list = []
    if category:
        query += " WHERE category = ?"
        params.append(category)
    query += " ORDER BY datetime(created_at) DESC, score DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def articles_missing_summary(limit: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM articles WHERE summary IS NULL OR summary = '' "
            "ORDER BY score DESC, datetime(created_at) DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def recent_articles(limit: int = 30) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM articles ORDER BY datetime(created_at) DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------
# Briefing helpers
# --------------------------------------------------------------------------
def insert_briefing(date: str, content: str, article_count: int) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO briefings (date, content, article_count, created_at) VALUES (?, ?, ?, ?)",
            (date, content, article_count, now_iso()),
        )
        return int(cur.lastrowid)


def latest_briefing() -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM briefings ORDER BY datetime(created_at) DESC LIMIT 1"
        ).fetchone()
    return dict(row) if row else None


# --------------------------------------------------------------------------
# Chat helpers
# --------------------------------------------------------------------------
def insert_chat_message(role: str, content: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO chat_messages (role, content, created_at) VALUES (?, ?, ?)",
            (role, content, now_iso()),
        )
        return int(cur.lastrowid)


def recent_chat_messages(limit: int = 20) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM chat_messages ORDER BY datetime(created_at) DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]
