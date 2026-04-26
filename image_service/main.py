from fastapi import FastAPI, HTTPException
from .models import ImageIn, ImageOut
from .client import generate_image

app = FastAPI(title="Image Generator Service")

@app.post("/generate_image", response_model=ImageOut)
async def generate_image_endpoint(payload: ImageIn):
    try:
        image_url = await generate_image(payload.prompt)
        return ImageOut(image_url=image_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok"}
