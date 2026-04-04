import aioboto3
from fastapi import UploadFile
from botocore.exceptions import ClientError
from app.core.config import settings


class StorageService:
    """Async storage service for MinIO (S3-compatible) object storage."""

    def __init__(self):
        """Initialize storage service with settings from config."""
        self.endpoint = settings.MINIO_ENDPOINT
        self.access_key = settings.MINIO_ROOT_USER
        self.secret_key = settings.MINIO_ROOT_PASSWORD
        self.bucket = settings.MINIO_BUCKET_NAME
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

    async def upload_file(self, file: UploadFile, key: str) -> str:
        """
        Upload a file to MinIO.
        
        Args:
            file: FastAPI UploadFile object
            key: Object key (path/filename)
            
        Returns:
            The object key
            
        Raises:
            Exception on upload failure
        """
        async with await self._get_client() as client:
            content = await file.read()
            await client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content,
                ContentType=file.content_type or "application/octet-stream",
            )
        return key

    async def get_presigned_url(self, key: str, expires: int = 604800) -> str:
        """
        Generate a presigned URL for file access.
        
        Args:
            key: Object key (path/filename)
            expires: URL expiration time in seconds (default: 7 days)
            
        Returns:
            Presigned URL string
        """
        async with await self._get_client() as client:
            url = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires,
            )
        return url


# Global storage service instance
storage_service = StorageService()
