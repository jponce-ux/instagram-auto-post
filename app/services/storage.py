import uuid
from urllib.parse import urlparse, urlunparse

import aioboto3
from fastapi import UploadFile
from botocore.exceptions import ClientError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.media_file import MediaFile


class StorageService:
    """Async storage service for MinIO (S3-compatible) object storage."""

    def __init__(self):
        """Initialize storage service with settings from config."""
        self.endpoint = settings.MINIO_ENDPOINT
        self.access_key = settings.MINIO_ROOT_USER
        self.secret_key = settings.MINIO_ROOT_PASSWORD
        self.bucket = settings.MINIO_BUCKET_NAME
        self.tunnel_host = settings.MINIO_TUNNEL_HOST
        self.sse_enabled = settings.MINIO_SSE_ENABLED
        self._client = None

    async def _get_client(self):
        """Get or create aioboto3 S3 client (lazy-loaded context manager)."""
        session = aioboto3.Session()
        return session.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )

    async def ensure_bucket_exists(self) -> None:
        """Create bucket if not exists. Call on app startup."""
        async with await self._get_client() as client:
            try:
                await client.head_bucket(Bucket=self.bucket)
            except ClientError:
                # Bucket does not exist, create it
                await client.create_bucket(Bucket=self.bucket)

    async def upload_file(self, file: UploadFile, user_id: int) -> str:
        """
        Upload a file to MinIO with user-scoped path.

        Args:
            file: FastAPI UploadFile object
            user_id: The authenticated user's ID for path scoping

        Returns:
            The object key ({user_id}/{uuid}.{ext})

        Raises:
            Exception on upload failure
        """
        # Generate user-scoped key
        file_ext = file.filename.split(".")[-1] if "." in file.filename else "bin"
        key = f"{user_id}/{uuid.uuid4()}.{file_ext}"

        # Prepare upload arguments
        extra_args = {"ContentType": file.content_type or "application/octet-stream"}
        if self.sse_enabled:
            extra_args["ServerSideEncryption"] = "AES256"

        async with await self._get_client() as client:
            content = await file.read()
            await client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content,
                **extra_args,
            )
        return key

    async def get_presigned_url(self, key: str, expires: int = 600) -> str:
        """
        Generate a short-lived presigned URL for file access.

        Args:
            key: Object key (path/filename)
            expires: URL expiration time in seconds (default: 600 = 10 minutes)

        Returns:
            Presigned URL string with tunnel host if configured
        """
        async with await self._get_client() as client:
            url = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires,
            )

        # Replace internal host with tunnel host if configured
        # Also force https scheme for public URLs (Cloudflare tunnel)
        if self.tunnel_host:
            parsed = urlparse(url)
            url = urlunparse(parsed._replace(scheme="https", netloc=self.tunnel_host))

        return url

    async def upload_file_for_user(
        self, file: UploadFile, user_id: int, db: AsyncSession
    ) -> MediaFile:
        """
        Upload a file and create MediaFile record in database.

        This creates both the S3 object and the ownership tracking record.

        Args:
            file: FastAPI UploadFile object
            user_id: The authenticated user's ID
            db: AsyncSession for database operations

        Returns:
            MediaFile record with ownership information
        """
        # Upload to S3
        key = await self.upload_file(file, user_id)

        # Create MediaFile record
        media_file = MediaFile(
            key=key,
            original_filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            user_id=user_id,
        )
        db.add(media_file)
        await db.commit()
        await db.refresh(media_file)

        return media_file

    async def get_media_file(
        self, file_id: int, user_id: int, db: AsyncSession
    ) -> MediaFile | None:
        """
        Get a MediaFile record with ownership verification.

        Args:
            file_id: The media file ID
            user_id: The requesting user's ID (for ownership check)
            db: AsyncSession for database operations

        Returns:
            MediaFile if found and owned by user, None otherwise
        """
        result = await db.execute(
            select(MediaFile).where(
                MediaFile.id == file_id, MediaFile.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_user_media_files(
        self, user_id: int, db: AsyncSession
    ) -> list[MediaFile]:
        """
        Get all MediaFile records for a user.

        Args:
            user_id: The user's ID
            db: AsyncSession for database operations

        Returns:
            List of MediaFile records owned by the user
        """
        result = await db.execute(
            select(MediaFile)
            .where(MediaFile.user_id == user_id)
            .order_by(MediaFile.created_at.desc())
        )
        return list(result.scalars().all())


# Global storage service instance
storage_service = StorageService()
