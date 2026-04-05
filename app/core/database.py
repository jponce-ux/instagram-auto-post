from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Sync engine for Celery Beat tasks (runs outside async context)
_sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2").replace(
    "postgresql://", "postgresql+psycopg2://"
)
sync_engine = create_engine(_sync_db_url, echo=settings.DEBUG)
SyncSessionLocal = sessionmaker(bind=sync_engine, class_=Session)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
