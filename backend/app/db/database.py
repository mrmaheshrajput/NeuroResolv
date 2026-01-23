from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

import boto3
from sqlalchemy import event

from app.config import get_settings


class Base(DeclarativeBase):
    pass

settings = get_settings()

def get_rds_iam_token():
    client = boto3.client("rds", region_name=settings.aws_region)
    return client.generate_db_auth_token(
        DBHostname=settings.postgres_host,
        Port=settings.postgres_port,
        DBUsername=settings.postgres_user,
        Region=settings.aws_region
    )

def create_engine_instance():
    url = settings.async_database_url
    
    if settings.use_rds_iam_auth and settings.postgres_host:
        token = get_rds_iam_token()
        url = url.replace("asyncpg://", f"asyncpg://{settings.postgres_user}:{token}@")
    
    return create_async_engine(
        url,
        echo=settings.debug,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

engine = create_engine_instance()

if settings.use_rds_iam_auth and settings.postgres_host:
    @event.listens_for(engine.sync_engine, "do_connect")
    def provide_token(dialect, conn_rec, cargs, cparams):
        cparams["password"] = get_rds_iam_token()

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
