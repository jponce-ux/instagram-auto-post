---
ticket: fix-asyncio-scope-and-token-error
phase: plan
model: qwen3.6-plus
generated: 2026-07-03
status: completed
---

# Plan: Fix asyncio scope error and 401 token error detection

## Target Service

- `app/worker.py` — Celery worker with post processing logic
- `app/services/instagram.py` — Meta Graph API client

## Root Cause Analysis

### Bug 1: asyncio free variable error

In `app/worker.py`, the `_process_post_sync` function (line 329) defines a nested function `_run_with_timeout` (line 359) that references `asyncio`. Python's closure mechanism captures `asyncio` as a free variable from the enclosing scope.

However, at line 473, inside the same `_process_post_sync` function, there is a redundant `import asyncio`:

```python
try:
    import asyncio
    from app.services.metrics import metrics_service
    asyncio.run(metrics_service._delete_cache_pattern(...))
```

Python's scoping rules treat this as a **local variable assignment** for the entire function scope. When `_run_with_timeout` is called at lines 386-488 (before line 473 executes), the local `asyncio` has not been assigned yet, causing:

```
cannot access free variable 'asyncio' where it is not associated with a value in enclosing scope
```

**Fix**: Remove the redundant `import asyncio` at line 473. The module-level import at line 1 is sufficient.

### Bug 2: 401 errors not detected as token errors

The `_is_token_error()` function (line 58-88) checks for:
- Error codes 463, 467
- "oauthexception"
- "token expired"
- "invalid" + "token" combination

But it does **NOT** check for HTTP 401 / "Unauthorized".

When `get_container_status` (instagram.py line 113-122) receives a 401, it calls `response.raise_for_status()` which raises `httpx.HTTPStatusError` with a message like:
```
Client error '401 Unauthorized' for url 'https://graph.instagram.com/...'
```

This message does not match any pattern in `_is_token_error()`, so:
1. The account is NOT deactivated
2. The error message shown to the user is technical and unhelpful
3. Retries keep failing with the same dead token

**Fix**: Add `"401"` and `"unauthorized"` checks to `_is_token_error()`.

## Architecture Changes

None — both fixes are localized to existing functions.

## Data Model Changes

None.

## API Changes

None.

## Dependencies

None new.

## Security and Auth Implications

- The 401 detection fix improves security posture by ensuring expired tokens result in account deactivation, preventing repeated failed API calls with invalid credentials.

## Test Strategy

1. Unit test: `_is_token_error()` returns `True` for messages containing "401" and "unauthorized"
2. Unit test: `_is_token_error()` returns `False` for non-token errors (e.g., rate limit, network error)
3. Integration: Verify post processing works end-to-end after removing redundant import

## Rollout Plan

- Single commit with both fixes
- No migration needed
- No feature flag needed

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Removing `import asyncio` breaks the cache invalidation block | Low | Medium | The module-level import at line 1 covers all uses |
| Adding "401" check causes false positives | Low | Low | 401 is exclusively an auth error; no legitimate non-token error returns 401 |
| Other endpoints also need 401 handling | Medium | Medium | Verified: `create_media_container` and `publish_media_container` already include status code in error messages; `get_container_status` uses `raise_for_status()` which includes "401" in the message |
