import asyncio
import logging
import re
import httpx
import json
from datetime import datetime, timedelta
from sqlalchemy import select

from admin_bot.config import OLLAMA_HOST, CHANNEL_ID
from admin_bot.database import async_session, get_bot_setting, NewsArticle, Worker
from admin_bot.bot import bot

logger = logging.getLogger(__name__)

last_post_time: datetime | None = None
_post_lock = asyncio.Lock()

# Days index aligned with datetime.weekday() (Mon=0 ... Sun=6)
_DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
# How long after a scheduled slot is it still valid to post (minutes)
_SCHEDULE_WINDOW_MIN = 2


# ---------------------------------------------------------------------------
# Schedule helpers
# ---------------------------------------------------------------------------

def _should_post_scheduled(schedule_json: str, last_post_dt: datetime | None, now: datetime) -> bool:
    """Return True if the current UTC time falls within any scheduled slot."""
    try:
        schedule = json.loads(schedule_json or "{}")
    except Exception:
        return False

    today_key = _DAY_KEYS[now.weekday()]
    for slot in schedule.get(today_key, []):
        try:
            hour, minute = map(int, slot.split(":"))
        except (ValueError, AttributeError):
            continue
        slot_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        window_end = slot_dt + timedelta(minutes=_SCHEDULE_WINDOW_MIN)
        if slot_dt <= now < window_end:
            if last_post_dt is None or last_post_dt < slot_dt:
                return True
    return False


def _clean_markdown(text: str) -> str:
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"#+\s?", "", text)
    return text.replace("`", "")


# ---------------------------------------------------------------------------
# AI generation — one function per provider
# ---------------------------------------------------------------------------

async def _generate_ollama(prompt: str, model: str) -> str:
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120.0,
        )
        res.raise_for_status()
        return res.json().get("response", "")


async def _generate_openai_compatible(
    prompt: str, model: str, api_key: str, base_url: str
) -> str:
    """Works for OpenAI and any OpenAI-compatible endpoint (OpenRouter, etc.)."""
    base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2000,
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=90.0)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]


async def _generate_anthropic(prompt: str, model: str, api_key: str) -> str:
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": prompt}],
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            headers=headers,
            timeout=90.0,
        )
        res.raise_for_status()
        return res.json()["content"][0]["text"]


async def _generate_gemini(prompt: str, model: str, api_key: str) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    async with httpx.AsyncClient() as client:
        res = await client.post(url, json=payload, timeout=90.0)
        res.raise_for_status()
        return res.json()["candidates"][0]["content"]["parts"][0]["text"]


async def _call_llm(setting) -> str:
    """Dispatch to the correct AI provider based on setting.llm_source."""
    source = (setting.llm_source or "ollama").strip()
    model = setting.model or "llama3.2"
    api_key = setting.api_key or ""
    base_url = setting.api_base_url or ""

    if source == "ollama":
        return await _generate_ollama("", model)  # prompt passed below; see caller

    if source == "openai":
        return await _generate_openai_compatible("", model, api_key, base_url or "https://api.openai.com/v1")

    if source == "openrouter":
        return await _generate_openai_compatible("", model, api_key, base_url or "https://openrouter.ai/api/v1")

    if source == "anthropic":
        return await _generate_anthropic("", model, api_key)

    if source == "gemini":
        return await _generate_gemini("", model, api_key)

    logger.warning(f"[LLM] Unknown source '{source}', falling back to Ollama")
    return await _generate_ollama("", model)


async def generate_text(prompt: str, setting) -> str:
    """Generate text using the configured provider. Returns empty string on failure."""
    source = (setting.llm_source or "ollama").strip()
    model = setting.model or "llama3.2"
    api_key = setting.api_key or ""
    base_url = setting.api_base_url or ""

    try:
        if source == "ollama":
            return await _generate_ollama(prompt, model)
        if source == "openai":
            return await _generate_openai_compatible(prompt, model, api_key, base_url or "https://api.openai.com/v1")
        if source == "openrouter":
            return await _generate_openai_compatible(prompt, model, api_key, base_url or "https://openrouter.ai/api/v1")
        if source == "anthropic":
            return await _generate_anthropic(prompt, model, api_key)
        if source == "gemini":
            return await _generate_gemini(prompt, model, api_key)
    except Exception as e:
        logger.error(f"[LLM] Provider '{source}' error: {e}")

    if source != "ollama":
        logger.info(f"[LLM] Falling back to Ollama after '{source}' failure")
        try:
            return await _generate_ollama(prompt, model)
        except Exception as e:
            logger.error(f"[LLM] Ollama fallback also failed: {e}")

    return ""


# ---------------------------------------------------------------------------
# Worker dispatch
# ---------------------------------------------------------------------------

async def _get_worker_for_channel(session, channel_id: int) -> Worker | None:
    result = await session.execute(select(Worker).where(Worker.is_active == True))
    for worker in result.scalars().all():
        try:
            if channel_id in json.loads(worker.channels or "[]"):
                return worker
        except Exception:
            pass
    return None


async def _dispatch_to_worker(worker: Worker, text: str, channel_id: int) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{worker.url.rstrip('/')}/api/publish",
                json={"token": worker.token, "channel_id": channel_id, "text": text},
                timeout=30.0,
            )
            if res.status_code == 200:
                logger.info(f"[Worker] '{worker.name}' published to channel {channel_id}.")
                return True
            logger.error(f"[Worker] '{worker.name}' returned {res.status_code}: {res.text[:200]}")
    except Exception as e:
        logger.error(f"[Worker] Failed to reach '{worker.name}': {e}")
    return False


# ---------------------------------------------------------------------------
# Core loops
# ---------------------------------------------------------------------------

async def process_generation(session, setting) -> None:
    valid_statuses = ["approved"]
    if getattr(setting, "auto_approve_news", False):
        valid_statuses.append("pending")

    result = await session.execute(
        select(NewsArticle)
        .where(NewsArticle.status.in_(valid_statuses))
        .order_by(NewsArticle.created_at.asc())
        .limit(1)
    )
    article = result.scalar_one_or_none()
    if not article:
        return

    logger.info(f"[Generation] Generating: {article.title}")

    full_prompt = (
        f"Системные инструкции: {setting.prompt}\n"
        f"Требуемый язык: {setting.language or 'RU'}. Стиль: {setting.post_style or 'informative'}.\n\n"
        f"Новость:\nЗаголовок: {article.title}\nТекст: {article.content}\n"
        f"Источник: {article.source} ({article.url})\n\n"
        "Напиши пост для Telegram канала как живой человек-блогер. "
        "СТРОГОЕ ПРАВИЛО: НЕ ИСПОЛЬЗУЙ markdown-разметку (никаких звездочек **, решеток #, таблиц). "
        "Не делай списки с дефисами, пиши связным текстом с обычными абзацами и уместными эмодзи."
    )

    text = await generate_text(full_prompt, setting)

    if text:
        article.generated_text = _clean_markdown(text)
        article.status = "ready_to_post" if getattr(setting, "auto_post", False) else "pending_review"
        logger.info(f"[Generation] Status → {article.status}")
        await session.commit()
    else:
        logger.warning(f"[Generation] No text produced for: {article.title}")


async def process_publishing(session, setting, channels_to_post: list, now: datetime) -> None:
    global last_post_time

    async with _post_lock:
        # Decide whether it is time to post
        mode = getattr(setting, "schedule_mode", "interval") or "interval"
        if mode == "weekly":
            if not _should_post_scheduled(setting.post_schedule or "{}", last_post_time, now):
                return
        else:
            interval_td = timedelta(minutes=max(1, setting.schedule_interval or 60))
            if last_post_time is not None and now < last_post_time + interval_td:
                return

        result = await session.execute(
            select(NewsArticle)
            .where(NewsArticle.status == "ready_to_post")
            .order_by(NewsArticle.created_at.asc())
            .limit(1)
        )
        article = result.scalar_one_or_none()
        if not article:
            return

        logger.info(f"[Publishing] Publishing: {article.title}")
        text = article.generated_text or article.content

        for channel_id in channels_to_post:
            # Try assigned worker first
            worker = await _get_worker_for_channel(session, channel_id)
            if worker:
                success = await _dispatch_to_worker(worker, text, channel_id)
                if success:
                    continue
                logger.warning(f"[Publishing] Worker failed for {channel_id}, falling back to local publish.")

            # Local publish with retry
            for attempt, delay in enumerate([0, 2, 5], start=1):
                if delay:
                    await asyncio.sleep(delay)
                try:
                    for i in range(0, len(text), 4000):
                        await bot.send_message(chat_id=channel_id, text=text[i : i + 4000])
                    logger.info(f"[Publishing] Posted locally to {channel_id}.")
                    break
                except Exception as e:
                    logger.error(f"[Publishing] Attempt {attempt}/3 failed for {channel_id}: {e}")

        article.status = "posted"
        await session.commit()
        last_post_time = now


async def autoposter_loop() -> None:
    logger.info("Autoposter background task started.")
    while True:
        try:
            async with async_session() as session:
                setting = await get_bot_setting(session)

                if setting and setting.is_active and setting.prompt and setting.model:
                    channels_to_post: list = []
                    if setting.target_channels:
                        try:
                            channels_to_post = json.loads(setting.target_channels)
                        except Exception as e:
                            logger.error(f"JSON parse error for target_channels: {e}")
                    if not channels_to_post:
                        raw_cid = CHANNEL_ID or (setting.channel_id if setting else None)
                        if raw_cid:
                            channels_to_post = [int(raw_cid)]

                    if channels_to_post:
                        now = datetime.utcnow()
                        await process_generation(session, setting)
                        await process_publishing(session, setting, channels_to_post, now)
        except Exception as e:
            logger.error(f"Autoposter loop error: {e}")

        await asyncio.sleep(20)
