"""
Worker Service — runs on a remote PC and publishes Telegram posts on behalf of the orchestrator.

The orchestrator (admin_bot) calls POST /api/publish with the post text, channel ID,
and the Telegram bot token this worker should use.

Start with:
    uvicorn worker_service.main:app --host 0.0.0.0 --port 8010
"""

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from worker_service.config import WORKER_NAME, WORKER_AUTH_TOKEN, ORCHESTRATOR_URL, WORKER_PORT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Worker '{WORKER_NAME}' started on port {WORKER_PORT}.")
    if ORCHESTRATOR_URL:
        await _auto_register()
    yield


app = FastAPI(title=f"Worker Service: {WORKER_NAME}", lifespan=lifespan)


async def _auto_register():
    """Optionally register this worker with the orchestrator on startup."""
    import socket
    try:
        hostname = socket.gethostname()
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{ORCHESTRATOR_URL.rstrip('/')}/api/workers",
                json={
                    "name": WORKER_NAME,
                    "url": f"http://{hostname}:{WORKER_PORT}",
                    "token": "",   # token is managed per-worker; orchestrator stores it
                    "channels": "[]",
                },
                timeout=5.0,
            )
            if res.status_code == 200:
                logger.info("Auto-registered with orchestrator.")
            else:
                logger.warning(f"Auto-registration returned {res.status_code}.")
    except Exception as e:
        logger.warning(f"Auto-registration failed (non-fatal): {e}")


class PublishTask(BaseModel):
    token: str        # Telegram Bot API token
    channel_id: int   # target channel ID
    text: str         # post text (plain, no markdown)
    x_worker_auth: str | None = None  # optional inline auth (fallback)


def _check_auth(x_worker_auth: str):
    if WORKER_AUTH_TOKEN and x_worker_auth != WORKER_AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid worker auth token")


@app.post("/api/publish")
async def publish(task: PublishTask, x_worker_auth: str = Header(default="")):
    _check_auth(x_worker_auth)

    if not task.token:
        raise HTTPException(status_code=400, detail="token is required")
    if not task.text:
        raise HTTPException(status_code=400, detail="text is required")

    tg_api = f"https://api.telegram.org/bot{task.token}"
    errors = []

    async with httpx.AsyncClient() as client:
        # Split long messages into 4000-char chunks
        chunks = [task.text[i : i + 4000] for i in range(0, len(task.text), 4000)]
        for chunk in chunks:
            payload = {"chat_id": task.channel_id, "text": chunk}
            for attempt in range(1, 4):
                try:
                    res = await client.post(f"{tg_api}/sendMessage", json=payload, timeout=15.0)
                    if res.status_code == 200:
                        logger.info(f"[{WORKER_NAME}] Sent chunk to {task.channel_id}.")
                        break
                    err = res.json().get("description", res.text)
                    logger.error(f"[{WORKER_NAME}] Attempt {attempt}: TG error: {err}")
                    errors.append(err)
                except Exception as e:
                    logger.error(f"[{WORKER_NAME}] Attempt {attempt}: {e}")
                    errors.append(str(e))

    if errors:
        return {"status": "partial", "errors": errors}
    return {"status": "ok", "worker": WORKER_NAME}


@app.get("/health")
def health():
    return {"status": "ok", "worker": WORKER_NAME}
