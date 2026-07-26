# Tasks: Analytics Detailed View

**Status**: Not Started
**Progress**: 0/14 tasks
**Current Phase**: —

## Dependencies & Execution Order

- Phase 1 (Foundation) must complete before Phase 2 (UI Components)
- Phase 2 must complete before Phase 3 (Integration)
- Tasks marked `[P]` are parallelizable within phase

---

## Phase 1: Foundation

### T001 [P] Add analytics cache methods to metrics service

Extend `app/services/metrics.py` with caching methods for analytics data.

**Deliverable**: Updated `app/services/metrics.py`
**File**: `app/services/metrics.py`
**Acceptance**:
- [ ] `get_cached_account_metrics()` method with cache lookup
- [ ] `set_cached_account_metrics()` method with TTL
- [ ] `invalidate_account_metrics_cache()` method
- [ ] `aggregate_daily_metrics()` for period aggregation

---

### T002 [P] Add analytics aggregation methods

Add methods to calculate KPIs, trends, and aggregations.

**Deliverable**: Updated `app/services/metrics.py`
**File**: `app/services/metrics.py`
**Acceptance**:
- [ ] `calculate_kpis()` method returning follower_count, reach, engagement_rate
- [ ] `calculate_trend_percentage()` method for period comparison
- [ ] `get_reach_timeseries()` for line chart data
- [ ] `get_follower_growth_timeseries()` for bar chart data

---

### T003 [P] Add analytics service methods

Add analytics methods to `app/dashboard/service.py`.

**Deliverable**: Updated `app/dashboard/service.py`
**File**: `app/dashboard/service.py`
**Acceptance**:
- [ ] `get_analytics_overview()` method
- [ ] `get_top_performing_posts()` method
- [ ] `get_media_insights()` method for post detail modal

---

### T004 [P] Add analytics routes

Add/modify routes in `app/dashboard/routes.py` for analytics endpoints.

**Deliverable**: Updated `app/dashboard/routes.py`
**File**: `app/dashboard/routes.py`
**Acceptance**:
- [ ] GET /dashboard/analytics - main analytics page
- [ ] GET /dashboard/analytics/kpis - KPI cards partial
- [ ] GET /dashboard/analytics/reach-chart - reach chart partial
- [ ] GET /dashboard/analytics/growth-chart - growth chart partial
- [ ] GET /dashboard/analytics/top-content - content grid partial
- [ ] GET /dashboard/analytics/media/{id} - post detail modal
- [ ] All support `period` query param: days_7, days_14, days_28, days_90
- [ ] HTMX request handling for partial updates

---

## Phase 2: UI Components

### T005 Refactor analytics.html with full UI

Replace existing `app/templates/dashboard/analytics.html` with full analytics dashboard.

**Deliverable**: Updated `app/templates/dashboard/analytics.html`
**File**: `app/templates/dashboard/analytics.html`
**Acceptance**:
- [ ] Extends app_layout.html
- [ ] Time filter buttons (Daily, Weekly, Monthly)
- [ ] KPI cards section
- [ ] Charts section (reach + growth)
- [ ] Top content grid section
- [ ] Chart.js included via CDN
- [ ] HTMX triggers on filter buttons

---

### T006 [P] Create KPI cards partial

Create `app/templates/dashboard/partials/kpi_cards.html`.

**Deliverable**: `app/templates/dashboard/partials/kpi_cards.html`
**File**: `app/templates/dashboard/partials/kpi_cards.html`
**Acceptance**:
- [ ] Three KPI cards: Total Followers, Monthly Reach, Engagement Rate
- [ ] Trend indicator with up/down arrow and percentage
- [ ] Color coding: green for positive, red for negative
- [ ] Loading skeleton state

---

### T007 [P] Create reach chart partial

Create `app/templates/dashboard/partials/reach_chart.html`.

**Deliverable**: `app/templates/dashboard/partials/reach_chart.html`
**File**: `app/templates/dashboard/partials/reach_chart.html`
**Acceptance**:
- [ ] Chart.js canvas element
- [ ] Data attributes for HTMX to inject JSON data
- [ ] Empty state if no data
- [ ] Responsive sizing

---

### T008 [P] Create growth chart partial

Create `app/templates/dashboard/partials/growth_chart.html`.

**Deliverable**: `app/templates/dashboard/partials/growth_chart.html`
**File**: `app/templates/dashboard/partials/growth_chart.html`
**Acceptance**:
- [ ] Chart.js bar chart + line for benchmark
- [ ] Data attributes for HTMX injection
- [ ] Legend showing "Your Growth" and "Industry Average"
- [ ] Empty state if no data

---

### T009 [P] Create top content grid partial

Create `app/templates/dashboard/partials/top_content.html`.

**Deliverable**: `app/templates/dashboard/partials/top_content.html`
**File**: `app/templates/dashboard/partials/top_content.html`
**Acceptance**:
- [ ] Grid of post cards (thumbnail, caption, likes, comments, category)
- [ ] Sorted by engagement (highest first)
- [ ] Click handler to open post analytics modal
- [ ] Empty state if no published posts

---

### T010 [P] Create post analytics modal partial

Create `app/templates/dashboard/partials/post_analytics_modal.html`.

**Deliverable**: `app/templates/dashboard/partials/post_analytics_modal.html`
**File**: `app/templates/dashboard/partials/post_analytics_modal.html`
**Acceptance**:
- [ ] Modal structure with backdrop
- [ ] Post thumbnail and caption
- [ ] Metrics grid: likes, comments, saves, impressions, reach
- [ ] Close button and ESC key handler

---

## Phase 3: Integration & Testing

### T011 Add Chart.js initialization script

Add JavaScript to initialize and update Chart.js instances on HTMX swap.

**Deliverable**: Script in `app/templates/dashboard/analytics.html`
**File**: `app/templates/dashboard/analytics.html`
**Acceptance**:
- [ ] Chart.js instances stored in variable for update
- [ ] `initCharts()` function called on page load
- [ ] `updateCharts(data)` function for HTMX-triggered updates
- [ ] Destroys old charts before creating new ones

---

### T012 Test KPI cards with trend indicators

Verify KPI cards display correctly with trend calculations.

**Deliverable**: Test checklist
**File**: Manual testing
**Acceptance**:
- [ ] All three KPIs display with values
- [ ] Trend arrows point correctly (up=green, down=red)
- [ ] Percentages calculated correctly
- [ ] Empty state shows for missing data

---

### T013 Test charts render and update via HTMX

Verify charts render with correct data and update when filters change.

**Deliverable**: Test checklist
**File**: Manual testing
**Acceptance**:
- [ ] Line chart shows reach over time
- [ ] Bar chart shows growth with benchmark line
- [ ] Charts update without full page reload when filter changes
- [ ] Chart.js handles resize correctly

---

### T014 Test top content grid and modal

Verify top posts grid and detail modal work correctly.

**Deliverable**: Test checklist
**File**: Manual testing
**Acceptance**:
- [ ] Posts sorted by engagement (highest first)
- [ ] Clicking post opens modal with details
- [ ] Modal closes on X click, backdrop click, or ESC
- [ ] Empty state shows if no published posts

---

## Progress Summary

- Phase 1 (Foundation): 4 tasks
- Phase 2 (UI Components): 6 tasks
- Phase 3 (Integration & Testing): 4 tasks

**Total**: 14 tasks
