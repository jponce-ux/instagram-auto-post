"""
Backfill thumbnails for existing MediaFile records.

Usage:
    uv run scripts/backfill_thumbnails.py

This script:
1. Queries all MediaFile records where thumbnail_key is NULL
2. Downloads the original image from MinIO
3. Generates a thumbnail using the existing StorageService logic
4. Uploads the thumbnail to MinIO
5. Updates the MediaFile record with the new thumbnail_key

Safe to run multiple times — skips records that already have thumbnails.
"""

import asyncio
import logging
import sys

from app.core.config import settings
from app.core.database import SyncSessionLocal
from app.models.media_file import MediaFile
from app.services.storage import storage_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def get_sync_client():
    """Get a synchronous boto3 S3 client for downloading original images."""
    import boto3
    return boto3.client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_access_key_id=settings.MINIO_ROOT_USER,
        aws_secret_access_key=settings.MINIO_ROOT_PASSWORD,
    )


def backfill_thumbnails():
    """Generate thumbnails for all MediaFile records missing them."""
    session = SyncSessionLocal()
    s3_client = get_sync_client()

    try:
        # Find all media files without thumbnails
        media_files = (
            session.query(MediaFile)
            .filter(MediaFile.thumbnail_key.is_(None))
            .filter(MediaFile.content_type.like("image/%"))
            .all()
        )

        total = len(media_files)
        if total == 0:
            logger.info("No media files need thumbnail backfill. Done!")
            return

        logger.info(f"Found {total} media files without thumbnails. Starting backfill...")

        success_count = 0
        skip_count = 0
        error_count = 0

        for i, mf in enumerate(media_files, 1):
            logger.info(f"[{i}/{total}] Processing MediaFile id={mf.id}, key={mf.key}")

            try:
                # Download original from MinIO
                response = s3_client.get_object(
                    Bucket=settings.MINIO_BUCKET_NAME,
                    Key=mf.key,
                )
                original_bytes = response["Body"].read()
                logger.info(f"  Downloaded original: {len(original_bytes)} bytes")

                # Generate thumbnail
                thumbnail_bytes = storage_service.generate_thumbnail(
                    original_bytes, mf.content_type
                )
                if thumbnail_bytes is None:
                    logger.warning(f"  Skipping id={mf.id}: thumbnail generation failed")
                    skip_count += 1
                    continue

                logger.info(f"  Generated thumbnail: {len(thumbnail_bytes)} bytes")

                # Upload thumbnail
                thumbnail_key = asyncio.run(
                    storage_service.upload_thumbnail(thumbnail_bytes, mf.key)
                )
                if thumbnail_key is None:
                    logger.warning(f"  Skipping id={mf.id}: thumbnail upload failed")
                    skip_count += 1
                    continue

                # Update database record
                mf.thumbnail_key = thumbnail_key
                session.commit()
                logger.info(f"  Updated MediaFile id={mf.id}: thumbnail_key={thumbnail_key}")
                success_count += 1

            except Exception as e:
                session.rollback()
                logger.error(f"  Error processing id={mf.id}: {e}")
                error_count += 1

        logger.info("=" * 60)
        logger.info(f"Backfill complete!")
        logger.info(f"  Total processed: {total}")
        logger.info(f"  Success: {success_count}")
        logger.info(f"  Skipped: {skip_count}")
        logger.info(f"  Errors: {error_count}")
        logger.info("=" * 60)

    finally:
        session.close()


if __name__ == "__main__":
    backfill_thumbnails()
