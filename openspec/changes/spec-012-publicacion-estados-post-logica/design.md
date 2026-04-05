# Design: Lógica de Publicación y Estados de Post

## Technical Approach

Modelo `Post` con estados (enum `PostStatus`) que referencia `MediaFile` e `InstagramAccount`. Celery task `process_instagram_post` orquesta flujo Meta (create container → poll status → publish). InstagramService extiende con métodos de Graph API.

## Architecture Decisions

### Decision: Post Status Enum

| Option | Tradeoff | Decision |
|--------|----------|------|
| Enum (PostStatus) | Type-safe, limited values | ✅ Chosen |
| String column | Flexible but error-prone | Rejected |
| Integer codes | Compact but unclear | Rejected |

**Rationale**: Enum prevents invalid states, self-documenting, works with SQLAlchemy.

### Decision: Asynchronous Publishing Flow

| Option | Tradeoff | Decision |
|--------|----------|------|
| Celery task | Non-blocking, scalable | ✅ Chosen |
| HTTP request wait | Simple but slow | Rejected - blocks request |
| Background thread | Complex, not distributed | Rejected |

**Rationale**: Non-blocking allows user to continue. Celery handles retries, distribution.

### Decision: Status Polling Strategy

| Option | Tradeoff | Decision |
|--------|----------|------|
| Poll every 2s, max 30s | Simple, predictable timeout | ✅ Chosen |
| Exponential backoff | More efficient, harder to debug | Deferred |
| Webhook | Instant but requires ngrok, not local | Rejected |

**Rationale**: Predictable timeout (30s) covers most Media processing. Simpler to implement.

### Decision: Error Message Storage

| Option | Tradeoff | Decision |
|--------|----------|------|
| `error_message` TEXT column | Flexible, unlimited length | ✅ Chosen |
| JSON column | Structured but overkill | Rejected |
| Log only | No user visibility | Rejected |

**Rationale**: Users need to see why a post failed (token expired, rate limit, etc.).

## Data Flow

```
User Uploads Media
       │
       ▼
  MediaFile created (user_id, key)
       │
       ▼
  Post created (PENDING, media_file_id, ig_account_id)
       │
       ├── POST /api/v1/posts ─► FastAPI returns {post_id, status: PENDING}
       │
       ▼
process_instagram_post.delay(post_id)
       │
       ▼
   Celery Worker
       │
       ├── 1. Fetch Post + InstagramAccount + MediaFile
       │      Generate fresh presigned URL
       │
       ├── 2. Update Post status → PROCESSING
       │
       ├── 3. POST /{ig_id}/media → create container
       │      Store ig_container_id
       │
       ├── 4. Poll GET /{container_id}?fields=status_code
       │      Wait for FINISHED (max 30s)
       │
       ├── 5. POST /{ig_id}/media_publish → publish
       │
       ▼
   Post status → PUBLISHED (ig_media_id stored)
    OR Post status → FAILED (error_message)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/models/post.py` | New | Post model with PostStatus enum |
| `app/models/__init__.py` | Modify | Export Post, PostStatus |
| `app/services/instagram.py` | Modify | Add create/publish methods |
| `app/worker.py` | Modify | Add process_instagram_post task |
| `migrations/versions/add_posts_table.py` | New | Alembic migration |

## Interfaces / Contracts

### Post Model

```python
# app/models/post.py
import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.sql import func
from app.models.base import Base

class PostStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ig_account_id = Column(Integer, ForeignKey("instagram_accounts.id"), nullable=False)
    media_file_id = Column(Integer, ForeignKey("media_files.id"), nullable=False)
    caption = Column(Text, nullable=True)
    status = Column(Enum(PostStatus), default=PostStatus.PENDING, nullable=False)
    ig_container_id = Column(String, nullable=True)
    ig_media_id = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)
```

### InstagramService Extensions

```python
# app/services/instagram.py additions

META_API_BASE = "https://graph.facebook.com/v18.0"

async def create_media_container(
    ig_account_id: str, 
    access_token: str, 
    media_url: str, 
    caption: str | None = None
) -> str:
    """Create IG Media Container. Returns container_id."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{META_API_BASE}/{ig_account_id}/media",
            params={
                "access_token": access_token,
                "image_url": media_url,
                "caption": caption or "",
            },
        )
        response.raise_for_status()
        return response.json()["id"]

async def get_container_status(container_id: str, access_token: str) -> str:
    """Get container status. Returns status_code."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{META_API_BASE}/{container_id}",
            params={"fields": "status_code", "access_token": access_token},
        )
        response.raise_for_status()
        return response.json().get("status_code", "UNKNOWN")

async def publish_media_container(
    ig_account_id: str, 
    access_token: str, 
    container_id: str
) -> str:
    """Publish container to IG feed. Returns ig_media_id."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{META_API_BASE}/{ig_account_id}/media_publish",
            params={
                "access_token": access_token,
                "creation_id": container_id,
            },
        )
        response.raise_for_status()
        return response.json()["id"]
```

### Celery Task

```python
# app/worker.py additions

import asyncio
from asgiref.sync import sync_to_async
from celery import celery_app
from app.models.post import Post, PostStatus
from app.models.instagram import InstagramAccount
from app.models.media_file import MediaFile
from app.services.instagram import create_media_container, get_container_status, publish_media_container
from app.services.storage import storage_service
from app.core.database import AsyncSessionLocal

@celery_app.task(bind=True)
def process_instagram_post(self, post_id: int):
    """Process Instagram post: create container, poll status, publish."""
    asyncio.run(_process_post_async(post_id))

async def _process_post_async(post_id: int):
    async with AsyncSessionLocal() as db:
        # 1. Fetch Post + InstagramAccount + MediaFile
        # 2. Update status → PROCESSING
        # 3. Generate presigned URL
        # 4. Create Media Container
        # 5. Poll status (max 30s)
        # 6. Publish
        # 7. Update status → PUBLISHED or FAILED
        pass
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Post model with enum states | SQLAlchemy model test |
| Unit | InstagramService new methods | Mock httpx.AsyncClient |
| Integration | Celery task execution | Mock Meta API, test DB |
| E2E | Full publish flow | With real containers (staging) |

## Migration / Rollout

1. Create migration: `alembic revision --autogenerate -m "add_posts_table"`
2. Apply: `alembic upgrade head`
3. Deploy worker container (requires SPEC-011)
4. Verify: Create test post, check PENDING status

## Open Questions

- [ ] ¿Retry policy para rate limits? → Sugerido: exponential backoff, max 3 retries
- [ ] ¿Timeout para container status polling? → Propuesto: 30 segundos
- [ ] ¿Notificar usuario cuando post falla? → Deferred (WebSocket/email)