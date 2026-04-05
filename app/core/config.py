from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    DEBUG: bool = False
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    BASE_URL: str = "http://localhost:8000"

    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://redis:6379/0"

    # MinIO Configuration
    MINIO_ENDPOINT: str = "http://minio:9000"
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin123"
    MINIO_BUCKET_NAME: str = "instagram-uploads"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
