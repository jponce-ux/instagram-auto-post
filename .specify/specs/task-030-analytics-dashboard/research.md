# Research: TASK-030 Analytics Dashboard

**Date**: 2026-07-03
**Spec**: [spec.md](./spec.md)

## Decision 1: Charting Library

**Decision**: Chart.js v4 via CDN

**Rationale**:
- Lightweight (~60KB gzipped), well-maintained, widely adopted
- Supports line charts with multiple datasets, tooltips, legends, responsive sizing
- Simple vanilla JS API — no build step or npm dependency required
- CDN URL: `https://cdn.jsdelivr.net/npm/chart.js@4`
- Compatible with all modern browsers (Chrome, Firefox, Safari, Edge)

**Alternatives considered**:
- **ApexCharts**: More polished default styles, but heavier (~100KB+) and more complex API
- **D3.js**: Overkill for simple line charts, steep learning curve
- **CSS-only charts**: Cannot meet "interactive graphical representations" requirement

## Decision 2: Trend Calculation Location

**Decision**: Backend calculates trends (new method in `metrics_service`)

**Rationale**:
- Avoids double API calls to Instagram Graph API from the frontend
- Backend can cache both current and previous period data efficiently
- Keeps frontend JavaScript simple — just renders pre-calculated trend percentages
- Consistent with TASK-029's pattern of server-side data processing

**Approach**:
1. `get_account_analytics_with_trend()` fetches current period metrics
2. Fetches previous period metrics (same duration, shifted back)
3. Calculates percentage change: `((current - previous) / previous) * 100`
4. Handles edge cases: previous = 0 → trend = 0 (no division by zero)
5. Returns combined response with `metrics`, `trends`, and `timeline` data

## Decision 3: Page Architecture

**Decision**: Dedicated route `GET /dashboard/analytics` returning HTML (Jinja2 template)

**Rationale**:
- Existing dashboard (`GET /dashboard/`) has inline analytics section — insufficient for deep analysis
- Dedicated page provides focused, full-screen analytics experience
- Extends `base.html` for consistent header/footer styling
- JavaScript fetches data from existing `GET /dashboard/analytics/account` JSON API
- Follows established pattern: HTML route for page, JSON route for data

## Decision 4: Timeline Data Source

**Decision**: Instagram Graph API provides daily breakdown via `time_series` in insights response

**Rationale**:
- The Instagram Graph API `/insights` endpoint returns `values` array with daily data points when `period=day`
- For `period=days_28`, the API returns aggregated values, but we can fetch daily granularity by making 28 individual calls or using the `since`/`until` parameters
- **Selected approach**: Use `since`/`until` parameters to fetch daily time-series data in a single call per metric
- API format: `GET /{ig-account-id}/insights?metric=impressions,reach,profile_views,follower_count&period=day&since={timestamp}&until={timestamp}`

## Decision 5: Period Selector Implementation

**Decision**: Client-side toggle buttons that trigger data refetch

**Rationale**:
- Two buttons: "7 días" and "28 días" (default: 28 días)
- On click, JavaScript fetches `/dashboard/analytics/account?period=days_7` or `days_28`
- Debounced to prevent rapid switching (300ms delay)
- Active period highlighted with distinct styling
- No page reload — single-page update via JavaScript
