"""Jarvis FastAPI application — Phase 1 MVP."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import database as db
from . import runtime_settings
from .agents import summarization_agent
from .config import settings
from .pipeline import run_pipeline
from .scheduler import shutdown_scheduler, start_scheduler
from .schemas import (
    Article,
    Briefing,
    ChatRequest,
    ChatResponse,
    PipelineResult,
    SettingsModel,
    SettingsUpdate,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("jarvis")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    runtime_settings.load()  # seed settings file
    start_scheduler()
    if settings.RUN_PIPELINE_ON_STARTUP and db.latest_briefing() is None:
        # Run once in the background so startup isn't blocked on network I/O.
        logger.info("No briefing found; kicking off initial pipeline run.")
        asyncio.create_task(run_pipeline())
    yield
    shutdown_scheduler()


app = FastAPI(title="Jarvis", version="1.0.0", description="Self-hosted AI intelligence assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "provider": runtime_settings.active_provider()}


@app.get("/briefing/latest", response_model=Briefing)
async def briefing_latest() -> Briefing:
    briefing = db.latest_briefing()
    if not briefing:
        raise HTTPException(status_code=404, detail="No briefing yet. Trigger /pipeline/run.")
    return Briefing(**briefing)


@app.get("/articles", response_model=list[Article])
async def articles(
    category: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[Article]:
    rows = db.list_articles(category=category, limit=limit)
    return [Article(**r) for r in rows]


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")

    context = db.recent_articles(limit=30)
    history = [turn.model_dump() for turn in req.history]

    db.insert_chat_message("user", req.message)
    answer = await summarization_agent.answer_question(req.message, context, history)
    db.insert_chat_message("assistant", answer)

    # Surface a few of the most relevant recent articles as sources.
    sources = [Article(**a) for a in context[:5]]
    return ChatResponse(answer=answer, sources=sources)


@app.post("/pipeline/run", response_model=PipelineResult)
async def pipeline_run() -> PipelineResult:
    result = await run_pipeline()
    return PipelineResult(**result)


@app.get("/settings", response_model=SettingsModel)
async def get_settings_endpoint() -> SettingsModel:
    return SettingsModel(**runtime_settings.load())


@app.put("/settings", response_model=SettingsModel)
async def update_settings_endpoint(update: SettingsUpdate) -> SettingsModel:
    payload = {k: v for k, v in update.model_dump().items() if v is not None}
    saved = runtime_settings.save(payload)
    return SettingsModel(**saved)
