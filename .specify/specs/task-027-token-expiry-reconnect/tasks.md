---
ticket: TASK-027
phase: tasks
model: qwen3.6-plus
generated: 2026-06-13
status: draft
---

# Tasks: Instagram Token Expiry Detection and Account Reconnection

**Input**: Design documents from `.specify/specs/task-027-token-expiry-reconnect/`
**Prerequisites**: plan.md (required), spec.md (required)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)

## Phase 1: Foundational (Blocking Prerequisites)

**Purpose**: Add SSE channel constant for account updates

- [x] T001 [P] Add `ACCOUNT_UPDATE_CHANNEL = "account_update"` constant in `app/services/sse.py`

---

## Phase 2: User Story 1 - Automatic Account Deactivation on Token Expiry (Priority: P1) 🎯 MVP

**Goal**: When the worker detects a "Token expired" error, deactivate the Instagram account and publish an SSE event.

**Independent Test**: Trigger a post with an expired token. Verify the account is deactivated and the post fails with the correct error message.

### Implementation for User Story 1

- [x] T002 [US1] Add `deactivate_account(account_id)` function in `app/dashboard/service.py` — sets `is_active=False` and commits
- [x] T003 [US1] Modify `_process_post_sync()` in `app/worker.py` — when error message contains "Token expired", call `deactivate_account()` before raising the exception
- [x] T004 [US1] Add `_publish_account_event(account_id, is_active, reason)` function in `app/worker.py` — publishes SSE event via Redis
- [x] T005 [US1] Call `_publish_account_event()` in `process_instagram_post()` task wrapper when token expiry is detected (both on retry and final failure)

**Checkpoint**: Account is automatically deactivated when token expires, and an SSE event is published.

---

## Phase 3: User Story 2 - Reconnect Button on Inactive Accounts (Priority: P2)

**Goal**: Display a "Reconectar" button next to inactive accounts in the dashboard.

**Independent Test**: View the dashboard with an inactive account. Verify the reconnect button is visible and clickable.

### Implementation for User Story 2

- [x] T006 [P] [US2] Modify `renderAccounts()` in `app/templates/dashboard/layout.html` — show "Inactiva" badge with "Reconectar" button when `account.is_active` is false
- [x] T007 [P] [US2] Modify `app/templates/dashboard/accounts_partial.html` — show "Inactiva" badge with "Reconectar" button for server-rendered fallback
- [x] T008 [US2] Add `reconnect_account()` endpoint in `app/dashboard/routes.py` — POST handler that redirects to `/auth/instagram/login`
- [x] T009 [US2] Modify `instagram_callback()` in `app/auth/instagram.py` — set `is_active=True` when updating an existing account's token

**Checkpoint**: Inactive accounts show a reconnect button that triggers the OAuth flow.

---

## Phase 4: User Story 3 - Real-Time Status Update via SSE (Priority: P3)

**Goal**: Dashboard updates account status in real-time when SSE event is received.

**Independent Test**: Have dashboard open, trigger token expiry, verify account status updates without page refresh.

### Implementation for User Story 3

- [x] T010 [US3] Add SSE event listener in `app/templates/dashboard/layout.html` — listen for `account_update` events and update account status badge + reconnect button
- [x] T011 [US3] Modify `loadAccounts()` in `app/templates/dashboard/layout.html` — re-fetch accounts on SSE account_update event and re-render

**Checkpoint**: Dashboard reflects account status changes in real-time via SSE.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Edge case handling, validation, and testing

- [x] T012 [P] Add `is_active` check in `create_post_endpoint()` in `app/dashboard/routes.py` — return 400 error if account is inactive before dispatching task
- [x] T013 [P] Add `is_active` check in `create_post()` in `app/dashboard/service.py` — raise ValueError if no active accounts
- [x] T014 Run `uv run pytest tests/ -v` to verify no regressions
- [ ] T015 Manual verification: test full flow (expire token → deactivate → reconnect → reactivate)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 1)**: No dependencies — can start immediately
- **User Story 1 (Phase 2)**: Depends on Phase 1 (SSE channel constant)
- **User Story 2 (Phase 3)**: Independent of Phase 2 — can run in parallel
- **User Story 3 (Phase 4)**: Depends on Phase 1 (SSE channel) and Phase 2 (deactivation logic)
- **Polish (Phase 5)**: Depends on all user stories being complete

### Parallel Opportunities

- T006 and T007 can run in parallel (JS template + server template)
- T012 and T013 can run in parallel (route check + service check)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Add SSE channel constant
2. Complete Phase 2: Account deactivation on token expiry
3. **STOP and VALIDATE**: Trigger a post with expired token, verify account is deactivated

### Incremental Delivery

1. Phase 1 + Phase 2 → Account auto-deactivates on token expiry
2. Phase 3 → Reconnect button appears for inactive accounts
3. Phase 4 → Real-time status updates via SSE
4. Phase 5 → Edge case handling and validation
