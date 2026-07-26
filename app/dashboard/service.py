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


async def get_post_image_url(db: AsyncSession, user: User, post: Post) -> dict | None:
    """Generate presigned URLs for a post's thumbnail and full-size image.

    Verifies that the user owns the media file before generating URLs.
    Returns None if the post has no associated media file.

    Args:
        db: AsyncSession for database operations
        user: The authenticated user (for ownership check)
        post: The Post to get the image URLs for

    Returns:
        Dict with 'thumbnail_url' and 'full_image_url', or None if no image.
        If no thumbnail exists, thumbnail_url is None and full_image_url is used.
    """
    if not post.media_file_id:
        return None

    result = await db.execute(
        select(MediaFile).where(
            MediaFile.id == post.media_file_id,
            MediaFile.user_id == user.id,
        )
    )
    media_file = result.scalar_one_or_none()
    if not media_file:
        return None

    full_image_url = None
    thumbnail_url = None

    try:
        full_image_url = await storage_service.get_presigned_url(media_file.key, expires=3600)
    except Exception as e:
        logger.warning(f"Failed to generate presigned URL for post {post.id}: {e}")
        return None

    # Generate thumbnail URL if available
    if media_file.thumbnail_key:
        try:
            thumbnail_url = await storage_service.get_presigned_url(media_file.thumbnail_key, expires=3600)
        except Exception as e:
            logger.warning(f"Failed to generate thumbnail URL for post {post.id}: {e}")
            # Fall back to full image — don't fail the whole request

    return {
        "thumbnail_url": thumbnail_url,
        "full_image_url": full_image_url,
    }


async def deactivate_account(db: AsyncSession, account_id: int) -> None:
    """Deactivate an Instagram account (set is_active=False).

    Called when token expiry is detected during post processing.
    """
    result = await db.execute(
        select(InstagramAccount).where(InstagramAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    if account:
        account.is_active = False
        await db.commit()
        logger.info(f"Instagram account {account_id} deactivated due to token expiry")


def deactivate_account_sync(account_id: int) -> bool:
    """Deactivate an Instagram account (sync version for Celery worker).

    Returns True if account was found and deactivated, False otherwise.
    """
    from app.core.database import SyncSessionLocal

    with SyncSessionLocal() as session:
        result = session.execute(
            select(InstagramAccount).where(InstagramAccount.id == account_id)
        )
        account = result.scalar_one_or_none()
        if account:
            account.is_active = False
            session.commit()
            logger.info(f"Instagram account {account_id} deactivated due to token expiry")
            return True
        logger.warning(f"Cannot deactivate account {account_id}: not found")
        return False


async def retry_post(db: AsyncSession, user: User, post_id: int) -> Post:
    """Retry a failed post by re-dispatching it to the Celery worker.

    Verifies:
    - User owns the post
    - Post is in FAILED state
    - Associated Instagram account is active

    Returns the updated Post with status set to PROCESSING.
    Raises ValueError on validation failures.
    """
    result = await db.execute(
        select(Post).where(
            Post.id == post_id,
            Post.user_id == user.id,
        )
    )
    post = result.scalar_one_or_none()
    if not post:
        raise ValueError("Post not found")

    if post.status != PostStatus.FAILED:
        raise ValueError(f"Post is not in a failed state. Current status: {post.status.value}")

    # Verify the associated Instagram account is active
    ig_result = await db.execute(
        select(InstagramAccount).where(
            InstagramAccount.id == post.ig_account_id,
            InstagramAccount.user_id == user.id,
        )
    )
    ig_account = ig_result.scalar_one_or_none()
    if not ig_account:
        raise ValueError("Instagram account not found")
    if not ig_account.is_active:
        raise ValueError("Instagram account is inactive. Please reconnect your account.")

    # Transition to PROCESSING
    post.status = PostStatus.PROCESSING
    post.processing_started_at = datetime.now(timezone.utc)
    post.error_message = None
    await db.commit()
    await db.refresh(post)

    # Dispatch Celery task
    try:
        from app.worker import process_instagram_post
        process_instagram_post.delay(post.id)
        logger.info(f"Retried post {post.id} for processing")
    except Exception as e:
        logger.warning(f"Failed to dispatch retry for post {post.id}: {e}")

    # Publish SSE event
    try:
        from app.services.sse import sse_manager, POST_UPDATE_CHANNEL
        await sse_manager.publish(POST_UPDATE_CHANNEL, {
            "post_id": post.id,
            "status": "processing",
            "user_id": user.id,
        })
    except Exception as e:
        logger.warning(f"Failed to publish SSE event for retry post {post.id}: {e}")

    return post


async def create_post(
    db: AsyncSession,
    user: User,
    file: UploadFile,
    caption: str = "",
) -> Post:
    """
    Create a new post with image upload and immediately dispatch processing.

    1. Upload file to MinIO storage
    2. Generate and upload thumbnail (for image files)
    3. Create MediaFile record with both original and thumbnail keys
    4. Create Post record with PENDING status and scheduled_at=now
    5. Dispatch Celery task for immediate processing
    6. Publish SSE event for real-time dashboard update
    """
    # Read file content once for both upload and thumbnail generation
    content = await file.read()
    file.file.seek(0)

    # Upload original to MinIO
    storage_key = await storage_service.upload_file(file, user.id)

    # Generate and upload thumbnail for image files
    thumbnail_key = None
    content_type = file.content_type or "application/octet-stream"
    if content_type.startswith("image/"):
        thumbnail_bytes = storage_service.generate_thumbnail(content, content_type)
        if thumbnail_bytes:
            thumbnail_key = await storage_service.upload_thumbnail(thumbnail_bytes, storage_key)
            if thumbnail_key:
                logger.info(
                    f"Thumbnail generated for post upload: "
                    f"{len(thumbnail_bytes)} bytes -> {thumbnail_key}"
                )

    # Create media file record with both keys
    media_file = MediaFile(
        key=storage_key,
        thumbnail_key=thumbnail_key,
        original_filename=file.filename or "upload",
        content_type=content_type,
        user_id=user.id,
    )
    db.add(media_file)
    await db.flush()

    # Get first Instagram account for the user (required FK)
    accounts = await get_user_accounts(db, user)
    if not accounts:
        raise ValueError("No Instagram account connected. Connect an account before creating posts.")

    # Check if the account is active (not deactivated due to token expiry)
    active_accounts = [acc for acc in accounts if acc.is_active]
    if not active_accounts:
        raise ValueError("Instagram account is inactive. Please reconnect your account.")

    ig_account_id = active_accounts[0].id

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
    post.processing_started_at = datetime.now(timezone.utc)
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


async def create_scheduled_post(
    db: AsyncSession,
    user: User,
    file: UploadFile,
    caption: str,
    scheduled_at: datetime,
    ig_account_id: int | None = None,
) -> Post:
    """
    Create a new scheduled post with future publish date.

    1. Upload file to MinIO storage
    2. Generate and upload thumbnail (for image files)
    3. Create MediaFile record with both original and thumbnail keys
    4. Create Post record with SCHEDULED status and user-specified scheduled_at
    5. Publish SSE event for real-time dashboard update

    Args:
        db: AsyncSession for database operations
        user: The authenticated user
        file: UploadFile with the image/video
        caption: Post caption text
        scheduled_at: Future datetime when post should be published
        ig_account_id: Optional specific Instagram account ID (uses first active if not provided)

    Returns:
        Created Post with SCHEDULED status

    Raises:
        ValueError: If no Instagram account connected or validation fails
    """
    # Validate scheduled_at is in the future
    now = datetime.now(timezone.utc)
    if scheduled_at <= now:
        raise ValueError("Scheduled date must be in the future")

    # Read file content once for both upload and thumbnail generation
    content = await file.read()
    file.file.seek(0)

    # Upload original to MinIO
    storage_key = await storage_service.upload_file(file, user.id)

    # Generate and upload thumbnail for image files
    thumbnail_key = None
    content_type = file.content_type or "application/octet-stream"
    if content_type.startswith("image/"):
        thumbnail_bytes = storage_service.generate_thumbnail(content, content_type)
        if thumbnail_bytes:
            thumbnail_key = await storage_service.upload_thumbnail(thumbnail_bytes, storage_key)
            if thumbnail_key:
                logger.info(
                    f"Thumbnail generated for scheduled post: "
                    f"{len(thumbnail_bytes)} bytes -> {thumbnail_key}"
                )

    # Create media file record with both keys
    media_file = MediaFile(
        key=storage_key,
        thumbnail_key=thumbnail_key,
        original_filename=file.filename or "upload",
        content_type=content_type,
        user_id=user.id,
    )
    db.add(media_file)
    await db.flush()

    # Get Instagram account
    if ig_account_id is None:
        accounts = await get_user_accounts(db, user)
        if not accounts:
            raise ValueError("No Instagram account connected. Connect an account before creating posts.")
        active_accounts = [acc for acc in accounts if acc.is_active]
        if not active_accounts:
            raise ValueError("Instagram account is inactive. Please reconnect your account.")
        ig_account_id = active_accounts[0].id
    else:
        # Verify the specified account belongs to user and is active
        result = await db.execute(
            select(InstagramAccount).where(
                InstagramAccount.id == ig_account_id,
                InstagramAccount.user_id == user.id,
            )
        )
        ig_account = result.scalar_one_or_none()
        if not ig_account:
            raise ValueError("Instagram account not found")
        if not ig_account.is_active:
            raise ValueError("Instagram account is inactive. Please reconnect your account.")

    # Create post record with SCHEDULED status
    post = Post(
        user_id=user.id,
        ig_account_id=ig_account_id,
        media_file_id=media_file.id,
        caption=caption,
        status=PostStatus.SCHEDULED,
        scheduled_at=scheduled_at,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)

    logger.info(f"Created scheduled post {post.id} for {scheduled_at.isoformat()}")

    # Publish SSE event so agenda shows the new post immediately
    try:
        from app.services.sse import sse_manager, POST_UPDATE_CHANNEL
        await sse_manager.publish(POST_UPDATE_CHANNEL, {
            "post_id": post.id,
            "status": "scheduled",
            "user_id": user.id,
        })
    except Exception as e:
        logger.warning(f"Failed to publish SSE event for scheduled post {post.id}: {e}")

    return post


async def get_scheduled_posts(db: AsyncSession, user: User) -> list[Post]:
    """
    Fetch all scheduled posts for a user, ordered by scheduled_at (nearest first).

    Args:
        db: AsyncSession for database operations
        user: The authenticated user

    Returns:
        List of Post objects with SCHEDULED status
    """
    result = await db.execute(
        select(Post)
        .where(Post.user_id == user.id, Post.status == PostStatus.SCHEDULED)
        .order_by(Post.scheduled_at.asc())
    )
    return list(result.scalars().all())


async def update_scheduled_post(
    db: AsyncSession,
    user: User,
    post_id: int,
    caption: str | None = None,
    scheduled_at: datetime | None = None,
) -> Post:
    """
    Update a scheduled post's caption or scheduled time.

    Args:
        db: AsyncSession for database operations
        user: The authenticated user
        post_id: ID of the post to update
        caption: New caption text (if provided)
        scheduled_at: New scheduled time (if provided)

    Returns:
        Updated Post

    Raises:
        ValueError: If post not found, not scheduled, or validation fails
    """
    result = await db.execute(
        select(Post).where(
            Post.id == post_id,
            Post.user_id == user.id,
            Post.status == PostStatus.SCHEDULED,
        )
    )
    post = result.scalar_one_or_none()
    if not post:
        raise ValueError("Scheduled post not found")

    # Validate new scheduled_at if provided
    if scheduled_at is not None:
        now = datetime.now(timezone.utc)
        if scheduled_at <= now:
            raise ValueError("Scheduled date must be in the future")
        post.scheduled_at = scheduled_at

    if caption is not None:
        post.caption = caption

    await db.commit()
    await db.refresh(post)

    logger.info(f"Updated scheduled post {post.id}")

    # Publish SSE event
    try:
        from app.services.sse import sse_manager, POST_UPDATE_CHANNEL
        await sse_manager.publish(POST_UPDATE_CHANNEL, {
            "post_id": post.id,
            "status": "scheduled",
            "user_id": user.id,
            "updated": True,
        })
    except Exception as e:
        logger.warning(f"Failed to publish SSE event for updated post {post.id}: {e}")

    return post


async def delete_scheduled_post(db: AsyncSession, user: User, post_id: int) -> None:
    """
    Delete a scheduled post.

    Args:
        db: AsyncSession for database operations
        user: The authenticated user
        post_id: ID of the post to delete

    Raises:
        ValueError: If post not found, not scheduled, or already processing
    """
    result = await db.execute(
        select(Post).where(
            Post.id == post_id,
            Post.user_id == user.id,
            Post.status == PostStatus.SCHEDULED,
        )
    )
    post = result.scalar_one_or_none()
    if not post:
        raise ValueError("Scheduled post not found")

    await db.delete(post)
    await db.commit()

    logger.info(f"Deleted scheduled post {post_id}")

    # Publish SSE event
    try:
        from app.services.sse import sse_manager, POST_UPDATE_CHANNEL
        await sse_manager.publish(POST_UPDATE_CHANNEL, {
            "post_id": post_id,
            "status": "deleted",
            "user_id": user.id,
        })
    except Exception as e:
        logger.warning(f"Failed to publish SSE event for deleted post {post_id}: {e}")
