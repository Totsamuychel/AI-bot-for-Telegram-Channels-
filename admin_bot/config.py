import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
ADMIN_IDS = [int(id_str) for id_str in os.getenv("ADMIN_IDS", "").split(",") if id_str.strip()]
CHANNEL_ID = os.getenv("CHANNEL_ID", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///local_bot.db")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
