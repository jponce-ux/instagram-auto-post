---
ticket: TASK-026
phase: tasks
model: qwen3.6-plus
generated: 2026-06-09
status: completed
---

# Tasks: Image Thumbnails and Lightbox Viewer

**Input**: Design documents from `.specify/specs/task-026-image-thumbnails-lightbox/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), data-model.md (embedded in plan.md), contracts/ (embedded in plan.md)

**Tests**: Not explicitly requested in the feature specification. Test tasks are included as verification steps within each user story phase.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add Pillow dependency for thumbnail generation

- [x] T001 Add Pillow dependency via `uv add pillow`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database migration and storage service changes that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 [P] Add `thumbnail_key` column to MediaFile model in `app/models/media_file.py`
- [x] T003 Create Alembic migration for `thumbnail_key` column: `uv run alembic revision --autogenerate -m "add thumbnail_key to media_files"` then verify in `migrations/versions/`
- [x] T004 Implement `generate_thumbnail()` method in `app/services/storage.py` — accepts image bytes, returns thumbnail bytes using Pillow (200px width, maintain aspect ratio, JPEG output)
- [x] T005 Implement `upload_thumbnail()` method in `app/services/storage.py` — uploads thumbnail bytes to private bucket with `-thumbnail` suffix in key

**Checkpoint**: Foundation ready — thumbnail generation and storage infrastructure in place

---

## Phase 3: User Story 1 - Thumbnail Generation on Upload (Priority: P1) 🎯 MVP

**Goal**: When a user uploads an image, automatically generate and store a thumbnail alongside the original in MinIO.

**Independent Test**: Upload an image through the dashboard post form, verify that two files exist in MinIO — the original and a `-thumbnail` version. The thumbnail should be significantly smaller in file size.

### Implementation for User Story 1

- [x] T006 [US1] Modify `upload_file_for_user()` in `app/services/storage.py` to also generate and upload a thumbnail, returning both keys
- [x] T007 [US1] Update `create_post()` in `app/dashboard/service.py` to use the new thumbnail-aware upload flow — store `thumbnail_key` in the MediaFile record
- [x] T008 [US1] Verify thumbnail generation works end-to-end: upload a test image via the dashboard, check MinIO for both files, verify thumbnail is < 200KB

**Checkpoint**: At this point, every new upload produces both an original and a thumbnail in MinIO. The `MediaFile.thumbnail_key` column is populated.

---

## Phase 4: User Story 2 - Dashboard History Shows Thumbnails (Priority: P2)

**Goal**: The post history table displays thumbnail images instead of full-size originals. Each thumbnail row includes metadata pointing to the full-size image URL.

**Independent Test**: Navigate to the dashboard with existing posts. Verify that each row in the history table shows a small thumbnail image. The page should load noticeably faster. Inspect the image element to confirm `src` points to thumbnail URL and `data-full-url` points to the original.

### Implementation for User Story 2

- [x] T009 [P] [US2] Add `get_presigned_url_for_key()` helper in `app/services/storage.py` — generates presigned URL for any given storage key (original or thumbnail)
- [x] T010 [US2] Modify `get_post_image_url()` in `app/dashboard/service.py` to return a dict with both `thumbnail_url` and `full_image_url` (fallback to full if no thumbnail)
- [x] T011 [US2] Update `posts_feed` endpoint in `app/dashboard/routes.py` to include `thumbnail_url` and `full_image_url` in the JSON response (replace old `image_url` field)
- [x] T012 [US2] Update `renderPosts()` in `app/templates/dashboard/layout.html` to use `thumbnail_url` for the `<img src>` and embed `full_image_url` as `data-full-url` attribute
- [x] T013 [US2] Update server-rendered `app/templates/dashboard/posts_feed.html` to show thumbnail images with `data-full-url` attribute for HTMX fallback
- [x] T014 [US2] Verify dashboard loads thumbnails: check Network tab for thumbnail-sized requests (< 200KB each), confirm `data-full-url` attribute is present on each image element

**Checkpoint**: Dashboard history table now shows thumbnails. Full-size URLs are embedded as metadata for the lightbox.

---

## Phase 5: User Story 3 - Lightbox Full-Size Viewer (Priority: P3)

**Goal**: Clicking a thumbnail opens a full-screen overlay (lightbox) displaying the original full-size image centered with rounded borders. Closeable via click-outside or Escape key.

**Independent Test**: Click any thumbnail in the history table. Verify dark overlay covers the viewport, full-size image appears centered with rounded corners. Click outside the image → lightbox closes. Press Escape → lightbox closes. Click the image itself → lightbox stays open.

### Implementation for User Story 3

- [x] T015 [P] [US3] Add lightbox CSS classes in `app/static/css/app.css` — overlay (fixed, full-screen, dark semi-transparent), centered image container, rounded borders (`border-radius: 12px`), responsive max-width
- [x] T016 [US3] Add lightbox HTML structure to `app/templates/dashboard/layout.html` — hidden `<div id="lightbox">` with overlay and `<img id="lightbox-img">`
- [x] T017 [US3] Add lightbox JavaScript in `app/templates/dashboard/layout.html` — click handler on thumbnails reads `data-full-url`, sets `lightbox-img.src`, shows overlay; click-outside and Escape key handlers to close
- [x] T018 [US3] Update `renderPosts()` in `app/templates/dashboard/layout.html` to add `onclick` handler on thumbnail images that triggers the lightbox with the `data-full-url`
- [x] T019 [US3] Verify lightbox behavior: click thumbnail → overlay appears with full image; click outside → closes; Escape → closes; click image → stays open; mobile viewport → image scales correctly

**Checkpoint**: All user stories are now independently functional. Thumbnails load fast, lightbox shows full-size images.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Edge case handling, backward compatibility, and validation

- [x] T020 [P] Add fallback logic: if `thumbnail_key` is null (old post), use `full_image_url` for both display and lightbox in `app/dashboard/service.py`
- [x] T021 [P] Add error handling in `generate_thumbnail()` for non-image files — log warning and skip thumbnail generation gracefully
- [x] T022 [P] Add logging for thumbnail generation in `app/services/storage.py` — log original size, thumbnail size, and generation time
- [x] T023 Run `uv run alembic upgrade head` to apply the migration
- [x] T024 Run `uv run pytest tests/ -v` to verify no regressions
- [x] T025 Validate quickstart.md test flow manually (upload → verify thumbnails → test lightbox → check performance)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can proceed sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) — Depends on US1's thumbnail generation being in place (thumbnails must exist to display them)
- **User Story 3 (P3)**: Can start after US2 is complete — Lightbox needs `data-full-url` metadata from US2's thumbnail rendering

### Within Each User Story

- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- T002 and T003 can run in parallel (model change + migration creation)
- T004 and T005 can run in parallel (thumbnail generation + upload methods)
- T009 (presigned URL helper) can run in parallel with T010-T011
- T015 (lightbox CSS) can run in parallel with T016-T017 (lightbox HTML/JS)
- T020, T021, T022 can all run in parallel (independent polish tasks)

---

## Parallel Example: Foundational Phase

```bash
# Launch model + migration together:
Task: "Add thumbnail_key column to MediaFile model in app/models/media_file.py"
Task: "Create Alembic migration for thumbnail_key column"

# Launch thumbnail methods together:
Task: "Implement generate_thumbnail() in app/services/storage.py"
Task: "Implement upload_thumbnail() in app/services/storage.py"
```

---

## Parallel Example: User Story 3 (Lightbox)

```bash
# Launch CSS + HTML/JS together:
Task: "Add lightbox CSS classes in app/static/css/app.css"
Task: "Add lightbox HTML structure in app/templates/dashboard/layout.html"
Task: "Add lightbox JavaScript in app/templates/dashboard/layout.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (add Pillow)
2. Complete Phase 2: Foundational (thumbnail generation + storage methods + migration)
3. Complete Phase 3: User Story 1 (thumbnail generation on upload)
4. **STOP and VALIDATE**: Upload an image, verify both files exist in MinIO
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Thumbnail infrastructure ready
2. Add User Story 1 → Thumbnails generated on upload → Verify in MinIO
3. Add User Story 2 → Dashboard shows thumbnails → Verify faster page load
4. Add User Story 3 → Lightbox viewer → Verify click-to-zoom behavior
5. Each story adds value without breaking previous stories

### Sequential Strategy (Single Developer)

1. T001 → T002 → T003 → T004 → T005 (Foundation)
2. T006 → T007 → T008 (US1: Thumbnail generation)
3. T009 → T010 → T011 → T012 → T013 → T014 (US2: Dashboard thumbnails)
4. T015 → T016 → T017 → T018 → T019 (US3: Lightbox)
5. T020 → T021 → T022 → T023 → T024 → T025 (Polish)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Pillow's `Image.thumbnail()` modifies in-place — always work on a copy of the image
- The `thumbnail_key` column is nullable for backward compatibility with existing posts
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
