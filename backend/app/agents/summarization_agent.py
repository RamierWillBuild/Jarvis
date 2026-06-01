"""Summarization Agent — calls OpenAI, with Ollama as an optional fallback.

Provider is selected by the runtime setting (default from LLM_PROVIDER). If the
selected provider is unavailable or errors, we degrade gracefully:
  openai -> ollama -> extractive (first sentences). This keeps the pipeline and
the /briefing endpoint working even with no API keys configured.
"""
from __future__ import annotations

import re

import httpx

from ..config import settings
from .. import runtime_settings


def _extractive(text: str, max_chars: int = 320) -> str:
    """Naive offline fallback: clean text and take the first sentences."""
    clean = re.sub(r"<[^>]+>", " ", text or "")
    clean = re.sub(r"\s+", " ", clean).strip()
    if not clean:
        return "No summary available."
    if len(clean) <= max_chars:
        return clean
    sentences = re.split(r"(?<=[.!?])\s+", clean)
    out = ""
    for sentence in sentences:
        if len(out) + len(sentence) > max_chars:
            break
        out += sentence + " "
    return (out.strip() or clean[:max_chars]).strip()


async def _call_openai(prompt: str, system: str, max_tokens: int) -> str:
    from openai import AsyncOpenAI  # imported lazily so the dep is optional at runtime

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
    resp = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=0.4,
    )
    return (resp.choices[0].message.content or "").strip()


async def _call_ollama(prompt: str, system: str) -> str:
    async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS * 4) as client:
        resp = await client.post(
            f"{settings.OLLAMA_URL.rstrip('/')}/api/generate",
            json={
                "model": settings.OLLAMA_MODEL,
                "prompt": f"{system}\n\n{prompt}",
                "stream": False,
            },
        )
        resp.raise_for_status()
        return (resp.json().get("response") or "").strip()


async def _generate(prompt: str, system: str, max_tokens: int, fallback_text: str) -> str:
    """Try the active provider, then the other, then extractive fallback."""
    provider = runtime_settings.active_provider()
    order = ["openai", "ollama"] if provider == "openai" else ["ollama", "openai"]

    for name in order:
        try:
            if name == "openai":
                if not settings.OPENAI_API_KEY:
                    continue
                result = await _call_openai(prompt, system, max_tokens)
            else:
                result = await _call_ollama(prompt, system)
            if result:
                return result
        except Exception:
            # Network error, bad key, model missing — fall through to next option.
            continue

    # No provider available: return the caller-prepared fallback verbatim.
    # (Callers that want truncation pass an already-extracted string.)
    return fallback_text


async def summarize_article(title: str, content: str) -> str:
    system = (
        "You are a concise news analyst. Summarize the article in 2-3 sentences, "
        "focusing on what happened and why it matters. No preamble."
    )
    prompt = f"Title: {title}\n\nContent:\n{(content or title)[:4000]}"
    # Offline fallback for a single article is a short extractive summary.
    return await _generate(
        prompt, system, max_tokens=180, fallback_text=_extractive(content or title)
    )


async def generate_briefing(articles: list[dict]) -> str:
    """Produce a short narrative briefing from the day's top articles."""
    if not articles:
        return "No news was gathered for today's briefing yet. Try running the pipeline."

    lines = []
    for a in articles:
        snippet = a.get("summary") or _extractive(a.get("content") or "", 160)
        lines.append(f"- [{a['category']}] {a['title']}: {snippet}")
    digest = "\n".join(lines)

    system = (
        "You are Jarvis, a personal intelligence analyst. Write a crisp daily "
        "briefing (4-7 sentences) synthesizing the most important stories below. "
        "Group related themes, highlight what matters most, and keep a calm, "
        "informed tone. Do not invent facts beyond the provided items."
    )
    prompt = f"Here are today's gathered stories:\n\n{digest}\n\nWrite the briefing."

    fallback = "Today's top stories:\n\n" + digest
    return await _generate(prompt, system, max_tokens=500, fallback_text=fallback)


async def answer_question(question: str, articles: list[dict], history: list[dict]) -> str:
    """Answer a user question grounded in recent articles."""
    if not articles:
        context = "(no articles available yet)"
    else:
        context = "\n".join(
            f"- [{a['category']}] {a['title']}: {a.get('summary') or _extractive(a.get('content') or '', 160)} ({a['url']})"
            for a in articles
        )

    history_text = ""
    for turn in history[-6:]:
        history_text += f"{turn['role'].upper()}: {turn['content']}\n"

    system = (
        "You are Jarvis, a personal intelligence assistant. Answer the user's "
        "question using ONLY the recent news context provided. If the answer is "
        "not in the context, say so plainly. Cite article titles when relevant."
    )
    prompt = (
        f"Recent news context:\n{context}\n\n"
        f"{('Conversation so far:\n' + history_text) if history_text else ''}"
        f"User question: {question}"
    )

    fallback = (
        "I can't reach a language model right now, but here are the most relevant "
        "recent headlines:\n\n"
        + "\n".join(f"- {a['title']} ({a['url']})" for a in articles[:5])
    )
    return await _generate(prompt, system, max_tokens=600, fallback_text=fallback)
