---
ticket: TASK-027
phase: spec
model: qwen3.6-plus
generated: 2026-06-13
status: draft
---

# Feature Specification: Instagram Token Expiry Detection and Account Reconnection

**Feature Branch**: `027-token-expiry-reconnect`  
**Created**: 2026-06-13  
**Status**: Draft  
**Input**: User description: "When the post flow encounters a 'Token expired' error from the Instagram Graph API, the system must deactivate the user's Instagram account (set is_active=False), show the account as 'Inactiva' in the dashboard with a 'Reconnect' button, and allow the user to re-authenticate via the existing OAuth flow to get a new token."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Account Deactivation on Token Expiry (Priority: P1)

When the Celery worker detects a "Token expired" error while processing a post, it automatically marks the associated Instagram account as inactive in the database. The user sees their account status change to "Inactiva" on the dashboard without any manual intervention.

**Why this priority**: Without this, the user has no indication that their token expired and keeps trying to post, which will always fail. The system must proactively detect and flag the issue.

**Independent Test**: Trigger a post with an expired token. Verify the InstagramAccount.is_active is set to False in the database and the post status transitions to FAILED with a user-friendly error message.

**Acceptance Scenarios**:

1. **Given** a user has an Instagram account with an expired token, **When** the worker attempts to create a media container, **Then** the account's `is_active` is set to `False` and the post status becomes `FAILED` with message "Token expired - please reconnect your Instagram account".
2. **Given** a post fails due to token expiry, **When** the user views the dashboard, **Then** their account shows status "Inactiva" with a visible "Reconnect" button.
3. **Given** the worker detects a token expiry error, **When** the error is processed, **Then** an SSE event is published so the dashboard updates in real-time without requiring a page refresh.

---

### User Story 2 - Reconnect Button on Inactive Accounts (Priority: P2)

When an Instagram account is inactive (is_active=False), the dashboard displays a "Reconnect" button next to the account. Clicking this button initiates the existing Instagram OAuth flow to obtain a new token.

**Why this priority**: Users need a clear, actionable way to fix the expired token problem. The reconnect button provides a direct path to resolution.

**Independent Test**: View the dashboard with an inactive account. Verify the "Reconnect" button is visible. Click it and verify the Instagram OAuth flow starts.

**Acceptance Scenarios**:

1. **Given** a user has an inactive Instagram account, **When** the accounts section renders, **Then** the account shows "Inactiva" status with a "Reconectar" button next to it.
2. **Given** the user clicks the "Reconectar" button, **When** the button is activated, **Then** the browser redirects to the Instagram OAuth authorization page (same flow as initial connection).
3. **Given** the user completes the OAuth flow after reconnecting, **When** the callback processes, **Then** the account's `is_active` is set back to `True`, the token is updated, and the user is redirected to the dashboard with a success message.

---

### User Story 3 - Real-Time Status Update via SSE (Priority: P3)

When an account is deactivated due to token expiry, the dashboard receives an SSE event and updates the account status in real-time without requiring a page refresh.

**Why this priority**: Provides immediate feedback to users who have the dashboard open while a post is being processed.

**Independent Test**: Have the dashboard open with an active account. Trigger a post with an expired token. Verify the account status updates to "Inactiva" with a reconnect button appearing without page refresh.

**Acceptance Scenarios**:

1. **Given** the user has the dashboard open with SSE connected, **When** a post fails due to token expiry, **Then** the account status badge updates from "Activa" to "Inactiva" and the reconnect button appears.
2. **Given** the user reconnects their account, **When** the OAuth callback completes, **Then** the account status updates from "Inactiva" to "Activa" and the reconnect button is replaced with the active status badge.

---

### Edge Cases

- **What happens if the user has multiple Instagram accounts and only one token expires?** Only the affected account is deactivated; other accounts remain active and can still be used for posting.
- **What if the user tries to post while their account is inactive?** The post creation endpoint checks `is_active` before dispatching the Celery task and returns a 400 error with message "Instagram account is inactive. Please reconnect your account."
- **What if the OAuth callback fails during reconnection?** The account remains inactive and the user is redirected to the dashboard with an error message.
- **What if the user reconnects but the new token also expires quickly?** The same flow repeats — account is deactivated again, user can reconnect again.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When the worker detects a "Token expired" error in `_process_post_sync()`, it MUST set the associated InstagramAccount's `is_active` to `False` before marking the post as FAILED.
- **FR-002**: The dashboard accounts endpoint (`GET /dashboard/accounts`) MUST include the `is_active` field in the JSON response (already implemented).
- **FR-003**: The dashboard frontend (`renderAccounts()` in `layout.html`) MUST display a "Reconectar" button next to accounts where `is_active` is `False`.
- **FR-004**: Clicking the "Reconectar" button MUST redirect the user to `/auth/instagram/login` to start the OAuth flow.
- **FR-005**: The Instagram OAuth callback (`/auth/instagram/callback`) MUST set `is_active` to `True` when successfully updating an existing account's token.
- **FR-006**: The post creation endpoint (`POST /dashboard/post`) MUST check if the user's Instagram account is active before dispatching the Celery task, and return a 400 error if inactive.
- **FR-007**: An SSE event MUST be published when an account is deactivated due to token expiry, containing the account ID and new status.
- **FR-008**: The server-rendered accounts partial (`accounts_partial.html`) MUST also show the "Reconectar" button for inactive accounts.

### Key Entities

- **InstagramAccount**: Already has `is_active` column (Boolean, default true). No schema changes needed.
- **Post**: Already has `error_message` field. The token expiry error message will be stored here.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When a token expires, the account is marked inactive within 5 seconds of the failed API call.
- **SC-002**: Users can reconnect their account in under 30 seconds (OAuth flow completion time).
- **SC-003**: The dashboard reflects the inactive status within 2 seconds via SSE (or on next page load if SSE is disconnected).
- **SC-004**: Posts cannot be submitted while the account is inactive — the endpoint returns a 400 error immediately.

## Assumptions

- The existing Instagram OAuth flow (`/auth/instagram/login` → `/auth/instagram/callback`) works correctly and only needs to set `is_active=True` on successful reconnection.
- The `InstagramAccount.is_active` column already exists in the database (added in a previous migration).
- The SSE infrastructure is already in place and can be extended to publish account status events.
- The error message "Token expired - please reconnect your Instagram account" is already being generated in the worker (seen in the traceback).
