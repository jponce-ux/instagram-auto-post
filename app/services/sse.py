"""
Server-Sent Events (SSE) manager for real-time post status updates.

Uses Redis pub/sub to broadcast post status changes from Celery workers
to connected dashboard clients via SSE streams.

Usage:
    # In Celery worker (publish events):
    from app.services.sse import sse_manager
    await sse_manager.publish("post_update", {"post_id": 1, "status": "processing"})

    # In FastAPI endpoint (subscribe and stream):
    from app.services.sse import sse_manager
    async for event in sse_manager.subscribe("post_update"):
        yield event
"""

import json
import asyncio
import logging
from typing import AsyncGenerator

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis channel for post status updates
POST_UPDATE_CHANNEL = "post_update"


class SSEManager:
    """Manages SSE connections via Redis pub/sub."""

    def __init__(self, redis_url: str | None = None):
        self._redis_url = redis_url or settings.CELERY_BROKER_URL
        self._pubsub: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        """Get or create Redis connection for pub/sub."""
        if self._pubsub is None:
            self._pubsub = aioredis.from_url(
                self._redis_url,
                decode_responses=True,
            )
        return self._pubsub

    async def publish(self, channel: str, data: dict) -> None:
        """Publish an event to a Redis channel.

        Args:
            channel: Redis channel name (e.g., "post_update")
            data: Event data to publish (will be JSON serialized)
        """
        try:
            redis_client = await self._get_redis()
            message = json.dumps(data)
            await redis_client.publish(channel, message)
            logger.debug(f"SSE published to {channel}: {data}")
        except Exception as e:
            # Non-critical: SSE is a nice-to-have, not required for core functionality
            logger.warning(f"Failed to publish SSE event to {channel}: {e}")

    @staticmethod
    def format_sse_event(event_type: str, data: dict) -> str:
        """Format data as a Server-Sent Event string.

        Args:
            event_type: SSE event type (e.g., "post_update")
            data: Event data (will be JSON serialized)

        Returns:
            Formatted SSE event string
        """
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    async def subscribe(self, channel: str) -> AsyncGenerator[str, None]:
        """Subscribe to a Redis channel and yield SSE-formatted events.

        This is an async generator that yields SSE event strings.
        It also sends heartbeats every 15 seconds to keep the connection alive.

        Args:
            channel: Redis channel name to subscribe to

        Yields:
            SSE-formatted event strings
        """
        redis_client = await self._get_redis()
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)

        try:
            while True:
                # Use wait_for with timeout to allow heartbeat
                try:
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True),
                        timeout=15.0,
                    )
                    if message and message["type"] == "message":
                        # Yield as SSE event
                        yield self.format_sse_event(channel, json.loads(message["data"]))
                    else:
                        # Timeout — send heartbeat
                        yield ":heartbeat\n\n"
                except asyncio.TimeoutError:
                    # Send heartbeat on timeout
                    yield ":heartbeat\n\n"
        except asyncio.CancelledError:
            logger.debug(f"SSE subscription to {channel} cancelled")
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            logger.debug(f"SSE subscription to {channel} closed")


# Singleton instance
sse_manager = SSEManager()
