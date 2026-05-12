"""
Email service for sending transactional emails via Resend + Celery.

This module provides a centralized email service that delegates actual
sending to a Celery task, ensuring non-blocking execution (<50ms overhead).

Usage:
    from app.services.email import EmailService

    # Send a custom transactional email
    EmailService.send_transactional_email(
        to="user@example.com",
        subject="Your receipt",
        html_body="<h1>Thank you!</h1>",
    )

    # Send a welcome email (uses pre-built template)
    EmailService.send_welcome_email(
        to="user@example.com",
        user_name="John",
    )
"""

import logging
from pathlib import Path

import resend
from jinja2 import Environment, FileSystemLoader

from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure Resend API key at module load time
resend.api_key = settings.RESEND_API_KEY

# Jinja2 environment for email templates
_email_template_dir = Path(__file__).parent.parent / "templates" / "email"
_email_env = Environment(
    loader=FileSystemLoader(str(_email_template_dir)),
    autoescape=True,
)


class EmailService:
    """
    Centralized email service that sends emails asynchronously via Celery.

    All methods enqueue a Celery task and return immediately, ensuring
    the calling code is not blocked by the email API call.
    """

    @staticmethod
    def send_transactional_email(
        to: str,
        subject: str,
        html_body: str,
        from_email: str | None = None,
        from_name: str | None = None,
    ) -> None:
        """
        Send a transactional email by enqueueing a Celery task.

        This method returns immediately (<50ms) after enqueueing the task
        to Redis. The actual email sending happens asynchronously in the
        Celery worker.

        Args:
            to: Recipient email address
            subject: Email subject line
            html_body: HTML content of the email
            from_email: Sender email (defaults to MAIL_FROM_ADDRESS)
            from_name: Sender name (defaults to MAIL_FROM_NAME)
        """
        try:
            from app.worker import task_dispatch_resend_email

            task_dispatch_resend_email.delay(
                to=to,
                subject=subject,
                html_body=html_body,
                from_email=from_email,
                from_name=from_name,
            )
            logger.info(f"Email task enqueued for {to}: {subject}")
        except Exception as e:
            # If Celery is unavailable, log warning but don't break the flow
            logger.warning(
                f"Failed to enqueue email task for {to}: {e}. "
                f"User flow will continue without email notification."
            )

    @staticmethod
    def send_welcome_email(to: str, user_name: str) -> None:
        """
        Send a welcome email to a newly registered user.

        Renders the welcome.html template with the user's name and
        enqueues the email task to Celery.

        Args:
            to: Recipient email address
            user_name: User's display name for personalization
        """
        try:
            template = _email_env.get_template("welcome.html")
            html_body = template.render(
                user_name=user_name,
                dashboard_url=f"{settings.BASE_URL}/dashboard",
            )
        except Exception as e:
            logger.error(f"Failed to render welcome email template: {e}")
            # Fallback to plain text if template rendering fails
            html_body = f"<p>Hola {user_name}, bienvenido a Mi App Instagram!</p>"

        EmailService.send_transactional_email(
            to=to,
            subject="¡Bienvenido a Mi App Instagram!",
            html_body=html_body,
        )
