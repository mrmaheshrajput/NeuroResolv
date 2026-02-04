"""
Local testing script for the email scheduler Lambda and email generation.

This script allows testing all email scenarios without deploying to AWS.
Run from the tasks/email_scheduler directory.

Usage:
    python test_email_scheduler.py              # Run all tests
    python test_email_scheduler.py --lambda     # Test Lambda handler only
    python test_email_scheduler.py --agent      # Test email agent only
    python test_email_scheduler.py --preview    # Preview email for a user
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

# Add backend to path for importing agents
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))


def test_lambda_handler_mock():
    """Test the Lambda handler with mocked API responses."""
    print("\n" + "=" * 60)
    print("TEST: Lambda Handler (Mocked API)")
    print("=" * 60)

    from handler import handler, get_current_utc_hour

    # Mock API responses
    mock_scheduled_users = {
        "users": [
            {
                "user_id": 1,
                "email": "user1@example.com",
                "full_name": "Test User 1",
                "timezone": "UTC",
                "preferred_hour": 9,
            },
            {
                "user_id": 2,
                "email": "user2@example.com",
                "full_name": "Test User 2",
                "timezone": "UTC",
                "preferred_hour": 9,
            },
        ],
        "utc_hour": get_current_utc_hour(),
    }

    mock_send_result = {
        "results": [
            {"user_id": 1, "success": True, "email_type": "learning_reflection"},
            {"user_id": 2, "success": True, "email_type": "micro_celebration"},
        ],
        "total_sent": 2,
        "total_failed": 0,
    }

    def mock_api_request(endpoint, method="GET", data=None):
        if "scheduled-users" in endpoint:
            return mock_scheduled_users
        elif "send" in endpoint:
            return mock_send_result
        return {}

    with patch("handler.make_api_request", side_effect=mock_api_request):
        result = handler({}, None)

    print(f"Lambda returned status: {result['statusCode']}")
    print(f"Response body: {json.dumps(json.loads(result['body']), indent=2)}")

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["emails_sent"] == 2
    print("✓ Lambda handler test PASSED")


def test_lambda_handler_no_users():
    """Test Lambda handler when no users are scheduled."""
    print("\n" + "=" * 60)
    print("TEST: Lambda Handler (No Users Scheduled)")
    print("=" * 60)

    from handler import handler

    def mock_api_request(endpoint, method="GET", data=None):
        if "scheduled-users" in endpoint:
            return {"users": [], "utc_hour": 0}
        return {}

    with patch("handler.make_api_request", side_effect=mock_api_request):
        result = handler({}, None)

    print(f"Lambda returned status: {result['statusCode']}")
    print(f"Response body: {json.dumps(json.loads(result['body']), indent=2)}")

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["users_processed"] == 0
    print("✓ No users test PASSED")


async def test_email_type_determination():
    """Test the email type determination logic."""
    print("\n" + "=" * 60)
    print("TEST: Email Type Determination Logic")
    print("=" * 60)

    try:
        from app.agents.email_reflection_agent import determine_email_type
        from app.schemas import EmailType
    except ImportError as e:
        print(f"⚠ Skipping test (import error): {e}")
        print(
            "  Make sure you're running from the project root with backend in PYTHONPATH"
        )
        return

    # Create mock database session
    class MockScalar:
        def __init__(self, value):
            self.value = value

        def scalar(self):
            return self.value

        def scalar_one_or_none(self):
            return self.value

        def scalars(self):
            return self

        def all(self):
            return self.value if isinstance(self.value, list) else [self.value]

    class MockDB:
        async def execute(self, query):
            # Return mock data based on query
            return MockScalar([])

    mock_db = MockDB()

    # Test with empty user data
    result = await determine_email_type(999, mock_db)
    print(f"Email type for user with no data: {result}")
    assert result is None

    print("✓ Email type determination test PASSED")


async def test_email_content_generation():
    """Test email content generation for each type."""
    print("\n" + "=" * 60)
    print("TEST: Email Content Generation")
    print("=" * 60)

    try:
        from app.agents.email_reflection_agent import (
            _generate_learning_reflection,
            _generate_micro_celebration,
            _generate_streak_encouragement,
        )
    except ImportError as e:
        print(f"⚠ Skipping test (import error): {e}")
        return

    # Sample user context
    user_context = {
        "user_name": "Alex",
        "full_name": "Alex Johnson",
        "resolutions": [
            {
                "id": 1,
                "goal": "Learn Python programming to build web applications",
                "category": "learning",
                "current_milestone": 3,
            }
        ],
        "recent_logs": [
            {
                "date": "2026-02-03",
                "content": "Completed chapter on Flask routing. Built my first API endpoint!",
                "verified": True,
                "ai_reflection": "Great progress on understanding RESTful concepts.",
            },
            {
                "date": "2026-02-02",
                "content": "Learned about decorators and how Flask uses them.",
                "verified": True,
                "ai_reflection": None,
            },
        ],
        "streaks": {
            1: {
                "current_streak": 14,
                "longest_streak": 14,
                "total_verified_days": 20,
                "last_log_date": "2026-02-03",
            }
        },
        "milestones": [
            {
                "title": "Complete Python basics",
                "status": "completed",
                "resolution_goal": "Learn Python",
            },
            {
                "title": "Build first web app",
                "status": "in_progress",
                "resolution_goal": "Learn Python",
            },
        ],
    }

    print("\n--- Testing Learning Reflection ---")
    try:
        result = await _generate_learning_reflection(user_context)
        if result.get("should_send"):
            print(f"Subject: {result.get('subject')}")
            print(f"Content preview: {result.get('text_content', '')[:200]}...")
        else:
            print(f"Not sending: {result.get('reason')}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n--- Testing Micro-celebration ---")
    try:
        result = await _generate_micro_celebration(user_context)
        if result.get("should_send"):
            print(f"Subject: {result.get('subject')}")
            print(f"Content preview: {result.get('text_content', '')[:200]}...")
        else:
            print(f"Not sending: {result.get('reason')}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n--- Testing Streak Encouragement ---")
    # Modify context to simulate user who hasn't logged in a while
    user_context["streaks"][1]["last_log_date"] = "2026-01-28"
    try:
        result = await _generate_streak_encouragement(user_context)
        if result.get("should_send"):
            print(f"Subject: {result.get('subject')}")
            print(f"Content preview: {result.get('text_content', '')[:200]}...")
        else:
            print(f"Not sending: {result.get('reason')}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n✓ Email content generation tests completed")


async def preview_email_for_user(user_id: int):
    """Preview what email would be sent to a specific user."""
    print("\n" + "=" * 60)
    print(f"PREVIEW: Email for User ID {user_id}")
    print("=" * 60)

    import urllib.request
    import urllib.error

    api_base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
    api_key = os.environ.get("API_KEY", "dev-api-key-12345")

    # Note: This requires the user to be logged in to preview their own email
    # For testing, you may need to use a service token or admin endpoint

    url = f"{api_base_url}/email/preview/{user_id}"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key,
    }

    request = urllib.request.Request(url, headers=headers, method="GET")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            print(f"Email Type: {result.get('email_type')}")
            print(f"Should Send: {result.get('should_send')}")
            if result.get("should_send"):
                print(f"\nSubject: {result.get('subject')}")
                print(f"\nContent:\n{result.get('text_content')}")
            else:
                print(f"Reason: {result.get('reason')}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        print(f"HTTP Error {e.code}: {error_body}")
    except urllib.error.URLError as e:
        print(f"Connection Error: {e.reason}")
        print("Make sure the backend server is running on localhost:8000")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("NEURORESOLV EMAIL SCHEDULER - TEST SUITE")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    # Lambda tests (no async needed)
    test_lambda_handler_mock()
    test_lambda_handler_no_users()

    # Agent tests (async)
    asyncio.run(test_email_type_determination())

    # Content generation tests (requires API key)
    if os.environ.get("GOOGLE_API_KEY") or os.environ.get("SKIP_LLM_TESTS") != "true":
        asyncio.run(test_email_content_generation())
    else:
        print("\n⚠ Skipping LLM tests (set GOOGLE_API_KEY to enable)")

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the email scheduler")
    parser.add_argument(
        "--lambda",
        dest="lambda_only",
        action="store_true",
        help="Test Lambda handler only",
    )
    parser.add_argument("--agent", action="store_true", help="Test email agent only")
    parser.add_argument(
        "--preview", type=int, metavar="USER_ID", help="Preview email for a user"
    )

    args = parser.parse_args()

    if args.lambda_only:
        test_lambda_handler_mock()
        test_lambda_handler_no_users()
    elif args.agent:
        asyncio.run(test_email_type_determination())
        asyncio.run(test_email_content_generation())
    elif args.preview:
        asyncio.run(preview_email_for_user(args.preview))
    else:
        run_all_tests()
