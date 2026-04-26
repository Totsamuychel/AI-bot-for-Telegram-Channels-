import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import httpx
from sqlalchemy import select, delete, func
import psutil
from datetime import datetime, timedelta

from admin_bot.database import init_db, async_session, BotSetting, get_bot_setting, NewsArticle, SettingsPreset
from admin_bot.config import OLLAMA_HOST
from admin_bot.bot import bot as tg_bot, dp
from admin_bot.autoposter import autoposter_loop

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import os
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
bg_tasks = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application lifecycle...")
    await init_db()
    
    # Start bot polling in background
    bot_task = asyncio.create_task(dp.start_polling(tg_bot))
    bg_tasks.append(bot_task)
    
    # Start autoposter
    poster_task = asyncio.create_task(autoposter_loop())
    bg_tasks.append(poster_task)
    
    yield
    
    logger.info("Shutting down application lifecycle...")
    for task in bg_tasks:
        task.cancel()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root(request: Request):
    setting = None
    try:
        async with async_session() as session:
            setting = await get_bot_setting(session)
    except Exception as e:
        logger.error(f"Error fetching settings: {e}")
        
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"setting": setting}
    )

class SettingsUpdate(BaseModel):
    channel_id: int | None = None
    prompt: str
    model: str
    schedule_interval: int
    is_active: bool
    llm_source: str = "ollama"
    api_key: str | None = None
    language: str = "RU"
    post_style: str = "informative"
    image_source: str = "none"
    extra_admins: str = "[]"
    target_channels: str = "[]"
    auto_post: bool = False
    auto_approve_news: bool = False

@app.post("/api/settings")
async def update_settings(data: SettingsUpdate):
    try:
        async with async_session() as session:
            setting = await get_bot_setting(session)
                
            setting.channel_id = data.channel_id
            setting.prompt = data.prompt
            setting.model = data.model
            setting.schedule_interval = data.schedule_interval
            setting.is_active = data.is_active
            setting.llm_source = data.llm_source
            setting.api_key = data.api_key
            setting.language = data.language
            setting.post_style = data.post_style
            setting.image_source = data.image_source
            setting.extra_admins = data.extra_admins
            setting.target_channels = data.target_channels
            setting.auto_post = data.auto_post
            setting.auto_approve_news = data.auto_approve_news
            await session.commit()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/models")
async def get_models():
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{OLLAMA_HOST}/api/tags", timeout=5.0)
            if res.status_code == 200:
                models = res.json().get("models", [])
                return {"models": [m["name"] for m in models]}
    except Exception as e:
        logger.error(f"Failed to fetch models: {e}")
    return {"models": []}

class NewsItemBase(BaseModel):
    title: str
    url: str
    content: str | None = None
    source: str = "unknown"

class PresetCreate(BaseModel):
    name: str

class NewsStatusUpdate(BaseModel):
    status: str
    content: str | None = None
    generated_text: str | None = None

@app.get("/api/news")
async def get_news():
    try:
        async with async_session() as session:
            result = await session.execute(
                select(NewsArticle).order_by(NewsArticle.created_at.desc()).limit(100)
            )
            articles = result.scalars().all()
            return {"articles": [
                {
                    "id": a.id,
                    "title": a.title,
                    "url": a.url,
                    "content": a.content,
                    "source": a.source,
                    "generated_text": a.generated_text,
                    "status": a.status,
                    "created_at": a.created_at.isoformat() if a.created_at else None
                } for a in articles
            ]}
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return {"articles": []}

@app.post("/api/news/ingest")
async def ingest_news(item: NewsItemBase):
    try:
        async with async_session() as session:
            # Check if exists
            result = await session.execute(select(NewsArticle).where(NewsArticle.url == item.url))
            if result.scalar_one_or_none() is None:
                new_article = NewsArticle(
                    title=item.title,
                    url=item.url,
                    content=item.content,
                    source=item.source,
                    status="pending"
                )
                session.add(new_article)
                await session.commit()
                return {"status": "ok", "message": "Ingested"}
            return {"status": "ignored", "message": "Already exists"}
    except Exception as e:
        logger.error(f"Error ingesting news: {e}")
        return {"status": "error", "message": str(e)}

@app.put("/api/news/{article_id}")
async def update_news(article_id: int, data: NewsStatusUpdate):
    try:
        async with async_session() as session:
            result = await session.execute(select(NewsArticle).where(NewsArticle.id == article_id))
            article = result.scalar_one_or_none()
            if article:
                article.status = data.status
                if data.content is not None:
                    article.content = data.content
                if data.generated_text is not None:
                    article.generated_text = data.generated_text
                await session.commit()
                return {"status": "ok"}
            return {"status": "error", "message": "Not found"}
    except Exception as e:
        logger.error(f"Error updating article: {e}")
        return {"status": "error", "message": str(e)}

@app.delete("/api/news/{news_id}")
async def delete_news(news_id: int):
    async with async_session() as session:
        try:
            result = await session.execute(select(NewsArticle).where(NewsArticle.id == news_id))
            article = result.scalar_one_or_none()
            if article:
                await session.delete(article)
                await session.commit()
                return {"status": "ok"}
            return {"status": "error", "message": "Not found"}
        except Exception as e:
            logger.error(f"Error deleting news: {e}")
            return {"status": "error", "message": "Failed to delete from DB"}

@app.delete("/api/news/all")
async def delete_all_news():
    async with async_session() as session:
        try:
            await session.execute(delete(NewsArticle))
            await session.commit()
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Error purging news: {e}")
            return {"status": "error", "message": "Failed to reset base"}

@app.post("/api/force_scrape")
async def force_scrape():
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post("http://127.0.0.1:8001/api/force_scrape", timeout=20.0)
            return res.json()
    except Exception as e:
        logger.error(f"Error triggering force scrape: {e}")
        return {"status": "error", "message": "Could not connect to news aggregator"}

@app.get("/api/system/stats")
def system_stats():
    try:
        import subprocess
        import psutil
        
        try:
            out = subprocess.check_output(
                ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total', '--format=csv,noheader,nounits'], 
                encoding='utf-8', timeout=2.0
            ).strip().split('\n')[0]
            parts = [p.strip() for p in out.split(',')]
            gpu_load = float(parts[0])
            vram_used = float(parts[1])
            vram_total = float(parts[2])
            vram_percent = (vram_used / vram_total) * 100 if vram_total > 0 else 0
        except Exception:
            gpu_load = 0
            vram_used = 0
            vram_total = 0
            vram_percent = 0
            
        cpu = psutil.cpu_percent(interval=0.1)
        vm = psutil.virtual_memory()
        ram_used = vm.used / (1024 * 1024)
        ram_total = vm.total / (1024 * 1024)
        
        return {
            "status": "ok", 
            "gpu": gpu_load, "vram_percent": float(f"{vram_percent:.1f}"), "vram_used_mb": vram_used, "vram_total_mb": vram_total,
            "cpu": cpu, "ram_percent": vm.percent, "ram_used_mb": ram_used, "ram_total_mb": ram_total
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "gpu": 0, "vram_percent": 0, "vram_used_mb": 0, "vram_total_mb": 0}

@app.get("/api/system/ollama_active")
async def ollama_active():
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{OLLAMA_HOST}/api/ps", timeout=5.0)
            if res.status_code == 200:
                data = res.json()
                models = [m["name"] for m in data.get("models", [])]
                return {"status": "ok", "models": models}
            return {"status": "ok", "models": []}
    except Exception:
        return {"status": "ok", "models": []}

@app.get("/api/analytics")
async def get_analytics():
    async with async_session() as session:
        res_all = await session.execute(select(func.count(NewsArticle.id)))
        total = res_all.scalar() or 0
        
        res_posted = await session.execute(select(func.count(NewsArticle.id)).where(NewsArticle.status == "posted"))
        posted = res_posted.scalar() or 0
        
        res_rej = await session.execute(select(func.count(NewsArticle.id)).where(NewsArticle.status == "rejected"))
        rejected = res_rej.scalar() or 0
        
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        stmt = select(NewsArticle.created_at).where(NewsArticle.status == "posted", NewsArticle.created_at >= seven_days_ago)
        res_dates = await session.execute(stmt)
        dates = res_dates.scalars().all()
        
        daily = {}
        for i in range(7):
            d = (datetime.utcnow() - timedelta(days=6-i)).strftime("%Y-%m-%d")
            daily[d] = 0
        for dt in dates:
            if dt:
                d_str = dt.strftime("%Y-%m-%d")
                if d_str in daily:
                    daily[d_str] += 1
                
        return {
            "total": total,
            "posted": posted,
            "rejected": rejected,
            "labels": list(daily.keys()),
            "data": list(daily.values())
        }

@app.get("/api/presets")
async def get_presets():
    async with async_session() as session:
        result = await session.execute(select(SettingsPreset))
        presets = result.scalars().all()
        return {"status": "ok", "presets": [{"id": p.id, "name": p.name} for p in presets]}

@app.post("/api/presets")
async def create_preset(data: PresetCreate):
    async with async_session() as session:
        try:
            result = await session.execute(select(BotSetting).where(BotSetting.id == 1))
            setting = result.scalar_one_or_none()
            if not setting: return {"status": "error"}
            
            p = SettingsPreset(
                name=data.name,
                prompt=setting.prompt,
                model=setting.model,
                schedule_interval=setting.schedule_interval,
                llm_source=setting.llm_source,
                api_key=setting.api_key,
                language=setting.language,
                post_style=setting.post_style,
                image_source=setting.image_source,
                target_channels=setting.target_channels,
                extra_admins=setting.extra_admins
            )
            session.add(p)
            await session.commit()
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

@app.post("/api/presets/load/{preset_id}")
async def load_preset(preset_id: int):
    async with async_session() as session:
        try:
            res = await session.execute(select(SettingsPreset).where(SettingsPreset.id == preset_id))
            preset = res.scalar_one_or_none()
            if not preset: return {"status": "error", "message": "Not found"}
            
            result = await session.execute(select(BotSetting).where(BotSetting.id == 1))
            setting = result.scalar_one_or_none()
            
            setting.prompt = preset.prompt
            setting.model = preset.model
            setting.schedule_interval = preset.schedule_interval
            setting.llm_source = preset.llm_source
            setting.api_key = preset.api_key
            setting.language = preset.language
            setting.post_style = preset.post_style
            setting.image_source = preset.image_source
            setting.target_channels = preset.target_channels
            setting.extra_admins = preset.extra_admins
            
            await session.commit()
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
