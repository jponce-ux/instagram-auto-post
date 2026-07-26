import logging
import re
from collections import defaultdict
from datetime import datetime, time, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql import func
from fastapi import UploadFile

from app.models.instagram import InstagramAccount
from app.models.post import Post, PostStatus
from app.models.media_file import MediaFile
from app.models.user import User
from app.models.hashtag_collection import HashtagCollection
from app.models.content_template import ContentTemplate
from app.models.recurring_schedule import RecurringSchedule
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


# ============================================================
# Hashtag Collection Service Methods
# ============================================================

async def get_hashtag_collections(db: AsyncSession, user: User) -> list[HashtagCollection]:
    """Fetch all hashtag collections for a user."""
    result = await db.execute(
        select(HashtagCollection)
        .where(HashtagCollection.user_id == user.id)
        .order_by(HashtagCollection.created_at.desc())
    )
    return list(result.scalars().all())


async def create_hashtag_collection(
    db: AsyncSession,
    user: User,
    name: str,
    hashtags: str,
) -> HashtagCollection:
    """Create a new hashtag collection."""
    collection = HashtagCollection(
        user_id=user.id,
        name=name,
        hashtags=hashtags,
    )
    db.add(collection)
    await db.commit()
    await db.refresh(collection)
    logger.info(f"Created hashtag collection {collection.id}: {name}")
    return collection


async def update_hashtag_collection(
    db: AsyncSession,
    user: User,
    collection_id: int,
    name: Optional[str] = None,
    hashtags: Optional[str] = None,
) -> HashtagCollection:
    """Update an existing hashtag collection."""
    result = await db.execute(
        select(HashtagCollection).where(
            HashtagCollection.id == collection_id,
            HashtagCollection.user_id == user.id,
        )
    )
    collection = result.scalar_one_or_none()
    if not collection:
        raise ValueError("Hashtag collection not found")

    if name is not None:
        collection.name = name
    if hashtags is not None:
        collection.hashtags = hashtags

    await db.commit()
    await db.refresh(collection)
    logger.info(f"Updated hashtag collection {collection_id}")
    return collection


async def delete_hashtag_collection(
    db: AsyncSession,
    user: User,
    collection_id: int,
) -> None:
    """Delete a hashtag collection."""
    result = await db.execute(
        select(HashtagCollection).where(
            HashtagCollection.id == collection_id,
            HashtagCollection.user_id == user.id,
        )
    )
    collection = result.scalar_one_or_none()
    if not collection:
        raise ValueError("Hashtag collection not found")

    await db.delete(collection)
    await db.commit()
    logger.info(f"Deleted hashtag collection {collection_id}")


# ============================================================
# Content Template Service Methods
# ============================================================

async def get_content_templates(db: AsyncSession, user: User) -> list[ContentTemplate]:
    """Fetch all content templates for a user."""
    result = await db.execute(
        select(ContentTemplate)
        .where(ContentTemplate.user_id == user.id)
        .order_by(ContentTemplate.created_at.desc())
    )
    return list(result.scalars().all())


async def create_content_template(
    db: AsyncSession,
    user: User,
    name: str,
    caption_template: str,
) -> ContentTemplate:
    """Create a new content template."""
    template = ContentTemplate(
        user_id=user.id,
        name=name,
        caption_template=caption_template,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    logger.info(f"Created content template {template.id}: {name}")
    return template


async def update_content_template(
    db: AsyncSession,
    user: User,
    template_id: int,
    name: Optional[str] = None,
    caption_template: Optional[str] = None,
) -> ContentTemplate:
    """Update an existing content template."""
    result = await db.execute(
        select(ContentTemplate).where(
            ContentTemplate.id == template_id,
            ContentTemplate.user_id == user.id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise ValueError("Content template not found")

    if name is not None:
        template.name = name
    if caption_template is not None:
        template.caption_template = caption_template

    await db.commit()
    await db.refresh(template)
    logger.info(f"Updated content template {template_id}")
    return template


async def delete_content_template(
    db: AsyncSession,
    user: User,
    template_id: int,
) -> None:
    """Delete a content template."""
    result = await db.execute(
        select(ContentTemplate).where(
            ContentTemplate.id == template_id,
            ContentTemplate.user_id == user.id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise ValueError("Content template not found")

    await db.delete(template)
    await db.commit()
    logger.info(f"Deleted content template {template_id}")


def extract_placeholders(caption_template: str) -> list[str]:
    """Extract placeholder names from a caption template.

    Returns list of placeholder names found in {{placeholder}} syntax.
    """
    pattern = r'\{\{(\w+)\}\}'
    return re.findall(pattern, caption_template)


def substitute_placeholders(caption_template: str, values: dict[str, str]) -> str:
    """Substitute placeholders in a caption template with provided values.

    Args:
        caption_template: Template string with {{placeholder}} syntax
        values: Dict mapping placeholder names to replacement values

    Returns:
        String with all placeholders replaced

    Raises:
        ValueError: If a required placeholder is missing from values
    """
    placeholders = extract_placeholders(caption_template)

    for placeholder in placeholders:
        if placeholder not in values:
            raise ValueError(f"Missing value for placeholder: {placeholder}")

    result = caption_template
    for placeholder, value in values.items():
        result = result.replace(f"{{{{{placeholder}}}}}", value)

    return result


def validate_placeholders(caption_template: str) -> list[str]:
    """Validate that all placeholders have names.

    Returns list of validation errors (empty if valid).
    """
    errors = []
    # Check for malformed placeholders like {{}} or {{{name}}}
    malformed = re.findall(r'\{\{+[\w]*\}\}+', caption_template)
    for match in malformed:
        if match != '{{' + re.match(r'\{\{(\w+)\}\}', match).group(1) + '}}':
            errors.append(f"Malformed placeholder: {match}")
    return errors


# ============================================================
# Recurring Schedule Service Methods
# ============================================================

async def get_recurring_schedules(db: AsyncSession, user: User) -> list[RecurringSchedule]:
    """Fetch all recurring schedules for a user."""
    result = await db.execute(
        select(RecurringSchedule)
        .where(RecurringSchedule.user_id == user.id)
        .order_by(RecurringSchedule.created_at.desc())
    )
    return list(result.scalars().all())


async def create_recurring_schedule(
    db: AsyncSession,
    user: User,
    ig_account_id: int,
    frequency: str,
    time_of_day: time,
    day_of_week: Optional[int] = None,
    template_id: Optional[int] = None,
    hashtag_collection_id: Optional[int] = None,
) -> RecurringSchedule:
    """Create a new recurring schedule."""
    # Verify ig_account belongs to user
    result = await db.execute(
        select(InstagramAccount).where(
            InstagramAccount.id == ig_account_id,
            InstagramAccount.user_id == user.id,
        )
    )
    ig_account = result.scalar_one_or_none()
    if not ig_account:
        raise ValueError("Instagram account not found")

    schedule = RecurringSchedule(
        user_id=user.id,
        ig_account_id=ig_account_id,
        frequency=frequency,
        time_of_day=time_of_day,
        day_of_week=day_of_week,
        template_id=template_id,
        hashtag_collection_id=hashtag_collection_id,
        is_active=True,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    logger.info(f"Created recurring schedule {schedule.id}: {frequency} at {time_of_day}")
    return schedule


async def update_recurring_schedule(
    db: AsyncSession,
    user: User,
    schedule_id: int,
    frequency: Optional[str] = None,
    time_of_day: Optional[time] = None,
    day_of_week: Optional[int] = None,
    template_id: Optional[int] = None,
    hashtag_collection_id: Optional[int] = None,
    is_active: Optional[bool] = None,
) -> RecurringSchedule:
    """Update an existing recurring schedule."""
    result = await db.execute(
        select(RecurringSchedule).where(
            RecurringSchedule.id == schedule_id,
            RecurringSchedule.user_id == user.id,
        )
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise ValueError("Recurring schedule not found")

    if frequency is not None:
        schedule.frequency = frequency
    if time_of_day is not None:
        schedule.time_of_day = time_of_day
    if day_of_week is not None:
        schedule.day_of_week = day_of_week
    if template_id is not None:
        schedule.template_id = template_id
    if hashtag_collection_id is not None:
        schedule.hashtag_collection_id = hashtag_collection_id
    if is_active is not None:
        schedule.is_active = is_active

    await db.commit()
    await db.refresh(schedule)
    logger.info(f"Updated recurring schedule {schedule_id}")
    return schedule


async def pause_recurring_schedule(
    db: AsyncSession,
    user: User,
    schedule_id: int,
) -> RecurringSchedule:
    """Pause a recurring schedule."""
    result = await db.execute(
        select(RecurringSchedule).where(
            RecurringSchedule.id == schedule_id,
            RecurringSchedule.user_id == user.id,
        )
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise ValueError("Recurring schedule not found")

    schedule.is_active = False
    await db.commit()
    await db.refresh(schedule)
    logger.info(f"Paused recurring schedule {schedule_id}")
    return schedule


async def resume_recurring_schedule(
    db: AsyncSession,
    user: User,
    schedule_id: int,
) -> RecurringSchedule:
    """Resume a paused recurring schedule."""
    result = await db.execute(
        select(RecurringSchedule).where(
            RecurringSchedule.id == schedule_id,
            RecurringSchedule.user_id == user.id,
        )
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise ValueError("Recurring schedule not found")

    schedule.is_active = True
    await db.commit()
    await db.refresh(schedule)
    logger.info(f"Resumed recurring schedule {schedule_id}")
    return schedule


async def delete_recurring_schedule(
    db: AsyncSession,
    user: User,
    schedule_id: int,
) -> None:
    """Delete a recurring schedule."""
    result = await db.execute(
        select(RecurringSchedule).where(
            RecurringSchedule.id == schedule_id,
            RecurringSchedule.user_id == user.id,
        )
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise ValueError("Recurring schedule not found")

    await db.delete(schedule)
    await db.commit()
    logger.info(f"Deleted recurring schedule {schedule_id}")


# ============================================================
# Best Times to Post (Analytics)
# ============================================================

async def calculate_best_times(db: AsyncSession, user: User) -> list[dict]:
    """Calculate best posting times based on engagement data.

    Requires at least 10 published posts with engagement data.
    Returns top 3 hours with highest average engagement.

    Returns:
        List of dicts with 'hour' (0-23) and 'avg_engagement' keys,
        sorted by engagement descending.
        Empty list if insufficient data.
    """
    # Get published posts with engagement data
    result = await db.execute(
        select(Post).where(
            Post.user_id == user.id,
            Post.status == PostStatus.PUBLISHED,
            Post.ig_media_id.isnot(None),
        )
    )
    posts = list(result.scalars().all())

    if len(posts) < 10:
        return []  # Not enough data

    # Group by hour
    hourly_engagement: dict[int, list[float]] = defaultdict(list)

    for post in posts:
        if post.published_at:
            hour = post.published_at.hour
            # For now, use simple weight based on whether post was successful
            # In a real implementation, we'd fetch actual likes/comments from Instagram API
            engagement_score = 1.0  # Placeholder - would use actual insights data
            hourly_engagement[hour].append(engagement_score)

    # Calculate averages
    averages = [
        {"hour": h, "avg_engagement": sum(v) / len(v), "post_count": len(v)}
        for h, v in hourly_engagement.items()
    ]

    # Sort and return top 3
    return sorted(averages, key=lambda x: x["avg_engagement"], reverse=True)[:3]


# ============================================================
# Analytics Service Methods (spec-026)
# ============================================================

async def get_analytics_overview(
    db: AsyncSession,
    user: User,
    period: str = "days_28",
) -> dict:
    """
    Get comprehensive analytics overview for the dashboard.

    Fetches account-level metrics with trends and structures data
    for KPI cards, reach chart, and growth chart.

    Args:
        db: AsyncSession for database operations
        user: The authenticated user
        period: Time period (days_7, days_14, days_28, days_90)

    Returns:
        Dict with kpis, reach_timeseries, growth_timeseries, and metadata
    """
    from app.services.metrics import metrics_service, TokenError, APIError

    # Get user's Instagram accounts
    accounts = await get_user_accounts(db, user)
    if not accounts:
        return {
            "error": "no_account",
            "message": "No Instagram account connected",
        }

    active_accounts = [acc for acc in accounts if acc.is_active]
    if not active_accounts:
        return {
            "error": "account_inactive",
            "message": "Instagram account is inactive",
        }

    account = active_accounts[0]

    try:
        # Fetch account analytics with trend data
        data = await metrics_service.get_account_analytics_with_trend(
            instagram_account_id=account.instagram_account_id,
            account_id=account.id,
            period=period,
            access_token=account.access_token,
        )

        # Extract metrics and trends
        metrics = data.get("metrics", {})
        trends = data.get("trends", {})
        timeline = data.get("timeline", {})

        # Calculate KPIs as per spec
        kpis = {
            "total_followers": {
                "value": metrics.get("follower_count", 0),
                "trend": trends.get("follower_count", 0),
            },
            "monthly_reach": {
                "value": metrics.get("reach", 0),
                "trend": trends.get("reach", 0),
            },
            "engagement_rate": {
                "value": _calculate_engagement_rate(metrics),
                "trend": trends.get("reach", 0),  # Use reach trend as proxy
            },
        }

        # Build reach timeseries for line chart
        reach_timeseries = {
            "labels": timeline.get("labels", []),
            "data": timeline.get("datasets", {}).get("reach", []),
        }

        # Build follower growth timeseries for bar chart
        # Calculate weekly aggregates from daily data
        growth_timeseries = _aggregate_weekly_growth(timeline)

        return {
            "kpis": kpis,
            "reach_timeseries": reach_timeseries,
            "growth_timeseries": growth_timeseries,
            "cached": data.get("cached", False),
            "stale": data.get("stale", False),
            "fetched_at": data.get("fetched_at"),
            "error": None,
        }

    except TokenError:
        return {
            "error": "token_expired",
            "message": "Instagram session expired",
        }
    except APIError:
        return {
            "error": "api_error",
            "message": "Analytics temporarily unavailable",
        }
    except Exception as e:
        logger.error(f"Unexpected error in get_analytics_overview: {e}", exc_info=True)
        return {
            "error": "unknown",
            "message": "An unexpected error occurred",
        }


def _calculate_engagement_rate(metrics: dict) -> float:
    """Calculate engagement rate from metrics.

    Formula: (total_interactions / reach) * 100
    Returns 0 if reach is 0.
    """
    reach = metrics.get("reach", 0)
    interactions = metrics.get("total_interactions", 0)

    if reach == 0:
        return 0.0

    return round((interactions / reach) * 100, 2)


def _aggregate_weekly_growth(timeline: dict) -> dict:
    """Aggregate daily follower data into weekly summaries for bar chart.

    Args:
        timeline: Dict with 'labels' (dates) and 'datasets' (metrics)

    Returns:
        Dict with 'labels' (week labels) and 'data' (follower deltas per week)
    """
    labels = timeline.get("labels", [])
    follower_data = timeline.get("datasets", {}).get("follower_count", [])

    if not labels or not follower_data:
        return {"labels": [], "data": []}

    # Calculate daily deltas from cumulative follower count
    daily_deltas = []
    for i in range(1, len(follower_data)):
        delta = follower_data[i] - follower_data[i - 1]
        daily_deltas.append(delta)

    # Aggregate into weeks (7-day chunks)
    weeks = []
    week_labels = []
    weekly_deltas = []

    for i in range(0, len(daily_deltas), 7):
        week_data = daily_deltas[i:i + 7]
        if week_data:
            weeks.append(sum(week_data))
            # Create week label like "Week 1", "Week 2"
            week_num = (i // 7) + 1
            week_labels.append(f"Semana {week_num}")
            weekly_deltas.append(sum(week_data))

    # If we have leftover days, add them as a partial week
    remaining = len(daily_deltas) % 7
    if remaining > 0 and len(daily_deltas) > 7:
        last_week_start = (len(weeks)) * 7
        last_week_data = daily_deltas[last_week_start:]
        if last_week_data:
            week_labels.append(f"Semana {len(weeks) + 1}")
            weekly_deltas.append(sum(last_week_data))

    return {
        "labels": week_labels,
        "data": weekly_deltas,
    }


async def get_top_performing_posts(
    db: AsyncSession,
    user: User,
    limit: int = 6,
) -> list[dict]:
    """
    Get top performing posts sorted by engagement.

    Args:
        db: AsyncSession for database operations
        user: The authenticated user
        limit: Maximum number of posts to return

    Returns:
        List of post dicts with engagement metrics, sorted by engagement descending
    """
    from app.services.metrics import metrics_service

    # Get published posts with media files
    result = await db.execute(
        select(Post, MediaFile)
        .join(MediaFile, Post.media_file_id == MediaFile.id)
        .where(
            Post.user_id == user.id,
            Post.status == PostStatus.PUBLISHED,
            Post.ig_media_id.isnot(None),
        )
        .order_by(Post.published_at.desc())
        .limit(limit * 2)  # Fetch more to filter
    )
    rows = list(result.all())

    if not rows:
        return []

    # Get user's active Instagram account for API access
    accounts = await get_user_accounts(db, user)
    active_accounts = [acc for acc in accounts if acc.is_active]
    if not active_accounts:
        return []

    account = active_accounts[0]

    # Fetch media insights for each post
    posts_with_engagement = []

    for post, media_file in rows:
        try:
            insights = await metrics_service.get_media_analytics(
                media_id=post.ig_media_id,
                access_token=account.access_token,
            )

            metrics = insights.get("metrics", {})
            engagement = metrics.get("engagement", 0)

            # Build image URLs
            thumbnail_url = None
            full_image_url = None

            try:
                full_image_url = await storage_service.get_presigned_url(
                    media_file.key, expires=3600
                )
                if media_file.thumbnail_key:
                    thumbnail_url = await storage_service.get_presigned_url(
                        media_file.thumbnail_key, expires=3600
                    )
            except Exception:
                pass

            posts_with_engagement.append({
                "id": post.id,
                "ig_media_id": post.ig_media_id,
                "caption": post.caption or "",
                "thumbnail_url": thumbnail_url,
                "full_image_url": full_image_url,
                "likes": metrics.get("likes", 0),
                "comments": metrics.get("comments", 0),
                "saves": metrics.get("saved", 0),
                "impressions": metrics.get("impressions", 0),
                "reach": metrics.get("reach", 0),
                "engagement": engagement,
                "published_at": post.published_at.isoformat() if post.published_at else None,
                "category": _infer_post_category(post.caption or ""),
            })

        except Exception as e:
            logger.warning(f"Failed to fetch insights for post {post.id}: {e}")
            continue

    # Sort by engagement (highest first) and limit
    posts_with_engagement.sort(key=lambda x: x["engagement"], reverse=True)
    return posts_with_engagement[:limit]


def _infer_post_category(caption: str) -> str:
    """Infer post category from caption content.

    Simple heuristic-based categorization.
    """
    caption_lower = caption.lower()

    categories = {
        "Promocional": ["descuento", "oferta", "promo", "gratis", "50% off", "20% off", "comprar", "shop"],
        "Educativo": ["consejo", "tip", "cómo", "tutorial", "aprende", "guía", "instrucción"],
        "Entretenimiento": ["jajaja", "gracioso", "divertido", "lol", "comedia", "humor"],
        "Lifestyle": ["vida", " día", " morning", "night", "routine", " weekend", " family"],
        "Producto": ["nuevo", "lanzamiento", "producto", "colección", "presentación"],
    }

    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in caption_lower:
                return category

    return "General"


async def get_media_insights(
    db: AsyncSession,
    user: User,
    post_id: int,
) -> dict:
    """
    Get detailed insights for a specific post.

    Args:
        db: AsyncSession for database operations
        user: The authenticated user
        post_id: The post ID to get insights for

    Returns:
        Dict with post details and media insights

    Raises:
        ValueError: If post not found or not accessible
    """
    from app.services.metrics import metrics_service

    # Fetch post with media file
    result = await db.execute(
        select(Post, MediaFile)
        .join(MediaFile, Post.media_file_id == MediaFile.id)
        .where(Post.id == post_id, Post.user_id == user.id)
    )
    row = result.one_or_none()

    if not row:
        raise ValueError("Post not found")

    post, media_file = row

    # Get user's active Instagram account
    accounts = await get_user_accounts(db, user)
    active_accounts = [acc for acc in accounts if acc.is_active]
    if not active_accounts:
        raise ValueError("Instagram account is inactive")

    account = active_accounts[0]

    # Fetch media insights
    insights = await metrics_service.get_media_analytics(
        media_id=post.ig_media_id,
        access_token=account.access_token,
    )

    # Build image URLs
    thumbnail_url = None
    full_image_url = None

    try:
        full_image_url = await storage_service.get_presigned_url(
            media_file.key, expires=3600
        )
        if media_file.thumbnail_key:
            thumbnail_url = await storage_service.get_presigned_url(
                media_file.thumbnail_key, expires=3600
            )
    except Exception:
        pass

    return {
        "post_id": post.id,
        "ig_media_id": post.ig_media_id,
        "caption": post.caption or "",
        "thumbnail_url": thumbnail_url,
        "full_image_url": full_image_url,
        "metrics": insights.get("metrics", {}),
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "category": _infer_post_category(post.caption or ""),
    }
