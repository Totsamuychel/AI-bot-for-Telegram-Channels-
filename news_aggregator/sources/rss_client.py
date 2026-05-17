import asyncio
import logging
import feedparser
from typing import List
from ..models import NewsItemOut
from datetime import datetime

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    "https://feeds.feedburner.com/TechCrunch/",
    "https://www.theverge.com/rss/index.xml",
    "https://arstechnica.com/feed/"
]

_RSS_TIMEOUT = 15.0


def _parse_feed_sync(url: str) -> feedparser.FeedParserDict:
    return feedparser.parse(url)


async def fetch_rss_news(limit: int = 5) -> List[NewsItemOut]:
    all_news = []
    loop = asyncio.get_event_loop()

    for url in RSS_FEEDS:
        try:
            feed = await asyncio.wait_for(
                loop.run_in_executor(None, _parse_feed_sync, url),
                timeout=_RSS_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.warning(f"RSS feed timed out after {_RSS_TIMEOUT}s: {url}")
            continue
        except Exception as e:
            logger.error(f"Failed to fetch RSS feed {url}: {e}")
            continue

        for entry in feed.entries[:limit]:
            published = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6])
                except Exception as e:
                    logger.debug(f"Could not parse date for entry in {url}: {e}")

            item = NewsItemOut(
                title=entry.get("title", "No Title"),
                description=entry.get("summary", "")[:500],
                url=entry.get("link", ""),
                source=feed.feed.get("title", "Unknown Source"),
                published_at=published
            )
            all_news.append(item)

    return sorted(all_news, key=lambda x: x.published_at or datetime.min, reverse=True)[:limit]
