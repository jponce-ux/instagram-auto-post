---
ticket: TASK-030
phase: plan
model: qwen3.6-plus
generated: 2026-07-03
status: draft
---

# Implementation Plan: Global Account Analytics View Dashboard

**Branch**: `feat/task-030-analytics-dashboard` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `.specify/specs/task-030-analytics-dashboard/spec.md`

## Summary

Build a dedicated Analytics page (`GET /dashboard/analytics`) that renders a full-page view with summary cards (Reach, Impressions, Profile Views, Follower Growth) featuring trend indicators (current vs. previous period), interactive timeline charts via Chart.js CDN, a period selector (7d/28d), skeleton loading states, and graceful error handling. Reuses the existing `GET /dashboard/analytics/account` JSON API from TASK-029 as the data source. The page extends the existing `base.html` template and follows the established Tailwind CSS + vanilla JavaScript patterns from `layout.html`.

## Technical Context

**Language/Version**: Python 3.11 (FastAPI backend), JavaScript (vanilla, frontend)
**Primary Dependencies**: FastAPI, Jinja2, Tailwind CSS, Chart.js (CDN)
**Storage**: Redis (caching, already operational from TASK-029)
**Testing**: pytest + pytest-asyncio (backend), manual browser testing (frontend)
**Target Platform**: Linux server (Docker), modern web browsers (Chrome, Firefox, Safari, Edge)
**Project Type**: Web application (FastAPI backend + Jinja2/HTMX/JS frontend)
**Performance Goals**: Page renders < 3s from cache, < 6s from fresh API fetch (per spec SC-001, SC-002)
**Constraints**: Must reuse existing TASK-029 analytics API; must follow existing Tailwind + vanilla JS patterns; Chart.js loaded via CDN only (no npm dependency)
**Scale/Scope**: Single-user dashboard, one or more Instagram accounts per user

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution at `.specify/memory/constitution.md` is still in template form with no active governance gates. No violations possible.

**Gate Status**: ✅ PASS — no constitution violations.

## Project Structure

### Documentation (this feature)

```text
specs/task-030-analytics-dashboard/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/           # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code Changes

```text
app/
├── dashboard/
│   ├── routes.py                # MODIFY: add GET /dashboard/analytics (HTML page route)
│   └── service.py               # No changes needed (uses existing get_user_accounts)
├── services/
│   └── metrics.py               # MODIFY: add get_account_analytics_with_trend() method
│                                  (fetches current + previous period data for trend calculation)
└── templates/
    └── dashboard/
        └── analytics.html       # CREATE: Full-page analytics view template
```

**Structure Decision**: Single-project web application. The new analytics page is a Jinja2 template served by a new FastAPI route. The metrics service gets a new method for trend calculation. No new database models, no new API endpoints (reuses TASK-029's JSON API for the frontend JS calls).

## Phase 0: Research

### Chart.js vs. ApexCharts Decision

**Decision**: Use Chart.js (via CDN)

**Rationale**:
- Chart.js is lighter (~60KB gzipped) vs. ApexCharts (~100KB+ with dependencies)
- Chart.js has simpler API for basic line/bar charts needed here
- Chart.js is more widely known, easier to maintain
- Both support responsive charts, tooltips, and multi-dataset line charts
- CDN loading: `https://cdn.jsdelivr.net/npm/chart.js@4` — no build step required

**Alternatives considered**:
- ApexCharts: More visually polished out-of-the-box, but heavier and more complex API
- D3.js: Too heavy and complex for simple timeline charts
- No chart library (CSS-only): Would not meet the "interactive graphical representations" requirement

### Trend Calculation Approach

**Decision**: Calculate trends client-side by fetching two periods from the API

**Rationale**:
- The existing `GET /dashboard/analytics/account?period=days_28` endpoint returns aggregated metrics
- For trend comparison, we need current period + previous period data
- Two approaches:
  1. **Backend calculates trends**: Add a new endpoint or modify existing one to return trend percentages
  2. **Frontend calculates trends**: Fetch current period, then fetch previous period, compute delta client-side
- **Selected**: Backend calculates trends (new method `get_account_analytics_with_trend()` in metrics service). This avoids double API calls to Instagram Graph API and keeps the frontend simple.
- The backend method will:
  1. Fetch current period metrics from Instagram API (or cache)
  2. Fetch previous period metrics from Instagram API (or cache)
  3. Calculate percentage change for each metric
  4. Return combined response with trend data

### Page Architecture

**Decision**: Dedicated route `GET /dashboard/analytics` returning HTML (Jinja2 template)

**Rationale**:
- The existing dashboard (`GET /dashboard/`) is a single-page layout with inline analytics
- A dedicated analytics page provides a cleaner, focused experience for deep analysis
- The page will extend `base.html` (same as `layout.html`) for consistent styling
- JavaScript will fetch data from the existing `GET /dashboard/analytics/account` JSON API
- Chart.js will be loaded via CDN `<script>` tag in the template

**Page layout**:
```
┌─────────────────────────────────────────────────┐
│  Header (from base.html)                        │
├─────────────────────────────────────────────────┤
│  ← Back to Dashboard  |  Period: [7d | 28d]     │
├─────────────────────────────────────────────────┤
│  Summary Cards (4 cards with trend indicators)  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────┐│
│  │ Reach    │ │ Impress. │ │ Profile  │ │ Flwr││
│  │ 8,900 ↑5%│ │ 12,500↑12│ │ 340 ↓2%  │ │1,250││
│  └──────────┘ └──────────┘ └──────────┘ └─────┘│
├─────────────────────────────────────────────────┤
│  Timeline Chart (Chart.js line chart)           │
│  ┌───────────────────────────────────────────┐  │
│  │  [Reach] [Impressions] [Profile Views]    │  │
│  │  ╱╲    ╱╲    ╱╲    ╱╲    ╱╲    ╱╲         │  │
│  │ ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲        │  │
│  │╱    ╲╱    ╲╱    ╲╱    ╲╱    ╲╱    ╲       │  │
│  └───────────────────────────────────────────┘  │
│  Day 1  Day 7  Day 14  Day 21  Day 28           │
├─────────────────────────────────────────────────┤
│  Footer (from base.html)                        │
└─────────────────────────────────────────────────┘
```

## Phase 1: Design & Contracts

### data-model.md

```markdown
# Data Model: TASK-030 Changes

## No Database Schema Changes

This feature does not require new database columns or tables. It reads from existing models and extends the metrics service.

## Extended Response Schema (Backend → Frontend JS)

The existing `GET /dashboard/analytics/account` response is extended with trend data:

```json
{
  "account_id": 1,
  "instagram_account_id": "17841400000000000",
  "period": "days_28",
  "metrics": {
    "impressions": 12500,
    "reach": 8900,
    "profile_views": 340,
    "follower_count": 1250
  },
  "trends": {
    "impressions": 12.5,
    "reach": 5.2,
    "profile_views": -2.1,
    "follower_count": 0.0
  },
  "timeline": {
    "labels": ["2026-06-05", "2026-06-06", ..., "2026-07-03"],
    "datasets": {
      "impressions": [400, 450, 380, ...],
      "reach": [300, 320, 290, ...],
      "profile_views": [10, 15, 12, ...],
      "follower_count": [1200, 1205, 1210, ...]
    }
  },
  "cached": true,
  "fetched_at": "2026-07-03T10:00:00Z",
  "stale": false
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `trends.*` | number (percentage) | Percentage change vs. previous period. Positive = growth, negative = decline, 0 = no change |
| `timeline.labels` | string[] | ISO date strings for each day in the period |
| `timeline.datasets.*` | number[] | Daily metric values aligned with labels |

## Redis Cache Schema (Extended)

| Key Pattern | TTL | Value |
|-------------|-----|-------|
| `insights:account:{account_id}:{period}` | 3600s | JSON with metrics + trends + timeline (extended from TASK-029) |
| `insights:account:{account_id}:{period}:previous` | 3600s | JSON with previous period metrics (for trend calculation) |
```

### contracts/analytics-page.md

```markdown
# Contract: Analytics Page

## GET /dashboard/analytics

Renders the full-page Analytics dashboard as HTML.

### Authentication
- Requires authenticated user (JWT cookie)
- Redirects to `/auth/login` if not authenticated

### Query Parameters
- `period` (optional): `days_7` or `days_28` (default: `days_28`)

### Response
- **200**: HTML page with analytics dashboard
- **303**: Redirect to login if not authenticated

### Page Components
1. **Header**: Back to Dashboard link + Period selector (7d / 28d)
2. **Summary Cards**: 4 cards (Reach, Impressions, Profile Views, Follower Growth) with trend indicators
3. **Timeline Chart**: Interactive Chart.js line chart with toggleable metric series
4. **Loading State**: Skeleton placeholders during initial data fetch
5. **Error States**:
   - No account connected → prompt to connect
   - Account inactive → prompt to reconnect
   - API unavailable → stale data + retry button, or "temporarily unavailable" message
```

### quickstart.md

```markdown
# Quickstart: TASK-030 Testing

## Prerequisites
- Docker Compose stack running (api, worker, beat, redis, postgres, minio)
- User account with verified Instagram Business/Creator account
- At least one published post with a valid `ig_media_id`
- TASK-029 backend analytics API functional

## Testing the Analytics Page
1. Log in to the dashboard
2. Navigate to `/dashboard/analytics` (via new nav link or direct URL)
3. Verify summary cards display with correct values and trend indicators
4. Verify the timeline chart renders with historical data
5. Switch between 7-day and 28-day periods — verify charts and cards update
6. Check Redis cache: `docker compose exec redis redis-cli KEYS "insights:account:*"`

## Testing Trend Indicators
1. View analytics for 28-day period
2. Verify each card shows a trend percentage (positive = green ↑, negative = red ↓, zero = gray —)
3. If all trends are zero, verify neutral indicator is shown

## Testing Loading States
1. Clear Redis cache: `docker compose exec redis redis-cli DEL insights:account:*`
2. Navigate to `/dashboard/analytics`
3. Verify skeleton loading placeholders are shown during fetch
4. Verify charts populate once data arrives

## Testing Error States
1. Disconnect Instagram account (revoke token in Meta Developer Portal)
2. Navigate to `/dashboard/analytics`
3. Verify "account inactive" message with reconnect button
4. Reconnect account and verify analytics load normally
```

## Complexity Tracking

No complexity beyond existing patterns. All changes follow established conventions from TASK-029 and the existing codebase.

| Change | Complexity | Justification |
|--------|------------|---------------|
| `GET /dashboard/analytics` route | Low | New FastAPI route returning HTML, follows existing dashboard route patterns |
| `analytics.html` template | Medium | New full-page template with Chart.js integration, period selector, trend cards |
| `get_account_analytics_with_trend()` | Medium | New metrics service method fetching current + previous period, calculating trends |
| Extended JSON response schema | Low | Adds `trends` and `timeline` fields to existing response structure |
| Chart.js CDN integration | Low | Single `<script>` tag, vanilla JS initialization |
