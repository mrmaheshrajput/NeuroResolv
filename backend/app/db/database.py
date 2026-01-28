"""
Database configuration for PostgreSQL with AWS Secrets Manager integration.

This module creates the async SQLAlchemy engine and session maker
using credentials fetched from AWS Secrets Manager.
"""

from functools import lru_cache
from urllib.parse import quote_plus

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings
from app.aws.secrets import get_db_credentials


class Base(DeclarativeBase):
    pass


@lru_cache(maxsize=1)
def get_database_url() -> str:
    """
    Build the PostgreSQL database URL.

    - In production: Uses credentials fetched from AWS Secrets Manager.
    - Otherwise: Uses local credentials from environment variables.

    Returns:
        PostgreSQL connection URL for asyncpg driver
    """
    settings = get_settings()
    
    if settings.environment == "production":
        creds_fetch = get_db_credentials(
            secret_name=settings.db_secret_name,
            region_name=settings.aws_region,
        )
        creds = {
            "username": creds_fetch["username"],
            "password": creds_fetch["password"],
            "host": creds_fetch["host"],
            "port": str(creds_fetch["port"]),
            "dbname": creds_fetch["dbname"],
        }
    else:
        creds = {
            "username": settings.db_user,
            "password": settings.db_password,
            "host": settings.db_host,
            "port": str(settings.db_port),
            "dbname": settings.db_name,
        }

    # URL-encode password to handle special characters
    encoded_password = quote_plus(creds["password"])

    return (
        f"postgresql+asyncpg://{creds['username']}:{encoded_password}"
        f"@{creds['host']}:{creds['port']}/{creds['dbname']}"
    )


def get_sync_database_url() -> str:
    """
    Build the PostgreSQL database URL for synchronous operations (e.g., Alembic).

    Returns:
        PostgreSQL connection URL for psycopg2 driver
    """
    settings = get_settings()

    if settings.environment == "production":
        creds_fetch = get_db_credentials(
            secret_name=settings.db_secret_name,
            region_name=settings.aws_region,
        )
        creds = {
            "username": creds_fetch["username"],
            "password": creds_fetch["password"],
            "host": creds_fetch["host"],
            "port": str(creds_fetch["port"]),
            "dbname": creds_fetch["dbname"],
        }
    else:
        creds = {
            "username": settings.db_user,
            "password": settings.db_password,
            "host": settings.db_host,
            "port": str(settings.db_port),
            "dbname": settings.db_name,
        }

    # URL-encode password to handle special characters
    encoded_password = quote_plus(creds["password"])

    return (
        f"postgresql+psycopg2://{creds['username']}:{encoded_password}"
        f"@{creds['host']}:{creds['port']}/{creds['dbname']}"
    )


engine = create_async_engine(
    get_database_url(),
    echo=get_settings().debug,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """Dependency for FastAPI to get database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    """Create all tables in the database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
