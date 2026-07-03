---
ticket: TASK-030
phase: tasks
model: qwen3.6-plus
generated: 2026-07-03
status: draft
---

# Tasks: Global Account Analytics View Dashboard

**Input**: Design documents from `.specify/specs/task-030-analytics-dashboard/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/analytics-page.md

**Tests**: Not explicitly requested in the feature specification. Manual browser testing per quickstart.md.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Verify existing dependencies and infrastructure

- [ ] T001 Verify Chart.js CDN URL is accessible and compatible with project (`https://cdn.jsdelivr.net/npm/chart.js@4`)
- [ ] T002 Confirm TASK-029 `GET /dashboard/analytics/account` endpoint returns valid JSON with metrics data

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extend backend metrics service and JSON API to support trends + timeline data. ALL user stories depend on this phase.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T003 [P] Add `_fetch_account_time_series()` method to `app/services/metrics.py` — fetches daily time-series data from Instagram Graph API using `period=day` with `since`/`until` parameters for a given date range. Returns `{labels: [...], impressions: [...], reach: [...], profile_views: [...], follower_count: [...]}`.
- [ ] T004 [P] Add `_calculate_trends()` static method to `app/services/metrics.py` — takes current period metrics dict and previous period metrics dict, returns trends dict with percentage change per metric. Formula: `((current - previous) / previous) * 100`. Edge cases: previous=0 → trend=0, both=0 → trend=0.
- [ ] T005 Add `get_account_analytics_with_trend()` method to `app/services/metrics.py` — orchestrates fetching current period metrics, previous period metrics (shifted back by same duration), time-series data, and trend calculation. Caches result at `insights:account:{account_id}:{period}` with extended schema (metrics + trends + timeline). Falls back to cache on API error. Handles TokenError by deactivating account.
- [ ] T006 Update `GET /dashboard/analytics/account` in `app/dashboard/routes.py` to use `get_account_analytics_with_trend()` instead of `get_account_analytics()`, returning the extended JSON response with `trends` and `timeline` fields per contracts/analytics-page.md.

**Checkpoint**: Backend returns extended JSON with metrics, trends, and timeline data. Verify with: `curl http://localhost:8000/dashboard/analytics/account?period=days_28`

---

## Phase 3: User Story 1 — View Full-Page Analytics Dashboard (Priority: P1) 🎯 MVP

**Goal**: User navigates to a dedicated Analytics page and sees summary cards with metric values and an interactive timeline chart with historical data. Period selector (7d/28d) updates the view.

**Independent Test**: Log in, navigate to `/dashboard/analytics`, verify summary cards display correct values and a Chart.js line chart renders with historical data. Page loads within 3 seconds from cache.

### Implementation for User Story 1

- [ ] T007 [US1] Add `GET /dashboard/analytics` HTML route to `app/dashboard/routes.py` — authenticates user, checks for active Instagram account, renders `dashboard/analytics.html` template with initial period from query param (default `days_28`). Redirects to `/auth/login` if not authenticated.
- [ ] T008 [US1] Create `app/templates/dashboard/analytics.html` — Jinja2 template extending `base.html` with: page header (back to dashboard link + period selector buttons), summary cards container (4 cards: Reach, Impressions, Profile Views, Follower Growth), timeline chart container (`<canvas id="analytics-chart">`), Chart.js CDN `<script>` tag, skeleton loading placeholders, and inline `<script>` block for JavaScript logic.
- [ ] T009 [US1] Implement `fetchAnalytics(period)` JavaScript function in `app/templates/dashboard/analytics.html` — calls `GET /dashboard/analytics/account?period={period}`, handles 401/403/400/502 responses, updates summary cards with metric values, and stores response in a module-scoped variable for reuse.
- [ ] T010 [US1] Implement `renderSummaryCards(metrics)` JavaScript function in `app/templates/dashboard/analytics.html` — renders 4 metric cards in a responsive grid (`grid-cols-2 sm:grid-cols-4`) with metric labels, formatted values (using existing `formatNumber()`), and metric icons (reuse existing `getMetricIcon()` from layout.html).
- [ ] T011 [US1] Implement `renderTimelineChart(timelineData)` JavaScript function in `app/templates/dashboard/analytics.html` — initializes Chart.js line chart with datasets for impressions, reach, profile_views, and follower_count. Configures responsive sizing, tooltips, legend toggling, and x-axis date labels. Uses Tailwind-consistent colors (purple for impressions, blue for reach, green for profile views, pink for follower count).
- [ ] T012 [US1] Implement period selector JavaScript in `app/templates/dashboard/analytics.html` — two toggle buttons ("7 días" / "28 días") that call `fetchAnalytics()` with the selected period, update active button styling, and re-render cards + chart. Default selection: 28 days.
- [ ] T013 [US1] Implement skeleton loading state in `app/templates/dashboard/analytics.html` — shows `animate-pulse` gray placeholder cards and chart area while `fetchAnalytics()` is in progress. Hides skeletons and shows real data on success.
- [ ] T014 [US1] Add "Analíticas" navigation link to existing dashboard — add a link/button in `app/templates/dashboard/layout.html` (or appropriate nav location) that navigates to `/dashboard/analytics`. Style consistently with existing dashboard navigation.

**Checkpoint**: User can navigate to `/dashboard/analytics`, see 4 summary cards with metric values, see an interactive Chart.js timeline chart, switch between 7-day and 28-day periods, and see skeleton loading during fetch.

---

## Phase 4: User Story 2 — Interpret Metric Trends with Visual Indicators (Priority: P2)

**Goal**: Each summary card shows a trend indicator (percentage change vs. previous period) with color-coded visual feedback: green for positive, red for negative, gray for neutral.

**Independent Test**: View the Analytics page with data showing metric changes between periods. Verify each card displays a trend indicator with correct color coding.

### Implementation for User Story 2

- [ ] T015 [US2] Add `renderTrendIndicator(trendValue)` JavaScript function in `app/templates/dashboard/analytics.html` — returns HTML for trend indicator: green upward arrow + percentage if positive, red downward arrow + percentage if negative, gray dash if zero, "—" if null. Uses Tailwind classes: `text-green-600` for positive, `text-red-600` for negative, `text-gray-400` for neutral.
- [ ] T016 [US2] Update `renderSummaryCards(metrics, trends)` JavaScript function in `app/templates/dashboard/analytics.html` — accept `trends` dict as second parameter, call `renderTrendIndicator()` for each metric, and append trend indicator HTML below the metric value in each card.
- [ ] T017 [US2] Update `fetchAnalytics()` call in `app/templates/dashboard/analytics.html` to pass `response.trends` to `renderSummaryCards()` so trend indicators render alongside metric values.

**Checkpoint**: Each summary card displays a trend indicator with correct color coding. Positive trends show green ↑, negative show red ↓, zero shows gray —.

---

## Phase 5: User Story 3 — Handle Error and Edge States Gracefully (Priority: P3)

**Goal**: The Analytics page displays appropriate error messages with actionable guidance for all error scenarios: no connected account, inactive account, API failure, rate limit exceeded.

**Independent Test**: Simulate each error scenario (disconnect account, revoke token, block API). Verify clear error messages with actionable guidance are displayed.

### Implementation for User Story 3

- [ ] T018 [US3] Implement "no account connected" state in `app/templates/dashboard/analytics.html` — when `fetchAnalytics()` returns 400, render a centered message "No hay cuenta de Instagram conectada" with a "Conectar Cuenta" button linking to `/auth/instagram/login`. Style consistently with existing `renderAccountsNoAccounts()` from layout.html.
- [ ] T019 [US3] Implement "account inactive" state in `app/templates/dashboard/analytics.html` — when `fetchAnalytics()` returns 403, render a centered warning message "Cuenta inactiva. Por favor reconecta tu cuenta de Instagram" with a "Reconectar Cuenta" POST form to `/dashboard/accounts/reconnect`. Style with red warning icon.
- [ ] T020 [US3] Implement "API unavailable with stale cache" state in `app/templates/dashboard/analytics.html` — when `fetchAnalytics()` returns 502 and cached data exists, render the cached data with an amber "Datos almacenados (sin conexión)" indicator and a "Reintentar" button that clears cache and retries.
- [ ] T021 [US3] Implement "API unavailable, no cache" state in `app/templates/dashboard/analytics.html` — when `fetchAnalytics()` returns 502 and no cached data exists, render "Analíticas temporalmente no disponibles. Inténtalo más tarde." with a "Reintentar" button.
- [ ] T022 [US3] Implement debounced period selector — wrap period change handler in a 300ms debounce function so rapid clicks only trigger the final selection. Cancel in-flight fetch when a new period is selected.
- [ ] T023 [US3] Implement "no data available yet" state for zero-value metrics — when all timeline data points are zero for a metric, render the chart with a flat line at zero and display "Sin actividad registrada en este período" below the chart.

**Checkpoint**: All error states display clear, actionable messages. Rapid period switching is debounced. Zero-value charts render gracefully.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T024 [P] Add `title` attributes and `aria-label` to summary cards and chart for accessibility
- [ ] T025 [P] Verify responsive layout on mobile (320px), tablet (768px), and desktop (1280px+) — cards stack correctly, chart resizes
- [ ] T026 [P] Add `AbortController` to cancel in-flight analytics fetch when user navigates away from the page
- [ ] T027 Run quickstart.md validation — test all scenarios listed in `.specify/specs/task-030-analytics-dashboard/quickstart.md`
- [ ] T028 Update `AGENTS.md` if new patterns or conventions were established during implementation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — **BLOCKS all user stories**
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) — Builds on US1's card rendering, adds trend indicators
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) — Builds on US1's fetch logic, adds error handling

### Within Each User Story

- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- T003 and T004 can run in parallel (different methods, same file but independent)
- T007 and T008 can run in parallel (route + template, different files)
- T009, T010, T011 can run in parallel (different JS functions, same file but independent logic)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)

### Parallel Example: User Story 1

```bash
# Launch route and template creation together:
Task: "T007 Add GET /dashboard/analytics HTML route in app/dashboard/routes.py"
Task: "T008 Create app/templates/dashboard/analytics.html template"

# Launch JS functions together (different functions, same file):
Task: "T009 Implement fetchAnalytics() in analytics.html"
Task: "T010 Implement renderSummaryCards() in analytics.html"
Task: "T011 Implement renderTimelineChart() in analytics.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Navigate to `/dashboard/analytics`, verify cards + chart render, switch periods
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Backend returns extended JSON with trends + timeline
2. Add User Story 1 → Full analytics page with cards, chart, period selector → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Trend indicators on cards → Test independently → Deploy/Demo
4. Add User Story 3 → Error states, debouncing, edge cases → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (route + template + JS)
   - Developer B: User Story 2 (trend indicators) — can start once T009-T011 are done
   - Developer C: User Story 3 (error states) — can start once T009 is done
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- The existing `formatNumber()`, `getMetricIcon()`, and skeleton HTML patterns from `layout.html` should be reused/adapted in `analytics.html`
- Chart.js colors should match the existing metric icon colors: purple (impressions), blue (reach), green (profile views), pink (follower count)
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
