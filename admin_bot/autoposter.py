import asyncio
import logging
import httpx
import json
from datetime import datetime, timedelta
from sqlalchemy import select

from admin_bot.config import TOKEN, OLLAMA_HOST, CHANNEL_ID
from admin_bot.database import async_session, BotSetting, get_bot_setting, NewsArticle
from admin_bot.bot import bot

logger = logging.getLogger(__name__)

last_post_time = None

async def generate_ollama(prompt: str, model: str) -> str:
    try:
        async with httpx.AsyncClient() as client:
            payload = {"model": model, "prompt": prompt, "stream": False}
            res = await client.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=120.0)
            if res.status_code == 200:
                return res.json().get("response", "")
    except Exception as e:
        logger.error(f"Error generating via Ollama: {e}")
    return ""

async def generate_openai_api(prompt: str, model: str, api_key: str) -> str:
    try:
        async with httpx.AsyncClient() as client:
            payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
            headers = {"Authorization": f"Bearer {api_key}"}
            res = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=60.0)
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Error generating API (OpenAI): {e}")
    return ""

async def generate_ai_image(prompt: str, api_key: str) -> str | None:
    logger.info("Image generation requested. (API placeholder)")
    return None

async def process_generation(session, setting):
    """
    Checks for `approved` (or `pending` if auto_approve_news) articles, generates text, and marks as `pending_review` or `ready_to_post`.
    """
    valid_statuses = ["approved"]
    if getattr(setting, 'auto_approve_news', False):
        valid_statuses.append("pending")

    result = await session.execute(
        select(NewsArticle).where(NewsArticle.status.in_(valid_statuses)).order_by(NewsArticle.created_at.asc()).limit(1)
    )
    article = result.scalar_one_or_none()
    if not article: return
    
    logger.info(f"[Generation] Generating text for: {article.title}")
    sys_prompt = setting.prompt
    language = setting.language or "RU"
    style = setting.post_style or "informative"
    
    full_prompt = (
        f"Системные инструкции: {sys_prompt}\n"
        f"Требуемый язык: {language}. Стиль: {style}.\n\n"
        f"Новость:\nЗаголовок: {article.title}\nТекст: {article.content}\n"
        f"Источник: {article.source} ({article.url})\n\n"
        f"Напиши пост для Telegram канала как живой человек-блогер. "
        f"СТРОГОЕ ПРАВИЛО: НЕ ИСПОЛЬЗУЙ markdown-разметку (никаких звездочек **, решеток #, или таблиц). "
        f"Не делай списки с дефисами, пиши связным текстом с обычными абзацами и уместными эмодзи."
    )

    if setting.llm_source == "api" and setting.api_key:
        text = await generate_openai_api(full_prompt, setting.model, setting.api_key)
    else:
        text = await generate_ollama(full_prompt, setting.model)
    
    if text:
        import re
        text = re.sub(r'\*+', '', text) # Удаляет все звездочки (одну, две, сколько угодно)
        text = re.sub(r'#+\s?', '', text) # Удаляет хэштеги/заголовки Markdown
        text = text.replace('`', '')
        
        article.generated_text = text
        if getattr(setting, 'auto_post', False):
            article.status = "ready_to_post"
            logger.info(f"[Generation] Auto-post is ON -> status: ready_to_post")
        else:
            article.status = "pending_review"
            logger.info(f"[Generation] Auto-post is OFF -> status: pending_review")
        await session.commit()
    else:
        logger.warning(f"[Generation] Failed to generate text for {article.title}")


async def process_publishing(session, setting, channels_to_post, now):
    """
    Checks for `ready_to_post` articles and posts them at intervals.
    """
    global last_post_time
    interval_td = timedelta(minutes=setting.schedule_interval)
    
    if last_post_time is not None and now < last_post_time + interval_td:
        return # Not time to post yet
        
    result = await session.execute(
        select(NewsArticle).where(NewsArticle.status == "ready_to_post").order_by(NewsArticle.created_at.asc()).limit(1)
    )
    article = result.scalar_one_or_none()
    
    if not article: return
    
    logger.info(f"[Publishing] Preparing to publish: {article.title}")
    text = article.generated_text or article.content # fallback to raw content if generated_text is missing somehow
    
    # Optional image generated block omitted for MVP
    
    for target_channel in channels_to_post:
        try:
            for i in range(0, len(text), 4000):
                await bot.send_message(chat_id=target_channel, text=text[i:i+4000])
            logger.info(f"[Publishing] Successfully posted to {target_channel}.")
        except Exception as e:
            logger.error(f"[Publishing] Failed to post to {target_channel}: {e}")
    
    article.status = "posted"
    await session.commit()
    last_post_time = now

async def autoposter_loop():
    logger.info("Autoposter background task started.")
    while True:
        try:
            async with async_session() as session:
                setting = await get_bot_setting(session)
                
                if setting and setting.is_active and setting.prompt and setting.model:
                    # Determine channels
                    channels_to_post = []
                    if setting.target_channels:
                        try: channels_to_post = json.loads(setting.target_channels)
                        except: pass
                    if not channels_to_post:
                        c = int(CHANNEL_ID) if CHANNEL_ID else (setting.channel_id if setting else None)
                        if c: channels_to_post = [c]

                    if channels_to_post:
                        now = datetime.now()
                        # 1. Attempt generation (Runs anytime there is a pending article)
                        await process_generation(session, setting)
                        
                        # 2. Attempt publishing (Runs only if timeline permits and ready_to_post is available)
                        await process_publishing(session, setting, channels_to_post, now)
        except Exception as e:
            logger.error(f"Error in autoposter loop: {e}")
            
        await asyncio.sleep(20) # check loop every 20 seconds
