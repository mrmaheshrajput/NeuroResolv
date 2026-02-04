"""
Email service for sending emails via AWS SES.
"""

import logging
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_ses_client():
    """Get an AWS SES client."""
    return boto3.client("ses", region_name=settings.aws_region)


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str,
    from_email: Optional[str] = None,
) -> bool:
    """
    Send an email using AWS SES.

    Args:
        to_email: Recipient email address
        subject: Email subject line
        html_content: HTML version of the email body
        text_content: Plain text version of the email body
        from_email: Sender email address (defaults to configured sender)

    Returns:
        True if email was sent successfully, False otherwise
    """
    # In development mode, just log the email
    if settings.environment == "development":
        logger.info(f"[DEV MODE] Would send email to: {to_email}")
        logger.info(f"[DEV MODE] Subject: {subject}")
        logger.info(f"[DEV MODE] Content preview: {text_content[:200]}...")
        return True

    sender = from_email or f"NeuroResolv <noreply@{_get_domain()}>"

    try:
        client = _get_ses_client()

        response = client.send_email(
            Source=sender,
            Destination={
                "ToAddresses": [to_email],
            },
            Message={
                "Subject": {
                    "Data": subject,
                    "Charset": "UTF-8",
                },
                "Body": {
                    "Text": {
                        "Data": text_content,
                        "Charset": "UTF-8",
                    },
                    "Html": {
                        "Data": html_content,
                        "Charset": "UTF-8",
                    },
                },
            },
        )

        logger.info(f"Email sent to {to_email}, MessageId: {response['MessageId']}")
        return True

    except ClientError as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending email to {to_email}: {e}")
        return False


def _get_domain() -> str:
    """Get the email domain based on environment."""
    # This should be configured based on your verified SES domain
    return "neuroresolv.com"


async def send_test_email(to_email: str) -> bool:
    """Send a test email to verify SES configuration."""
    return await send_email(
        to_email=to_email,
        subject="NeuroResolv Email Test",
        html_content="""
        <html>
        <body style="font-family: sans-serif; padding: 20px;">
            <h1 style="color: #8b5cf6;">Email Configuration Test</h1>
            <p>If you're reading this, your email configuration is working correctly!</p>
            <p>- The NeuroResolv Team</p>
        </body>
        </html>
        """,
        text_content="Email Configuration Test\n\nIf you're reading this, your email configuration is working correctly!\n\n- The NeuroResolv Team",
    )
