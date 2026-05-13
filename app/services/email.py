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
        user_id=42,  # optional: enables logging and idempotency
    )
"""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.core.config import settings

logger = logging.getLogger(__name__)

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

    When user_id is provided, email activity is logged to the database
    and idempotency checks prevent duplicate sends within 24 hours.
    """

    @staticmethod
    def send_transactional_email(
        to: str,
        subject: str,
        html_body: str,
        from_email: str | None = None,
        from_name: str | None = None,
        log_id: int | None = None,
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
            log_id: Optional email_logs ID for status tracking
        """
        try:
            from app.worker import task_dispatch_resend_email

            task_dispatch_resend_email.delay(
                to=to,
                subject=subject,
                html_body=html_body,
                from_email=from_email,
                from_name=from_name,
                log_id=log_id,
            )
            logger.info(f"Email task enqueued for {to}: {subject}")
        except Exception as e:
            # If Celery is unavailable, log warning but don't break the flow
            logger.warning(
                f"Failed to enqueue email task for {to}: {e}. "
                f"User flow will continue without email notification."
            )

    @staticmethod
    def send_welcome_email(
        to: str,
        user_name: str,
        user_id: int | None = None,
    ) -> None:
        """
        Send a welcome email to a newly registered user.

        Renders the welcome.html template with the user's name and
        enqueues the email task to Celery.

        If user_id is provided:
        - Checks idempotency (skips if welcome email sent within 24h)
        - Creates an email_logs record (status: queued)
        - Passes log_id to Celery task for status tracking

        Args:
            to: Recipient email address
            user_name: User's display name for personalization
            user_id: Optional user ID for logging and idempotency
        """
        # Idempotency check: skip if welcome email sent within 24h
        if user_id is not None:
            from app.core.database import SyncSessionLocal
            from app.models.email_log import EmailLog

            with SyncSessionLocal() as session:
                if EmailLog.check_idempotency(session, user_id, "welcome", hours=24):
                    logger.info(
                        f"Skipping welcome email for user {user_id}: "
                        f"already sent within 24h"
                    )
                    return

        # Render template
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

        # Create email log if user_id is provided
        log_id = None
        if user_id is not None:
            from app.core.database import SyncSessionLocal
            from app.models.email_log import EmailLog, EmailStatus

            try:
                with SyncSessionLocal() as session:
                    log_entry = EmailLog(
                        user_id=user_id,
                        email_type="welcome",
                        to_email=to,
                        from_email=settings.MAIL_FROM_ADDRESS,
                        status=EmailStatus.QUEUED,
                        template_name="welcome",
                        metadata_={"user_name": user_name},
                    )
                    session.add(log_entry)
                    session.commit()
                    log_id = log_entry.id
                    logger.info(f"Email log created: id={log_id} for {to}")
            except Exception as e:
                logger.warning(f"Failed to create email log: {e}. Continuing without logging.")

        EmailService.send_transactional_email(
            to=to,
            subject="¡Bienvenido a Mi App Instagram!",
            html_body=html_body,
            log_id=log_id,
        )

    @staticmethod
    def send_verification_email(
        to: str,
        user_name: str,
        user_id: int,
    ) -> None:
        """
        Send an email verification email with a unique verification link.

        Generates a JWT token, builds the verification URL, renders the
        welcome template with the link, and enqueues the email task.

        Args:
            to: Recipient email address
            user_name: User's display name for personalization
            user_id: User's database ID for token generation
        """
        from app.auth.tokens import create_verification_token

        token = create_verification_token(user_id, to)
        verify_url = f"{settings.BASE_URL}/auth/verify-email/{token}"

        # Render template with verification link
        try:
            template = _email_env.get_template("welcome.html")
            html_body = template.render(
                user_name=user_name,
                dashboard_url=f"{settings.BASE_URL}/dashboard",
                verify_url=verify_url,
            )
        except Exception as e:
            logger.error(f"Failed to render welcome email template: {e}")
            html_body = (
                f"<p>Hola {user_name}, bienvenido a Mi App Instagram!</p>"
                f'<p><a href="{verify_url}">Verifica tu email aquí</a></p>'
            )

        # Create email log
        log_id = None
        from app.core.database import SyncSessionLocal
        from app.models.email_log import EmailLog, EmailStatus

        try:
            with SyncSessionLocal() as session:
                log_entry = EmailLog(
                    user_id=user_id,
                    email_type="verification",
                    to_email=to,
                    from_email=settings.MAIL_FROM_ADDRESS,
                    status=EmailStatus.QUEUED,
                    template_name="welcome",
                    metadata_={"user_name": user_name, "type": "verification"},
                )
                session.add(log_entry)
                session.commit()
                log_id = log_entry.id
        except Exception as e:
            logger.warning(f"Failed to create email log: {e}. Continuing without logging.")

        EmailService.send_transactional_email(
            to=to,
            subject="¡Bienvenido! Verifica tu email para activar tu cuenta",
            html_body=html_body,
            log_id=log_id,
        )
