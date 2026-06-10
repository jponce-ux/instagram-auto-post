import json
import logging
import uuid
from io import BytesIO
from urllib.parse import urlparse, urlunparse

import aioboto3
from fastapi import UploadFile
from botocore.exceptions import ClientError
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.media_file import MediaFile

logger = logging.getLogger(__name__)

# Thumbnail configuration
THUMBNAIL_MAX_WIDTH = 200  # pixels, maintains aspect ratio
THUMBNAIL_FORMAT = "JPEG"
THUMBNAIL_QUALITY = 85


class StorageService:
    """Async storage service for MinIO (S3-compatible) object storage.

    Uses a two-bucket strategy:
    - Private bucket (MINIO_BUCKET_NAME): Encrypted permanent copy for the user
    - Public bucket (MINIO_PUBLIC_BUCKET_NAME): Temporary copy for Instagram
      to download. Deleted after successful publish.
    """

    def __init__(self):
        """Initialize storage service with settings from config."""
        self.endpoint = settings.MINIO_ENDPOINT
        self.access_key = settings.MINIO_ROOT_USER
        self.secret_key = settings.MINIO_ROOT_PASSWORD
        self.bucket = settings.MINIO_BUCKET_NAME
        self.public_bucket = settings.MINIO_PUBLIC_BUCKET_NAME
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

    @staticmethod
    def generate_thumbnail(image_bytes: bytes, content_type: str = "image/jpeg") -> bytes | None:
        """Generate a thumbnail from image bytes.

        Args:
            image_bytes: Raw image data
            content_type: MIME type of the original image

        Returns:
            Thumbnail image bytes (JPEG) or None if generation fails
        """
        try:
            img = Image.open(BytesIO(image_bytes))
            # Convert to RGB if necessary (PNG with transparency, etc.)
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")
            # Generate thumbnail maintaining aspect ratio
            img.thumbnail((THUMBNAIL_MAX_WIDTH, THUMBNAIL_MAX_WIDTH), Image.LANCZOS)
            # Save as JPEG
            output = BytesIO()
            img.save(output, format=THUMBNAIL_FORMAT, quality=THUMBNAIL_QUALITY)
            output.seek(0)
            return output.read()
        except Exception as e:
            logger.warning(f"Failed to generate thumbnail: {e}")
            return None

    async def upload_thumbnail(self, thumbnail_bytes: bytes, original_key: str) -> str | None:
        """Upload a thumbnail to the private bucket with -thumbnail suffix.

        Args:
            thumbnail_bytes: Thumbnail image data
            original_key: Original image key (e.g., {user_id}/{uuid}.jpg)

        Returns:
            Thumbnail key or None if upload fails
        """
        # Derive thumbnail key: {user_id}/{uuid}-thumbnail.{ext}
        base, ext = original_key.rsplit(".", 1)
        thumbnail_key = f"{base}-thumbnail.{ext}"

        try:
            extra_args = {"ContentType": "image/jpeg"}
            if self.sse_enabled:
                extra_args["ServerSideEncryption"] = "AES256"

            async with await self._get_client() as client:
                await client.put_object(
                    Bucket=self.bucket,
                    Key=thumbnail_key,
                    Body=thumbnail_bytes,
                    **extra_args,
                )
            logger.info(f"Thumbnail uploaded: {thumbnail_key} ({len(thumbnail_bytes)} bytes)")
            return thumbnail_key
        except Exception as e:
            logger.warning(f"Failed to upload thumbnail for {original_key}: {e}")
            return None

    async def ensure_bucket_exists(self) -> None:
        """Create both buckets if they don't exist. Set public read policy on public bucket."""
        async with await self._get_client() as client:
            # Private bucket (encrypted, no public access)
            try:
                await client.head_bucket(Bucket=self.bucket)
            except ClientError:
                await client.create_bucket(Bucket=self.bucket)

            # Public bucket (readable by anyone, for Instagram API)
            try:
                await client.head_bucket(Bucket=self.public_bucket)
            except ClientError:
                await client.create_bucket(Bucket=self.public_bucket)

            # Set public read policy on public bucket
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "PublicReadGetObject",
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{self.public_bucket}/*"],
                    }
                ],
            }
            await client.put_bucket_policy(
                Bucket=self.public_bucket,
                Policy=json.dumps(policy),
            )

    async def upload_file(self, file: UploadFile, user_id: int) -> str:
        """
        Upload a file to the private (encrypted) bucket.

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

        # Prepare upload arguments with encryption
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

    async def copy_to_public_bucket(self, key: str) -> None:
        """Copy a file from the private bucket to the public bucket.

        This makes the file accessible to Instagram API without auth.
        The file should be deleted from the public bucket after publish.

        Args:
            key: Object key (same key used in both buckets)
        """
        async with await self._get_client() as client:
            copy_source = {"Bucket": self.bucket, "Key": key}
            await client.copy_object(
                Bucket=self.public_bucket,
                Key=key,
                CopySource=copy_source,
                ContentType="image/jpeg",  # Default, will be overridden if known
            )

    async def delete_from_public_bucket(self, key: str) -> None:
        """Delete a file from the public bucket after successful publish.

        Args:
            key: Object key to delete
        """
        try:
            async with await self._get_client() as client:
                await client.delete_object(Bucket=self.public_bucket, Key=key)
        except Exception as e:
            # Non-critical: the public bucket is temporary, cleanup can be lazy
            from app.core.config import settings
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to delete {key} from public bucket: {e}")

    async def get_public_url(self, key: str) -> str:
        """Generate a clean public URL for the file (no auth params).

        Used by Instagram API to download the image.

        Args:
            key: Object key (path/filename)

        Returns:
            Public URL string
        """
        if self.tunnel_host:
            return f"https://{self.tunnel_host}/{self.public_bucket}/{key}"
        # Fallback: direct MinIO URL (for local dev)
        return f"{self.endpoint}/{self.public_bucket}/{key}"

    async def get_presigned_url(self, key: str, expires: int = 600) -> str:
        """
        Generate a presigned URL for private file access.

        Used for user-facing downloads from the private bucket.

        Args:
            key: Object key (path/filename)
            expires: URL expiration time in seconds (default: 600 = 10 minutes)

        Returns:
            Presigned URL string
        """
        async with await self._get_client() as client:
            url = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires,
            )

        # Replace internal host with tunnel host if configured
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
        Also generates and uploads a thumbnail for image files.

        Args:
            file: FastAPI UploadFile object
            user_id: The authenticated user's ID
            db: AsyncSession for database operations

        Returns:
            MediaFile record with ownership information
        """
        # Read file content once
        content = await file.read()
        # Reset file pointer so upload_file can read it again
        file.file.seek(0)

        # Upload original to S3
        key = await self.upload_file(file, user_id)

        # Generate and upload thumbnail for image files
        thumbnail_key = None
        content_type = file.content_type or "application/octet-stream"
        if content_type.startswith("image/"):
            thumbnail_bytes = self.generate_thumbnail(content, content_type)
            if thumbnail_bytes:
                thumbnail_key = await self.upload_thumbnail(thumbnail_bytes, key)
                if thumbnail_key:
                    logger.info(
                        f"Thumbnail generated for {key}: "
                        f"{len(thumbnail_bytes)} bytes -> {thumbnail_key}"
                    )

        # Create MediaFile record with both keys
        media_file = MediaFile(
            key=key,
            thumbnail_key=thumbnail_key,
            original_filename=file.filename,
            content_type=content_type,
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
