"""Pydantic request/response models."""
from __future__ import annotations

from pydantic import BaseModel


class Article(BaseModel):
    id: int
    external_id: str | None = None
    source: str
    title: str
    url: str
    content: str | None = None
    summary: str | None = None
    category: str
    score: int = 0
    published_at: str | None = None
    created_at: str


class Briefing(BaseModel):
    id: int
    date: str
    content: str
    article_count: int
    created_at: str


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatTurn] = []


class ChatResponse(BaseModel):
    answer: str
    sources: list[Article] = []


class PipelineResult(BaseModel):
    status: str
    fetched: int
    inserted: int
    summarized: int
    briefing_id: int | None = None


class SettingsModel(BaseModel):
    categories: dict[str, bool]
    llm_provider: str


class SettingsUpdate(BaseModel):
    categories: dict[str, bool] | None = None
    llm_provider: str | None = None
