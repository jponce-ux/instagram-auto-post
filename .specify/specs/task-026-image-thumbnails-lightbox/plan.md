---
ticket: TASK-026
phase: plan
model: qwen3.6-plus
generated: 2026-06-09
status: draft
---

# Implementation Plan: Image Thumbnails and Lightbox Viewer

**Branch**: `026-image-thumbnails-lightbox` | **Date**: 2026-06-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `.specify/specs/task-026-image-thumbnails-lightbox/spec.md`

## Summary

Add automatic thumbnail generation during image upload, serve thumbnails in the dashboard post history table (instead of full-size images), and implement a client-side lightbox viewer for full-size image inspection. Thumbnails are stored alongside originals in MinIO with a `-thumbnail` suffix in the storage key.

## Technical Context

**Language/Version**: Python 3.11, JavaScript (vanilla)
**Primary Dependencies**: FastAPI, aioboto3 (MinIO/S3), Pillow (thumbnail generation), Jinja2, HTMX
**Storage**: MinIO (S3-compatible) — two-bucket strategy (private encrypted + public temporary)
**Testing**: pytest + pytest-asyncio
**Target Platform**: Linux server (Docker), modern web browsers
**Project Type**: Web application (FastAPI backend + Jinja2/JS frontend)
**Performance Goals**: Dashboard page load < 2s with 10+ posts; thumbnail generation < 2s per image
**Constraints**: Thumbnail generation must not block the upload response; must work within existing Celery/MinIO flow
**Scale/Scope**: Single-user dashboard, ~10-100 posts per user, images up to 20MB

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution at `.specify/memory/constitution.md` is still in template form (placeholders not filled). No active governance gates are defined. Proceeding with project conventions from `AGENTS.md`:

- **FastAPI async pattern**: Use `AsyncSession` for API routes, `SyncSessionLocal` for Celery tasks
- **UV package manager**: All commands use `uv run`, not `pip`
- **Two-bucket MinIO strategy**: Private (encrypted, permanent) + Public (temporary, for Instagram API)
- **JWT auth**: Cookies with HttpOnly, Secure, SameSite=Lax
- **SSE for real-time updates**: Redis pub/sub, no polling

**Gate Status**: ✅ PASS — no constitution violations. Design follows existing patterns.

## Project Structure

### Documentation (this feature)

```text
specs/task-026-image-thumbnails-lightbox/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (not created by /speckit.plan)
```

### Source Code (repository root)

```text
app/
├── services/
│   └── storage.py       # ADD: generate_thumbnail() method, upload_file_with_thumbnail()
├── dashboard/
│   ├── routes.py        # MODIFY: posts_feed endpoint returns thumbnail_url + full_image_url
│   └── service.py       # MODIFY: get_post_image_url() returns both thumbnail and full URLs
├── models/
│   └── media_file.py    # ADD: thumbnail_key column (nullable for backward compat)
├── templates/
│   └── dashboard/
│       ├── layout.html  # MODIFY: renderPosts() — thumbnail with data-full-url, lightbox JS
│       └── posts_feed.html  # MODIFY: server-rendered thumbnails with lightbox support
└── static/
    └── css/
        └── app.css      # ADD: lightbox CSS classes (overlay, centered image, rounded borders)

migrations/
└── versions/
    └── add_thumbnail_key_to_media_files.py  # NEW: ALTER TABLE media_files ADD COLUMN thumbnail_key
```

**Structure Decision**: Single project web application. Thumbnail generation is added to the existing `StorageService` class. The `MediaFile` model gains a `thumbnail_key` column. The dashboard frontend is extended with lightbox JavaScript and CSS. No new services or modules needed.

## Phase 0: Research

### research.md

```markdown
# Research: Image Thumbnails and Lightbox Viewer

## Decision 1: Thumbnail Generation Library

**Decision**: Use Pillow (PIL) for thumbnail generation.

**Rationale**: 
- Pillow is the standard Python image processing library, well-maintained and widely used.
- Supports JPEG, PNG, WebP — all formats the app already handles.
- `Image.thumbnail()` method resizes in-place while maintaining aspect ratio.
- Can be used synchronously in the Celery worker (no async needed for image processing).
- Already available as a transitive dependency in many Python projects; adding it explicitly is low-risk.

**Alternatives considered**:
- `wand` (ImageMagick bindings): More powerful but heavier dependency, requires system-level ImageMagick.
- `opencv-python`: Overkill for simple resizing, large binary dependency.
- Pure Python resize: No dependency but reinventing the wheel, slower, no format support.

## Decision 2: Thumbnail Storage Strategy

**Decision**: Store thumbnail in the same private MinIO bucket with `-thumbnail` suffix in the key.

**Rationale**:
- Matches the spec requirement (FR-002, FR-003).
- Same bucket = same presigned URL generation logic, no new bucket policies needed.
- Key pattern: `{user_id}/{uuid}-thumbnail.{ext}` mirrors the original `{user_id}/{uuid}.{ext}`.
- The `MediaFile` model tracks the original key; adding a `thumbnail_key` column links them.

**Alternatives considered**:
- Separate thumbnail bucket: Unnecessary complexity, same access patterns as originals.
- Store thumbnail key as a derived value (no DB column): Fragile — requires string manipulation on every lookup.
- Store thumbnail in public bucket: Violates privacy — thumbnails should also be behind presigned URLs.

## Decision 3: When to Generate Thumbnails

**Decision**: Generate thumbnails synchronously during the upload step in `create_post()` (dashboard service), before the Celery dispatch.

**Rationale**:
- The user expects the thumbnail to be available immediately for the dashboard history.
- Upload already happens synchronously in `create_post()` — adding thumbnail generation adds ~100-500ms.
- Alternative (generate in Celery worker) would mean the dashboard shows a placeholder until the worker runs.
- For large images (20MB+), Pillow's thumbnail() is fast because it reads only the necessary data.

**Alternatives considered**:
- Generate in Celery worker: Delays thumbnail availability, complicates the dashboard rendering.
- Generate on-demand (lazy): First request triggers generation, cached afterward. Adds complexity and race conditions.
- Generate via separate microservice: Overkill for a single-app deployment.

## Decision 4: Lightbox Implementation

**Decision**: Pure JavaScript + CSS lightbox (no external library).

**Rationale**:
- The lightbox is a simple overlay with an image — no need for a heavy library like Fancybox or Lightbox2.
- ~50 lines of JS + ~30 lines of CSS is sufficient.
- No additional dependencies to manage, no CDN calls, no version pinning.
- The full-size URL is already embedded as `data-full-url` on the thumbnail element.

**Alternatives considered**:
- Fancybox/Lightbox2: More features (zoom, swipe, gallery navigation) but adds 50KB+ JS dependency.
- HTMX-based lightbox: Would require a server round-trip, defeats the purpose of embedding the URL as metadata.

## Decision 5: Thumbnail Dimensions

**Decision**: 200px width, maintaining aspect ratio.

**Rationale**:
- The current table cell is `w-12 h-12` (48px) in Tailwind, but the actual rendered thumbnail should be slightly larger for clarity.
- 200px width produces ~15-50KB JPEG thumbnails (well under the 200KB target in SC-002).
- Matches the spec assumption of "150-200px width".
- Can be adjusted later via a config constant without changing the data model.

## Decision 6: Backward Compatibility for Existing Posts

**Decision**: Existing posts without thumbnails fall back to the full-size image (FR-011). The `thumbnail_key` column is nullable.

**Rationale**:
- No migration needed to backfill existing posts — they simply use the full-size image.
- A future migration script could generate thumbnails for existing posts, but that's out of scope.
- The `get_post_image_url()` function checks for `thumbnail_key` and falls back gracefully.
```

## Phase 1: Design & Contracts

### data-model.md

```markdown
# Data Model: Image Thumbnails

## Entity: MediaFile (MODIFIED)

Existing model gains one new column:

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | Integer | No | Primary key |
| `key` | String | No | Original image key: `{user_id}/{uuid}.{ext}` |
| `thumbnail_key` | String | **Yes** | Thumbnail key: `{user_id}/{uuid}-thumbnail.{ext}` |
| `original_filename` | String | No | Original filename from upload |
| `content_type` | String | No | MIME type (image/jpeg, image/png, etc.) |
| `user_id` | Integer | No | FK to users.id |
| `created_at` | DateTime | No | Upload timestamp |

### Relationships
- `MediaFile.user` → `User.media_files` (one-to-many)
- `MediaFile.posts` → `Post.media_file` (one-to-many)

### Validation Rules
- `thumbnail_key` is nullable for backward compatibility with existing records.
- When `thumbnail_key` is set, it MUST follow the pattern `{original_key_stem}-thumbnail.{ext}`.
- Both `key` and `thumbnail_key` reference objects in the private MinIO bucket.

## Entity: Post (UNCHANGED)

No changes to the Post model. The Post references MediaFile via `media_file_id`, and the MediaFile now carries both the original and thumbnail keys.

## State Transitions

No new state transitions. The thumbnail generation is a side-effect of the upload process, not a state change.
```

### contracts/posts-feed-api.md

```markdown
# Contract: Posts Feed API

## GET /dashboard/posts/feed

Returns JSON array of posts with both thumbnail and full-size image URLs.

### Response Format

```json
{
  "posts": [
    {
      "id": 42,
      "caption": "My sunset photo",
      "status": "published",
      "created_at": "2026-06-09T15:30:00+00:00",
      "thumbnail_url": "https://minio.loquinto.com/private-bucket/1/abc123-thumbnail.jpg?X-Amz-...",
      "full_image_url": "https://minio.loquinto.com/private-bucket/1/abc123.jpg?X-Amz-..."
    }
  ]
}
```

### Field Changes from Current API

| Field | Before | After |
|-------|--------|-------|
| `image_url` | Single presigned URL (full-size) | **REMOVED** |
| `thumbnail_url` | N/A | **NEW**: Presigned URL for thumbnail (or null if no thumbnail) |
| `full_image_url` | N/A | **NEW**: Presigned URL for full-size original (or null if no media) |

### Backward Compatibility

- Clients that only read `image_url` will break. This is acceptable because the only consumer is the dashboard's own JavaScript (`layout.html`), which will be updated simultaneously.
- If `thumbnail_url` is null (old post without thumbnail), the frontend falls back to `full_image_url`.

## POST /dashboard/post

No changes to the request format. The response gains no new fields (thumbnail generation is a side-effect).
```

### quickstart.md

```markdown
# Quickstart: Testing Thumbnails and Lightbox

## Prerequisites

- Docker Compose stack running (`docker compose up -d`)
- At least one Instagram account connected
- Pillow installed: `uv add pillow`

## Test Flow

### 1. Upload a New Image

1. Navigate to `/dashboard`
2. Select an image file (JPEG or PNG, ideally > 1MB)
3. Add a caption and click "Publicar"
4. Verify the post appears in the history table with a small thumbnail

### 2. Verify Thumbnail Storage

```bash
# Check MinIO for both files
docker exec mi-app-instagram-minio mc ls myminio/instagram-app-private/1/
# Should see: {uuid}.jpg AND {uuid}-thumbnail.jpg
```

### 3. Test Lightbox

1. Click on any thumbnail in the history table
2. Verify: dark overlay appears, full-size image centered with rounded borders
3. Click outside the image → lightbox closes
4. Press Escape → lightbox closes
5. Click the image itself → lightbox stays open

### 4. Verify Performance

1. Open browser DevTools → Network tab
2. Reload `/dashboard`
3. Check image request sizes — thumbnails should be < 200KB each
4. Compare total page load time vs. before (should be ~50% faster)

### 5. Test Fallback (Old Posts)

1. If you have posts created before this feature, verify they still display
2. They should show the full-size image (no thumbnail available)
3. Clicking should still open the lightbox
```

## Complexity Tracking

> No constitution violations. No complexity beyond the existing architecture.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
