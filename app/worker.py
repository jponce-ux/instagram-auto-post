import asyncio
import json
import logging
import time
from celery import Celery
from datetime import timedelta

import redis

from app.core.config import settings
from app.core.database import SyncSessionLocal
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

# Redis client for SSE event publishing (sync, for Celery worker)
_sse_redis = redis.Redis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)
_SSE_CHANNEL = "post_update"


def _sanitize_error_message(error_msg: str) -> str:
    """Remove sensitive data from error messages before showing to users.

    Strips out tokens, internal paths, and technical details while keeping
    the user-facing error description.
    """
    if not error_msg:
        return ""

    # Remove common sensitive patterns
    sanitized = error_msg
    # Remove access tokens (long alphanumeric strings)
    import re
    sanitized = re.sub(r'access_token[=:]\s*[A-Za-z0-9_-]{20,}', 'access_token=[REDACTED]', sanitized)
    # Remove internal URLs with query params
    sanitized = re.sub(r'(https?://[^\s]+\?)[^\s]+', r'\1[REDACTED]', sanitized)
    # Remove Python tracebacks
    if 'Traceback (most recent call last)' in sanitized:
        sanitized = sanitized.split('Traceback')[0].strip()
    # Remove Instagram API error codes/types but keep the message
    sanitized = re.sub(r'Instagram API error \d+: \w+ — ', '', sanitized)

    # Truncate if too long
    if len(sanitized) > 200:
        sanitized = sanitized[:197] + "..."

    return sanitized


def _is_token_error(error_msg: str) -> bool:
    """Detect if an error message indicates a token expiry/invalidation.

    Checks for:
    - Instagram Graph API error codes 463, 467 (token expired/invalid)
    - OAuthException patterns
    - Existing "token expired" string matching
    - "invalid" + "token" combinations
    """
    if not error_msg:
        return False

    msg_lower = error_msg.lower()

    # Explicit error codes
    if "463" in error_msg or "467" in error_msg:
        return True

    # OAuth exception patterns
    if "oauthexception" in msg_lower:
        return True

    # Existing string match from TASK-027
    if "token expired" in msg_lower:
        return True

    # Token + invalid combination
    if "token" in msg_lower and ("invalid" in msg_lower or "expired" in msg_lower):
        return True

    return False


def _publish_post_event(post_id: int, status: str, user_id: int, error_message: str = "") -> None:
    """Publish a post status change event to Redis for SSE streaming.

    Fire-and-forget: failures are logged but don't affect post processing.
    Sync version for use in Celery tasks.
    """
    try:
        event = json.dumps({
            "post_id": post_id,
            "status": status,
            "user_id": user_id,
            "error_message": _sanitize_error_message(error_message) if error_message else "",
        })
        _sse_redis.publish(_SSE_CHANNEL, event)
        logger.debug(f"SSE event published: post_id={post_id}, status={status}")
    except Exception as e:
        logger.warning(f"Failed to publish SSE event for post {post_id}: {e}")


def _publish_account_event(account_id: int, is_active: bool, reason: str, user_id: int = 0) -> None:
    """Publish an account status change event to Redis for SSE streaming.

    Fire-and-forget: failures are logged but don't affect post processing.
    Sync version for use in Celery tasks.
    """
    try:
        event = json.dumps({
            "account_id": account_id,
            "is_active": is_active,
            "reason": reason,
            "user_id": user_id,
        })
        _sse_redis.publish("account_update", event)
        logger.debug(f"SSE account event published: account_id={account_id}, is_active={is_active}")
    except Exception as e:
        logger.warning(f"Failed to publish SSE account event for account {account_id}: {e}")


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
        "schedule": timedelta(seconds=60),
    },
    "check-stalled-posts": {
        "task": "app.worker.check_stalled_posts",
        "schedule": timedelta(seconds=60),
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
                    post.processing_started_at = datetime.now(timezone.utc)
                    session.commit()
                    process_instagram_post.delay(post.id)
                    _publish_post_event(post.id, "processing", post.user_id)
                    dispatched_count += 1
                    logger.info(f"Dispatched post {post.id} for processing")
                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to dispatch post {post.id}: {e}")

            return total_found

    try:
        _query_and_dispatch()
        logger.info(
            f"Beat cycle complete: {dispatched_count}/{total_found} posts dispatched"
        )
        return {"found": total_found, "dispatched": dispatched_count, "error": None}
    except Exception as e:
        logger.error(f"Beat task failed: {e}")
        return {"error": str(e), "found": 0, "dispatched": 0}


@celery_app.task(bind=True, max_retries=0)
def check_stalled_posts(self) -> dict:
    """
    Beat task: detect posts stuck in processing or retrying state and mark them as failed.

    Runs every 60 seconds via Celery Beat. Finds posts where:
    - status='processing' AND processing_started_at < NOW() - 15 minutes
    - status='retrying' AND processing_started_at < NOW() - 5 minutes

    Transitions them to FAILED with appropriate error message and publishes SSE events.
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select

    stalled_count = 0

    def _find_and_fail_stalled():
        nonlocal stalled_count
        now = datetime.now(timezone.utc)
        processing_timeout = now - timedelta(minutes=15)
        retrying_timeout = now - timedelta(minutes=5)

        with SyncSessionLocal() as session:
            # Find stalled processing posts
            stmt_processing = (
                select(Post)
                .where(
                    Post.status == PostStatus.PROCESSING,
                    Post.processing_started_at != None,
                    Post.processing_started_at < processing_timeout,
                )
            )
            stalled_processing = session.execute(stmt_processing).scalars().all()

            for post in stalled_processing:
                try:
                    post.status = PostStatus.FAILED
                    post.processing_started_at = None
                    post.error_message = "Processing timeout exceeded"
                    session.commit()
                    _publish_post_event(
                        post.id, "failed", post.user_id, "Processing timeout exceeded"
                    )
                    stalled_count += 1
                    logger.info(f"Marked post {post.id} as failed: processing timeout")
                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to mark post {post.id} as failed: {e}")

            # Find stalled retrying posts
            stmt_retrying = (
                select(Post)
                .where(
                    Post.status == PostStatus.RETRYING,
                    Post.processing_started_at != None,
                    Post.processing_started_at < retrying_timeout,
                )
            )
            stalled_retrying = session.execute(stmt_retrying).scalars().all()

            for post in stalled_retrying:
                try:
                    post.status = PostStatus.FAILED
                    post.processing_started_at = None
                    post.error_message = "Retry timeout exceeded"
                    session.commit()
                    _publish_post_event(
                        post.id, "failed", post.user_id, "Retry timeout exceeded"
                    )
                    stalled_count += 1
                    logger.info(f"Marked post {post.id} as failed: retry timeout")
                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to mark post {post.id} as failed: {e}")

            # Fallback: posts with NULL processing_started_at in processing/retrying state
            # Use created_at as fallback for pre-migration posts
            fallback_timeout = now - timedelta(minutes=15)
            stmt_fallback = (
                select(Post)
                .where(
                    Post.status == PostStatus.PROCESSING,
                    Post.processing_started_at == None,
                    Post.created_at < fallback_timeout,
                )
            )
            fallback_posts = session.execute(stmt_fallback).scalars().all()

            for post in fallback_posts:
                try:
                    post.status = PostStatus.FAILED
                    post.error_message = "Processing timeout exceeded"
                    session.commit()
                    _publish_post_event(
                        post.id, "failed", post.user_id, "Processing timeout exceeded"
                    )
                    stalled_count += 1
                    logger.info(f"Marked post {post.id} as failed: processing timeout (fallback)")
                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to mark post {post.id} as failed: {e}")

            return stalled_count

    try:
        _find_and_fail_stalled()
        logger.info(f"Stalled post check complete: {stalled_count} posts marked as failed")
        return {"stalled": stalled_count, "error": None}
    except Exception as e:
        logger.error(f"Stalled post check failed: {e}")
        return {"error": str(e), "stalled": 0}


def _process_post_sync(post_id: int) -> None:
    """
    Process an Instagram post synchronously (for Celery worker).

    Uses SyncSessionLocal for DB operations to avoid asyncpg event loop conflicts.
    Wraps async external calls (storage, IG API) in individual asyncio.run() calls.

    Flow:
    1. Fetch Post + InstagramAccount + MediaFile from DB
    2. Update Post status -> PROCESSING, clear previous error_message
    3. Copy file to public bucket (Instagram needs public URL)
    4. Generate public URL for Instagram API
    5. Create media container via Meta API
    6. Poll container status until FINISHED (max 30s)
    7. Publish media container
    8. Update Post status -> PUBLISHED (awaiting webhook confirmation)

    Public bucket cleanup is NOT done here — the webhook handler deletes the
    public copy once Instagram confirms the image is live on the feed.

    On error: rollback, cleanup public bucket, re-raise.
    Status transitions (FAILED/RETRYING) are handled by the task wrapper.
    """
    from sqlalchemy import select
    from sqlalchemy.sql import func
    from datetime import datetime, timezone

    # Timeout for async operations (prevent indefinite hangs)
    ASYNC_TIMEOUT = 60  # seconds

    def _run_with_timeout(coro):
        """Run async coroutine with timeout to prevent indefinite hangs."""
        return asyncio.run(asyncio.wait_for(coro, timeout=ASYNC_TIMEOUT))

    with SyncSessionLocal() as db:
        try:
            # Step 1: Fetch Post with related data
            result = db.execute(
                select(Post, InstagramAccount, MediaFile)
                .join(InstagramAccount, Post.ig_account_id == InstagramAccount.id)
                .join(MediaFile, Post.media_file_id == MediaFile.id)
                .where(Post.id == post_id)
            )
            row = result.first()

            if not row:
                raise ValueError(f"Post {post_id} not found or missing related data")

            post, ig_account, media_file = row

            # Step 2: Update status to PROCESSING, clear any previous error
            post.status = PostStatus.PROCESSING
            post.processing_started_at = datetime.now(timezone.utc)
            post.error_message = None
            db.commit()

            # Step 3: Ensure public bucket exists with correct policy, then copy file
            _run_with_timeout(storage_service.ensure_bucket_exists())
            _run_with_timeout(storage_service.copy_to_public_bucket(media_file.key))

            # Step 4: Generate public URL (no auth params, Instagram can access)
            media_url = _run_with_timeout(storage_service.get_public_url(media_file.key))

            # Step 5: Create media container
            try:
                container_id = _run_with_timeout(create_media_container(
                    ig_account_id=ig_account.instagram_account_id,
                    access_token=ig_account.access_token,
                    media_url=media_url,
                    caption=post.caption or "",
                ))
                post.ig_container_id = container_id
                db.commit()
            except Exception as e:
                error_msg = str(e)
                if _is_token_error(error_msg):
                    error_msg = (
                        "Token expired - please reconnect your Instagram account"
                    )
                    # Deactivate the account so dashboard shows "Inactiva"
                    try:
                        from app.dashboard.service import deactivate_account_sync
                        deactivate_account_sync(ig_account.id)
                        _publish_account_event(
                            account_id=ig_account.id,
                            is_active=False,
                            reason="token_expired",
                            user_id=post.user_id,
                        )
                    except Exception as deact_err:
                        logger.error(f"Failed to deactivate account {ig_account.id}: {deact_err}")
                raise Exception(f"Failed to create media container: {error_msg}")

            # Step 6: Poll container status (max 30s, every 2s)
            max_wait = 30  # seconds
            poll_interval = 2  # seconds
            elapsed = 0

            while elapsed < max_wait:
                status_data = _run_with_timeout(get_container_status(
                    container_id=container_id,
                    access_token=ig_account.access_token,
                ))
                status_code = status_data.get("status_code", "")

                if status_code == "FINISHED":
                    break
                elif status_code == "ERROR":
                    raise Exception("Media container processing failed")

                time.sleep(poll_interval)
                elapsed += poll_interval
            else:
                # Timeout reached
                raise Exception(
                    "Container processing timeout - max wait exceeded (30s)"
                )

            # Step 7: Publish media container
            try:
                media_id = _run_with_timeout(publish_media_container(
                    ig_account_id=ig_account.instagram_account_id,
                    access_token=ig_account.access_token,
                    container_id=container_id,
                ))
                post.ig_media_id = media_id
            except Exception as e:
                error_msg = str(e)
                if "rate limit" in error_msg.lower():
                    error_msg = "Rate limit exceeded - please try again later"
                raise Exception(f"Failed to publish media: {error_msg}")

            # Step 8: Update status to PUBLISHED
            # Note: Do NOT delete from public bucket here. Instagram still needs
            # to download the image. Cleanup happens when the webhook confirms
            # the post is live on the feed (see webhooks/meta.py).
            post.status = PostStatus.PUBLISHED
            post.processing_started_at = None
            post.published_at = func.now()
            db.commit()
            _publish_post_event(post.id, "published", post.user_id)

        except Exception as e:
            # Rollback any partial DB changes
            db.rollback()

            # Cleanup: delete from public bucket (non-critical)
            try:
                _run_with_timeout(storage_service.delete_from_public_bucket(media_file.key))
            except Exception:
                pass

            # Re-raise so the task wrapper can decide status
            raise


@celery_app.task(bind=True, max_retries=3)
def process_instagram_post(self, post_id: int) -> str:
    """
    Celery task to process an Instagram post.

    Handles status transitions based on retry state:
    - Processing: while attempting or retrying
    - Retrying: between attempts (with error info for the dashboard)
    - Failed: all retries exhausted
    - Published: successful completion

    Args:
        post_id: The ID of the Post to process

    Returns:
        Success message with post_id

    Raises:
        Exception on final failure (after all retries exhausted)
    """
    retry_count = self.request.retries

    try:
        _process_post_sync(post_id)
        return f"Post {post_id} processed successfully"
    except Exception as exc:
        from sqlalchemy import select
        from datetime import datetime, timezone

        if retry_count < 3:
            # Mark as RETRYING so dashboard shows "reintentando..."
            # instead of "fallido" while retries are pending
            error_msg = str(exc)
            with SyncSessionLocal() as db:
                result = db.execute(select(Post).where(Post.id == post_id))
                post = result.scalar_one_or_none()
                if post:
                    post.status = PostStatus.RETRYING
                    post.processing_started_at = datetime.now(timezone.utc)
                    post.error_message = error_msg
                    db.commit()
                    _publish_post_event(post.id, "retrying", post.user_id, error_msg)

                    # Also publish account event if token expiry detected
                    if _is_token_error(error_msg):
                        from app.dashboard.service import deactivate_account_sync
                        # Account may already be deactivated in _process_post_sync,
                        # but publish SSE event as safety net
                        _publish_account_event(
                            account_id=post.ig_account_id,
                            is_active=False,
                            reason="token_expired",
                            user_id=post.user_id,
                        )

            # Exponential backoff: 60s, 120s, 240s
            countdown = 60 * (2**retry_count)
            raise self.retry(exc=exc, countdown=countdown)
        else:
            # All retries exhausted — mark as FAILED
            error_msg = str(exc)
            with SyncSessionLocal() as db:
                result = db.execute(select(Post).where(Post.id == post_id))
                post = result.scalar_one_or_none()
                if post:
                    post.status = PostStatus.FAILED
                    post.processing_started_at = None
                    post.error_message = error_msg
                    db.commit()
                    _publish_post_event(post.id, "failed", post.user_id, error_msg)

                    # Publish account event if token expiry caused the failure
                    if _is_token_error(error_msg):
                        _publish_account_event(
                            account_id=post.ig_account_id,
                            is_active=False,
                            reason="token_expired",
                            user_id=post.user_id,
                        )
            raise


# ============================================================
# Email Tasks (Resend)
# ============================================================

def _update_email_log_success(log_id: int, message_id: str) -> None:
    """Update email log status to 'sent' after successful send."""
    from app.models.email_log import EmailLog
    from datetime import datetime, timezone

    with SyncSessionLocal() as session:
        log_entry = session.get(EmailLog, log_id)
        if log_entry:
            log_entry.status = "sent"
            log_entry.message_id = message_id
            log_entry.sent_at = datetime.now(timezone.utc)
            session.commit()
            logger.info(f"Email log {log_id} updated to 'sent'")


def _update_email_log_failure(log_id: int, error: str, retry_count: int = 0) -> None:
    """Update email log status to 'failed' after final failure."""
    from app.models.email_log import EmailLog
    from datetime import datetime, timezone

    with SyncSessionLocal() as session:
        log_entry = session.get(EmailLog, log_id)
        if log_entry:
            log_entry.status = "failed"
            log_entry.error_message = error
            log_entry.failed_at = datetime.now(timezone.utc)
            log_entry.retry_count = retry_count
            session.commit()
            logger.info(f"Email log {log_id} updated to 'failed'")


def _update_email_log_retry(log_id: int, retry_count: int) -> None:
    """Update retry count on email log during retry attempts."""
    from app.models.email_log import EmailLog

    with SyncSessionLocal() as session:
        log_entry = session.get(EmailLog, log_id)
        if log_entry:
            log_entry.retry_count = retry_count
            session.commit()


@celery_app.task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def task_dispatch_resend_email(
    self,
    to: str,
    subject: str,
    html_body: str,
    from_email: str | None = None,
    from_name: str | None = None,
    log_id: int | None = None,
) -> dict:
    """
    Celery task to send an email via Resend API.

    Retries up to 3 times with exponential backoff for transient errors.
    Does NOT retry for 4xx client errors (bad request, invalid email, etc.).

    Args:
        to: Recipient email address
        subject: Email subject line
        html_body: HTML content of the email
        from_email: Sender email (defaults to MAIL_FROM_ADDRESS config)
        from_name: Sender name (defaults to MAIL_FROM_NAME config)
        log_id: Optional email_logs ID for status tracking

    Returns:
        dict with 'message_id' on success

    Raises:
        resend.error.ResendError: On API failure (triggers retry for 5xx)
    """
    import resend
    from app.core.config import settings

    # Configure Resend API key in the worker process
    resend.api_key = settings.RESEND_API_KEY

    sender = from_email or settings.MAIL_FROM_ADDRESS
    sender_name = from_name or settings.MAIL_FROM_NAME

    try:
        email_response = resend.Emails.send({
            "from": f"{sender_name} <{sender}>",
            "to": [to],
            "subject": subject,
            "html": html_body,
        })
        message_id = email_response.get("id", "unknown")
        logger.info(
            f"Email sent successfully to {to}: message_id={message_id}"
        )

        # Update log status on success
        if log_id:
            _update_email_log_success(log_id, message_id)

        return {"message_id": message_id, "to": to, "status": "sent"}
    except Exception as e:
        # Check if it's a 4xx client error — don't retry
        status_code = getattr(e, "code", None)
        retry_count = self.request.retries

        if status_code and 400 <= status_code < 500:
            logger.error(
                f"Email failed (client error {status_code}) for {to}: {e}"
            )
            if log_id:
                _update_email_log_failure(log_id, str(e), retry_count)
            return {"error": str(e), "to": to, "status": "failed", "status_code": status_code}

        logger.warning(
            f"Email failed for {to} (will retry, attempt {retry_count + 1}/3): {e}"
        )

        if log_id:
            _update_email_log_retry(log_id, retry_count)

        if retry_count >= 3:
            if log_id:
                _update_email_log_failure(log_id, str(e), retry_count)

        raise
