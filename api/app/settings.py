# api/app/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    ENV: str = "development"
    SAFE_MODE: bool = True  # set False to hit real agents
    OPENAI_API_KEY: str | None = None

    # Comma-separated list in env: ALLOWED_ORIGINS="https://signal-scale-frontend.onrender.com,http://localhost:5173"
    ALLOWED_ORIGINS: List[str] = []

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
