---
ticket: fix-asyncio-scope-and-token-error
phase: tasks
model: qwen3.6-plus
generated: 2026-07-03
status: completed
progress: 4/4 tasks completed (already implemented)
---

# Tasks: Fix asyncio scope error and 401 token error detection

## Task 1: Remove redundant `import asyncio` in `_process_post_sync` ✅ Already fixed

- **File**: `app/worker.py`
- **Status**: The redundant `import asyncio` inside the cache invalidation block at line ~473 has **already been removed**. Only the module-level `import asyncio` at line 1 exists.
- **Verification**: AST scan confirms no `import asyncio` inside `_process_post_sync`. The `_run_with_timeout` function correctly references the module-level `asyncio`.
- **Size**: S

## Task 2: Add 401/unauthorized detection to `_is_token_error()` ✅ Already fixed

- **File**: `app/worker.py`
- **Lines**: 77-79
- **Status**: `_is_token_error()` **already contains** checks for `"401"` and `"unauthorized"`:
  ```python
  if "401" in error_msg or "unauthorized" in msg_lower:
      return True
  ```
- **Verification**: `_is_token_error("Client error '401 Unauthorized' for url '...'")` returns `True`; `_is_token_error("Rate limit exceeded")` returns `False`
- **Size**: S

## Task 3: Verify `get_container_status` error message includes status code ✅ Already correct

- **File**: `app/services/instagram.py`
- **Lines**: 121
- **Status**: `get_container_status` uses `response.raise_for_status()` which includes the HTTP status code in the exception message. Additionally, `create_media_container` and `publish_media_container` both build error messages with the status code from the Instagram API response.
- **Verification**: All three endpoints produce error messages containing "401" when a token error occurs.
- **Size**: S

## Task 4: Run existing tests to verify no regressions ✅

- **Status**: `uv run pytest tests/ -v` — **149/149 passed, 0 failures**
- **Size**: M
