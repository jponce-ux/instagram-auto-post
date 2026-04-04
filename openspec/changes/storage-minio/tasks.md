# Tasks: Storage MinIO

## Phase 1: Infrastructure

- [ ] 1.1 Add MinIO service to `docker-compose.yml` with image `minio/minio:latest`
- [ ] 1.2 Configure MinIO command: `server /data --console-address ":9001"`
- [ ] 1.3 Set MinIO environment variables: `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` from `${VAR}` interpolation
- [ ] 1.4 Add volume `minio_data:/data` to volumes section
- [ ] 1.5 Expose ports `9000:9000` (API) and `9001:9001` (Console)
- [ ] 1.6 Add healthcheck using `curl -f http://localhost:9000/minio/health/live`
- [ ] 1.7 Add dependency: `web` service depends on `minio` with health condition
- [ ] 1.8 Add `aioboto3>=12.0.0` to dependencies via `uv add aioboto3`

## Phase 2: Configuration

- [ ] 2.1 Add to `.env`: `MINIO_ENDPOINT=http://minio:9000`
- [ ] 2.2 Add to `.env`: `MINIO_ROOT_USER=minioadmin`
- [ ] 2.3 Add to `.env`: `MINIO_ROOT_PASSWORD=minioadmin123`
- [ ] 2.4 Add to `.env`: `MINIO_BUCKET_NAME=instagram-uploads`
- [ ] 2.5 Add to `.env.example`: All four MINIO_* variables with example values
- [ ] 2.6 Modify `app/core/config.py`: Add fields `MINIO_ENDPOINT`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_BUCKET_NAME` to `Settings` class

## Phase 3: Core Implementation

- [ ] 3.1 Create `app/services/storage.py` with `StorageService` class
- [ ] 3.2 Implement `__init__()` to load settings: endpoint, access_key, secret_key, bucket
- [ ] 3.3 Implement `get_client()` with lazy-loaded context manager using `aioboto3.client('s3', ...)`
- [ ] 3.4 Import `ClientError` from `botocore.exceptions` for bucket existence check
- [ ] 3.5 Implement `ensure_bucket_exists()` async method: check `head_bucket()`, create if not exists
- [ ] 3.6 Implement `upload_file(file: UploadFile, key: str)` async method using `put_object()`
- [ ] 3.7 Implement `get_presigned_url(key: str, expires: int = 604800)` async method
- [ ] 3.8 Add type hints and docstrings to all methods

## Phase 4: Integration

- [ ] 4.1 Import `StorageService` in `app/main.py`
- [ ] 4.2 Create global `storage_service = StorageService()` instance
- [ ] 4.3 Add `lifespan` async context manager to FastAPI app
- [ ] 4.4 Call `await storage_service.ensure_bucket_exists()` in lifespan startup
- [ ] 4.5 Create debug router in `app/main.py` or new file `app/debug/routes.py`
- [ ] 4.6 Implement `POST /api/v1/debug/upload` endpoint to accept `UploadFile`
- [ ] 4.7 Generate unique key using `uuid.uuid4()` + file extension
- [ ] 4.8 Call `storage_service.upload_file()` and `storage_service.get_presigned_url()`
- [ ] 4.9 Return JSON response with presigned URL

## Phase 5: Verification

- [ ] 5.1 Restart Docker Compose: `docker compose up --build`
- [ ] 5.2 Verify MinIO container health: `docker compose ps` shows `healthy`
- [ ] 5.3 Access MinIO Console at `http://localhost:9001` with credentials
- [ ] 5.4 Verify bucket exists in Console UI or via `mc ls minio/instagram-uploads`
- [ ] 5.5 Test upload endpoint: `curl -X POST -F "file=@test.jpg" http://localhost:8000/api/v1/debug/upload`
- [ ] 5.6 Verify response contains presigned URL
- [ ] 5.7 Test presigned URL accessibility: `curl -I <presigned_url>` returns HTTP 200
- [ ] 5.8 Verify file appears in MinIO bucket via Console UI