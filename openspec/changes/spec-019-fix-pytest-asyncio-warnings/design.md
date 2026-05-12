# Design: Fix pytest-asyncio warnings

## Root Cause Analysis

`pyproject.toml` line 35:
```toml
asyncio_mode = "auto"
```

The `"auto"` mode tells pytest-asyncio to automatically mark **every** test function as async, regardless of whether it's actually async. This produces a warning for each sync test function.

The project has **zero** `async def test_*` functions. All tests are synchronous using `TestClient`, mocks, and direct function calls.

## Solution

Change to `"strict"` mode:
```toml
asyncio_mode = "strict"
```

In strict mode, only tests explicitly decorated with `@pytest.mark.asyncio` are treated as async. Since no tests in the project need async behavior, no tests will be affected and all warnings disappear.

## Why not remove the asyncio plugin entirely?

The plugin is still useful for future async tests. Keeping it with `strict` mode:
- Allows explicit async tests when needed
- Doesn't produce false warnings
- Is the recommended default by pytest-asyncio maintainers

## Risk Assessment
- **Risk**: None. This is a configuration-only change with no code impact.
- **Rollback**: Change back to `"auto"` — instant revert.
