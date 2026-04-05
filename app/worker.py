import asyncio
import logging
import time
from celery import Celery
from celery.schedules import interval

from app.core.config import settings
from app.core.database import AsyncSessionLocal, SyncSessionLocal
from app.models.post import Post, PostStatus
from app.models.instagram import InstagramAccount
from app.models.media_file import MediaFile
from app.services.storage import storage_service
from app.services.instagram import (
    create_media_container,
    get_container_status,
    publish_media_container,
)

logger = logging.getLogger(__name__)

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Celery Beat schedule: run check_scheduled_posts every 60 seconds
celery_app.conf.beat_schedule = {
    "check-scheduled-posts": {
        "task": "app.worker.check_scheduled_posts",
        "schedule": interval(seconds=60),
    },
}


@celery_app.task
def debug_task(name: str) -> str:
    """Validates Celery integration."""
    return f"Hello, {name}!"


@celery_app.task(bind=True, max_retries=0)
def check_scheduled_posts(self) -> dict:
    """
    Beat task: query for scheduled posts and dispatch processing tasks.

    Runs every 60 seconds via Celery Beat. Finds posts with status=PENDING
    and scheduled_at <= now(), transitions them to PROCESSING, and dispatches
    process_instagram_post for each.
    """
    from datetime import datetime, timezone
    from sqlalchemy import select

    dispatched_count = 0
    total_found = 0

    def _query_and_dispatch():
        nonlocal dispatched_count, total_found
        with SyncSessionLocal() as session:
            stmt = (
                select(Post)
                .where(
                    Post.status == PostStatus.PENDING,
                    Post.scheduled_at <= datetime.now(timezone.utc),
                )
                .order_by(Post.scheduled_at.asc())
            )
            posts = session.execute(stmt).scalars().all()
            total_found = len(posts)

            for post in posts:
                try:
                    post.status = PostStatus.PROCESSING
                    session.commit()
                    process_instagram_post.delay(post.id)
                    dispatched_count += 1
                    logger.info(f"Dispatched post {post.id} for processing")
                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to dispatch post {post.id}: {e}")

            return total_found

    try:
        # Run sync query in thread pool to avoid blocking
        asyncio.run(asyncio.to_thread(_query_and_dispatch))
        logger.info(
            f"Beat cycle complete: {dispatched_count}/{total_found} posts dispatched"
        )
        return {"found": total_found, "dispatched": dispatched_count, "error": None}
    except Exception as e:
        logger.error(f"Beat task failed: {e}")
        return {"error": str(e), "found": 0, "dispatched": 0}


async def _process_post_async(post_id: int) -> None:
    """
    Process an Instagram post asynchronously.

    Flow:
    1. Fetch Post + InstagramAccount + MediaFile from DB
    2. Update Post status -> PROCESSING
    3. Generate fresh presigned URL
    4. Create media container via Meta API
    5. Poll container status until FINISHED (max 30s)
    6. Publish media container
    7. Update Post status -> PUBLISHED

    On error: Update Post status -> FAILED, store error_message
    """
    async with AsyncSessionLocal() as db:
        try:
            # Step 1: Fetch Post with related data
            from sqlalchemy import select

            result = await db.execute(
                select(Post, InstagramAccount, MediaFile)
                .join(InstagramAccount, Post.ig_account_id == InstagramAccount.id)
                .join(MediaFile, Post.media_file_id == MediaFile.id)
                .where(Post.id == post_id)
            )
            row = result.first()

            if not row:
                raise ValueError(f"Post {post_id} not found or missing related data")

            post, ig_account, media_file = row

            # Step 2: Update status to PROCESSING
            post.status = PostStatus.PROCESSING
            await db.commit()

            # Step 3: Generate fresh presigned URL (10 min expiration)
            media_url = await storage_service.get_presigned_url(
                media_file.key, expires=600
            )

            # Step 4: Create media container
            try:
                container_id = await create_media_container(
                    ig_account_id=ig_account.instagram_account_id,
                    access_token=ig_account.access_token,
                    media_url=media_url,
                    caption=post.caption or "",
                )
                post.ig_container_id = container_id
                await db.commit()
            except Exception as e:
                error_msg = str(e)
                if "token" in error_msg.lower() and "expired" in error_msg.lower():
                    error_msg = (
                        "Token expired - please reconnect your Instagram account"
                    )
                raise Exception(f"Failed to create media container: {error_msg}")

            # Step 5: Poll container status (max 30s, every 2s)
            max_wait = 30  # seconds
            poll_interval = 2  # seconds
            elapsed = 0

            while elapsed < max_wait:
                status_data = await get_container_status(
                    container_id=container_id,
                    access_token=ig_account.access_token,
                )
                status_code = status_data.get("status_code", "")

                if status_code == "FINISHED":
                    break
                elif status_code == "ERROR":
                    raise Exception("Media container processing failed")

                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
            else:
                # Timeout reached
                raise Exception(
                    "Container processing timeout - max wait exceeded (30s)"
                )

            # Step 6: Publish media container
            try:
                media_id = await publish_media_container(
                    ig_account_id=ig_account.instagram_account_id,
                    access_token=ig_account.access_token,
                    container_id=container_id,
                )
                post.ig_media_id = media_id
            except Exception as e:
                error_msg = str(e)
                if "rate limit" in error_msg.lower():
                    error_msg = "Rate limit exceeded - please try again later"
                raise Exception(f"Failed to publish media: {error_msg}")

            # Step 7: Update status to PUBLISHED
            from sqlalchemy.sql import func

            post.status = PostStatus.PUBLISHED
            post.published_at = func.now()
            await db.commit()

        except Exception as e:
            # Error handling: Update status to FAILED
            await db.rollback()

            # Fetch post again to update error
            from sqlalchemy import select

            result = await db.execute(select(Post).where(Post.id == post_id))
            post = result.scalar_one_or_none()

            if post:
                post.status = PostStatus.FAILED
                post.error_message = str(e)
                await db.commit()

            # Re-raise to mark task as failed in Celery
            raise


@celery_app.task(bind=True, max_retries=3)
def process_instagram_post(self, post_id: int) -> str:
    """
    Celery task to process an Instagram post.

    Args:
        post_id: The ID of the Post to process

    Returns:
        Success message with post_id

    Raises:
        Exception on failure (will trigger retry)
    """
    try:
        asyncio.run(_process_post_async(post_id))
        return f"Post {post_id} processed successfully"
    except Exception as exc:
        # Retry with exponential backoff
        retry_count = self.request.retries
        if retry_count < 3:
            # Exponential backoff: 60s, 120s, 240s
            countdown = 60 * (2**retry_count)
            raise self.retry(exc=exc, countdown=countdown)
        raise
