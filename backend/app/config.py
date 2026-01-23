from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database Settings
    database_url: str = "sqlite+aiosqlite:///./neuroresolv.db"
    
    # Postgres specific (optional, used if provided)
    postgres_user: str | None = ""
    postgres_password: str | None = ""
    postgres_host: str | None = ""
    postgres_port: int = 5432
    postgres_db: str | None = ""
    postgres_db: str | None = ""
    
    # AWS RDS IAM Authentication
    use_rds_iam_auth: bool = False
    aws_region: str = "us-east-1"
    
    secret_key: str = "dev-secret-key-not-for-production-use-only"
    access_token_expire_minutes: int = 1440
    
    google_api_key: str = "sample-gemini-api-key"
    openai_api_key: str = "sample-openai-api-key"
    
    # Opik Cloud Settings
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
    
    @property
    def async_database_url(self) -> str:
        if self.postgres_host and self.postgres_db and self.postgres_user:
            # Construct postgres URL if all required fields are present
            password = self.postgres_password or ""
            return f"postgresql+asyncpg://{self.postgres_user}:{password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        return self.database_url

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
