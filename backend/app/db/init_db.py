"""
Database initialization script for PostgreSQL.

Creates the target database if it doesn't exist.
Used during container startup before running migrations.
"""

import sys
from urllib.parse import quote_plus

from app.aws.secrets import get_db_credentials
from app.config import get_settings
from app.db.database import get_sync_database_url
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError


def create_database_if_not_exists() -> bool:
    """
    Create the target database if it doesn't exist.

    Connects to the 'postgres' default database to create the target database.
    Returns True if database was created, False if it already exists.
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

    encoded_password = quote_plus(creds["password"])
    target_db = creds["dbname"]

    # Connect to the default 'postgres' database to create the target database
    admin_url = (
        f"postgresql+psycopg2://{creds['username']}:{encoded_password}"
        f"@{creds['host']}:{creds['port']}/postgres"
    )
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            # Check if database exists
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": target_db},
            )
            exists = result.scalar() is not None

            if not exists:
                print(f"Creating database '{target_db}'...")
                conn.execute(text(f'CREATE DATABASE "{target_db}"'))
                print(f"Database '{target_db}' created successfully.")
                return True
            else:
                print(f"Database '{target_db}' already exists.")
                return False

    except ProgrammingError as e:
        print(f"Error checking/creating database: {e}")
        raise
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        create_database_if_not_exists()
        sys.exit(0)
    except Exception as e:
        print(f"Failed to create database: {e}")
        sys.exit(1)
