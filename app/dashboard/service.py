import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql import func
from fastapi import UploadFile

from app.models.instagram import InstagramAccount
from app.models.post import Post, PostStatus
from app.models.media_file import MediaFile
from app.models.user import User
from app.services.storage import storage_service

logger = logging.getLogger(__name__)


async def get_user_accounts(db: AsyncSession, user: User) -> list[InstagramAccount]:
    """Fetch all Instagram accounts linked to the user."""
    result = await db.execute(
        select(InstagramAccount).where(InstagramAccount.user_id == user.id)
    )
    return list(result.scalars().all())


async def get_user_posts(db: AsyncSession, user: User) -> list[Post]:
    """Fetch all posts belonging to the user, ordered by newest first."""
    result = await db.execute(
        select(Post).where(Post.user_id == user.id).order_by(Post.created_at.desc())
    )
    return list(result.scalars().all())


async def create_post(
    db: AsyncSession,
    user: User,
    file: UploadFile,
    caption: str = "",
) -> Post:
    """
    Create a new post with image upload and immediately dispatch processing.

    1. Upload file to MinIO storage
    2. Create MediaFile record
    3. Create Post record with PENDING status and scheduled_at=now
    4. Dispatch Celery task for immediate processing
    5. Publish SSE event for real-time dashboard update
    """
    # Generate unique storage key
    file_ext = file.filename.split(".")[-1] if "." in file.filename else "bin"
    storage_key = f"{user.id}/{uuid.uuid4()}.{file_ext}"

    # Upload to MinIO
    await storage_service.upload_file(file, storage_key)

    # Create media file record
    media_file = MediaFile(
        key=storage_key,
        original_filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        user_id=user.id,
    )
    db.add(media_file)
    await db.flush()

    # Get first Instagram account for the user (required FK)
    accounts = await get_user_accounts(db, user)
    if not accounts:
        raise ValueError("No Instagram account connected. Connect an account before creating posts.")
    ig_account_id = accounts[0].id

    # Create post record with scheduled_at=now so beat task can pick it up
    post = Post(
        user_id=user.id,
        ig_account_id=ig_account_id,
        media_file_id=media_file.id,
        caption=caption,
        status=PostStatus.PENDING,
        scheduled_at=datetime.now(timezone.utc),
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)

    # Dispatch Celery task for immediate processing (don't wait for beat cycle)
    try:
        from app.worker import process_instagram_post
        process_instagram_post.delay(post.id)
        logger.info(f"Dispatched post {post.id} for immediate processing")
    except Exception as e:
        logger.warning(f"Failed to dispatch post {post.id} to Celery: {e}. Beat task will pick it up.")

    # Publish SSE event so dashboard shows the new post immediately
    try:
        from app.services.sse import sse_manager, POST_UPDATE_CHANNEL
        await sse_manager.publish(POST_UPDATE_CHANNEL, {
            "post_id": post.id,
            "status": "pending",
            "user_id": user.id,
        })
    except Exception as e:
        logger.warning(f"Failed to publish SSE event for new post {post.id}: {e}")

    return post
