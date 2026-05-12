# Spec: Fix pytest-asyncio warnings

## Requirements

### Requirement 1: Zero asyncio warnings
**Priority:** P0  
**Description:** Running `uv run pytest tests/ -v` SHALL produce zero `PytestWarning` messages about `@pytest.mark.asyncio` on non-async functions.

#### Scenario 1.1: Full test suite runs clean
**Given** the test suite is executed with `uv run pytest tests/ -v`  
**When** the output is analyzed for warnings  
**Then** no `PytestWarning` about asyncio marks appears

#### Scenario 1.2: All tests still pass
**Given** the asyncio_mode is changed to strict  
**When** `uv run pytest tests/ -v` is run  
**Then** all existing tests pass (78+)

### Requirement 2: No functional changes to tests
**Priority:** P0  
**Description:** The change SHALL NOT alter test behavior, assertions, or outcomes.

#### Scenario 2.1: Sync tests behave identically
**Given** a sync test function (e.g., `def test_valid_signature_passes_validation`)  
**When** the test runs before and after the change  
**Then** the result (pass/fail) and assertions are identical

## Non-Goals
- Converting sync tests to async
- Adding new tests
- Changing test logic or assertions

## Success Metrics
- 58 warnings → 0 warnings
- 78+ tests still passing
- 1 line changed in `pyproject.toml`
