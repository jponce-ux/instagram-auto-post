"""
Tests for spec-017-email-notifications-resend
Email service with Resend SDK + Celery async delivery.
"""

import os
from unittest.mock import Mock, patch, MagicMock

import pytest

# Set required env vars BEFORE importing app modules
os.environ.setdefault("META_APP_SECRET", "test_app_secret_for_testing_12345")
os.environ.setdefault("META_WEBHOOK_VERIFY_TOKEN", "test_verify_token_12345")
os.environ.setdefault("SECRET_KEY", "test_secret_key_for_testing")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("CELERY_BROKER_URL", "redis://redis:6379/0")
os.environ.setdefault("RESEND_API_KEY", "re_test_key_12345")


# ============================================================
# EmailService Unit Tests
# ============================================================

class TestEmailServiceTransactional:
    """Test EmailService.send_transactional_email()"""

    @patch("app.worker.task_dispatch_resend_email")
    def test_enqueues_celery_task(self, mock_task):
        """GIVEN EmailService.send_transactional_email is called
        WHEN called with valid parameters
        THEN task_dispatch_resend_email.delay is called with correct args"""
        from app.services.email import EmailService

        EmailService.send_transactional_email(
            to="user@example.com",
            subject="Test Subject",
            html_body="<h1>Hello</h1>",
        )

        mock_task.delay.assert_called_once_with(
            to="user@example.com",
            subject="Test Subject",
            html_body="<h1>Hello</h1>",
            from_email=None,
            from_name=None,
        )

    @patch("app.worker.task_dispatch_resend_email")
    def test_passes_custom_sender(self, mock_task):
        """GIVEN custom from_email and from_name are provided
        WHEN send_transactional_email is called
        THEN the task receives the custom sender values"""
        from app.services.email import EmailService

        EmailService.send_transactional_email(
            to="user@example.com",
            subject="Test",
            html_body="<p>Body</p>",
            from_email="custom@example.com",
            from_name="My App",
        )

        mock_task.delay.assert_called_once_with(
            to="user@example.com",
            subject="Test",
            html_body="<p>Body</p>",
            from_email="custom@example.com",
            from_name="My App",
        )

    @patch("app.worker.task_dispatch_resend_email")
    def test_celery_unavailable_does_not_crash(self, mock_task):
        """GIVEN Celery is unavailable (Redis down)
        WHEN send_transactional_email is called
        THEN the method logs a warning but does not raise an exception"""
        from app.services.email import EmailService

        mock_task.delay.side_effect = Exception("Connection refused")

        # Should not raise
        EmailService.send_transactional_email(
            to="user@example.com",
            subject="Test",
            html_body="<p>Body</p>",
        )


class TestEmailServiceWelcome:
    """Test EmailService.send_welcome_email()"""

    @patch("app.services.email.EmailService.send_transactional_email")
    def test_renders_template_and_sends(self, mock_send):
        """GIVEN a new user registers
        WHEN send_welcome_email is called
        THEN the welcome template is rendered and sent with correct subject"""
        from app.services.email import EmailService

        EmailService.send_welcome_email(
            to="newuser@example.com",
            user_name="newuser",
        )

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["to"] == "newuser@example.com"
        assert "Bienvenido" in call_kwargs["subject"]
        assert "newuser" in call_kwargs["html_body"]

    @patch("app.services.email._email_env")
    @patch("app.services.email.EmailService.send_transactional_email")
    def test_fallback_on_template_error(self, mock_send, mock_env):
        """GIVEN the template rendering fails
        WHEN send_welcome_email is called
        THEN a fallback HTML body is used"""
        from app.services.email import EmailService

        mock_env.get_template.side_effect = Exception("Template not found")

        EmailService.send_welcome_email(
            to="user@example.com",
            user_name="testuser",
        )

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert "testuser" in call_kwargs["html_body"]


# ============================================================
# Celery Task Unit Tests
# ============================================================

class TestTaskDispatchResendEmail:
    """Test task_dispatch_resend_email Celery task"""

    @patch("resend.Emails.send")
    def test_successful_send(self, mock_send):
        """GIVEN Resend API responds successfully
        WHEN task_dispatch_resend_email is called
        THEN it returns the message_id and logs success"""
        from app.worker import task_dispatch_resend_email

        mock_response = Mock()
        mock_response.id = "msg_abc123"
        mock_send.return_value = mock_response

        result = task_dispatch_resend_email.run(
            to="user@example.com",
            subject="Test",
            html_body="<h1>Hello</h1>",
        )

        assert result["message_id"] == "msg_abc123"
        assert result["status"] == "sent"
        assert result["to"] == "user@example.com"
        mock_send.assert_called_once()

    @patch("resend.Emails.send")
    def test_uses_config_defaults(self, mock_send):
        """GIVEN no custom sender is provided
        WHEN task is called
        THEN it uses MAIL_FROM_ADDRESS and MAIL_FROM_NAME from config"""
        from app.worker import task_dispatch_resend_email
        from app.core.config import settings

        mock_response = Mock()
        mock_response.id = "msg_abc123"
        mock_send.return_value = mock_response

        task_dispatch_resend_email.run(
            to="user@example.com",
            subject="Test",
            html_body="<p>Body</p>",
        )

        # Verify the send call used config defaults
        call_args = mock_send.call_args[0][0]
        # SendParams is a dict with 'from_' key
        from_str = call_args.get("from_", "")
        assert settings.MAIL_FROM_ADDRESS in from_str
        assert settings.MAIL_FROM_NAME in from_str

    @patch("resend.Emails.send")
    def test_4xx_error_does_not_retry(self, mock_send):
        """GIVEN Resend returns a 4xx client error
        WHEN task_dispatch_resend_email is called
        THEN it returns error status without raising (no retry)"""
        from resend.exceptions import ResendError
        from app.worker import task_dispatch_resend_email

        error = ResendError(
            code=400,
            error_type="invalid_request",
            message="Bad request",
            suggested_action="Check your parameters",
        )
        mock_send.side_effect = error

        result = task_dispatch_resend_email.run(
            to="invalid-email",
            subject="Test",
            html_body="<p>Body</p>",
        )

        assert result["status"] == "failed"
        assert "error" in result

    @patch("resend.Emails.send")
    def test_5xx_error_raises_for_retry(self, mock_send):
        """GIVEN Resend returns a 5xx server error
        WHEN task_dispatch_resend_email is called
        THEN it raises the exception (triggers Celery retry)"""
        from resend.exceptions import ResendError
        from app.worker import task_dispatch_resend_email

        error = ResendError(
            code=500,
            error_type="internal_error",
            message="Internal server error",
            suggested_action="Try again later",
        )
        mock_send.side_effect = error

        with pytest.raises(ResendError):
            task_dispatch_resend_email.run(
                to="user@example.com",
                subject="Test",
                html_body="<p>Body</p>",
            )


# ============================================================
# Integration Test: Register → Email Enqueued
# ============================================================

class TestRegisterWithEmailIntegration:
    """Test that registration triggers welcome email"""

    @patch("app.services.email.EmailService.send_welcome_email")
    def test_register_calls_welcome_email(self, mock_welcome):
        """GIVEN a user registers successfully (DB mocked)
        WHEN POST /auth/register is called
        THEN EmailService.send_welcome_email is called"""
        from fastapi.testclient import TestClient
        from app.main import app
        from unittest.mock import patch, AsyncMock, MagicMock
        from app.core.database import get_db
        from app.models.user import User

        # Create mock objects
        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.email = "testuser@example.com"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(side_effect=[None, mock_user])
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        async def fake_get_db():
            yield mock_session

        with patch.object(app, 'dependency_overrides', {get_db: fake_get_db}):
            client = TestClient(app)

            response = client.post(
                "/auth/register",
                data={
                    "email": "testuser@example.com",
                    "password": "testpassword123",
                    "password_confirm": "testpassword123",
                },
            )

            # Should return success
            assert response.status_code in (200, 303, 307)

        # Welcome email should have been called
        mock_welcome.assert_called_once_with(
            to="testuser@example.com",
            user_name="testuser",
        )
