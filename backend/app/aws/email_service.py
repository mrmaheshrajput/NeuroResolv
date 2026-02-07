"""
Email service for sending emails via AWS SES.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config import get_settings

settings = get_settings()


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
    if settings.environment == "development":
        print(f"[DEV MODE] Would send email to: {to_email}")
        print(f"[DEV MODE] Subject: {subject}")
        print(f"[DEV MODE] Content preview: {text_content[:200]}...")
        return True

    if not settings.gmail_email or not settings.gmail_app_password:
        print("Email service requested but Gmail credentials are not configured")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"NeuroResolv <{settings.gmail_email}>"
    msg["To"] = to_email

    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(settings.gmail_email, settings.gmail_app_password)
            server.sendmail(settings.gmail_email, to_email, msg.as_string())

        print(f"Email sent successfully to {to_email}")
        return True

    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
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
