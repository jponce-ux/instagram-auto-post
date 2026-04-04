# Proposal: MinIO Security and Privacy (SPEC-010)

## Intent

Current MinIO implementation stores files in a flat structure with public presigned URLs (7-day expiration). This violates user privacy: anyone with a URL can access any file, and files are not isolated by user. This change implements user data isolation, short-lived access tokens, IAM policies, and encryption at rest.

## Scope

### In Scope
- User-scoped file paths: `/{user_id}/{uuid}.jpg`
- Private bucket (no anonymous access)
- Short-lived presigned URLs (10-minute expiration for Meta API)
- Tunnel host in URLs (Cloudflare instead of localhost)
- Protected endpoint `/dashboard/media/{file_id}` with JWT validation + ownership check
- MinIO IAM policies (scoped credentials)
- SSE-S3 encryption at rest

### Out of Scope
- User management UI (already implemented)
- Legal/compliance documentation
- Data deletion workflow (future change)
- Admin dashboard for file management

## Capabilities

### New Capabilities
- `media-privacy`: User-scoped storage with ownership validation and encrypted files

### Modified Capabilities
- `object-storage`: Requirements change — private bucket, user-scoped paths, short-lived URLs

## Approach

1. **Folder Structure**: Modify `upload_file()` to accept `user_id` and generate keys as `/{user_id}/{uuid}.{ext}`
2. **Bucket Privacy**: Remove any public policy, ensure bucket ACL is private
3. **Short-lived URLs**: Default `expires=600` (10 min), accept `tunnel_host` config for Cloudflare
4. **Protected Endpoint**: Create `GET /dashboard/media/{file_id}` that validates JWT, checks DB ownership, returns presigned URL
5. **IAM Policy**: Create MinIO policy JSON limiting to `s3:PutObject`, `s3:GetObject` on bucket
6. **SSE-S3**: Configure bucket with server-side encryption

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/storage.py` | Modified | Add user_id to paths, tunnel_host in URLs, privacy checks |
| `app/main.py` | Modified | Add `/dashboard/media/{file_id}` endpoint |
| `app/auth/dependencies.py` | Used | JWT validation (existing) |
| `docker-compose.yml` | Modified | Add MINIO_TUNNEL_HOST env var |
| `app/core/config.py` | Modified | Add MINIO_TUNNEL_HOST, MINIO_IAM_POLICY settings |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Breaking existing uploads | Medium | Migration script for existing files (if any) |
| IAM complexity | Low | Use MinIO default policy template |
| Cloudflare tunnel not ready | Medium | Cloudflare-tunnel (SPEC-009) is dependency |

## Rollback Plan

1. Revert `upload_file()` to flat structure
2. Remove MINIO_TUNNEL_HOST from config
3. Remove IAM policy from MinIO
4. Set `expires=604800` (7 days) in presigned URLs
5. Remove `/dashboard/media` endpoint

## Dependencies

- **SPEC-009 (cloudflare-tunnel)**: Required for tunnel host configuration
- **SPEC-006 (auth-argon2-jwt)**: Required for JWT validation and user_id

## Success Criteria

- [ ] Files stored as `/{user_id}/{uuid}.jpg`
- [ ] Bucket has no public policy (curl to URL returns 403)
- [ ] Presigned URLs expire in 600 seconds
- [ ] URLs use tunnel host (instagramjp.domain.com)
- [ ] `GET /dashboard/media/{file_id}` returns 401 without JWT
- [ ] `GET /dashboard/media/{file_id}` returns 403 when user doesn't own file
- [ ] MinIO console shows SSE-S3 encryption enabled on bucket