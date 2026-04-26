import asyncio
import logging
import httpx
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from typing import List
from .models import NewsItemOut
from .sources.rss_client import fetch_rss_news

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_scrape_workflow():
    news = await fetch_rss_news(limit=15)
    admin_bot_url = os.getenv("ADMIN_BOT_URL", "http://127.0.0.1:8000")
            
    async with httpx.AsyncClient() as client:
        for item in news:
            payload = {
                "title": item.title,
                "url": item.url,
                "content": item.description,
                "source": item.source
            }
            try:
                res = await client.post(f"{admin_bot_url}/api/news/ingest", json=payload, timeout=10.0)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("status") == "ok":
                        logger.info(f"Ingested new article: {item.title}")
            except Exception as e:
                logger.error(f"Error sending article to admin_bot: {e}")

async def scraper_loop():
    logger.info("Scraper background task started.")
    while True:
        try:
            await run_scrape_workflow()
        except Exception as e:
            logger.error(f"Error in scraper loop: {e}")
            
        await asyncio.sleep(1800) # scrape every 30 mins

bg_tasks = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background scraper
    scraper_task = asyncio.create_task(scraper_loop())
    bg_tasks.append(scraper_task)
    yield
    for task in bg_tasks:
        task.cancel()

app = FastAPI(title="News Aggregator Service", lifespan=lifespan)

@app.get("/news", response_model=List[NewsItemOut])
async def get_news(limit: int = 5, topic: str = "ai"):
    try:
        news = await fetch_rss_news(limit=limit * 2)
        if topic:
            filtered = [
                n for n in news 
                if topic.lower() in n.title.lower() or topic.lower() in n.description.lower()
            ]
            return filtered[:limit]
        return news[:limit]
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/force_scrape")
async def force_scrape():
    try:
        await run_scrape_workflow()
        return {"status": "ok", "message": "Scrape triggered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
