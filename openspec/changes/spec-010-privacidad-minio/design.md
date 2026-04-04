# Design: MinIO Security and Privacy (SPEC-010)

## Technical Approach

Extend the existing `StorageService` to support user-scoped paths, private bucket access, and short-lived presigned URLs. Create a `MediaFile` model to track file ownership, enabling authorization checks. Add a protected endpoint `/dashboard/media/{file_id}` that validates JWT and ownership before returning presigned URLs. Configure MinIO bucket with SSE-S3 encryption and restrictive IAM policies.

## Architecture Decisions

### Decision: MediaFile Model for Ownership Tracking

**Choice**: Create `MediaFile` SQLAlchemy model linked to `User`
**Alternatives considered**: 
- Store ownership in filename metadata (fragile, not queryable)
- Use separate key-value store (over-engineering)
**Rationale**: SQLAlchemy already integrated; provides FK relationship, queryable ownership, enables "list my files" feature later

### Decision: Short-lived Presigned URLs (10 minutes)

**Choice**: Default `expires=600` seconds for Meta API uploads
**Alternatives considered**:
- 1-hour expiration (too long for security)
- 1-minute expiration (too short for slow networks)
- Per-request configurable (adds complexity)
**Rationale**: 10 minutes is enough time for Meta to download; URL becomes useless immediately after

### Decision: Tunnel Host Configuration

**Choice**: Add `MINIO_TUNNEL_HOST` config (e.g., `instagramjp.domain.com`)
**Alternatives considered**:
- Hardcode in code (inflexible)
- Auto-detect from request headers (unreliable with proxies)
- Use presigned URL hostname replacement (extra processing)
**Rationale**: Config-driven; MinIO generates internal URL, we replace host with tunnel host

### Decision: SSE-S3 Encryption

**Choice**: Server-side encryption with S3-managed keys (SSE-S3)
**Alternatives considered**:
- SSE-KMS with MinIO KMS (requires KMS setup)
- Client-side encryption (complex, slow uploads)
**Rationale**: SSE-S3 is simplest; MinIO handles encryption transparently; no external KMS dependency

## Data Flow

```
Frontend Upload ──POST /upload──→ FastAPI (user_id from JWT)
                                        │
                                        ▼
                              StorageService.upload_file()
                                        │
                                        ▼
                        Key: {user_id}/{uuid}.{ext}
                                        │
                                        ▼
                               MediaFile DB record
                                        │
                                        ▼
                              MinIO (SSE-S3 encrypted)
                                        │
                                        ────────────────────────┐
                                        │                        │
                                   Meta API fetch          Dashboard view
                                  (presigned URL            (JWT + ownership check)
                                   10-min exp)                     │
                                   ───────────                      ▼
                                        │              GET /dashboard/media/{file_id}
                                        │                        │
                                        │                        ▼
                                        │              StorageService.get_presigned_url()
                                        │                        │
                                        │                        ▼
                                        │              URL with tunnel host
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/models/media_file.py` | Create | MediaFile model with user_id FK |
| `app/models/__init__.py` | Modify | Export MediaFile |
| `migrations/versions/add_media_file.py` | Create | Alembic migration for media_files table |
| `app/services/storage.py` | Modify | User-scoped paths, short URLs, tunnel host |
| `app/main.py` | Modify | Add `/dashboard/media/{file_id}` endpoint |
| `app/core/config.py` | Modify | Add MINIO_TUNNEL_HOST, MINIO_SSE_ENABLED |
| `docker-compose.yml` | Modify | Add MINIO_TUNNEL_HOST env var |

## Interfaces / Contracts

### MediaFile Model

```python
# app/models/media_file.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.models.base import Base

class MediaFile(Base):
    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False)  # {user_id}/{uuid}.{ext}
    original_filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### StorageService Updates

```python
# app/services/storage.py (modifications)

class StorageService:
    def __init__(self):
        # ... existing init ...
        self.tunnel_host = settings.MINIO_TUNNEL_HOST  # NEW
        self.sse_enabled = settings.MINIO_SSE_ENABLED  # NEW

    async def upload_file(self, file: UploadFile, user_id: int) -> MediaFile:
        """Upload with user-scoped path. Returns MediaFile with ownership."""
        file_ext = file.filename.split(".")[-1] if "." in file.filename else "bin"
        key = f"{user_id}/{uuid.uuid4()}.{file_ext}"
        
        # Upload with SSE-S3 if enabled
        extra_args = {"ServerSideEncryption": "AES256"} if self.sse_enabled else {}
        
        async with await self._get_client() as client:
            content = await file.read()
            await client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content,
                ContentType=file.content_type,
                **extra_args
            )
        
        # Create MediaFile record (DB operation separate)
        return MediaFile(key=key, original_filename=file.filename, 
                         content_type=file.content_type, user_id=user_id)

    async def get_presigned_url(self, key: str, expires: int = 600) -> str:
        """Short-lived presigned URL with tunnel host."""
        async with await self._get_client() as client:
            url = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires,
            )
        
        # Replace internal host with tunnel host
        if self.tunnel_host:
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(url)
            url = urlunparse(parsed._replace(netloc=self.tunnel_host))
        
        return url
```

### Protected Endpoint

```python
# app/main.py (addition)

from app.auth.dependencies import get_current_user
from app.models.media_file import MediaFile
from sqlalchemy import select

@app.get("/dashboard/media/{file_id}")
async def get_media_url(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get presigned URL for user's own media file."""
    result = await db.execute(
        select(MediaFile).where(MediaFile.id == file_id)
    )
    media_file = result.scalar_one_or_none()
    
    if media_file is None:
        raise HTTPException(status_code=404, detail="File not found")
    
    if media_file.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    url = await storage_service.get_presigned_url(media_file.key)
    return {"url": url, "expires_in": 600}
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `StorageService.upload_file()` with user_id | Mock aioboto3, verify key format `{user_id}/{uuid}` |
| Unit | `StorageService.get_presigned_url()` host replacement | Mock client, verify tunnel host in URL |
| Unit | `/dashboard/media/{file_id}` authorization | Mock DB, test 401/403/200 responses |
| Integration | Upload + DB record creation | Test file, verify MediaFile created with correct user_id |
| Integration | Bucket privacy | Direct curl to presigned URL after expiration → 403 |
| Integration | SSE-S3 encryption | Check MinIO console for encryption flag |

## Migration / Rollout

1. **Create migration for MediaFile table**: `alembic revision -m "add_media_file"`
2. **Add MINIO_TUNNEL_HOST to .env** (default to empty for dev)
3. **Update StorageService** with new methods
4. **Run migration**: `alembic upgrade head`
5. **Add protected endpoint**
6. **Configure SSE-S3 on bucket** (one-time MinIO setup)

**No data migration needed** - new uploads use new path structure. Existing files unaffected.

## Open Questions

- [ ] Should we add a "soft delete" flag to MediaFile for user account deletion workflow? (Future change)
- [ ] Should `/dashboard/media/{file_id}` return the presigned URL or redirect directly? (Design decision: return URL for flexibility)