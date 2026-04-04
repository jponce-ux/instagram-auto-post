# Tasks: MinIO Security and Privacy (SPEC-010)

## Phase 0: Git Branch

- [ ] 0.1 `git checkout main`
- [ ] 0.2 `git pull origin main`
- [ ] 0.3 `git checkout -b feat/010-minio-security-privacy`

## Phase 1: Foundation

- [ ] 1.1 Create `app/models/media_file.py` with MediaFile model (id, key, original_filename, content_type, user_id FK, created_at)
- [ ] 1.2 Add MediaFile export to `app/models/__init__.py`
- [ ] 1.3 Create Alembic migration: `alembic revision -m "add_media_file_table"`
- [ ] 1.4 Define media_files table in migration with columns: id, key (unique), original_filename, content_type, user_id (FK to users.id), created_at
- [ ] 1.5 Run migration: `docker compose exec web uv run alembic upgrade head`
- [ ] 1.6 Add `MINIO_TUNNEL_HOST: str = ""` to `app/core/config.py` Settings class
- [ ] 1.7 Add `MINIO_SSE_ENABLED: bool = False` to `app/core/config.py` Settings class
- [ ] 1.8 Add `MINIO_TUNNEL_HOST=${MINIO_TUNNEL_HOST}` to `.env` and `.env.example`

## Phase 2: Core Implementation

- [ ] 2.1 Add `self.tunnel_host = settings.MINIO_TUNNEL_HOST` to StorageService.__init__
- [ ] 2.2 Add `self.sse_enabled = settings.MINIO_SSE_ENABLED` to StorageService.__init__
- [ ] 2.3 Modify `upload_file()` signature: add `user_id: int` parameter
- [ ] 2.4 Generate key as `f"{user_id}/{uuid.uuid4()}.{file_ext}"` in upload_file
- [ ] 2.5 Add SSE-S3 encryption args if `self.sse_enabled` in put_object call
- [ ] 2.6 Update `upload_file()` docstring with new user_id parameter
- [ ] 2.7 Change default expiration in `get_presigned_url()` from 604800 to 600 seconds
- [ ] 2.8 Add tunnel host URL replacement logic in `get_presigned_url()` using urlparse
- [ ] 2.9 Add new method `upload_file_for_user(file, user_id, db)` that creates MediaFile DB record after S3 upload

## Phase 3: Integration

- [ ] 3.1 Import MediaFile model in `app/main.py`
- [ ] 3.2 Modify `/api/v1/debug/upload` to accept `current_user: User = Depends(get_current_user)`
- [ ] 3.3 Modify debug_upload to pass `current_user.id` to storage_service.upload_file_for_user()
- [ ] 3.4 Modify debug_upload to create MediaFile record in DB with user_id
- [ ] 3.5 Create `GET /dashboard/media/{file_id}` endpoint in `app/main.py`
- [ ] 3.6 Add query `select(MediaFile).where(MediaFile.id == file_id)` in endpoint
- [ ] 3.7 Add ownership check: `if media_file.user_id != current_user.id: raise HTTPException(403)`
- [ ] 3.8 Return JSON with presigned URL and expires_in from endpoint
- [ ] 3.9 Add MINIO_SSE_ENABLED to docker-compose web service environment

## Phase 4: Database Integration

- [ ] 4.1 Import MediaFile in main.py and ensure SQLAlchemy knows the model
- [ ] 4.2 In upload_file_for_user, create MediaFile with: key, original_filename, content_type, user_id
- [ ] 4.3 Use `db.add(media_file)` and `await db.commit()` pattern
- [ ] 4.4 Return MediaFile object from upload_file_for_user

## Phase 5: Verification

- [ ] 5.1 Test upload: POST /api/v1/debug/upload with JWT → verify key is `{user_id}/{uuid}.jpg`
- [ ] 5.2 Test ownership: GET /dashboard/media/{file_id} with different user → expect 403
- [ ] 5.3 Test URL expiration: Wait 11 minutes, try presigned URL → expect 403 from MinIO
- [ ] 5.4 Test tunnel host: Verify presigned URL contains tunnel host (if configured)
- [ ] 5.5 Test SSE-s3: Check MinIO console for encryption status on uploaded files
- [ ] 5.6 Test MediaFile creation: Query DB after upload, verify record exists with correct user_id

## Phase 6: Git Commit

- [ ] 6.1 `git add .`
- [ ] 6.2 `git commit -m "feat(010): implement MinIO security and privacy - user-scoped paths, short-lived URLs, ownership tracking"`
- [ ] 6.3 `git push origin feat/010-minio-security-privacy` (optional)
- [ ] 6.4 Return to main: `git checkout main` (wait for PR review before merge)