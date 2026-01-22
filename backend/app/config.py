from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./neuroresolv.db"
    secret_key: str = "dev-secret-key-not-for-production-use-only"
    access_token_expire_minutes: int = 1440
    
    google_api_key: str = "sample-gemini-api-key"
    openai_api_key: str = "sample-openai-api-key"
    
    opik_api_key: str = "sample-opik-api-key"
    opik_workspace: str = "default"
    opik_project_name: str = "neuroresolv"
    
    chroma_persist_directory: str = "./chroma_data"
    
    environment: str = "development"
    debug: bool = True
    
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
