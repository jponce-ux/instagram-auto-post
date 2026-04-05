import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import UploadFile

from app.models.instagram import InstagramAccount
from app.models.post import Post, PostStatus
from app.models.media_file import MediaFile
from app.models.user import User
from app.services.storage import storage_service


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
    Create a new post with image upload.

    1. Upload file to MinIO storage
    2. Create MediaFile record
    3. Create Post record with PENDING status
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
    ig_account_id = accounts[0].id if accounts else None

    # Create post record
    post = Post(
        user_id=user.id,
        ig_account_id=ig_account_id,
        media_file_id=media_file.id,
        caption=caption,
        status=PostStatus.PENDING,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)

    return post
