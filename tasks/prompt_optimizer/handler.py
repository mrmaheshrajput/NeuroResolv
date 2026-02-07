"""
AWS Lambda handler for scheduled prompt optimization.

This Lambda is triggered weekly by AWS EventBridge to:
1. Call the NeuroResolv API to run MetaPromptOptimizer on prompts
   that have received negative user feedback.
2. The optimizer will analyze feedback traces and create improved
   prompt versions in Opik.

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
        "User-Agent": "aws-lambda-prompt-optimizer",
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
        with urllib.request.urlopen(request, timeout=120) as response:
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
        f"Prompt optimizer Lambda triggered at {datetime.now(timezone.utc).isoformat()}"
    )

    # Configuration from environment
    min_samples = int(os.environ.get("MIN_SAMPLES", "5"))

    try:
        print("Starting prompt optimization...")
        result = make_api_request(
            f"/system/optimize-prompts?min_samples={min_samples}",
            method="POST",
        )

        optimization_results = result.get("results", [])

        # Count successes and failures
        successful = sum(
            1 for r in optimization_results if r.get("status") == "success"
        )
        skipped = sum(1 for r in optimization_results if r.get("status") == "skipped")
        errors = sum(1 for r in optimization_results if r.get("status") == "error")

        print(
            f"Optimization complete. Success: {successful}, Skipped: {skipped}, Errors: {errors}"
        )

        for r in optimization_results:
            print(
                f"  - {r.get('prompt_name', 'unknown')}: {r.get('status')} - {r.get('message', r.get('new_version', ''))}"
            )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Prompt optimization processing complete",
                    "successful": successful,
                    "skipped": skipped,
                    "errors": errors,
                    "results": optimization_results,
                }
            ),
        }

    except Exception as e:
        print(f"Fatal error in prompt optimizer Lambda: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
