# api/app/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

class Settings(BaseSettings):
    ENV: str = "development"
    OPENAI_API_KEY: Optional[str] = None
    CORS_ORIGINS: List[str] = ["*"]  # or set to your exact frontend origin(s)
    SAFE_MODE: bool = True  # <-- default True so your UI works now

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()