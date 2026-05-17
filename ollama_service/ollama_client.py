import logging
import httpx
from .config import settings
from .prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

async def generate_with_ollama(prompt: str) -> str:
    url = f"{settings.OLLAMA_HOST}/api/chat"

    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "format": "json"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
        except httpx.RequestError as exc:
            logger.error(f"Request error while calling Ollama at {exc.request.url!r}: {exc}")
            raise
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP {exc.response.status_code} from Ollama at {exc.request.url!r}")
            raise
