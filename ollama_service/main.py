from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import json
from .models import NewsItemIn, PostOut
from .prompts import build_post_prompt
from .ollama_client import generate_with_ollama

app = FastAPI(title="Ollama News Generator")

@app.post("/generate_post", response_model=PostOut)
async def generate_post(news: NewsItemIn):
    try:
        user_prompt = build_post_prompt(news)
        raw_response = await generate_with_ollama(user_prompt)
        
        # Parse the JSON response from Ollama
        try:
            parsed_response = json.loads(raw_response)
        except json.JSONDecodeError:
             raise HTTPException(status_code=500, detail="Failed to parse JSON from LLM response")

        return PostOut(**parsed_response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok"}
