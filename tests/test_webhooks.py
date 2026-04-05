"""
Tests for spec-015-meta-webhooks
Meta Instagram webhook integration with HMAC-SHA1 signature validation.
"""

import hmac
import hashlib
import json
import time
from unittest.mock import Mock, patch, MagicMock, AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.config import settings
from app.core.database import get_db
from app.models.post import Post, PostStatus


# Create mock database session for testing
def override_get_db():
    """Override for get_db dependency - returns mock session."""
    mock_db = AsyncMock(spec=AsyncSession)
    yield mock_db


# Override the dependency
app.dependency_overrides[get_db] = override_get_db

# Test Client
client = TestClient(app)


class TestSignatureValidation:
    """Tests for HMAC-SHA1 signature validation decorator"""

    def test_valid_signature_passes_validation(self):
        """Test: Valid signature → passes validation (200 response)

        GIVEN a POST request with valid X-Hub-Signature header
        WHEN HMAC-SHA1 computed over body matches signature
        THEN payload is processed and returns 200"""
        # Create a known payload
        payload = {
            "object": "instagram",
            "entry": [
                {
                    "id": "123456",
                    "time": int(time.time()),
                    "changes": [
                        {
                            "value": {
                                "media_id": "media_123",
                                "container_id": "container_123",
                                "status": "PUBLISHED",
                                "timestamp": int(time.time()),
                            },
                            "field": "mentions",
                        }
                    ],
                }
            ],
        }
        body = json.dumps(payload)

        # Compute valid HMAC-SHA1 signature
        app_secret = settings.META_APP_SECRET.encode("utf-8")
        signature = hmac.new(app_secret, body.encode("utf-8"), hashlib.sha1).hexdigest()

        response = client.post(
            "/webhooks/instagram",
            data=body,
            headers={"X-Hub-Signature": f"sha1={signature}"},
        )

        # Should return 200 (acknowledges webhook even if post not found)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_invalid_signature_returns_401(self):
        """Test: Invalid signature → returns 401

        GIVEN a POST request with tampered body or wrong signature
        WHEN signature validation fails
        THEN system returns 401 Unauthorized"""
        payload = {"object": "instagram", "entry": []}
        body = json.dumps(payload)

        # Use an invalid signature
        response = client.post(
            "/webhooks/instagram",
            data=body,
            headers={"X-Hub-Signature": "sha1=invalid_signature_hash"},
        )

        assert response.status_code == 401
        assert "signature" in response.text.lower() or "Invalid" in response.text

    def test_missing_signature_returns_401(self):
        """Test: Missing signature → returns 401

        GIVEN a POST request without X-Hub-Signature header
        WHEN signature validation is attempted
        THEN system returns 401 Unauthorized"""
        payload = {"object": "instagram", "entry": []}
        body = json.dumps(payload)

        response = client.post(
            "/webhooks/instagram",
            data=body,
            # No X-Hub-Signature header
        )

        assert response.status_code == 401

    def test_invalid_signature_format_returns_401(self):
        """Test: Invalid signature format → returns 401

        GIVEN a POST request with X-Hub-Signature not starting with 'sha1='
        WHEN signature parsing is attempted
        THEN system returns 401 Unauthorized"""
        payload = {"object": "instagram", "entry": []}
        body = json.dumps(payload)

        response = client.post(
            "/webhooks/instagram",
            data=body,
            headers={"X-Hub-Signature": "invalid_format_no_sha1_prefix"},
        )

        assert response.status_code == 401


class TestHubChallengeVerification:
    """Tests for GET /webhooks/instagram hub challenge verification"""

    def test_valid_verification_returns_challenge(self):
        """Test: Valid hub.challenge → returns 200 with challenge

        GIVEN Meta servers send GET with correct verify_token
        WHEN hub.mode=subscribe, hub.challenge, hub.verify_token are correct
        THEN system returns 200 with plain text hub.challenge value"""
        challenge = "test_challenge_123"

        response = client.get(
            "/webhooks/instagram",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": challenge,
                "hub.verify_token": settings.META_WEBHOOK_VERIFY_TOKEN,
            },
        )

        assert response.status_code == 200
        assert response.text == f'"{challenge}"' or response.text == challenge

    def test_invalid_verify_token_returns_403(self):
        """Test: Invalid verify_token → returns 403

        GIVEN request contains incorrect hub.verify_token
        THEN system returns 403 Forbidden"""
        response = client.get(
            "/webhooks/instagram",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "test_challenge",
                "hub.verify_token": "wrong_token",
            },
        )

        assert response.status_code == 403

    def test_invalid_hub_mode_returns_403(self):
        """Test: Invalid hub.mode → returns 403

        GIVEN hub.mode is not 'subscribe'
        THEN system returns 403 Forbidden"""
        response = client.get(
            "/webhooks/instagram",
            params={
                "hub.mode": "unsubscribe",  # Invalid mode
                "hub.challenge": "test_challenge",
                "hub.verify_token": settings.META_WEBHOOK_VERIFY_TOKEN,
            },
        )

        assert response.status_code == 403


class TestWebhookPayloadProcessing:
    """Tests for webhook payload processing and Post updates"""

    def _create_valid_signature(self, body: str) -> str:
        """Helper to create a valid HMAC-SHA1 signature"""
        app_secret = settings.META_APP_SECRET.encode("utf-8")
        return hmac.new(app_secret, body.encode("utf-8"), hashlib.sha1).hexdigest()

    @patch("app.webhooks.meta._process_webhook_change")
    def test_webhook_calls_process_function(self, mock_process):
        """Test: Webhook calls _process_webhook_change for each change

        GIVEN valid webhook payload with entries
        WHEN signature is valid
        THEN _process_webhook_change is called for each change"""
        mock_process.return_value = None

        payload = {
            "object": "instagram",
            "entry": [
                {
                    "id": "123456",
                    "time": int(time.time()),
                    "changes": [
                        {
                            "value": {
                                "media_id": "media_123",
                                "container_id": "container_123",
                                "status": "PUBLISHED",
                            },
                            "field": "mentions",
                        }
                    ],
                }
            ],
        }
        body = json.dumps(payload)
        signature = self._create_valid_signature(body)

        response = client.post(
            "/webhooks/instagram",
            data=body,
            headers={"X-Hub-Signature": f"sha1={signature}"},
        )

        assert response.status_code == 200
        mock_process.assert_called_once()

    @patch("app.webhooks.meta._process_webhook_change")
    def test_multiple_entries_processed(self, mock_process):
        """Test: Multiple entries in webhook → all processed

        GIVEN webhook contains multiple entries with different posts
        WHEN payload is parsed
        THEN all entries are processed"""
        mock_process.return_value = None

        payload = {
            "object": "instagram",
            "entry": [
                {
                    "id": "123456",
                    "time": int(time.time()),
                    "changes": [
                        {
                            "value": {
                                "container_id": "container_1",
                                "status": "PUBLISHED",
                            },
                            "field": "mentions",
                        }
                    ],
                },
                {
                    "id": "789012",
                    "time": int(time.time()),
                    "changes": [
                        {
                            "value": {
                                "container_id": "container_2",
                                "status": "PUBLISHED",
                            },
                            "field": "mentions",
                        }
                    ],
                },
            ],
        }
        body = json.dumps(payload)
        signature = self._create_valid_signature(body)

        response = client.post(
            "/webhooks/instagram",
            data=body,
            headers={"X-Hub-Signature": f"sha1={signature}"},
        )

        assert response.status_code == 200
        assert mock_process.call_count == 2  # Two changes processed

    @patch("app.webhooks.meta.logger")
    def test_invalid_payload_returns_200_with_error(self, mock_logger):
        """Test: Invalid JSON payload → returns 200 with error status

        GIVEN invalid JSON in request body
        WHEN parsing fails
        THEN returns 200 with error message (acknowledges to prevent retries)"""
        # Invalid JSON body
        body = "not valid json {{"
        signature = self._create_valid_signature(body)

        response = client.post(
            "/webhooks/instagram",
            data=body,
            headers={"X-Hub-Signature": f"sha1={signature}"},
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "error"
        mock_logger.error.assert_called_once()


class TestProcessWebhookChangeUnit:
    """Unit tests for _process_webhook_change function"""

    @pytest.mark.asyncio
    async def test_post_found_by_container_id_updates_status(self):
        """Test: Post found by container_id → status updated to PUBLISHED

        GIVEN webhook contains ig_container_id that matches a Post
        WHEN Post with matching ig_container_id exists
        THEN Post is updated with new status PUBLISHED"""
        from app.webhooks.meta import _process_webhook_change
        from app.webhooks.schemas import WebhookValue

        # Setup mock post
        mock_post = Mock(spec=Post)
        mock_post.id = 1
        mock_post.status = PostStatus.PROCESSING

        # Setup mock database
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_post
        mock_db.execute.return_value = mock_result

        # Create webhook value
        value = WebhookValue(
            media_id="media_123", container_id="container_123", status="PUBLISHED"
        )

        result = await _process_webhook_change(value, mock_db)

        assert result == mock_post
        assert mock_post.status == PostStatus.PUBLISHED
        assert mock_post.ig_media_id == "media_123"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_post_found_by_media_id_fallback(self):
        """Test: Post lookup falls back to media_id when container_id not found

        GIVEN webhook contains ig_media_id but no matching container_id
        WHEN no Post matches container_id but media_id matches
        THEN Post is updated with new status"""
        from app.webhooks.meta import _process_webhook_change
        from app.webhooks.schemas import WebhookValue

        # Setup mock post
        mock_post = Mock(spec=Post)
        mock_post.id = 2
        mock_post.status = PostStatus.PROCESSING

        # Setup mock database - first query returns None, second returns post
        mock_db = AsyncMock(spec=AsyncSession)

        first_result = MagicMock()
        first_result.scalar_one_or_none.return_value = None

        second_result = MagicMock()
        second_result.scalar_one_or_none.return_value = mock_post

        mock_db.execute.side_effect = [first_result, second_result]

        # Create webhook value without container_id
        value = WebhookValue(media_id="media_456", status="PUBLISHED")

        result = await _process_webhook_change(value, mock_db)

        assert result == mock_post
        assert mock_post.status == PostStatus.PUBLISHED
        assert mock_db.execute.call_count == 2  # Both lookups attempted

    @pytest.mark.asyncio
    async def test_post_not_found_returns_none_and_logs(self):
        """Test: Post not found → returns None and logs warning

        GIVEN webhook references unknown container_id or media_id
        THEN returns None AND error is logged without crashing"""
        from app.webhooks.meta import _process_webhook_change
        from app.webhooks.schemas import WebhookValue

        # Setup mock database - returns None for both lookups
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Create webhook value
        value = WebhookValue(
            media_id="unknown_media",
            container_id="unknown_container",
            status="PUBLISHED",
        )

        with patch("app.webhooks.meta.logger") as mock_logger:
            result = await _process_webhook_change(value, mock_db)

        assert result is None
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_status_updates_to_failed(self):
        """Test: Webhook with ERROR status → Post marked as FAILED

        GIVEN Meta sends POST with entry containing status=ERROR
        WHEN payload is validated and parsed
        THEN Post status is updated to FAILED AND error_message is stored"""
        from app.webhooks.meta import _process_webhook_change
        from app.webhooks.schemas import WebhookValue

        # Setup mock post
        mock_post = Mock(spec=Post)
        mock_post.id = 3
        mock_post.status = PostStatus.PROCESSING

        # Setup mock database
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_post
        mock_db.execute.return_value = mock_result

        # Create webhook value with ERROR status
        value = WebhookValue(
            container_id="container_789",
            status="ERROR",
            error_message="Media upload failed: invalid format",
        )

        result = await _process_webhook_change(value, mock_db)

        assert result == mock_post
        assert mock_post.status == PostStatus.FAILED
        assert mock_post.error_message == "Media upload failed: invalid format"
        mock_db.commit.assert_called_once()


class TestWebhookSchemas:
    """Tests for webhook Pydantic schemas"""

    def test_webhook_value_schema(self):
        """Test: WebhookValue schema validates correctly"""
        from app.webhooks.schemas import WebhookValue

        data = {
            "media_id": "media_123",
            "container_id": "container_123",
            "status": "PUBLISHED",
            "error_message": None,
            "timestamp": 1234567890,
        }

        value = WebhookValue(**data)
        assert value.media_id == "media_123"
        assert value.container_id == "container_123"
        assert value.status == "PUBLISHED"

    def test_webhook_payload_schema(self):
        """Test: WebhookPayload schema validates correctly"""
        from app.webhooks.schemas import WebhookPayload

        data = {
            "object": "instagram",
            "entry": [
                {
                    "id": "123456",
                    "time": 1234567890,
                    "changes": [
                        {"value": {"status": "PUBLISHED"}, "field": "mentions"}
                    ],
                }
            ],
        }

        payload = WebhookPayload(**data)
        assert payload.object == "instagram"
        assert len(payload.entry) == 1
        assert payload.entry[0].id == "123456"

    def test_webhook_value_optional_fields(self):
        """Test: WebhookValue schema handles optional fields"""
        from app.webhooks.schemas import WebhookValue

        # Minimal data (only required field: status)
        value = WebhookValue(status="PUBLISHED")
        assert value.status == "PUBLISHED"
        assert value.media_id is None
        assert value.container_id is None


class TestWebhookSecurityUnit:
    """Unit tests for security module"""

    def test_decorator_requires_request_object(self):
        """Test: Decorator raises 500 if Request object not found"""
        from app.webhooks.security import verify_webhook_signature

        @verify_webhook_signature
        async def handler_without_request():
            return {"status": "ok"}

        import asyncio

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(handler_without_request())

        assert exc_info.value.status_code == 500


# Mark async tests
pytestmark = pytest.mark.asyncio
