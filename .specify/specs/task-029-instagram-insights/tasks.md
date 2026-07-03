---
ticket: TASK-029
phase: tasks
model: qwen3.6-plus
generated: 2026-06-30
status: draft
---

# Tasks: Instagram Graph API Insights Integration

**Input**: Design documents from `.specify/specs/task-029-instagram-insights/`
**Prerequisites**: plan.md (required), spec.md (required)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)

## Phase 1: Setup (Redis & HTTP Client)

**Purpose**: Prepare existing Redis connection and HTTP client for insights API calls

- [x] T001 [P] Add `httpx` to project dependencies in `pyproject.toml` (if not already present) for async Instagram Graph API calls

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create `InstagramMetricsService` with Redis caching, error handling, and API client

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 [P] Create `app/services/metrics.py` — define `InstagramMetricsService` class with `__init__` accepting Redis client and base API URL
- [x] T003 [P] Add `_get_cached(key)` and `_set_cache(key, data, ttl=3600)` helper methods in `app/services/metrics.py` using existing Redis connection
- [x] T004 [P] Add `_call_insights_api(endpoint, params)` async method in `app/services/metrics.py` using `httpx.AsyncClient` with error handling for HTTP errors, timeouts, and token errors
- [x] T005 Add `_handle_token_error(account_id)` method in `app/services/metrics.py` — calls `deactivate_account_sync()` (from TASK-028), deletes all cache keys for the account, logs the error

**Checkpoint**: `InstagramMetricsService` is ready with caching, API client, and token error handling

---

## Phase 3: User Story 1 - View Account-Level Analytics (Priority: P1) 🎯 MVP

**Goal**: Fetch and display account-level insights (impressions, reach, profile_views, follower_count) with 1-hour Redis caching and cache invalidation on post publish.

**Independent Test**: Log in to dashboard, view analytics section. Verify metrics display correctly. Check Redis for cache keys. Publish a new post and verify cache is invalidated.

### Implementation for User Story 1

- [x] T006 [US1] Add `get_account_analytics(account_id, period="days_28")` method in `app/services/metrics.py` — checks cache, calls API if expired, parses response into `{impressions, reach, profile_views, follower_count}`, handles token errors via `_handle_token_error()`
- [x] T007 [US1] Add `GET /dashboard/analytics/account` endpoint in `app/dashboard/routes.py` — authenticates user, gets active Instagram account, calls `get_account_analytics()`, returns JSON per `contracts/insights-api.md`
- [x] T008 [US1] Add cache invalidation call in `app/worker.py` — when post transitions to PUBLISHED, delete `insights:account:{account_id}:*` keys from Redis
- [ ] T009 [P] [US1] Add analytics section to `app/templates/dashboard/layout.html` — displays metrics cards with loading spinner + skeleton placeholders, "Refreshing..." indicator for stale cache, and "Retry" button on failure

**Checkpoint**: Account-level analytics are visible on dashboard with caching, loading states, and cache invalidation on publish

---

## Phase 4: User Story 2 - View Media-Level Analytics On-Demand (Priority: P2)

**Goal**: Fetch and display media-level insights (engagement, impressions, reach, saved, likes, comments) when user clicks on a specific post. On-demand with 1-hour caching per media item.

**Independent Test**: View post history, click on a published post. Verify media metrics display. Click on a pending post — verify "metrics not yet available" message.

### Implementation for User Story 2

- [x] T010 [US2] Add `get_media_analytics(media_id)` method in `app/services/metrics.py` — checks cache, calls API if expired, parses response into `{engagement, impressions, reach, saved, likes, comments}`, handles 404 for deleted media
- [x] T011 [US2] Add `GET /dashboard/analytics/media/{post_id}` endpoint in `app/dashboard/routes.py` — verifies post ownership and published status, calls `get_media_analytics()`, returns JSON per `contracts/insights-api.md`
- [ ] T012 [P] [US2] Add click handler in `app/templates/dashboard/layout.html` — when user clicks a post row, fetches `/dashboard/analytics/media/{post_id}`, displays metrics in a modal or expanded row with loading state

**Checkpoint**: Media-level analytics are available on-demand with caching and proper error handling for unpublished posts

---

## Phase 5: User Story 3 - Token Error Handling and Account Deactivation (Priority: P3)

**Goal**: Automatically deactivate accounts and clear cache when Instagram API returns token errors during any insights fetch. Prevent further API calls for inactive accounts.

**Independent Test**: Revoke Instagram token. View analytics. Verify account marked "Inactiva", cache cleared, and no further API calls made.

### Implementation for User Story 3

- [x] T013 [US3] Integrate `_is_token_error()` from TASK-028 into `_call_insights_api()` in `app/services/metrics.py` — detect OAuthException, codes 463/467, "token expired" patterns
- [x] T014 [US3] Add account active check in `GET /dashboard/analytics/account` and `GET /dashboard/analytics/media/{post_id}` endpoints — return 403 with reconnect prompt if `is_active=False`
- [x] T015 [US3] Add cache cleanup in `_handle_token_error()` — delete all `insights:account:{account_id}:*` and `insights:media:*` keys for the affected account

**Checkpoint**: Token errors automatically deactivate accounts, clear cache, and block further API calls

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Logging, edge case handling, testing, and validation

- [x] T016 [P] Add logging in `app/services/metrics.py` — log all API calls (success, failure, cache hit, cache miss) with account ID, metric type, response time, and error details (FR-014)
- [x] T017 [P] Add concurrent request deduplication in `app/services/metrics.py` — if multiple requests for same media_id arrive simultaneously, reuse in-flight request instead of duplicate API calls
- [x] T018 [P] Add unit test for `InstagramMetricsService.get_account_analytics()` in `tests/test_metrics.py` — test cache hit, cache miss, token error, API failure
- [x] T019 [P] Add unit test for `InstagramMetricsService.get_media_analytics()` in `tests/test_metrics.py` — test cache hit, cache miss, 404 handling, partial metrics
- [ ] T020 Run `uv run pytest tests/ -v` to verify no regressions
- [ ] T021 Manual verification: follow `quickstart.md` test scenarios for all 3 user stories

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (httpx dependency) — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 (InstagramMetricsService base)
- **User Story 2 (Phase 4)**: Depends on Phase 2 (InstagramMetricsService base)
- **User Story 3 (Phase 5)**: Depends on Phase 2 (token error handling in service)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) — Independent of US1 and US3
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) — Independent of US1 and US2 (builds on TASK-028's token detection)

### Within Each User Story

- Service methods before endpoints
- Endpoints before UI integration
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- T002, T003, T004 can run in parallel (different methods in same file, no dependencies)
- T009 and T012 can run in parallel (different UI sections)
- T018, T019 can run in parallel (different test files)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Add httpx dependency
2. Complete Phase 2: Create InstagramMetricsService with caching and API client
3. Complete Phase 3: Add account analytics endpoint and UI section
4. **STOP and VALIDATE**: Log in, view analytics, verify metrics display and cache works

### Incremental Delivery

1. Phase 1 + Phase 2 → Service foundation ready
2. Phase 3 → Account-level analytics visible on dashboard
3. Phase 4 → Media-level analytics available on-demand
4. Phase 5 → Token error handling and account deactivation
5. Phase 6 → Logging, tests, and validation

### Parallel Team Strategy

With multiple developers:

1. Team completes Phase 1 + Phase 2 together
2. Once Foundational is done:
   - Developer A: User Story 1 (account analytics + UI)
   - Developer B: User Story 2 (media analytics + UI)
   - Developer C: User Story 3 (token error handling)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- TASK-028 already implemented `deactivate_account_sync()` and `_is_token_error()` — reuse these in T005, T013, T015
- Redis connection is already available via `app/services/sse.py` — reuse or create a shared Redis client in `app/core/redis.py`
