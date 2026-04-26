import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://ollama:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")

    class Config:
        env_file = ".env"

settings = Settings()
