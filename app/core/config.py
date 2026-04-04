from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    DEBUG: bool = False
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    BASE_URL: str = "http://localhost:8000"

    # MinIO Configuration
    MINIO_ENDPOINT: str = "http://minio:9000"
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin123"
    MINIO_BUCKET_NAME: str = "instagram-uploads"
    MINIO_TUNNEL_HOST: str = (
        ""  # Tunnel host for presigned URLs (e.g., instagramjp.domain.com)
    )
    MINIO_SSE_ENABLED: bool = False  # Server-side encryption (SSE-S3)

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
