from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional

class NewsItemOut(BaseModel):
    title: str
    description: str
    url: str
    source: str
    published_at: Optional[datetime] = None
