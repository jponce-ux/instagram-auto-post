"""
Meta Instagram webhook router.

Provides endpoints for:
- GET /webhooks/instagram: Hub challenge verification (subscription setup)
- POST /webhooks/instagram: Webhook payload reception with HMAC signature validation

The webhook endpoints are public (no JWT auth) but use HMAC-SHA1
signature validation via X-Hub-Signature header.

When Instagram confirms a post is live on the feed (PUBLISHED) or failed (ERROR),
this handler cleans up the temporary public bucket copy of the image.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.models.post import Post, PostStatus
from app.models.media_file import MediaFile
from app.services.storage import storage_service
from app.webhooks.schemas import WebhookPayload, WebhookValue
from app.webhooks.security import verify_webhook_signature

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/webhooks/instagram")
async def verify_hub_challenge(
    hub_mode: str,
    hub_challenge: str,
    hub_verify_token: str,
):
    """
    Meta webhook subscription verification endpoint.

    Meta sends a GET request during webhook subscription setup to verify
    that this endpoint is controlled by the app owner.

    Args:
        hub_mode: Must be "subscribe"
        hub_challenge: Challenge string to echo back
        hub_verify_token: Must match META_WEBHOOK_VERIFY_TOKEN config

    Returns:
        Plain text response with hub_challenge value

    Raises:
        HTTPException: 403 if verify token doesn't match
    """
    # Validate mode
    if hub_mode != "subscribe":
        raise HTTPException(status_code=403, detail=f"Invalid hub.mode: {hub_mode}")

    # Validate verify token against config
    if hub_verify_token != settings.META_WEBHOOK_VERIFY_TOKEN:
        logger.warning(f"Webhook verification failed: invalid token received")
        raise HTTPException(status_code=403, detail="Invalid verify token")

    logger.info("Webhook subscription verified successfully")

    # Return challenge as plain text (required by Meta)
    return hub_challenge


@router.post("/webhooks/instagram")
@verify_webhook_signature
async def receive_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Receive and process webhook payloads from Meta.

    This endpoint is protected by HMAC-SHA1 signature validation
    via the @verify_webhook_signature decorator.

    Parses webhook payload and updates Post records based on:
    - ig_container_id (primary lookup)
    - ig_media_id (fallback lookup)

    Args:
        request: FastAPI request object containing webhook payload
        db: Database session for Post updates

    Returns:
        200 OK (always returns 200 to acknowledge receipt, even if Post not found)

    Note:
        Always returns 200 to prevent Meta retry storms for orphaned webhooks.
        Logs warnings for posts that cannot be found.
    """
    # Parse payload
    try:
        payload_data = await request.json()
        payload = WebhookPayload(**payload_data)
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        # Still return 200 to acknowledge receipt (prevents Meta retries)
        return {"status": "error", "message": "Invalid payload"}

    # Process each entry and its changes
    for entry in payload.entry:
        for change in entry.changes:
            await _process_webhook_change(change.value, db)

    return {"status": "ok"}


async def _process_webhook_change(
    value: WebhookValue,
    db: AsyncSession,
) -> Optional[Post]:
    """
    Process a single webhook change value and update the corresponding Post.

    Looks up Post by:
    1. ig_container_id (if present in webhook)
    2. ig_media_id (fallback if container_id lookup fails)

    Updates Post status based on webhook status:
    - PUBLISHED: Confirms post is live on Instagram feed, cleans up public bucket
    - ERROR/FAILED: Marks post as failed, cleans up public bucket

    Cleanup: Deletes the temporary public bucket copy of the image once Instagram
    confirms the post is on the feed (or failed), since the private encrypted copy
    remains in the private bucket.

    Args:
        value: The webhook value containing status and IDs
        db: Database session

    Returns:
        The updated Post if found, None otherwise
    """
    post: Optional[Post] = None

    # Try lookup by container_id first (with MediaFile joined for cleanup)
    if value.container_id:
        result = await db.execute(
            select(Post, MediaFile)
            .join(MediaFile, Post.media_file_id == MediaFile.id)
            .where(Post.ig_container_id == value.container_id)
        )
        row = result.first()
        if row:
            post, media_file = row

    # Fallback to media_id lookup if container_id not found
    if post is None and value.media_id:
        result = await db.execute(
            select(Post, MediaFile)
            .join(MediaFile, Post.media_file_id == MediaFile.id)
            .where(Post.ig_media_id == value.media_id)
        )
        row = result.first()
        if row:
            post, media_file = row

    # If no post found, log warning and return (acknowledge webhook)
    if post is None:
        logger.warning(
            f"Webhook received for unknown post: "
            f"container_id={value.container_id}, media_id={value.media_id}"
        )
        return None

    # Determine if public bucket cleanup is needed
    needs_cleanup = False
    status = value.status.upper()

    if status == "PUBLISHED":
        # Even if already PUBLISHED (idempotent), still clean up public bucket
        if post.status == PostStatus.PUBLISHED:
            logger.info(
                f"Post {post.id} already PUBLISHED, cleaning up public bucket"
            )
            needs_cleanup = True
        else:
            post.status = PostStatus.PUBLISHED
            if value.media_id:
                post.ig_media_id = value.media_id
            logger.info(f"Post {post.id} marked as PUBLISHED via webhook")
            await db.commit()
            needs_cleanup = True

    elif status in ("ERROR", "FAILED"):
        # Even if already FAILED (idempotent), still clean up public bucket
        if post.status == PostStatus.FAILED:
            logger.info(
                f"Post {post.id} already FAILED, cleaning up public bucket"
            )
            needs_cleanup = True
        else:
            post.status = PostStatus.FAILED
            if value.error_message:
                post.error_message = value.error_message
            logger.warning(
                f"Post {post.id} marked as FAILED via webhook: {value.error_message}"
            )
            await db.commit()
            needs_cleanup = True

    else:
        logger.info(f"Post {post.id} received status update: {status}")

    # Clean up public bucket: Instagram no longer needs the public URL
    if needs_cleanup and media_file:
        try:
            await storage_service.delete_from_public_bucket(media_file.key)
            logger.info(
                f"Deleted {media_file.key} from public bucket after webhook confirmation"
            )
        except Exception as e:
            logger.warning(
                f"Failed to delete {media_file.key} from public bucket: {e}"
            )

    return post
