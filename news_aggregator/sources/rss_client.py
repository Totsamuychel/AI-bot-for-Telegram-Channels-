import feedparser
from typing import List
from ..models import NewsItemOut
from datetime import datetime

# Example Tech RSS Feeds
RSS_FEEDS = [
    "https://feeds.feedburner.com/TechCrunch/",
    "https://www.theverge.com/rss/index.xml",
    "https://arstechnica.com/feed/"
]

async def fetch_rss_news(limit: int = 5) -> List[NewsItemOut]:
    all_news = []
    
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:limit]:
            # Basic parsing, handling time formats can be complex so skipping precise datetime parsing for simplicity in this MVP
            published = None
            if hasattr(entry, 'published_parsed'):
                 try:
                    published = datetime.fromtimestamp(datetime(*entry.published_parsed[:6]).timestamp())
                 except:
                    pass

            item = NewsItemOut(
                title=entry.get("title", "No Title"),
                description=entry.get("summary", "")[:500], # Truncate description
                url=entry.get("link", ""),
                source=feed.feed.get("title", "Unknown Source"),
                published_at=published
            )
            all_news.append(item)
            
    # Sort by published date if available
    return sorted(all_news, key=lambda x: x.published_at or datetime.min, reverse=True)[:limit]
