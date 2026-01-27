from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    aws_region: str = "us-east-1"
    db_secret_name: str = "rdb_creds"

    secret_key: str = "dev-secret-key-not-for-production-use-only"
    access_token_expire_minutes: int = 1440

    # API Keys
    google_api_key: str = "sample-gemini-api-key"
    openai_api_key: str = "sample-openai-api-key"

    # Opik Cloud Settings
    opik_api_key: str = "sample-opik-api-key"
    opik_workspace: str = "default"
    opik_project_name: str = "neuroresolv"

    # Application Settings
    environment: str = "development"
    debug: bool = True

    # Local Database Settings (Used when ENVIRONMENT="development")
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "neuroresolv"

    # CORS Origins (for frontend)
    # Include localhost for local dev and Vercel domains for production
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        # This might be not a good idea to include this
        "https://neuro-resolv.vercel.app",  
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
