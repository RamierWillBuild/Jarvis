# Jarvis

Self-hosted AI intelligence assistant. Gathers tech & world news, summarizes it
with an LLM, and serves a daily briefing plus a conversational Q&A interface.

> **Phase 1 (MVP).** News Agent + Summarization Agent only. Trend, Impact,
> Investment, and Memory agents are intentionally **not** built yet.

## Architecture

```
backend/   FastAPI + APScheduler + SQLite
  app/
    main.py                  HTTP API + lifespan (scheduler, startup pipeline)
    pipeline.py              fetch -> store -> summarize -> briefing
    scheduler.py             APScheduler cron (every 6h, configurable)
    database.py              SQLite: articles, briefings, chat_messages
    runtime_settings.py      user-editable settings (categories, provider)
    config.py                all env-var configuration
    agents/
      news_agent.py          HackerNews API + 3 configurable RSS feeds
      summarization_agent.py OpenAI, with Ollama fallback, then offline extractive
frontend/  React + Vite (dark dashboard)
  src/pages/  Dashboard · Chat · Settings
docker-compose.yml   api + frontend services with hot reload
.env.example         all configuration
```

Agents are **plain async Python functions** — no LangChain or agent framework.

## API

| Method | Path                      | Description                              |
|--------|---------------------------|------------------------------------------|
| GET    | `/briefing/latest`        | Today's generated briefing               |
| POST   | `/chat`                   | Conversational Q&A about recent news     |
| GET    | `/articles?category=`     | List fetched articles (optional filter)  |
| POST   | `/pipeline/run`           | Manually trigger the news pipeline       |
| GET    | `/settings`               | Current categories + LLM provider        |
| PUT    | `/settings`               | Update categories / provider             |
| GET    | `/health`                 | Liveness + active provider               |

Interactive docs at `http://localhost:8000/docs`.

## Quick start (Docker)

```bash
cp .env.example .env        # then add OPENAI_API_KEY (optional)
docker compose up --build
```

- Frontend → http://localhost:5173
- API → http://localhost:8000
- Both services hot-reload on source changes.

> No LLM key? Jarvis still works: summaries/briefings fall back to an offline
> extractive method, so `/briefing/latest` always responds.

## Local dev (without Docker)

**Backend**
```bash
cd backend
py -m venv .venv
.venv\Scripts\activate          # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

## Configuration

Everything is an environment variable — see [`.env.example`](.env.example).
Key options: `LLM_PROVIDER`, `OPENAI_API_KEY`, `OLLAMA_URL`, `NEWS_CATEGORIES`,
`RSS_FEEDS` (three `category::url` pairs), `PIPELINE_INTERVAL_HOURS`.

## How the pipeline works

1. **News Agent** fetches the top HackerNews stories and the configured RSS
   feeds concurrently, categorizes them, and de-duplicates by URL.
2. New articles are stored in SQLite.
3. **Summarization Agent** summarizes articles lacking a summary via the active
   LLM provider (OpenAI → Ollama → offline fallback).
4. A daily **briefing** is synthesized from the freshest top articles per
   category and stored.

Runs automatically every `PIPELINE_INTERVAL_HOURS` (default 6) and once on
first startup, or on demand via `POST /pipeline/run`.
