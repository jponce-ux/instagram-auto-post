# Design: Storage MinIO

## Technical Approach

Add MinIO as an S3-compatible object storage service in Docker Compose, then create an async Python service using `aioboto3` to handle file uploads and presigned URL generation. The system will auto-provision a bucket on startup using MinIO's REST API, matching the existing service pattern in `app/services/instagram.py`.

## Architecture Decisions

### Decision: Use aioboto3 vs boto3

**Choice**: `aioboto3`
**Alternatives considered**: `boto3` (sync), `minio-py` (MinIO client)
**Rationale**: Project uses async/await throughout (`asyncpg`, `httpx.AsyncClient`, `AsyncSession`). Sync boto3 would block the event loop. MinIO client is less mature than aioboto3, and aioboto3 provides identical API to boto3with async support.

### Decision: Presigned URLs vs Public Bucket

**Choice**: Presigned URLs with 7-day expiration
**Alternatives considered**: Public bucket (anonymous read), Proxy through FastAPI
**Rationale**: 
- Public bucket is insecure (anyone can access)
- Proxy adds latency and bandwidth overhead to FastAPI
- Presigned URLs are the S3-standard for temporary access — Meta can fetch the image directly from MinIO without going through our API

### Decision: Bucket Auto-Creation Strategy

**Choice**: REST API call from FastAPI on startup
**Alternatives considered**: MinIO console manual creation, Init container, Docker entrypoint script
**Rationale**: 
- Manual creation is fragile (devs forget)
- Init container adds complexity
- Entrypoint script is MinIO implementation-specific
- REST API (using existing httpx) is simple and matches service pattern

### Decision: Service Location

**Choice**: `app/services/storage.py` with class-based design
**Alternatives considered**: Functional module like `instagram.py`, отдельный microservice
**Rationale**: 
- Class allows connection reuse and initialization logic
- Follows layered architecture pattern
- Keeps infrastructure simple (no additional containers for dev)

## Data Flow

```
Frontend (HTMX) ──POST /upload──→ FastAPI Debug Endpoint
                                        │
                                        ▼
                                  StorageService.upload_file()
                                        │
                                        ▼
                              aioboto3.put_object(bucket, key, file)
                                        │
                                        ▼
                                    MinIO Container
                                        │
                                        ▼
                              StorageService.get_presigned_url(key)
                                        │
                                        ▼
                              aioboto3.generate_presigned_url()
                                        │
                                        ▼
                                  Return URL to Frontend
                                        │
                                        ▼
                            Meta API fetches image from URL
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `docker-compose.yml` | Modify | Add `minio` service with volume `minio_data:/data` |
| `app/core/config.py` | Modify | Add `MINIO_ENDPOINT`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_BUCKET_NAME` |
| `app/services/storage.py` | Create | `StorageService` class with `upload_file()` and `get_presigned_url()` |
| `app/main.py` | Modify | Add startup event to create bucket via `StorageService.ensure_bucket_exists()` |
| `pyproject.toml` | Modify | Add `aioboto3>=12.0.0` |
| `.env.example` | Modify | Add MINIO_* variable examples |

## Interfaces / Contracts

### StorageService Class

```python
# app/services/storage.py

class StorageService:
    def __init__(self):
        self.endpoint = settings.MINIO_ENDPOINT
        self.access_key = settings.MINIO_ROOT_USER
        self.secret_key = settings.MINIO_ROOT_PASSWORD
        self.bucket = settings.MINIO_BUCKET_NAME
        self._client = None
    
    async def get_client(self):
        """Lazy-load aioboto3 client"""
        if self._client is None:
            self._client = aioboto3.client(
                's3',
                endpoint_url=self.endpoint,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
            )
        return self._client
    
    async def ensure_bucket_exists(self):
        """Create bucket if not exists (call on startup)"""
        client = await self.get_client()
        try:
            await client.head_bucket(Bucket=self.bucket)
        except ClientError:
            await client.create_bucket(Bucket=self.bucket)
    
    async def upload_file(self, file: UploadFile, key: str) -> str:
        """Upload file and return key. Raises Exception on failure."""
        client = await self.get_client()
        content = await file.read()
        await client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=file.content_type,
        )
        return key
    
    async def get_presigned_url(self, key: str, expires: int = 604800) -> str:
        """Generate presigned URL (default 7 days)"""
        client = await self._get_client()
        url = await client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': key},
            ExpiresIn=expires,
        )
        return url
```

### Environment Variables

```bash
# .env.example additions
MINIO_ENDPOINT=http://minio:9000
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
MINIO_BUCKET_NAME=instagram-uploads
```

### Docker Compose Service

```yaml
# docker-compose.yml additions
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"  # API
      - "9001:9001"  # Console
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

volumes:
  minio_data:
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `StorageService.ensure_bucket_exists()` | Mock aioboto3 client, test create vs no-op |
| Unit | `StorageService.upload_file()` | Mock client, verify put_object called |
| Unit | `StorageService.get_presigned_url()` | Mock client, verify URL format |
| Integration | Upload + presigned URL flow | Start MinIO container in test suite, upload real file |
| E2E | Debug upload endpoint | `curl POST /api/v1/debug/upload`, verify response contains URL |

**Note**: Project has no test infrastructure (pytest not installed). Tests documented but not implemented in this change.

## Migration / Rollout

No migration required. This is a new capability with no existing data to migrate.

**Rollout顺序**:
1. Add MinIO to docker-compose.yml
2. Add aioboto3 dependency
3. Create StorageService
4. Add config fields
5. Add startup event for bucket creation
6. Add debug endpoint

## Open Questions

None. All technical decisions resolved in Architecture Decisions section.