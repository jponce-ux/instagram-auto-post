# Proposal: Fix pytest-asyncio warnings

## Problem
Running `uv run pytest tests/ -v` produces **58 warnings** of the form:

```
PytestWarning: The test <Function test_*> is marked with '@pytest.mark.asyncio'
but it is not an async function.
```

This happens across 3 test files:
- `tests/test_beat_scheduler.py` — 12 warnings
- `tests/test_dashboard.py` — 14 warnings
- `tests/test_webhooks.py` — 32 warnings

## Root Cause
`pyproject.toml` has `asyncio_mode = "auto"`, which auto-marks **every** test function as async, even sync ones. The project has **zero** `async def test_*` functions — all tests are synchronous.

## Solution
Change `asyncio_mode` from `"auto"` to `"strict"` in `pyproject.toml`. In strict mode, only tests explicitly decorated with `@pytest.mark.asyncio` are treated as async. Since no tests need async, zero warnings will be produced.

## Impact
- **pyproject.toml**: One line change
- **Tests**: No functional changes, all 78+ tests continue to pass
- **Warnings**: 58 → 0

## Dependencies
- None
