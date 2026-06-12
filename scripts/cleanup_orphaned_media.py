"""
Clean up orphaned MediaFile records where the original file no longer exists in MinIO.

Usage:
    docker compose exec web uv run python -m scripts.cleanup_orphaned_media

This script:
1. Queries all MediaFile records
2. Checks if the original file exists in MinIO
3. If missing, deletes the MediaFile record (and any associated Post records)
4. Reports what was cleaned up

WARNING: This deletes database records. Run with --dry-run first to preview.
"""

import argparse
import logging
import sys
import os

# Add project root to Python path so we can import app.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.database import SyncSessionLocal
from app.models.media_file import MediaFile
from app.models.post import Post

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def get_sync_client():
    """Get a synchronous boto3 S3 client."""
    return boto3.client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_access_key_id=settings.MINIO_ROOT_USER,
        aws_secret_access_key=settings.MINIO_ROOT_PASSWORD,
    )


def file_exists(s3_client, bucket: str, key: str) -> bool:
    """Check if a file exists in S3/MinIO."""
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        raise


def cleanup_orphaned_media(dry_run: bool = True):
    """Find and optionally delete MediaFile records with missing originals."""
    session = SyncSessionLocal()
    s3_client = get_sync_client()
    bucket = settings.MINIO_BUCKET_NAME

    try:
        all_media = session.query(MediaFile).all()
        total = len(all_media)
        logger.info(f"Checking {total} MediaFile records for orphaned files...")

        orphaned = []
        healthy = 0

        for mf in all_media:
            exists = file_exists(s3_client, bucket, mf.key)
            if not exists:
                orphaned.append(mf)
                logger.warning(f"  ORPHANED: id={mf.id}, key={mf.key}")
            else:
                healthy += 1

        logger.info(f"Healthy: {healthy}, Orphaned: {len(orphaned)}")

        if not orphaned:
            logger.info("No orphaned records found. Done!")
            return

        if dry_run:
            logger.info("DRY RUN — no deletions performed. Re-run without --dry-run to delete.")
            logger.info("Orphaned records that would be deleted:")
            for mf in orphaned:
                # Check for associated posts
                post_count = session.query(Post).filter(Post.media_file_id == mf.id).count()
                logger.info(f"  id={mf.id}, key={mf.key}, associated_posts={post_count}")
            return

        # Delete orphaned records
        deleted_count = 0
        for mf in orphaned:
            # Delete associated posts first (foreign key constraint)
            session.query(Post).filter(Post.media_file_id == mf.id).delete()
            session.delete(mf)
            deleted_count += 1
            logger.info(f"  Deleted MediaFile id={mf.id} and associated posts")

        session.commit()
        logger.info(f"Cleaned up {deleted_count} orphaned MediaFile records.")

    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean up orphaned MediaFile records")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Preview orphaned records without deleting (default: True)")
    parser.add_argument("--force", action="store_false", dest="dry_run",
                        help="Actually delete orphaned records")
    args = parser.parse_args()

    cleanup_orphaned_media(dry_run=args.dry_run)
