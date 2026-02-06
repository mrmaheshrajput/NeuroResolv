"""
AWS Lambda handler for scheduled roadmap refreshes.

This Lambda is triggered weekly by AWS EventBridge to:
1. Trigger the NeuroResolv API to identify and refresh roadmaps that are due.
2. The AI agent will auto-evolve roadmaps based on user progress logs and streak data.

Dependencies: Only Python standard library (urllib, json, os)
Configure via environment variables: API_BASE_URL, API_KEY
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone


def make_api_request(
    endpoint: str,
    method: str = "POST",
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
        "User-Agent": "aws-lambda-roadmap-refresh",
    }

    body = None
    if method.upper() in {"POST", "PUT", "PATCH"} and data is not None:
        body = json.dumps(data).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method=method.upper(),
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"HTTP Error {e.code}: {error_body}")
        raise
    except Exception as e:
        print(f"Connection Error: {e}")
        raise


def lambda_handler(event: dict, context) -> dict:
    """
    Lambda handler function.
    Triggered by EventBridge (e.g., every Sunday at midnight).
    """
    print(
        f"Roadmap refresh Lambda triggered at {datetime.now(timezone.utc).isoformat()}"
    )

    try:
        # Trigger the system auto-refresh
        print("Initialzing bulk roadmap refresh...")
        result = make_api_request("/resolutions/system/auto-refresh", method="POST")

        refreshed = result.get("refreshed_count", 0)
        failed = result.get("failed_count", 0)

        print(f"Refresh complete. Success: {refreshed}, Failed: {failed}")
        if result.get("errors"):
            print(f"Errors encountered: {json.dumps(result['errors'])}")

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Roadmap refresh processing complete",
                    "refreshed_count": refreshed,
                    "failed_count": failed,
                    "status": result.get("status"),
                }
            ),
        }

    except Exception as e:
        print(f"Fatal error in roadmap refresh Lambda: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
