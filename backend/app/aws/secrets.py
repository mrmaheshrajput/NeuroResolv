"""
AWS Secrets Manager integration for database credentials.

This module fetches PostgreSQL credentials from AWS Secrets Manager
and caches them using lru_cache for performance.
"""

import json
from functools import lru_cache
from typing import TypedDict

import boto3
from botocore.exceptions import ClientError


class DatabaseCredentials(TypedDict):
    """Type definition for database credentials from Secrets Manager."""

    username: str
    password: str
    host: str
    port: str
    dbname: str


@lru_cache(maxsize=1)
def get_db_credentials(secret_name: str, region_name: str) -> DatabaseCredentials:
    """
    Fetch database credentials from AWS Secrets Manager.

    Uses lru_cache to cache credentials since they don't change often.

    Args:
        secret_name: The name of the secret in AWS Secrets Manager
        region_name: AWS region where the secret is stored

    Returns:
        DatabaseCredentials containing username, password, host, port, dbname

    Raises:
        ClientError: If unable to fetch the secret from AWS
        json.JSONDecodeError: If the secret value is not valid JSON
        KeyError: If the secret is missing required fields
    """
    client = boto3.client(service_name="secretsmanager", region_name=region_name)

    try:
        response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "DecryptionFailureException":
            raise RuntimeError(
                "Secrets Manager can't decrypt the secret using the provided KMS key."
            ) from e
        elif error_code == "InternalServiceErrorException":
            raise RuntimeError("An error occurred on the server side.") from e
        elif error_code == "InvalidParameterException":
            raise RuntimeError("Invalid parameter value provided.") from e
        elif error_code == "InvalidRequestException":
            raise RuntimeError("Invalid request to Secrets Manager.") from e
        elif error_code == "ResourceNotFoundException":
            raise RuntimeError(
                f"Secret '{secret_name}' not found in region '{region_name}'."
            ) from e
        else:
            raise

    secret_string = response.get("SecretString")
    if not secret_string:
        raise RuntimeError("Secret does not contain a string value.")

    credentials = json.loads(secret_string)

    # Validate required fields
    required_fields = ["username", "password", "host", "port", "dbname"]
    missing_fields = [field for field in required_fields if field not in credentials]
    if missing_fields:
        raise KeyError(f"Secret is missing required fields: {missing_fields}")

    return DatabaseCredentials(
        username=credentials["username"],
        password=credentials["password"],
        host=credentials["host"],
        port=str(credentials["port"]),
        dbname=credentials["dbname"],
    )


def clear_credentials_cache() -> None:
    """Clear the cached credentials."""
    get_db_credentials.cache_clear()
