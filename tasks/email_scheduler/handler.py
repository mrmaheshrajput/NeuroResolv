"""
AWS Lambda handler for scheduled email notifications.

This Lambda is triggered every hour by AWS EventBridge to:
1. Query the API server for users scheduled to receive emails at the current UTC hour
2. Trigger the API to generate and send personalized emails to those users

Dependencies: Only Python standard library (urllib, json, os)
Configure via environment variables: API_BASE_URL, API_KEY
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone


def get_current_utc_hour() -> int:
    """Get the current hour in UTC."""
    return datetime.now(timezone.utc).hour


def make_api_request(
    endpoint: str,
    method: str = "GET",
    data: dict = None,
) -> dict:
    """
    Make a request to the NeuroResolv API.

    Uses only stdlib to avoid Lambda layer dependencies.
    """
    api_base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
    api_key = os.environ.get("API_KEY", "dev-api-key-12345")

    url = f"{api_base_url}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key,
        "User-Agent": "aws-lambda",
    }

    body = None
    if method.upper() in {"POST", "PUT", "PATCH"} and data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method=method.upper(),
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print("Status:", e.code)
        print("Response body:", error_body)
        raise


def get_scheduled_users(utc_hour: int) -> list:
    """Get users scheduled to receive emails at this UTC hour."""
    response = make_api_request(f"/email/scheduled-users?utc_hour={utc_hour}")
    return response.get("users", [])


def send_emails(user_ids: list) -> dict:
    """Trigger the API to send emails to the specified users."""
    if not user_ids:
        return {"results": [], "total_sent": 0, "total_failed": 0}

    response = make_api_request(
        "/email/send",
        method="POST",
        data={"user_ids": user_ids},
    )
    return response


def lambda_handler(event: dict, context) -> dict:
    """
    Lambda handler function.

    Triggered by EventBridge on a schedule (every hour).

    Args:
        event: EventBridge event (not used, but required)
        context: Lambda context object

    Returns:
        dict with execution summary
    """
    print(
        f"Email scheduler Lambda triggered at {datetime.now(timezone.utc).isoformat()}"
    )

    # Get current UTC hour
    utc_hour = get_current_utc_hour()
    print(f"Current UTC hour: {utc_hour}")

    try:
        # Get users scheduled for this hour
        users = get_scheduled_users(utc_hour)
        print(f"Found {len(users)} users scheduled for hour {utc_hour}")

        if not users:
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": "No users scheduled for this hour",
                        "utc_hour": utc_hour,
                        "users_processed": 0,
                    }
                ),
            }

        # Extract user IDs and send emails
        user_ids = [u["user_id"] for u in users]
        print(f"Sending emails to user IDs: {user_ids}")

        result = send_emails(user_ids)

        print(
            f"Email send results: {result['total_sent']} sent, {result['total_failed']} failed"
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Email processing complete",
                    "utc_hour": utc_hour,
                    "users_processed": len(users),
                    "emails_sent": result["total_sent"],
                    "emails_failed": result["total_failed"],
                }
            ),
        }

    except Exception as e:
        print(f"Error in email scheduler: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "error": str(e),
                    "utc_hour": utc_hour,
                }
            ),
        }
