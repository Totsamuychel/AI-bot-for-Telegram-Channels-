import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
ADMIN_IDS = [int(id_str) for id_str in os.getenv("ADMIN_IDS", "").split(",") if id_str.strip()]
CHANNEL_ID = os.getenv("CHANNEL_ID", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///local_bot.db")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
NEWS_AGGREGATOR_URL = os.getenv("NEWS_AGGREGATOR_URL", "http://news_aggregator:8002")
WEB_API_KEY = os.getenv("WEB_API_KEY", "")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:8003").split(",") if o.strip()]
WORKER_AUTH_TOKEN = os.getenv("WORKER_AUTH_TOKEN", "")
