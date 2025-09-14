# api/app/settings.py
import os
from pydantic import BaseModel

class Settings(BaseModel):
    ENV: str = os.getenv("ENV", "production")
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./local.db")
    APP_NAME: str = "Signal & Scale"
    TZ: str = "America/Chicago"

settings = Settings()
