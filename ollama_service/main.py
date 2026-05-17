import logging
from fastapi import FastAPI, HTTPException
import json
from .models import NewsItemIn, PostOut
from .prompts import build_post_prompt
from .ollama_client import generate_with_ollama

logger = logging.getLogger(__name__)

app = FastAPI(title="Ollama News Generator")

_MAX_RETRIES = 3

@app.post("/generate_post", response_model=PostOut)
async def generate_post(news: NewsItemIn):
    user_prompt = build_post_prompt(news)
    last_error: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            raw_response = await generate_with_ollama(user_prompt)
            try:
                parsed_response = json.loads(raw_response)
            except json.JSONDecodeError as e:
                logger.warning(f"Attempt {attempt}: invalid JSON from LLM: {e}. Raw: {raw_response[:200]}")
                last_error = e
                continue
            return PostOut(**parsed_response)
        except Exception as e:
            logger.error(f"Attempt {attempt}: error calling Ollama: {e}")
            last_error = e

    raise HTTPException(status_code=500, detail=f"Failed after {_MAX_RETRIES} attempts: {last_error}")

@app.get("/health")
def health_check():
    return {"status": "ok"}
