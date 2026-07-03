"""
Instagram Metrics Service — fetches account-level and media-level insights
from the Instagram Graph API with Redis caching and token error handling.

Usage:
    from app.services.metrics import metrics_service

    # Account-level analytics
    result = await metrics_service.get_account_analytics(account_id=1, period="days_28")

    # Media-level analytics (on-demand)
    result = await metrics_service.get_media_analytics(media_id="17841400000000001")
"""

import json
import logging
import time
import asyncio
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

META_API_BASE = "https://graph.instagram.com/v21.0"
API_TIMEOUT = 30.0
CACHE_TTL = 3600  # 1 hour


class InstagramMetricsService:
    """
    Service for fetching Instagram Graph API insights with Redis caching.

    Handles:
    - Account-level metrics (impressions, reach, profile_views, follower_count)
    - Media-level metrics (engagement, impressions, reach, saved, likes, comments)
    - Redis caching with configurable TTL
    - Token error detection and account deactivation
    - Graceful fallback to stale cached data on API failures
    - Concurrent request deduplication (reuses in-flight requests)
    """

    def __init__(self, redis_url: str | None = None):
        self._redis_url = redis_url or settings.CELERY_BROKER_URL
        self._redis: aioredis.Redis | None = None
        self._in_flight: dict[str, asyncio.Future] = {}  # Deduplication tracker

    async def _get_redis(self) -> aioredis.Redis:
        """Get or create async Redis connection."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                self._redis_url,
                decode_responses=True,
            )
        return self._redis

    async def _get_cached(self, key: str) -> dict | None:
        """Get cached data from Redis. Returns None if not found or expired."""
        try:
            redis_client = await self._get_redis()
            data = await redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis cache read failed for {key}: {e}")
        return None

    async def _set_cache(self, key: str, data: dict, ttl: int = CACHE_TTL) -> None:
        """Set cached data in Redis with TTL."""
        try:
            redis_client = await self._get_redis()
            await redis_client.setex(key, ttl, json.dumps(data))
        except Exception as e:
            logger.warning(f"Redis cache write failed for {key}: {e}")

    async def _delete_cache_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern. Returns count of deleted keys."""
        try:
            redis_client = await self._get_redis()
            keys = await redis_client.keys(pattern)
            if keys:
                return await redis_client.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis cache delete failed for pattern {pattern}: {e}")
        return 0

    async def _deduplicate(self, cache_key: str, coro):
        """
        Concurrent request deduplication (T017).

        If multiple requests for the same cache_key arrive simultaneously,
        reuse the in-flight request instead of making duplicate API calls.
        """
        if cache_key in self._in_flight:
            logger.info(f"Reusing in-flight request for {cache_key}")
            return await self._in_flight[cache_key]

        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._in_flight[cache_key] = future

        try:
            result = await coro
            future.set_result(result)
            return result
        except Exception as e:
            future.set_exception(e)
            raise
        finally:
            self._in_flight.pop(cache_key, None)

    async def _call_insights_api(
        self,
        endpoint: str,
        params: dict,
        access_token: str,
    ) -> dict:
        """
        Call the Instagram Graph API insights endpoint.

        Args:
            endpoint: API path (e.g., "/{account_id}/insights")
            params: Query parameters (metric, period, etc.)
            access_token: Instagram access token

        Returns:
            Parsed JSON response

        Raises:
            TokenError: If token is expired/invalid
            APIError: If API call fails for other reasons
        """
        import httpx

        url = f"{META_API_BASE}{endpoint}"
        params["access_token"] = access_token

        start_time = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
                response = await client.get(url, params=params)

                elapsed = time.monotonic() - start_time
                logger.info(
                    f"Instagram API call: {endpoint} — "
                    f"status={response.status_code}, time={elapsed:.2f}s"
                )

                if response.status_code == 401 or response.status_code == 400:
                    body = response.json() if response.content else {}
                    error_type = body.get("error", {}).get("error_subcode", 0)
                    error_message = body.get("error", {}).get("message", "")

                    # Check for token errors (codes 463, 467, OAuthException)
                    if self._is_token_error(error_type, error_message):
                        raise TokenError(
                            f"Token error: {error_message}",
                            error_subcode=error_type,
                        )

                response.raise_for_status()
                return response.json()

        except httpx.TimeoutException:
            elapsed = time.monotonic() - start_time
            logger.error(f"Instagram API timeout: {endpoint} after {elapsed:.2f}s")
            raise APIError(f"API timeout after {elapsed:.2f}s")

        except httpx.HTTPStatusError as e:
            elapsed = time.monotonic() - start_time
            logger.error(
                f"Instagram API HTTP error: {endpoint} — "
                f"status={e.response.status_code}, time={elapsed:.2f}s"
            )
            raise APIError(f"API error: {e.response.status_code}")

    @staticmethod
    def _is_token_error(error_subcode: int, error_message: str) -> bool:
        """Detect if an API error indicates a token problem."""
        if not error_message:
            return False

        msg_lower = error_message.lower()

        # Explicit error codes
        if error_subcode in (463, 467):
            return True

        # OAuth exception patterns
        if "oauthexception" in msg_lower:
            return True

        # Token expired/invalid patterns
        if "token expired" in msg_lower or "token is invalid" in msg_lower:
            return True
        if "access token" in msg_lower and ("expired" in msg_lower or "invalid" in msg_lower):
            return True

        return False

    async def _handle_token_error(self, account_id: int) -> None:
        """
        Handle token error: deactivate account, clear cache, log error.

        Reuses deactivate_account_sync() from TASK-028.
        """
        from app.dashboard.service import deactivate_account_sync

        logger.warning(f"Token error detected for account {account_id} — deactivating")

        # Deactivate the account
        deactivate_account_sync(account_id)

        # Clear all cache keys for this account
        account_deleted = await self._delete_cache_pattern(
            f"insights:account:{account_id}:*"
        )
        media_deleted = await self._delete_cache_pattern(
            f"insights:media:*"  # Broad cleanup — media insights may belong to this account
        )

        logger.info(
            f"Account {account_id} deactivated. "
            f"Cache cleared: {account_deleted} account keys, {media_deleted} media keys"
        )

    async def get_account_analytics(
        self,
        instagram_account_id: str,
        account_id: int,
        period: str = "days_28",
        access_token: str | None = None,
    ) -> dict:
        """
        Fetch account-level insights with caching.

        Args:
            instagram_account_id: Instagram Business Account ID
            account_id: Local database account ID (for cache key and error handling)
            period: "day" or "days_28"
            access_token: Instagram access token

        Returns:
            Dict with metrics, cache status, and timestamp
        """
        cache_key = f"insights:account:{account_id}:{period}"

        # Check cache first
        cached = await self._get_cached(cache_key)
        if cached:
            cached["cached"] = True
            cached["stale"] = False
            logger.info(f"Account analytics cache HIT for account {account_id}")
            return cached

        # Fetch from API with deduplication (T017)
        async def _fetch():
            params = {
                "metric": "impressions,reach,profile_views,follower_count",
                "period": period,
            }
            if access_token:
                params["access_token"] = access_token

            response = await self._call_insights_api(
                f"/{instagram_account_id}/insights",
                params,
                access_token or "",
            )

            # Parse response into flat metrics dict
            metrics = self._parse_account_metrics(response)

            # Cache the result
            result = {
                "account_id": account_id,
                "instagram_account_id": instagram_account_id,
                "period": period,
                "metrics": metrics,
                "cached": False,
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "stale": False,
            }
            await self._set_cache(cache_key, result)

            logger.info(f"Account analytics cache MISS for account {account_id} — fetched fresh")
            return result

        try:
            return await self._deduplicate(cache_key, _fetch())

        except TokenError as e:
            logger.error(f"Token error fetching account analytics: {e}")
            await self._handle_token_error(account_id)
            raise

        except APIError as e:
            logger.error(f"API error fetching account analytics: {e}")
            # Return stale cached data if available
            stale = await self._get_cached(cache_key)
            if stale:
                stale["cached"] = True
                stale["stale"] = True
                logger.info(f"Returning stale cached data for account {account_id}")
                return stale
            raise

    async def get_account_analytics_with_trend(
        self,
        instagram_account_id: str,
        account_id: int,
        period: str = "days_28",
        access_token: str | None = None,
    ) -> dict:
        """
        Fetch account-level insights with trend comparison and timeline data.

        Extends get_account_analytics() by also fetching:
        - Previous period metrics for trend calculation
        - Daily time-series data for chart rendering

        Args:
            instagram_account_id: Instagram Business Account ID
            account_id: Local database account ID (for cache key and error handling)
            period: "day", "days_7", or "days_28"
            access_token: Instagram access token

        Returns:
            Dict with metrics, trends, timeline, cache status, and timestamp
        """
        import datetime

        cache_key = f"insights:account:{account_id}:{period}"

        # Check cache first
        cached = await self._get_cached(cache_key)
        if cached:
            cached["cached"] = True
            cached["stale"] = False
            logger.info(f"Account analytics with trend cache HIT for account {account_id}")
            return cached

        # Calculate date ranges for current and previous periods
        now = datetime.datetime.now(datetime.timezone.utc)

        if period == "days_7":
            days = 7
        elif period == "days_28":
            days = 28
        else:
            days = 1  # period=day

        current_until = int(now.timestamp())
        current_since = int((now - datetime.timedelta(days=days)).timestamp())
        previous_until = current_since
        previous_since = int((now - datetime.timedelta(days=days * 2)).timestamp())

        async def _fetch():
            token = access_token or ""

            # Fetch current period metrics
            current_params = {
                "metric": "impressions,reach,profile_views,follower_count",
                "period": period if period in ("day", "days_28") else "days_28",
            }
            current_response = await self._call_insights_api(
                f"/{instagram_account_id}/insights",
                current_params,
                token,
            )
            current_metrics = self._parse_account_metrics(current_response)

            # Fetch previous period metrics for trend calculation
            previous_params = {
                "metric": "impressions,reach,profile_views,follower_count",
                "period": period if period in ("day", "days_28") else "days_28",
                "since": str(previous_since),
                "until": str(previous_until),
            }
            try:
                previous_response = await self._call_insights_api(
                    f"/{instagram_account_id}/insights",
                    previous_params,
                    token,
                )
                previous_metrics = self._parse_account_metrics(previous_response)
            except (APIError, TokenError):
                # If previous period fetch fails, use zeros for trends
                logger.warning(f"Previous period fetch failed for account {account_id} — trends will be zero")
                previous_metrics = {k: 0 for k in current_metrics}

            # Calculate trends
            trends = self._calculate_trends(current_metrics, previous_metrics)

            # Fetch time-series data for charts
            try:
                timeline = await self._fetch_account_time_series(
                    instagram_account_id=instagram_account_id,
                    access_token=token,
                    since=current_since,
                    until=current_until,
                )
            except (APIError, TokenError) as e:
                logger.warning(f"Time-series fetch failed for account {account_id}: {e}")
                timeline = {"labels": [], "datasets": {}}

            # Build extended result
            result = {
                "account_id": account_id,
                "instagram_account_id": instagram_account_id,
                "period": period,
                "metrics": current_metrics,
                "trends": trends,
                "timeline": timeline,
                "cached": False,
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "stale": False,
            }
            await self._set_cache(cache_key, result)

            logger.info(f"Account analytics with trend cache MISS for account {account_id}")
            return result

        try:
            return await self._deduplicate(cache_key, _fetch())

        except TokenError as e:
            logger.error(f"Token error fetching account analytics with trend: {e}")
            await self._handle_token_error(account_id)
            raise

        except APIError as e:
            logger.error(f"API error fetching account analytics with trend: {e}")
            # Return stale cached data if available
            stale = await self._get_cached(cache_key)
            if stale:
                stale["cached"] = True
                stale["stale"] = True
                logger.info(f"Returning stale cached data for account {account_id}")
                return stale
            raise

    async def get_media_analytics(
        self,
        media_id: str,
        access_token: str | None = None,
    ) -> dict:
        """
        Fetch media-level insights with caching (on-demand).

        Args:
            media_id: Instagram media ID
            access_token: Instagram access token

        Returns:
            Dict with metrics, cache status, and timestamp
        """
        cache_key = f"insights:media:{media_id}"

        # Check cache first
        cached = await self._get_cached(cache_key)
        if cached:
            cached["cached"] = True
            cached["stale"] = False
            logger.info(f"Media analytics cache HIT for media {media_id}")
            return cached

        # Fetch from API with deduplication (T017)
        async def _fetch():
            params = {
                "metric": "engagement,impressions,reach,saved,likes,comments",
            }
            if access_token:
                params["access_token"] = access_token

            response = await self._call_insights_api(
                f"/{media_id}/insights",
                params,
                access_token or "",
            )

            # Parse response into flat metrics dict
            metrics = self._parse_media_metrics(response)

            # Cache the result
            result = {
                "media_id": media_id,
                "metrics": metrics,
                "cached": False,
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "stale": False,
            }
            await self._set_cache(cache_key, result)

            logger.info(f"Media analytics cache MISS for media {media_id} — fetched fresh")
            return result

        try:
            return await self._deduplicate(cache_key, _fetch())

        except TokenError as e:
            logger.error(f"Token error fetching media analytics: {e}")
            # Note: We don't have account_id here, so we can't deactivate
            # The caller should handle this
            raise

        except APIError as e:
            logger.error(f"API error fetching media analytics: {e}")
            # Return stale cached data if available
            stale = await self._get_cached(cache_key)
            if stale:
                stale["cached"] = True
                stale["stale"] = True
                logger.info(f"Returning stale cached data for media {media_id}")
                return stale
            raise

    @staticmethod
    def _calculate_trends(current: dict, previous: dict) -> dict:
        """
        Calculate percentage change between current and previous period metrics.

        Formula: ((current - previous) / previous) * 100

        Edge cases:
        - previous == 0 → trend = 0 (avoid division by zero)
        - both == 0 → trend = 0
        - current == 0, previous > 0 → trend = -100

        Args:
            current: Dict of current period metric values
            previous: Dict of previous period metric values

        Returns:
            Dict of trend percentages per metric (rounded to 1 decimal)
        """
        trends = {}
        for key in current:
            curr_val = current.get(key, 0) or 0
            prev_val = previous.get(key, 0) or 0

            if prev_val == 0:
                trends[key] = 0.0
            else:
                trends[key] = round(((curr_val - prev_val) / prev_val) * 100, 1)

        return trends

    async def _fetch_account_time_series(
        self,
        instagram_account_id: str,
        access_token: str,
        since: int,
        until: int,
    ) -> dict:
        """
        Fetch daily time-series data from Instagram Graph API.

        Uses period=day with since/until timestamps to get one data point per day.

        Args:
            instagram_account_id: Instagram Business Account ID
            access_token: Instagram access token
            since: Unix timestamp for start date
            until: Unix timestamp for end date

        Returns:
            Dict with 'labels' (date strings) and 'datasets' (metric arrays)
        """
        params = {
            "metric": "impressions,reach,profile_views,follower_count",
            "period": "day",
            "since": str(since),
            "until": str(until),
        }

        response = await self._call_insights_api(
            f"/{instagram_account_id}/insights",
            params,
            access_token,
        )

        # Parse time-series response into chart-friendly format
        data = response.get("data", [])

        # Collect all unique dates from all metrics
        all_dates = set()
        metric_values = {}  # metric_name -> {date -> value}

        for item in data:
            name = item.get("name", "")
            values = item.get("values", [])
            metric_values[name] = {}
            for entry in values:
                end_time = entry.get("end_time", "")
                value = entry.get("value", 0)
                # Extract date portion (YYYY-MM-DD)
                date_str = end_time[:10] if end_time else ""
                if date_str:
                    all_dates.add(date_str)
                    metric_values[name][date_str] = value

        # Sort dates chronologically
        sorted_dates = sorted(all_dates)

        # Build aligned datasets
        datasets = {}
        for metric_name in ["impressions", "reach", "profile_views", "follower_count"]:
            datasets[metric_name] = [
                metric_values.get(metric_name, {}).get(date, 0)
                for date in sorted_dates
            ]

        return {
            "labels": sorted_dates,
            "datasets": datasets,
        }

    @staticmethod
    def _parse_account_metrics(response: dict) -> dict:
        """Parse account insights API response into flat metrics dict."""
        metrics = {
            "impressions": 0,
            "reach": 0,
            "profile_views": 0,
            "follower_count": 0,
        }

        data = response.get("data", [])
        for item in data:
            name = item.get("name", "")
            values = item.get("values", [])
            value = item.get("value")

            # Use the most recent value or the single value
            metric_value = 0
            if values:
                metric_value = values[-1].get("value", 0)
            elif value is not None:
                metric_value = value

            if name in metrics:
                metrics[name] = metric_value

        return metrics

    @staticmethod
    def _parse_media_metrics(response: dict) -> dict:
        """Parse media insights API response into flat metrics dict."""
        metrics = {
            "engagement": 0,
            "impressions": 0,
            "reach": 0,
            "saved": 0,
            "likes": 0,
            "comments": 0,
        }

        data = response.get("data", [])
        for item in data:
            name = item.get("name", "")
            values = item.get("values", [])
            value = item.get("value")

            metric_value = 0
            if values:
                metric_value = values[-1].get("value", 0)
            elif value is not None:
                metric_value = value

            if name in metrics:
                metrics[name] = metric_value

        return metrics


class TokenError(Exception):
    """Raised when the Instagram API returns a token-related error."""

    def __init__(self, message: str, error_subcode: int = 0):
        super().__init__(message)
        self.error_subcode = error_subcode


class APIError(Exception):
    """Raised when the Instagram API call fails for non-token reasons."""

    pass


# Singleton instance
metrics_service = InstagramMetricsService()
