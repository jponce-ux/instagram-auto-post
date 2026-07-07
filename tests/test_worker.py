"""
Tests for task-028-post-timeout-retry
Stalled Post Timeout, Retry, and Token Health Check
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock

# Set required env vars BEFORE importing app modules
os.environ.setdefault("META_APP_SECRET", "test_app_secret_for_testing_12345")
os.environ.setdefault("META_WEBHOOK_VERIFY_TOKEN", "test_verify_token_12345")
os.environ.setdefault("SECRET_KEY", "test_secret_key_for_testing")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("CELERY_BROKER_URL", "redis://redis:6379/0")

from app.worker import _is_token_error


# ============================================================
# Token Error Detection Tests
# ============================================================
# Requirement: FR-009 — Token errors detected by error codes 463, 467
# Requirement: FR-010 — Non-token errors do NOT deactivate account
# User Story 3 — Token Health Detection and Account Deactivation


class TestIsTokenError:
    """Tests for _is_token_error helper in app.worker.

    Covers:
    - Instagram Graph API error codes 463, 467 (token expired/invalid)
    - HTTP 401 Unauthorized
    - OAuthException patterns
    - "token expired" string matching
    - "token" + "invalid" / "expired" combinations
    - Non-token errors (rate limit, server errors, network errors)
    - Edge cases (empty string, None, mixed case)
    """

    # --- Error Codes ---

    def test_error_code_463(self):
        """GIVEN error message contains '463'
        WHEN _is_token_error checks it
        THEN returns True (token-related error)"""
        assert _is_token_error("Instagram API error 463: OAuthException — The access token has expired") is True

    def test_error_code_467(self):
        """GIVEN error message contains '467'
        WHEN _is_token_error checks it
        THEN returns True (token-related error)"""
        assert _is_token_error("Instagram API error 467: OAuthException — Access token has been revoked") is True

    def test_error_code_in_message_not_error(self):
        """GIVEN error message with '463' as part of a larger number
        WHEN _is_token_error checks it
        THEN returns True (substring match is sufficient)"""
        assert _is_token_error("Something 463 happened") is True

    # --- HTTP 401 Unauthorized ---

    def test_http_401(self):
        """GIVEN error response with HTTP 401
        WHEN _is_token_error checks it
        THEN returns True"""
        assert _is_token_error("HTTP 401: Unauthorized — token invalid") is True

    def test_unauthorized_string(self):
        """GIVEN error contains 'unauthorized'
        WHEN _is_token_error checks it
        THEN returns True"""
        assert _is_token_error("Unauthorized request") is True

    # --- OAuthException Patterns ---

    def test_oauth_exception(self):
        """GIVEN error contains 'OAuthException'
        WHEN _is_token_error checks it
        THEN returns True"""
        assert _is_token_error("OAuthException: The access token is invalid") is True

    def test_oauth_exception_lowercase(self):
        """GIVEN error contains 'oauthexception' (lowercase)
        WHEN _is_token_error checks it
        THEN returns True"""
        assert _is_token_error("oauthexception: token expired") is True

    # --- Token Expired String ---

    def test_token_expired(self):
        """GIVEN error contains 'token expired'
        WHEN _is_token_error checks it
        THEN returns True"""
        assert _is_token_error("The token has expired") is True

    def test_token_expired_mixed_case(self):
        """GIVEN error contains 'Token Expired' (mixed case)
        WHEN _is_token_error checks it (lowercased)
        THEN returns True"""
        assert _is_token_error("Token Expired: please refresh") is True

    # --- Token + Invalid Combination ---

    def test_token_invalid(self):
        """GIVEN error contains 'token' and 'invalid'
        WHEN _is_token_error checks it
        THEN returns True"""
        assert _is_token_error("Access token is invalid") is True

    def test_token_expired_combination(self):
        """GIVEN error contains 'token' and 'expired'
        WHEN _is_token_error checks it
        THEN returns True"""
        assert _is_token_error("Your token has expired") is True

    # --- Non-Token Errors ---

    def test_rate_limit_error(self):
        """GIVEN error is a rate limit
        WHEN _is_token_error checks it
        THEN returns False"""
        assert _is_token_error("Rate limit exceeded") is False

    def test_network_timeout(self):
        """GIVEN error is a network timeout
        WHEN _is_token_error checks it
        THEN returns False"""
        assert _is_token_error("Connection timeout") is False

    def test_server_error(self):
        """GIVEN error is a server error
        WHEN _is_token_error checks it
        THEN returns False"""
        assert _is_token_error("Instagram API error 500: ServerError — Internal server error") is False

    def test_invalid_parameter(self):
        """GIVEN error is an invalid parameter
        WHEN _is_token_error checks it
        THEN returns False"""
        assert _is_token_error("Instagram API error 400: InvalidParameter — caption too long") is False

    # --- Edge Cases ---

    def test_empty_string(self):
        """GIVEN error message is empty
        WHEN _is_token_error checks it
        THEN returns False"""
        assert _is_token_error("") is False

    def test_none_input(self):
        """GIVEN error message is None
        WHEN _is_token_error checks it
        THEN returns False"""
        assert _is_token_error(None) is False

    def test_whitespace_only(self):
        """GIVEN error message is whitespace
        WHEN _is_token_error checks it
        THEN returns False"""
        assert _is_token_error("   ") is False

    def test_code_463_in_other_context(self):
        """GIVEN message has '463' in non-error context
        WHEN _is_token_error checks it
        THEN returns True (substring match)"""
        assert _is_token_error("Post 463 was processed") is True
