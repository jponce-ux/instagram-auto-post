---
ticket: fix-asyncio-scope-and-token-error
phase: spec
model: qwen3.6-plus
generated: 2026-07-03
status: completed
---

# Spec: Fix asyncio scope error and 401 token error detection

## Problem Statement

Two bugs prevent successful Instagram post publishing:

1. **`asyncio` free variable error**: When posting an image, the Celery worker crashes with `"cannot access free variable 'asyncio' where it is not associated with a value in enclosing scope"`. This is caused by a redundant `import asyncio` inside `_process_post_sync` (worker.py line 473) that shadows the module-level import, breaking the closure of the nested `_run_with_timeout` function.

2. **401 errors not detected as token errors**: When the Instagram API returns a 401 (expired/invalid token), the `_is_token_error()` function does not recognize it. The account's `is_active` flag is never set to `False`, so the dashboard shows the account as active and retries keep failing with the same dead token.

## User Stories

### US-1: Post an image without asyncio scope error
- **Given** a user has a connected Instagram account with a valid token
- **When** the user creates a new post with an image
- **Then** the Celery worker processes the post without crashing on the asyncio scope error
- **And** the image is successfully published to Instagram

### US-2: Account deactivated on 401 token error
- **Given** a user has a connected Instagram account with an expired/revoked token
- **When** the Celery worker attempts to publish a post and receives a 401 from the Instagram API
- **Then** the `_is_token_error()` function detects the 401 as a token error
- **And** the account's `is_active` flag is set to `False` in the database
- **And** an SSE account event is published notifying the dashboard
- **And** the user sees the account as "Inactiva" in the dashboard

## Acceptance Criteria

### AC-1: asyncio scope error eliminated
- The redundant `import asyncio` inside `_process_post_sync` is removed
- The module-level `import asyncio` (line 1) is the sole import
- `_run_with_timeout` correctly references the module-level `asyncio`
- Posts can be created and processed without the free variable error

### AC-2: 401 detected as token error
- `_is_token_error()` returns `True` when the error message contains `"401"` or `"unauthorized"` (case-insensitive)
- When `get_container_status` receives a 401, the error message includes the status code
- When `create_media_container` or `publish_media_container` receive a 401, the error message includes the status code
- The account is deactivated via `deactivate_account_sync()` on any 401 during post processing

### AC-3: All Instagram API endpoints handle 401 consistently
- `create_media_container`, `get_container_status`, and `publish_media_container` all produce error messages that include the HTTP status code when the response is not 200
- The `_is_token_error()` function catches all three endpoints' 401 errors

## Non-Goals

- Do not change the overall post processing flow
- Do not change the retry logic (3 retries with exponential backoff)
- Do not change the SSE event publishing mechanism
- Do not add new API endpoints

## Success Metrics

- Posts can be created and published without the asyncio scope error
- Accounts with expired tokens are automatically deactivated within one retry cycle
- Dashboard correctly shows "Inactiva" for accounts with expired tokens

## Open Questions

- None — both issues are well-understood and have clear fixes.
