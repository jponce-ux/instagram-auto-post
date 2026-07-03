---
ticket: fix-asyncio-scope-and-token-error
phase: tasks
model: qwen3.6-plus
generated: 2026-07-03
status: draft
---

# Tasks: Fix asyncio scope error and 401 token error detection

## Task 1: Remove redundant `import asyncio` in `_process_post_sync`

- **File**: `app/worker.py`
- **Line**: 473
- **Deliverable**: Remove the `import asyncio` line inside the cache invalidation try block
- **Acceptance check**: The module-level `import asyncio` at line 1 is the only import; `_run_with_timeout` can reference `asyncio` without scope error
- **Size**: S

## Task 2: Add 401/unauthorized detection to `_is_token_error()`

- **File**: `app/worker.py`
- **Lines**: 58-88
- **Deliverable**: Add checks for `"401"` and `"unauthorized"` (case-insensitive) in the `_is_token_error()` function
- **Acceptance check**: `_is_token_error("Client error '401 Unauthorized' for url '...'")` returns `True`; `_is_token_error("Rate limit exceeded")` returns `False`
- **Size**: S

## Task 3: Verify `get_container_status` error message includes status code

- **File**: `app/services/instagram.py`
- **Lines**: 103-122
- **Deliverable**: Confirm that `response.raise_for_status()` on a 401 produces an error message containing "401" (it does — httpx includes the status code in the exception message). No code change needed if confirmed.
- **Acceptance check**: The httpx `HTTPStatusError` message format includes the status code (e.g., `"Client error '401 Unauthorized'"`)
- **Size**: S

## Task 4: Run existing tests to verify no regressions

- **File**: `tests/test_webhooks.py`, `tests/test_beat_scheduler.py`
- **Deliverable**: All existing tests pass after the changes
- **Acceptance check**: `uv run pytest tests/ -v` passes
- **Size**: M
