"""
email_service.py — Optional welcome email with the generated SDK attached.

Email is disabled by default (``EMAIL_ENABLED=false``). When enabled, SMTP
credentials are read from the environment via ``settings`` — never hard-coded.
Failures are logged and swallowed so they can never break an API request.
"""

import logging
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from .config import TEMPLATE_DIR, settings

logger = logging.getLogger("ach.email")


def _build_html_email(name: str) -> str:
    template_path = TEMPLATE_DIR / "welcome_email.html"
    if not template_path.exists():
        return f"<h1>Welcome, {name}!</h1><p>Your voice SDK is attached.</p>"
    return template_path.read_text(encoding="utf-8").replace("{{UserName}}", name)


def send_welcome_email(name: str, email: str, whl_path: str) -> None:
    """Send the welcome email with the .whl attached. No-op unless enabled."""
    if not settings.email_enabled:
        logger.info("Email disabled — skipping welcome email to %s", email)
        return
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning("EMAIL_ENABLED but SMTP credentials missing — skipping.")
        return

    try:
        msg = MIMEMultipart("mixed")
        msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_user}>"
        msg["To"] = email
        msg["Subject"] = f"Welcome to {settings.app_name}, {name}!"

        body = MIMEMultipart("alternative")
        body.attach(
            MIMEText(
                f"Welcome to {settings.app_name}, {name}!\n\n"
                "Your voice authentication SDK is attached.",
                "plain",
            )
        )
        body.attach(MIMEText(_build_html_email(name), "html"))
        msg.attach(body)

        whl_file = Path(whl_path)
        if whl_file.exists():
            with open(whl_file, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{whl_file.name}"')
            msg.attach(part)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_user, email, msg.as_string())

        logger.info("Welcome email sent to %s", email)
    except Exception as exc:  # noqa: BLE001 — email must never crash a request
        logger.error("Failed to send welcome email to %s: %s", email, exc)
