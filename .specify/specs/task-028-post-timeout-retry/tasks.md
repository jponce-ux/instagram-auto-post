---
ticket: TASK-028
phase: tasks
model: qwen3.6-plus
generated: 2026-06-19
status: draft
---

# Tasks: Stalled Post Timeout, Retry, and Token Health Check

**Input**: Design documents from `.specify/specs/task-028-post-timeout-retry/`
**Prerequisites**: plan.md (required), spec.md (required)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)

## Phase 1: Setup (Database Migration)

**Purpose**: Add `processing_started_at` column to the Post table

- [x] T001 Create Alembic migration to add `processing_started_at` (TIMESTAMP WITH TIME ZONE, nullable) to the `posts` table in `migrations/versions/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Set `processing_started_at` on all status transitions across existing code paths

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T002 [P] Modify `check_scheduled_posts()` in `app/worker.py` — set `processing_started_at = NOW()` when transitioning post from PENDING to PROCESSING
- [ ] T003 [P] Modify `_process_post_sync()` in `app/worker.py` — set `processing_started_at = NOW()` when post status becomes PROCESSING, clear to NULL on PUBLISHED or FAILED
- [ ] T004 [P] Modify `process_instagram_post()` in `app/worker.py` — set `processing_started_at = NOW()` when status becomes RETRYING, clear to NULL on FAILED
- [ ] T005 [P] Modify `create_post()` in `app/dashboard/service.py` — set `processing_started_at = NOW()` when dispatching Celery task for immediate processing

**Checkpoint**: All status transitions now track `processing_started_at` — stalled post detection can begin

---

## Phase 3: User Story 1 - Automatic Stalled Post Detection and Failure (Priority: P1) 🎯 MVP

**Goal**: Detect posts stuck in "procesando" (>15 min) or "reintentando" (>5 min) state, automatically mark them as "fallido", and publish SSE events for real-time dashboard updates.

**Independent Test**: Manually set a post to "procesando" with `processing_started_at` 16 minutes ago. Within 60 seconds, verify the post transitions to "fallido" and the dashboard reflects the change via SSE.

### Implementation for User Story 1

- [ ] T006 [US1] Add `check_stalled_posts()` Celery Beat task in `app/worker.py` — scans for posts where `status='processing' AND processing_started_at < NOW() - 15 min` OR `status='retrying' AND processing_started_at < NOW() - 5 min`, transitions them to FAILED with appropriate error message
- [ ] T007 [US1] Register `check_stalled_posts` in `celery_app.conf.beat_schedule` in `app/worker.py` with 60-second interval
- [ ] T008 [US1] Add `_publish_post_event()` call in `check_stalled_posts()` in `app/worker.py` — publish SSE event when post transitions to FAILED due to timeout
- [ ] T009 [US1] Add NULL fallback logic in `check_stalled_posts()` — if `processing_started_at` is NULL, use `created_at` for timeout calculation (safe fallback for pre-migration posts)

**Checkpoint**: Stalled posts are automatically detected and marked as "fallido" with SSE notification

---

## Phase 4: User Story 2 - Retry Failed Posts (Priority: P2)

**Goal**: Add a retry endpoint and "Reintentar" button so users can re-dispatch failed posts using the original MinIO image. Include client-side cooldown logic (disabled during request, 10s cooldown after 3 consecutive failures).

**Independent Test**: Set a post to "fallido" state. View the dashboard, click "Reintentar". Verify the post transitions to "procesando", the Celery task is dispatched, and the dashboard updates in real-time.

### Implementation for User Story 2

- [ ] T010 [P] [US2] Add `retry_post(post_id, db)` async function in `app/dashboard/service.py` — verifies post is FAILED, verifies account is active, sets status to PROCESSING, sets `processing_started_at`, dispatches Celery task, publishes SSE event
- [ ] T011 [US2] Add `POST /dashboard/posts/{post_id}/retry` endpoint in `app/dashboard/routes.py` — calls `retry_post()`, returns 200 on success, 400/401/403/404 on errors per contract in `contracts/retry-api.md`
- [ ] T012 [P] [US2] Modify `renderPosts()` in `app/templates/dashboard/layout.html` — add "Reintentar" button next to posts with status "failed"
- [ ] T013 [US2] Add JavaScript retry handler in `app/templates/dashboard/layout.html` — POST to `/dashboard/posts/{id}/retry`, disable button during request, track consecutive failures, enforce 10-second cooldown after 3 failures

**Checkpoint**: Users can retry failed posts with a single click, using the original MinIO image

---

## Phase 5: User Story 3 - Token Health Detection and Account Deactivation (Priority: P3)

**Goal**: Enhance token error detection in the worker to catch explicit Graph API error codes (463, 467) and deactivate the associated Instagram account on token expiry.

**Independent Test**: Trigger a post with an expired/revoked Instagram token. Verify the account is marked "Inactiva", the post is marked "fallido", and subsequent post attempts are blocked.

### Implementation for User Story 3

- [ ] T014 [US3] Add `_is_token_error(error_msg)` helper function in `app/worker.py` — checks for error codes 463, 467, OAuthException patterns, and existing "token expired" string matching
- [ ] T015 [US3] Modify `_process_post_sync()` in `app/worker.py` — use `_is_token_error()` to detect token errors, call `deactivate_account_sync()` (from TASK-027) when token error detected, publish SSE account event
- [ ] T016 [US3] Modify `process_instagram_post()` in `app/worker.py` — use `_is_token_error()` in retry/failure paths to publish account deactivation SSE events when token error detected
- [ ] T017 [US3] Modify `instagram_callback()` in `app/auth/instagram.py` — verify existing `is_active=True` reactivation logic from TASK-027 is present and correct

**Checkpoint**: Token errors automatically deactivate accounts, preventing further post attempts

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Testing, validation, and edge case handling

- [ ] T018 [P] Add unit test for `_is_token_error()` in `tests/test_worker.py` — test error codes 463, 467, "token expired" string, and non-token errors
- [ ] T019 [P] Add unit test for `check_stalled_posts()` in `tests/test_beat_scheduler.py` — test 15-min processing timeout, 5-min retrying timeout, NULL fallback
- [ ] T020 [P] Add unit test for `retry_post()` in `tests/test_dashboard.py` — test happy path, inactive account, wrong state, unauthorized
- [ ] T021 Run `uv run pytest tests/ -v` to verify no regressions
- [ ] T022 Manual verification: follow `quickstart.md` test scenarios for all 3 user stories

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (migration must exist before code references the column)
- **User Story 1 (Phase 3)**: Depends on Phase 2 (status transitions must track `processing_started_at`)
- **User Story 2 (Phase 4)**: Depends on Phase 2 (retry sets `processing_started_at`)
- **User Story 3 (Phase 5)**: Depends on Phase 2 (token error handling uses existing status transition logic)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) — Independent of US1 and US3
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) — Independent of US1 and US2 (builds on TASK-027's existing token detection)

### Within Each User Story

- Models/services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- T002, T003, T004, T005 can run in parallel (different code paths, same file but different functions)
- T010 and T012 can run in parallel (service layer + frontend template)
- T018, T019, T020 can run in parallel (different test files)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Add `processing_started_at` migration
2. Complete Phase 2: Set `processing_started_at` on all status transitions
3. Complete Phase 3: Add `check_stalled_posts` Beat task
4. **STOP and VALIDATE**: Manually set a post to "procesando" with old timestamp, verify it transitions to "fallido"

### Incremental Delivery

1. Phase 1 + Phase 2 → `processing_started_at` tracking in place
2. Phase 3 → Stalled posts auto-fail with SSE notification
3. Phase 4 → Users can retry failed posts
4. Phase 5 → Token errors auto-deactivate accounts
5. Phase 6 → Tests and validation

### Parallel Team Strategy

With multiple developers:

1. Team completes Phase 1 + Phase 2 together
2. Once Foundational is done:
   - Developer A: User Story 1 (stalled detection)
   - Developer B: User Story 2 (retry endpoint + UI)
   - Developer C: User Story 3 (token error codes)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- TASK-027 already implemented `deactivate_account_sync()` and `_publish_account_event()` — reuse these in T015/T016
