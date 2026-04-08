from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    DEBUG: bool = False
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    BASE_URL: str = "http://localhost:8000"

    # MinIO Configuration
    MINIO_ENDPOINT: str
    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    MINIO_BUCKET_NAME: str
    MINIO_TUNNEL_HOST: str = ""
    MINIO_SSE_ENABLED: bool = False

    # Celery Configuration
    CELERY_BROKER_URL: str

    # Meta Webhook Configuration
    META_WEBHOOK_VERIFY_TOKEN: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
