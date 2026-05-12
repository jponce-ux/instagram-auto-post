# Tasks: Fix pytest-asyncio warnings

## Phase 1: Fix

- [x] **T001** Change `asyncio_mode` from `"auto"` to `"strict"` in `pyproject.toml`
  - File: `pyproject.toml` (line 35)
  - Deliverable: One-line config change
  - Acceptance: `asyncio_mode = "strict"`
  - Size: XS

## Phase 2: Verify

- [x] **T002** Run full test suite and verify zero asyncio warnings
  - Command: `uv run pytest tests/ -v`
  - Deliverable: All tests pass, 0 PytestWarning about asyncio
  - Acceptance: `78 passed, 0 asyncio warnings`
  - Size: XS

## Phase 3: Cleanup (discovered during implementation)

- [x] **T003** Remove `pytestmark = pytest.mark.asyncio` from `tests/test_dashboard.py`
  - File: `tests/test_dashboard.py` (line 406)
  - Deliverable: Module-level async mark removed
  - Acceptance: No more blanket async marking
  - Size: XS

- [x] **T004** Remove `pytestmark = pytest.mark.asyncio` from `tests/test_beat_scheduler.py`
  - File: `tests/test_beat_scheduler.py` (line 374)
  - Deliverable: Module-level async mark removed
  - Acceptance: No more blanket async marking
  - Size: XS

- [x] **T005** Remove `pytestmark = pytest.mark.asyncio` from `tests/test_webhooks.py`
  - File: `tests/test_webhooks.py` (line 654)
  - Deliverable: Module-level async mark removed
  - Acceptance: No more blanket async marking
  - Size: XS

## Dependencies
- T002 depends on T001
