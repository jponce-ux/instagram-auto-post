# Proposal: Storage MinIO

## Intent

The Instagram Business API requires publicly accessible image URLs for media publishing. Currently, the application has no mechanism to store and serve images. This change introduces MinIO, an S3-compatible object storage service, to store images uploaded by users and generate presigned URLs that Meta's API can access.

## Scope

### In Scope
- MinIO service in Docker Compose with persistent volume
- Async Python storage service using aioboto3
- Presigned URL generation for public access
- Auto-provisioned bucket on startup
- Debug endpoint for file upload testing

### Out of Scope
- Cloudflare Tunnel configuration (SPEC-009)
- Production-grade security hardening
- Image compression/resizing
- Multi-bucket strategies

## Capabilities

> Capability specs will be created in `openspec/specs/` after this proposal.

### New Capabilities
- `object-storage`: Async storage service for uploading files and generating public URLs via MinIO (S3-compatible)

### Modified Capabilities
None - this is a new capability.

## Approach

1. **Docker Service**: Add MinIO container to docker-compose.yml (ports 9000 for API, 9001 for console)
2. **Configuration**: Add MINIO_ROOT_USER, MINIO_ROOT_PASSWORD, MINIO_ENDPOINT to .env and config.py
3. **Storage Service**: Create `app/services/storage.py` with async methods `upload_file()` and `get_presigned_url()` using aioboto3
4. **Auto-provision**: Use MinIO's REST API to create `instagram-uploads` bucket on first startup
5. **Debug Endpoint**: `POST /api/v1/debug/upload` to test the full flow during development

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `docker-compose.yml` | New | Add MinIO service with volume |
| `.env.example` | Modified | Add MINIO_* variables |
| `app/core/config.py` | Modified | Add MINIO_* settings fields |
| `app/services/storage.py` | New | StorageService class |
| `app/main.py` | Modified | Include debug upload route |
| `pyproject.toml` | Modified | Add aioboto3 dependency |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| MinIO default credentials in dev | Medium | Clearly document default credentials are for dev only |
| Presigned URL expiration | Low | Use 7-day expiration (configurable) |
| Bucket creation race condition | Low | Use idempotent REST API for bucket creation |

## Rollback Plan

1. Remove MinIO service from docker-compose.yml
2. Delete `app/services/storage.py`
3. Remove aioboto3 from pyproject.toml: `uv remove aioboto3`
4. Revert MINIO_* config fields from config.py
5. Prune MinIO volume: `docker volume rm mi-app-instagram_minio_data`

## Dependencies

- Docker Compose must be running
- No external dependencies beyond aioboto3

## Success Criteria

- [ ] `docker compose up` starts MinIO service successfully
- [ ] MinIO console accessible at http://localhost:9001
- [ ] Bucket `instagram-uploads` exists after startup
- [ ] `POST /api/v1/debug/upload` returns a valid presigned URL
- [ ] Presigned URL is publicly accessible (curl returns file)