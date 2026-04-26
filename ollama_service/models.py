from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class NewsItemIn(BaseModel):
    title: str
    description: str
    url: HttpUrl
    source: str

class PostOut(BaseModel):
    title: str
    body: str
    tags: List[str]
    image_prompt: str
