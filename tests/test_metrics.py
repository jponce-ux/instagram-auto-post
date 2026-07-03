"""Unit tests for InstagramMetricsService (TASK-029).

Tests cover:
- Cache hit/miss for account and media analytics
- Token error handling and account deactivation
- API failure with stale data fallback
- Concurrent request deduplication
- Partial metrics parsing
"""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set env vars BEFORE importing app modules
os.environ.setdefault("META_APP_SECRET", "test_secret")
os.environ.setdefault("META_WEBHOOK_VERIFY_TOKEN", "test_token")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "test")
os.environ.setdefault("MINIO_SECRET_KEY", "test")
os.environ.setdefault("MINIO_BUCKET_NAME", "test")


from app.services.metrics import (
    APIError,
    InstagramMetricsService,
    TokenError,
)


@pytest.fixture
def mock_redis():
    """Create a mock async Redis client."""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()
    redis_mock.keys = AsyncMock(return_value=[])
    redis_mock.delete = AsyncMock(return_value=0)
    return redis_mock


@pytest.fixture
def service(mock_redis):
    """Create InstagramMetricsService with mocked Redis."""
    svc = InstagramMetricsService(redis_url="redis://localhost:6379/0")
    svc._redis = mock_redis
    return svc


# ============================================================
# Account Analytics Tests (T018)
# ============================================================


class TestGetAccountAnalytics:
    """Tests for get_account_analytics method."""

    @pytest.mark.asyncio
    async def test_cache_hit(self, service, mock_redis):
        """Cache hit returns cached data without API call."""
        cached_data = {
            "account_id": 1,
            "instagram_account_id": "12345",
            "period": "days_28",
            "metrics": {"impressions": 1000, "reach": 800, "profile_views": 50, "follower_count": 200},
            "cached": False,
            "fetched_at": "2026-06-30T10:00:00Z",
            "stale": False,
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))

        result = await service.get_account_analytics(
            instagram_account_id="12345",
            account_id=1,
            period="days_28",
            access_token="test_token",
        )

        assert result["cached"] is True
        assert result["stale"] is False
        assert result["metrics"]["impressions"] == 1000
        # API should NOT be called
        assert not hasattr(service, "_call_insights_api_called")

    @pytest.mark.asyncio
    async def test_cache_miss_api_success(self, service, mock_redis):
        """Cache miss fetches from API and caches result."""
        mock_redis.get = AsyncMock(return_value=None)

        api_response = {
            "data": [
                {"name": "impressions", "values": [{"value": 5000}]},
                {"name": "reach", "values": [{"value": 3500}]},
                {"name": "profile_views", "value": 120},
                {"name": "follower_count", "values": [{"value": 1500}]},
            ]
        }

        with patch.object(service, "_call_insights_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = api_response

            result = await service.get_account_analytics(
                instagram_account_id="12345",
                account_id=1,
                period="days_28",
                access_token="test_token",
            )

            assert result["cached"] is False
            assert result["stale"] is False
            assert result["metrics"]["impressions"] == 5000
            assert result["metrics"]["reach"] == 3500
            assert result["metrics"]["profile_views"] == 120
            assert result["metrics"]["follower_count"] == 1500
            mock_api.assert_called_once()
            # Verify cache was set
            mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_token_error_deactivates_account(self, service, mock_redis):
        """Token error triggers account deactivation and raises TokenError."""
        mock_redis.get = AsyncMock(return_value=None)

        with patch.object(service, "_call_insights_api", new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = TokenError("Token expired", error_subcode=467)

            with patch("app.dashboard.service.deactivate_account_sync", return_value=True):
                with pytest.raises(TokenError):
                    await service.get_account_analytics(
                        instagram_account_id="12345",
                        account_id=1,
                        period="days_28",
                        access_token="expired_token",
                    )

    @pytest.mark.asyncio
    async def test_api_error_returns_stale_cache(self, service, mock_redis):
        """API error returns stale cached data if available."""
        stale_data = {
            "account_id": 1,
            "instagram_account_id": "12345",
            "period": "days_28",
            "metrics": {"impressions": 900, "reach": 700, "profile_views": 40, "follower_count": 190},
            "cached": False,
            "fetched_at": "2026-06-29T10:00:00Z",
            "stale": False,
        }
        # First call: cache miss, then API fails, then stale fetch
        call_count = 0

        async def mock_get(key):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None  # Initial cache miss
            return json.dumps(stale_data)  # Stale data after API failure

        mock_redis.get = AsyncMock(side_effect=mock_get)

        with patch.object(service, "_call_insights_api", new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = APIError("API timeout after 30.00s")

            result = await service.get_account_analytics(
                instagram_account_id="12345",
                account_id=1,
                period="days_28",
                access_token="test_token",
            )

            assert result["cached"] is True
            assert result["stale"] is True
            assert result["metrics"]["impressions"] == 900

    @pytest.mark.asyncio
    async def test_api_error_no_cache_raises(self, service, mock_redis):
        """API error with no cached data raises APIError."""
        mock_redis.get = AsyncMock(return_value=None)

        with patch.object(service, "_call_insights_api", new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = APIError("API unavailable")

            with pytest.raises(APIError):
                await service.get_account_analytics(
                    instagram_account_id="12345",
                    account_id=1,
                    period="days_28",
                    access_token="test_token",
                )


# ============================================================
# Media Analytics Tests (T019)
# ============================================================


class TestGetMediaAnalytics:
    """Tests for get_media_analytics method."""

    @pytest.mark.asyncio
    async def test_cache_hit(self, service, mock_redis):
        """Cache hit returns cached media data without API call."""
        cached_data = {
            "media_id": "media_123",
            "metrics": {"engagement": 450, "impressions": 3200, "reach": 2800, "saved": 85, "likes": 320, "comments": 45},
            "cached": False,
            "fetched_at": "2026-06-30T10:00:00Z",
            "stale": False,
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))

        result = await service.get_media_analytics(
            media_id="media_123",
            access_token="test_token",
        )

        assert result["cached"] is True
        assert result["stale"] is False
        assert result["metrics"]["engagement"] == 450
        assert result["metrics"]["likes"] == 320

    @pytest.mark.asyncio
    async def test_cache_miss_api_success(self, service, mock_redis):
        """Cache miss fetches media insights from API."""
        mock_redis.get = AsyncMock(return_value=None)

        api_response = {
            "data": [
                {"name": "engagement", "values": [{"value": 500}]},
                {"name": "impressions", "values": [{"value": 4000}]},
                {"name": "reach", "value": 3500},
                {"name": "saved", "values": [{"value": 100}]},
                {"name": "likes", "values": [{"value": 350}]},
                {"name": "comments", "values": [{"value": 50}]},
            ]
        }

        with patch.object(service, "_call_insights_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = api_response

            result = await service.get_media_analytics(
                media_id="media_123",
                access_token="test_token",
            )

            assert result["cached"] is False
            assert result["metrics"]["engagement"] == 500
            assert result["metrics"]["impressions"] == 4000
            assert result["metrics"]["reach"] == 3500
            assert result["metrics"]["saved"] == 100
            assert result["metrics"]["likes"] == 350
            assert result["metrics"]["comments"] == 50

    @pytest.mark.asyncio
    async def test_partial_metrics(self, service, mock_redis):
        """Partial API response fills missing metrics with zeros."""
        mock_redis.get = AsyncMock(return_value=None)

        # Only returns some metrics
        api_response = {
            "data": [
                {"name": "impressions", "values": [{"value": 2000}]},
                {"name": "likes", "values": [{"value": 150}]},
            ]
        }

        with patch.object(service, "_call_insights_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = api_response

            result = await service.get_media_analytics(
                media_id="media_456",
                access_token="test_token",
            )

            assert result["metrics"]["impressions"] == 2000
            assert result["metrics"]["likes"] == 150
            # Missing metrics should be 0
            assert result["metrics"]["engagement"] == 0
            assert result["metrics"]["reach"] == 0
            assert result["metrics"]["saved"] == 0
            assert result["metrics"]["comments"] == 0

    @pytest.mark.asyncio
    async def test_api_error_returns_stale(self, service, mock_redis):
        """API error returns stale cached media data."""
        stale_data = {
            "media_id": "media_789",
            "metrics": {"engagement": 200, "impressions": 1500, "reach": 1200, "saved": 30, "likes": 150, "comments": 20},
            "cached": False,
            "fetched_at": "2026-06-29T10:00:00Z",
            "stale": False,
        }
        call_count = 0

        async def mock_get(key):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None
            return json.dumps(stale_data)

        mock_redis.get = AsyncMock(side_effect=mock_get)

        with patch.object(service, "_call_insights_api", new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = APIError("Rate limit exceeded")

            result = await service.get_media_analytics(
                media_id="media_789",
                access_token="test_token",
            )

            assert result["cached"] is True
            assert result["stale"] is True
            assert result["metrics"]["impressions"] == 1500


# ============================================================
# Token Error Detection Tests
# ============================================================


class TestIsTokenError:
    """Tests for _is_token_error static method."""

    def test_error_code_463(self):
        assert InstagramMetricsService._is_token_error(463, "Some error") is True

    def test_error_code_467(self):
        assert InstagramMetricsService._is_token_error(467, "Some error") is True

    def test_oauth_exception(self):
        assert InstagramMetricsService._is_token_error(0, "OAuthException: token expired") is True

    def test_token_expired(self):
        assert InstagramMetricsService._is_token_error(0, "The token has expired") is True

    def test_token_invalid(self):
        assert InstagramMetricsService._is_token_error(0, "Access token is invalid") is True

    def test_not_token_error(self):
        assert InstagramMetricsService._is_token_error(0, "Rate limit exceeded") is False

    def test_empty_message(self):
        assert InstagramMetricsService._is_token_error(0, "") is False

    def test_other_error_code(self):
        assert InstagramMetricsService._is_token_error(190, "Some other error") is False


# ============================================================
# Metrics Parsing Tests
# ============================================================


class TestParseAccountMetrics:
    """Tests for _parse_account_metrics static method."""

    def test_full_response(self):
        response = {
            "data": [
                {"name": "impressions", "values": [{"value": 10000}]},
                {"name": "reach", "values": [{"value": 7500}]},
                {"name": "profile_views", "value": 200},
                {"name": "follower_count", "values": [{"value": 5000}]},
            ]
        }
        result = InstagramMetricsService._parse_account_metrics(response)
        assert result["impressions"] == 10000
        assert result["reach"] == 7500
        assert result["profile_views"] == 200
        assert result["follower_count"] == 5000

    def test_empty_response(self):
        response = {"data": []}
        result = InstagramMetricsService._parse_account_metrics(response)
        assert result == {"impressions": 0, "reach": 0, "profile_views": 0, "follower_count": 0}

    def test_missing_metrics(self):
        response = {"data": [{"name": "impressions", "values": [{"value": 500}]}]}
        result = InstagramMetricsService._parse_account_metrics(response)
        assert result["impressions"] == 500
        assert result["reach"] == 0  # Missing metric defaults to 0


class TestParseMediaMetrics:
    """Tests for _parse_media_metrics static method."""

    def test_full_response(self):
        response = {
            "data": [
                {"name": "engagement", "values": [{"value": 300}]},
                {"name": "impressions", "values": [{"value": 2000}]},
                {"name": "reach", "value": 1800},
                {"name": "saved", "values": [{"value": 50}]},
                {"name": "likes", "values": [{"value": 200}]},
                {"name": "comments", "values": [{"value": 30}]},
            ]
        }
        result = InstagramMetricsService._parse_media_metrics(response)
        assert result["engagement"] == 300
        assert result["impressions"] == 2000
        assert result["reach"] == 1800
        assert result["saved"] == 50
        assert result["likes"] == 200
        assert result["comments"] == 30

    def test_empty_response(self):
        response = {"data": []}
        result = InstagramMetricsService._parse_media_metrics(response)
        assert result["engagement"] == 0
        assert result["impressions"] == 0


# ============================================================
# Concurrent Request Deduplication Tests (T017)
# ============================================================


class TestConcurrentDeduplication:
    """Tests for concurrent request deduplication."""

    @pytest.mark.asyncio
    async def test_deduplication_reuses_in_flight(self, service, mock_redis):
        """Concurrent requests for same key reuse the in-flight request."""
        mock_redis.get = AsyncMock(return_value=None)
        call_count = 0

        async def slow_api(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            import asyncio
            await asyncio.sleep(0.1)
            return {"data": [{"name": "impressions", "values": [{"value": 100}]}]}

        with patch.object(service, "_call_insights_api", new=slow_api):
            import asyncio
            task1 = asyncio.create_task(
                service.get_account_analytics("12345", 1, "days_28", "token")
            )
            task2 = asyncio.create_task(
                service.get_account_analytics("12345", 1, "days_28", "token")
            )

            results = await asyncio.gather(task1, task2)

            # Both should succeed with same data
            assert results[0]["metrics"]["impressions"] == 100
            assert results[1]["metrics"]["impressions"] == 100
            # API should only be called once due to deduplication
            assert call_count == 1
