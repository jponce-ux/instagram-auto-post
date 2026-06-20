---
ticket: TASK-028
phase: plan
model: qwen3.6-plus
generated: 2026-06-19
status: draft
---

# Implementation Plan: Stalled Post Timeout, Retry, and Token Health Check

**Branch**: `028-post-timeout-retry` | **Date**: 2026-06-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `.specify/specs/task-028-post-timeout-retry/spec.md`

## Summary

Detect posts stuck in "procesando" (>15 min) or "reintentando" (>5 min) state via a periodic Celery Beat task, automatically transition them to "fallido", publish SSE events for real-time dashboard updates, add a retry endpoint that re-dispatches failed posts using the original MinIO image, and enhance token error detection with explicit Graph API error code handling (463, 467) to deactivate accounts on token expiry.

## Technical Context

**Language/Version**: Python 3.11, JavaScript (vanilla)
**Primary Dependencies**: FastAPI, Celery + Celery Beat, SQLAlchemy 2.0 (async + sync), Jinja2, SSE (Redis pub/sub)
**Storage**: PostgreSQL (Post table needs new `processing_started_at` column via Alembic migration)
**Testing**: pytest + pytest-asyncio
**Target Platform**: Linux server (Docker), modern web browsers
**Project Type**: Web application (FastAPI backend + Jinja2/JS frontend)
**Performance Goals**: Stalled post check completes within 5 seconds; SSE event delivery within 2 seconds
**Constraints**: Must use existing Celery Beat infrastructure; must reuse `_process_post_sync()` for retry; no new database migrations beyond `processing_started_at` column
**Scale/Scope**: Single-user dashboard, one or more Instagram accounts per user

## Constitution Check

The project constitution at `.specify/memory/constitution.md` is still in template form. No active governance gates. Proceeding with project conventions from `AGENTS.md`.

**Gate Status**: ✅ PASS — no constitution violations.

## Project Structure

### Documentation (this feature)

```text
specs/task-028-post-timeout-retry/
├── plan.md              # This file
├── spec.md              # Feature specification
├── data-model.md        # Phase 1 output
├── contracts/           # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code Changes

```text
app/
├── worker.py                    # MODIFY: add check_stalled_posts Beat task, set processing_started_at, enhance token error detection
├── dashboard/
│   ├── routes.py                # MODIFY: add POST /dashboard/posts/{id}/retry endpoint
│   └── service.py               # MODIFY: add retry_post() helper, set processing_started_at on status transitions
├── services/
│   └── instagram.py             # MODIFY: enhance token error detection with error codes 463, 467
├── models/
│   └── post.py                  # MODIFY: add processing_started_at column
└── templates/
    └── dashboard/
        └── layout.html          # MODIFY: add "Reintentar" button for failed posts, SSE account_update listener, retry cooldown logic

migrations/versions/
└── <new_migration>.py           # CREATE: add processing_started_at column to posts table
```

## Phase 0: Research

No research needed — all technical decisions follow established patterns from TASK-027 and existing codebase conventions.

Key decisions documented:
- **Timeout measurement**: Uses new `processing_started_at` column (not `created_at` or `updated_at`) for accurate per-state timing
- **Retry mechanism**: Reuses existing `_process_post_sync()` — no new worker logic needed, just re-dispatch
- **Token error detection**: String matching on error message for "token expired" (existing) + explicit error code checking for 463/467 (new)
- **SSE events**: Reuses existing `post_update` channel; stalled timeout publishes same event format as processing failure
- **Retry failure counter**: Client-side only (browser memory), reset on page refresh

## Phase 1: Design & Contracts

### data-model.md

```markdown
# Data Model: TASK-028 Changes

## Post Table — New Column

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `processing_started_at` | TIMESTAMP WITH TIME ZONE | Yes | NULL | Set when status transitions to "processing" or "retrying". Cleared when status transitions to "published" or "failed". Used for stalled post timeout calculation. |

### Migration Notes
- Column is nullable to support existing rows
- Fallback: if NULL and status is "processing"/"retrying", use `created_at` for timeout calculation
- No index needed — periodic check scans by status + timestamp comparison

## State Transitions

```
pending → processing (processing_started_at = NOW)
processing → published (processing_started_at = NULL)
processing → failed (processing_started_at = NULL)
processing → retrying (processing_started_at = NOW) [via Celery retry]
retrying → processing (processing_started_at = NOW) [via Celery retry attempt]
retrying → failed (processing_started_at = NULL)
failed → processing (processing_started_at = NOW) [via retry endpoint]
```

### Stalled Post Detection Logic

- **Processing timeout**: `status = 'processing' AND processing_started_at < NOW() - INTERVAL '15 minutes'`
- **Retrying timeout**: `status = 'retrying' AND processing_started_at < NOW() - INTERVAL '5 minutes'`
- **Fallback for NULL**: `status = 'processing' AND (processing_started_at IS NULL OR processing_started_at < NOW() - INTERVAL '15 minutes')`
```

### contracts/retry-api.md

```markdown
# Contract: Retry Post API

## POST /dashboard/posts/{post_id}/retry

Retries a failed post by re-dispatching it to the Celery worker.

### Authorization
- Requires authenticated user (JWT cookie)
- User must own the post
- Post's Instagram account must be linked to the user

### Request
- Path parameter: `post_id` (integer)
- No request body

### Success Response
- Status: 200
- Content-Type: application/json
```json
{
  "success": true,
  "post": {
    "id": 1,
    "status": "processing",
    "error_message": null
  }
}
```

### Error Responses

**400 — Post not in failed state**
```json
{
  "error": "Post is not in a failed state. Current status: processing"
}
```

**400 — Account inactive**
```json
{
  "error": "Instagram account is inactive. Please reconnect your account."
}
```

**400 — Post already processing**
```json
{
  "error": "Post is already being processed."
}
```

**401 — Unauthorized**
```json
{
  "error": "Unauthorized"
}
```

**403 — Post not owned by user**
```json
{
  "error": "Post not found"
}
```

**404 — Post not found**
```json
{
  "error": "Post not found"
}
```
```

### contracts/stalled-timeout-events.md

```markdown
# Contract: Stalled Post Timeout SSE Events

## Event Format (reuses existing post_update channel)

When a post transitions to "failed" due to stalled timeout:

```json
{
  "post_id": 1,
  "status": "failed",
  "user_id": 42,
  "error_message": "Processing timeout exceeded"
}
```

When a post transitions to "failed" due to retry timeout:

```json
{
  "post_id": 1,
  "status": "failed",
  "user_id": 42,
  "error_message": "Retry timeout exceeded"
}
```

Note: These use the same SSE channel (`post_update`) and event format as existing post status events. The dashboard's existing SSE handler already refreshes the post feed on any `post_update` event.
```

### quickstart.md

```markdown
# Quickstart: TASK-028 Testing

## Prerequisites
- Docker Compose stack running (api, worker, beat, redis, postgres, minio)
- User account with linked Instagram account

## Testing Stalled Post Timeout
1. Create a post via the dashboard
2. In the database, manually set the post status to 'processing' and `processing_started_at` to 16 minutes ago:
   ```sql
   UPDATE posts SET status = 'processing', processing_started_at = NOW() - INTERVAL '16 minutes' WHERE id = <post_id>;
   ```
3. Wait up to 60 seconds for the Beat task to run
4. Verify the post status transitions to 'failed' with error message "Processing timeout exceeded"
5. Verify the dashboard updates in real-time via SSE

## Testing Retry
1. Set a post status to 'failed' in the database
2. View the dashboard — the "Reintentar" button should appear next to the failed post
3. Click "Reintentar"
4. Verify the post status changes to 'processing'
5. Verify the Celery worker picks up the task
6. Verify the dashboard updates in real-time

## Testing Token Error Detection
1. Set the Instagram account's access_token to an expired/invalid token
2. Create a post
3. Verify the worker detects the token error, deactivates the account, and marks the post as 'failed'
4. Verify the dashboard shows the account as "Inactiva" with a "Reconectar" button
```

## Phase 2: Tasks

See tasks.md for the full task breakdown (created by `/speckit.tasks`).

## Complexity Tracking

No complexity beyond existing patterns. All changes follow established conventions from TASK-027 and the existing codebase.

| Change | Complexity | Justification |
|--------|------------|---------------|
| `processing_started_at` column | Low | Single nullable timestamp column, no index needed |
| `check_stalled_posts` Beat task | Low | Follows existing `check_scheduled_posts` pattern |
| Retry endpoint | Low | Thin wrapper around existing `create_post` flow |
| Token error code detection | Low | String matching on existing error messages |
