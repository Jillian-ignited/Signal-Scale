from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    APP_NAME: str = "Signal & Scale API"
    ENV: str = "development"
    
    # Database
    DATABASE_URL: str = "sqlite:///./signal_scale.db"
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = None
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
