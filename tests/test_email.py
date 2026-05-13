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
            log_id=None,
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
            log_id=None,
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

        mock_send.return_value = {"id": "msg_abc123"}

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

        mock_send.return_value = {"id": "msg_abc123"}

        task_dispatch_resend_email.run(
            to="user@example.com",
            subject="Test",
            html_body="<p>Body</p>",
        )

        # Verify the send call used config defaults
        call_args = mock_send.call_args[0][0]
        # Now it's a dict with 'from' key (not 'from_')
        from_str = call_args.get("from", "")
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
    """Test that registration triggers verification email"""

    @patch("app.services.email.EmailService.send_verification_email")
    def test_register_calls_verification_email(self, mock_verify):
        """GIVEN a user registers successfully (DB mocked)
        WHEN POST /auth/register is called
        THEN EmailService.send_verification_email is called"""
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

        # Mock refresh to set ID on the real User object created by the route
        async def mock_refresh(obj):
            obj.id = 1
            obj.email = "testuser@example.com"

        mock_session.refresh = mock_refresh

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

        # Verification email should have been called with user_id
        mock_verify.assert_called_once()
        call_kwargs = mock_verify.call_args[1]
        assert call_kwargs["to"] == "testuser@example.com"
        assert call_kwargs["user_name"] == "testuser"
        assert call_kwargs["user_id"] == 1


# ============================================================
# SPEC-018: Email History Tracking Tests
# ============================================================

class TestEmailLogModel:
    """Test EmailLog model query methods (T5.1)"""

    def test_get_by_user_returns_user_logs(self):
        """GIVEN email logs exist for multiple users
        WHEN get_by_user is called for a specific user
        THEN only that user's logs are returned, ordered by queued_at desc"""
        from app.models.email_log import EmailLog, EmailStatus
        from unittest.mock import MagicMock
        from sqlalchemy import select

        mock_session = MagicMock()
        log1 = MagicMock(spec=EmailLog)
        log1.user_id = 1
        log2 = MagicMock(spec=EmailLog)
        log2.user_id = 1
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [log1, log2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        results = EmailLog.get_by_user(mock_session, user_id=1)

        assert len(results) == 2
        # Verify the query was executed
        mock_session.execute.assert_called_once()

    def test_get_by_status_filters_correctly(self):
        """GIVEN email logs exist with various statuses
        WHEN get_by_status is called
        THEN only logs matching the status are returned"""
        from app.models.email_log import EmailLog, EmailStatus
        from unittest.mock import MagicMock

        mock_session = MagicMock()
        log1 = MagicMock(spec=EmailLog)
        log1.status = EmailStatus.QUEUED
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [log1]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        results = EmailLog.get_by_status(mock_session, status=EmailStatus.QUEUED)

        assert len(results) == 1
        assert results[0].status == EmailStatus.QUEUED
        mock_session.execute.assert_called_once()

    def test_check_idempotency_returns_true_for_recent_sent(self):
        """GIVEN a welcome email was sent within 24 hours
        WHEN check_idempotency is called
        THEN it returns True"""
        from app.models.email_log import EmailLog
        from unittest.mock import MagicMock

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()  # Found a recent log
        mock_session.execute.return_value = mock_result

        result = EmailLog.check_idempotency(mock_session, user_id=1, email_type="welcome", hours=24)

        assert result is True
        mock_session.execute.assert_called_once()

    def test_check_idempotency_returns_false_for_old_email(self):
        """GIVEN a welcome email was sent more than 24 hours ago
        WHEN check_idempotency is called with 24h window
        THEN it returns False"""
        from app.models.email_log import EmailLog
        from unittest.mock import MagicMock

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No recent log found
        mock_session.execute.return_value = mock_result

        result = EmailLog.check_idempotency(mock_session, user_id=1, email_type="welcome", hours=24)

        assert result is False

    def test_check_idempotency_returns_false_for_failed_email(self):
        """GIVEN a welcome email failed (status=failed)
        WHEN check_idempotency is called
        THEN it returns False (failed emails don't block retries)"""
        from app.models.email_log import EmailLog
        from unittest.mock import MagicMock

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No SENT log found
        mock_session.execute.return_value = mock_result

        result = EmailLog.check_idempotency(mock_session, user_id=1, email_type="welcome", hours=24)

        assert result is False


class TestEmailLogCeleryTaskUpdates:
    """Test Celery task updates email log status (T5.3)"""

    @patch("app.worker._update_email_log_success")
    @patch("resend.Emails.send")
    def test_task_updates_log_to_sent_on_success(self, mock_send, mock_update):
        """GIVEN an email log exists with status=queued
        WHEN task_dispatch_resend_email succeeds
        THEN _update_email_log_success is called with log_id and message_id"""
        from app.worker import task_dispatch_resend_email

        mock_send.return_value = {"id": "msg_test123"}

        result = task_dispatch_resend_email.run(
            to="task_test@example.com",
            subject="Test",
            html_body="<p>Test</p>",
            log_id=42,
        )

        assert result["status"] == "sent"
        assert result["message_id"] == "msg_test123"
        mock_update.assert_called_once_with(42, "msg_test123")

    @patch("app.worker._update_email_log_failure")
    @patch("resend.Emails.send")
    def test_task_updates_log_to_failed_on_4xx(self, mock_send, mock_update):
        """GIVEN an email log exists with status=queued
        WHEN task_dispatch_resend_email gets a 4xx error
        THEN _update_email_log_failure is called"""
        from resend.exceptions import ResendError
        from app.worker import task_dispatch_resend_email

        error = ResendError(
            code=400,
            error_type="invalid_request",
            message="Bad request",
            suggested_action="Check parameters",
        )
        mock_send.side_effect = error

        result = task_dispatch_resend_email.run(
            to="task_fail@example.com",
            subject="Test",
            html_body="<p>Test</p>",
            log_id=42,
        )

        assert result["status"] == "failed"
        mock_update.assert_called_once()
        call_args = mock_update.call_args[0]
        assert call_args[0] == 42  # log_id

    @patch("app.worker._update_email_log_retry")
    @patch("resend.Emails.send")
    def test_task_updates_retry_count_on_5xx(self, mock_send, mock_update):
        """GIVEN an email log exists with status=queued
        WHEN task_dispatch_resend_email gets a 5xx error
        THEN _update_email_log_retry is called"""
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
                to="task_retry@example.com",
                subject="Test",
                html_body="<p>Test</p>",
                log_id=42,
            )

        mock_update.assert_called_once()
        call_args = mock_update.call_args[0]
        assert call_args[0] == 42  # log_id

    def test_task_works_without_log_id(self):
        """GIVEN task is called without log_id
        WHEN task runs successfully
        THEN it completes without errors (backward compatibility)"""
        from app.worker import task_dispatch_resend_email

        with patch("resend.Emails.send") as mock_send:
            mock_send.return_value = {"id": "msg_nolog"}

            result = task_dispatch_resend_email.run(
                to="user@example.com",
                subject="Test",
                html_body="<p>Test</p>",
                log_id=None,
            )

            assert result["status"] == "sent"
            assert result["message_id"] == "msg_nolog"


class TestEmailServiceIdempotency:
    """Test idempotency in EmailService (T5.4)"""

    @patch("app.services.email.EmailService.send_transactional_email")
    @patch("app.core.database.SyncSessionLocal")
    def test_skips_email_if_recently_sent(self, mock_session_factory, mock_send):
        """GIVEN a welcome email was sent within 24 hours
        WHEN send_welcome_email is called again
        THEN the email is NOT sent (idempotency check blocks it)"""
        from app.services.email import EmailService
        from app.models.email_log import EmailLog

        # Mock the session to return idempotency=True
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session_factory.return_value = mock_session

        with patch.object(EmailLog, 'check_idempotency', return_value=True):
            EmailService.send_welcome_email(
                to="user@example.com",
                user_name="testuser",
                user_id=1,
            )

            # Should NOT have called send_transactional_email
            mock_send.assert_not_called()

    @patch("app.services.email.EmailService.send_transactional_email")
    @patch("app.core.database.SyncSessionLocal")
    def test_sends_email_if_not_recently_sent(self, mock_session_factory, mock_send):
        """GIVEN no welcome email was sent in the last 24 hours
        WHEN send_welcome_email is called
        THEN the email IS sent"""
        from app.services.email import EmailService
        from app.models.email_log import EmailLog

        # Mock the session
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session_factory.return_value = mock_session

        with patch.object(EmailLog, 'check_idempotency', return_value=False):
            EmailService.send_welcome_email(
                to="user@example.com",
                user_name="testuser",
                user_id=1,
            )

            # Should have called send_transactional_email
            mock_send.assert_called_once()


class TestEmailLogIntegration:
    """Integration test: log creation during registration (T5.2)"""

    @patch("app.services.email.EmailService.send_transactional_email")
    @patch("app.models.email_log.EmailLog.check_idempotency", return_value=False)
    @patch("app.core.database.SyncSessionLocal")
    def test_registration_creates_email_log(self, mock_sync_session, mock_idem, mock_send):
        """GIVEN a user registers successfully
        WHEN POST /auth/register is called
        THEN EmailService.send_welcome_email is called with user_id"""
        from fastapi.testclient import TestClient
        from app.main import app
        from unittest.mock import patch, AsyncMock, MagicMock
        from app.core.database import get_db
        from app.models.user import User

        # Mock sync session for email logging - simulate ID assignment on commit
        mock_sync_sess = MagicMock()
        mock_sync_sess.__enter__ = MagicMock(return_value=mock_sync_sess)
        mock_sync_sess.__exit__ = MagicMock(return_value=False)

        def mock_commit():
            pass  # Simulate commit

        mock_sync_sess.commit = mock_commit
        mock_sync_session.return_value = mock_sync_sess

        # Create mock objects for async DB
        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.email = "logtest@example.com"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(side_effect=[None, mock_user])
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        async def mock_refresh(obj):
            obj.id = 1
            obj.email = "logtest@example.com"

        mock_session.refresh = mock_refresh

        async def fake_get_db():
            yield mock_session

        with patch.object(app, 'dependency_overrides', {get_db: fake_get_db}):
            # Patch EmailLog to assign an ID on init
            from app.models.email_log import EmailLog
            original_init = EmailLog.__init__

            def patched_init(self, *args, **kwargs):
                original_init(self, *args, **kwargs)
                self.id = 99  # Simulate DB-assigned ID

            with patch.object(EmailLog, '__init__', patched_init):
                client = TestClient(app)

                response = client.post(
                    "/auth/register",
                    data={
                        "email": "logtest@example.com",
                        "password": "testpassword123",
                        "password_confirm": "testpassword123",
                    },
                )

                assert response.status_code in (200, 303, 307)

        # Verify email was sent with user_id (which triggers log creation)
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["log_id"] is not None
        assert call_kwargs["log_id"] == 99
