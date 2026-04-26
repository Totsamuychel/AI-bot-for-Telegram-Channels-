from pydantic import BaseModel, HttpUrl

class ImageIn(BaseModel):
    prompt: str

class ImageOut(BaseModel):
    image_url: str
