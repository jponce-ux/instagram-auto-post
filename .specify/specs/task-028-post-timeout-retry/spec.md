---
ticket: TASK-028
phase: spec
model: qwen3.6-plus
generated: 2026-06-19
status: completed
---

# Feature Specification: Stalled Post Timeout, Retry, and Token Health Check

**Feature Branch**: `028-post-timeout-retry`  
**Created**: 2026-06-19  
**Status**: Draft  
**Input**: User description: "Resolve the issue of stuck posts remaining indefinitely in the 'procesando' state. Implement a 15-minute maximum processing timeout, dynamic row fallback to 'fallido', an asynchronous retry mechanism utilizing high-quality MinIO assets, and automated Instagram Graph API token health verification."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Stalled Post Detection and Failure (Priority: P1)

When a post remains in the "procesando" state for more than 15 minutes, the system automatically marks it as "fallido" and notifies the user via real-time dashboard update. This prevents posts from being stuck indefinitely with no feedback.

**Why this priority**: Without this, posts can remain in "procesando" forever, giving users false hope and no actionable path forward. This is the foundational safety net for the entire publishing pipeline.

**Independent Test**: Create a post, manually set its status to "procesando" and its created_at to 16 minutes ago. Within 60 seconds, verify the post status transitions to "fallido" and the dashboard reflects the change without a page refresh.

**Acceptance Scenarios**:

1. **Given** a post has been in "procesando" state for more than 15 minutes, **When** the periodic check runs, **Then** the post status is updated to "fallido" with an error message "Processing timeout exceeded".
2. **Given** a post transitions to "fallido" due to timeout, **When** the user has the dashboard open, **Then** the post row updates in real-time via SSE without requiring a page refresh.
3. **Given** a post has been in "procesando" state for less than 15 minutes, **When** the periodic check runs, **Then** the post status remains unchanged.
4. **Given** a post has been in "reintentando" state for more than 5 minutes, **When** the periodic check runs, **Then** the post status is updated to "fallido" with an error message "Retry timeout exceeded".

---

### User Story 2 - Retry Failed Posts (Priority: P2)

When a post is in "fallido" state, the user can click a "Reintentar" button to retry the publication. The system re-dispatches the post using the original high-quality image from storage and the original caption.

**Why this priority**: Users need a way to recover from failed publications without re-uploading the image. This provides a direct path to resolution for transient failures.

**Independent Test**: View a failed post in the dashboard. Click "Reintentar". Verify the post status changes to "procesando", the Celery task is dispatched, and the original image is used (not a cached thumbnail).

**Acceptance Scenarios**:

1. **Given** a post is in "fallido" state, **When** the user clicks "Reintentar", **Then** the post status changes to "procesando" and a new Celery task is dispatched.
2. **Given** the user retries a failed post, **When** the worker processes the retry, **Then** the original high-quality image from MinIO is used, not a cached or thumbnail version.
3. **Given** the user retries a post, **When** the retry succeeds, **Then** the post status transitions to "publicado" and the dashboard updates in real-time.
4. **Given** the user retries a post, **When** the retry fails again, **Then** the post returns to "fallido" state with an updated error message.
5. **Given** the user clicks "Reintentar", **When** the request is in-flight, **Then** the button is immediately disabled until the backend responds with success or failure.
6. **Given** a post has failed 3 consecutive retry attempts, **When** the endpoint responds with failure, **Then** the "Reintentar" button remains disabled for an additional 10 seconds before becoming clickable again.

---

### User Story 3 - Token Health Detection and Account Deactivation (Priority: P3)

When the Instagram Graph API returns a token-related error during post processing or retry, the system automatically deactivates the associated Instagram account and prevents further post attempts until the user reconnects.

**Why this priority**: Prevents repeated failures from expired tokens and provides a clear signal to the user that re-authentication is needed. Builds on TASK-027's token expiry detection with explicit Graph API error code handling.

**Independent Test**: Trigger a post with an Instagram account that has an expired/revoked token. Verify the account is marked "Inactiva", the post is marked "fallido", and subsequent post attempts are blocked with a clear error message.

**Acceptance Scenarios**:

1. **Given** the Instagram Graph API returns an OAuth exception (error codes 463, 467, or similar token-invalidated codes), **When** the worker processes the error, **Then** the associated Instagram account is marked "Inactiva" and the post is marked "fallido".
2. **Given** an Instagram account is "Inactiva", **When** the user attempts to create a new post, **Then** the system returns a 400 error with message "Instagram account is inactive. Please reconnect your account."
3. **Given** the Graph API returns a non-token error (network timeout, rate limit), **When** the worker processes the error, **Then** the post is marked "fallido" but the account remains "Activa".

---

### Edge Cases

- **What happens if the user retries a post whose associated Instagram account is now inactive?** The retry endpoint returns a 400 error with message "Instagram account is inactive. Please reconnect your account."
- **What happens if the original image file is missing from MinIO when retrying?** The post transitions to "fallido" with error message "Original image file not found. Please create a new post."
- **What happens if multiple posts are stalled simultaneously?** All stalled posts are detected and marked "fallido" in a single periodic check cycle.
- **What happens if the user retries a post while another retry for the same post is still processing?** The retry endpoint returns a 400 error with message "Post is already being processed."
- **What happens if the token expires between the retry dispatch and the actual API call?** The worker detects the token error, deactivates the account, and marks the post "fallido" (same as User Story 3).
- **What happens after 3 consecutive retry failures?** The "Reintentar" button enters a 10-second cooldown period after the failure response, during which it remains disabled. After cooldown, the user can retry again (no limit on total attempts).
- **What happens if `processing_started_at` is null for a post in "procesando" state?** The periodic check treats it as if processing started at `created_at` (safe fallback for posts created before the migration).
- **What happens if a post is stuck in "reintentando" state for more than 5 minutes?** The periodic check transitions it to "fallido" with error message "Retry timeout exceeded". This protects against crashed workers mid-retry.

## Clarifications

### Session 2026-06-19

- Q: Should there be a maximum number of retry attempts per post, or allow unlimited retries? → A: Unlimited retries. Button becomes disabled immediately after clicking until backend responds. After 3 consecutive failures, button remains disabled for 10 extra seconds after endpoint responds.
- Q: Should the 15-minute timeout be measured from when the post was created, or from when it entered "procesando" state? → A: Measure from when post entered "procesando" state — 15 minutes of actual processing time.
- Q: Should the system add a new `processing_started_at` column or use `updated_at` for timeout calculation? → A: Add `processing_started_at` column — set when status transitions to "procesando", cleared on completion/failure.
- Q: Should the stalled post timeout check also apply to posts in "reintentando" state? → A: Yes — apply a shorter 5-minute timeout to "reintentando" state since retries should complete faster.

### Functional Requirements

- **FR-001**: The system MUST automatically detect any post in "procesando" state that has been in that state for more than 15 minutes and transition it to "fallido" status.
- **FR-001a**: The system MUST automatically detect any post in "reintentando" state that has been in that state for more than 5 minutes and transition it to "fallido" status.
- **FR-002**: A periodic background task MUST run every 60 seconds to scan for stalled posts and update their status.
- **FR-002a**: When a post transitions to "procesando" or "reintentando" state, the system MUST set `processing_started_at` to the current timestamp. When the post transitions to any terminal state (published, failed), the field MUST be cleared.
- **FR-003**: When a post transitions to "fallido" (whether by timeout or processing failure), an SSE event MUST be published so the dashboard updates in real-time.
- **FR-004**: Posts in "fallido" state MUST display a "Reintentar" button in the dashboard history table.
- **FR-005**: Clicking "Reintentar" MUST trigger an asynchronous retry that re-dispatches the post to the Celery worker using the original image from MinIO and the original caption from the database.
- **FR-006**: The retry endpoint MUST verify that the authenticated user owns the post before allowing the retry.
- **FR-007**: The retry endpoint MUST verify that the post is in "fallido" state before allowing the retry.
- **FR-008**: The retry endpoint MUST verify that the associated Instagram account is "Activa" before dispatching the retry task.
- **FR-009**: When the Instagram Graph API returns an OAuth/token-related error (error codes 463, 467, or equivalent), the system MUST deactivate the associated Instagram account (set `is_active=False`).
- **FR-010**: When the Instagram Graph API returns a non-token error (network timeout, rate limit, server error), the system MUST mark the post as "fallido" WITHOUT deactivating the account.
- **FR-011**: The post creation endpoint MUST reject new posts if the user's Instagram account is "Inactiva", returning a 400 error with a user-friendly message.
- **FR-012**: All UI state labels MUST remain in Spanish ("procesando", "fallido", "publicado", "reintentando", "pendiente").
- **FR-013**: The "Reintentar" button MUST become disabled immediately upon click and remain disabled until the backend responds. After 3 consecutive retry failures, the button MUST remain disabled for an additional 10 seconds after the failure response before becoming clickable again.

### Key Entities

- **Post**: Has `status` field (enum: pending, processing, retrying, published, failed), `created_at`, `processing_started_at` (new — set when status transitions to "procesando" or "reintentando", cleared on completion/failure), `error_message`, `ig_account_id`, `media_file_id`, `caption`. The `status` field maps to Spanish labels in the UI.
- **InstagramAccount**: Has `is_active` field (Boolean). When `False`, the account is shown as "Inactiva" and cannot be used for posting.
- **MediaFile**: Has `key` field pointing to the original file in MinIO private bucket. Used for retry asset recovery.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: No post remains in "procesando" state for longer than 16 minutes of actual processing time (15-minute threshold + 60-second check interval).
- **SC-001a**: No post remains in "reintentando" state for longer than 6 minutes (5-minute threshold + 60-second check interval).
- **SC-002**: Stalled post status transitions are reflected in the dashboard within 5 seconds via SSE (or on next page load if SSE is disconnected).
- **SC-003**: Retried posts use the original high-quality image from MinIO, verified by comparing file size/hash against the original upload.
- **SC-004**: Token-related errors result in account deactivation within 10 seconds of the failed API call, preventing further post attempts.
- **SC-005**: Users can successfully retry a failed post with a single click, and the retry completes within the same time bounds as a fresh post submission.

## Assumptions

- The existing Celery Beat infrastructure is already configured and running (established in prior specs).
- The `Post.status` enum already includes all necessary states (pending, processing, retrying, published, failed).
- The original image file remains available in the MinIO private bucket for the lifetime of the post record.
- The Instagram Graph API error codes 463 and 467 are the primary indicators of token expiry/invalidation; other OAuthException sub-codes may also indicate token issues.
- The SSE infrastructure (Redis pub/sub) is already in place and functional (established in TASK-027).
- The `InstagramAccount.is_active` column already exists in the database (added in TASK-027).
- The retry mechanism reuses the existing `_process_post_sync()` logic in the worker, with the same image upload and container creation flow.
- A database migration is required to add the `processing_started_at` column to the Post table.
