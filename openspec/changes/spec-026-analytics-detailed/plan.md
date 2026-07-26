# Plan: Analytics Detailed View (spec-026-analytics-detailed)

## Summary

Build a comprehensive Analytics dashboard view that extends the existing basic analytics. Features include KPI cards with trend indicators, reach line chart, follower growth bar chart with industry benchmark, and top content grid. All visualizations update via HTMX without full page reload.

## Technical Context

**Language/Framework**: Python 3.11+ / FastAPI
**Primary Dependencies**: FastAPI, Jinja2, HTMX, Chart.js (or similar lightweight charting), Tailwind CSS
**Storage**: PostgreSQL, Redis (for analytics cache)
**Testing**: pytest with async support

**Target Platform**: Web (responsive, mobile-first)
**Project Type**: FastAPI HTML dashboard with HTMX

**Depends On**: 
- SPEC-012 (Post model with states)
- SPEC-023 (Sidebar layout with Analytics route)

## Applied Lessons

None yet — new feature work.

## Architecture Decisions

| Decision | Options | Tradeoffs | Choice |
|----------|---------|-----------|--------|
| Charting library | Chart.js vs ApexCharts vs Custom SVG | Chart.js: simple, lightweight; ApexCharts: prettier; Custom: full control | Chart.js (CDN) - good balance of simplicity and features |
| Data granularity | Pre-aggregate vs on-demand | Pre-aggregate: faster queries, more storage; On-demand: simpler, flexible | Pre-aggregate daily metrics, aggregate on-demand for weekly/monthly |
| Industry benchmark | Static constant vs API lookup | Static: simpler; API: more accurate | Static constants per industry (hardcoded for v1) |
| Cache strategy | Redis vs DB vs memory | Redis: distributed; DB: persistent; Memory: fast but single-instance | Redis for shared cache, with DB fallback |
| Chart rendering | Server-rendered HTML (img/SVG) vs client-side JS | Server: simpler, SEO; Client: more interactive | Client-side JS with Chart.js |

## Data Flow

```
User navigates to /dashboard/analytics
        │
        ▼
    GET /dashboard/analytics?period=days_28
        │
        ▼
    Check Redis cache
        │
        ├── Cache hit + not stale → return cached data
        │
        └── Cache miss or stale
                │
                ▼
        Fetch from Meta Graph API
                │
                ▼
        Transform and aggregate data
                │
                ▼
        Store in Redis (TTL: 1 hour)
                │
                ▼
        Return analytics data
                │
                ▼
    HTMX response → Update charts
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/metrics.py` | Modify | Add analytics aggregation methods |
| `app/dashboard/routes.py` | Modify | Add /analytics route with period param |
| `app/dashboard/service.py` | Modify | Add analytics service methods |
| `app/templates/dashboard/analytics.html` | Refactor | Full analytics UI with Chart.js |
| `app/templates/dashboard/partials/kpi_cards.html` | Create | KPI cards partial |
| `app/templates/dashboard/partials/reach_chart.html` | Create | Reach line chart partial |
| `app/templates/dashboard/partials/growth_chart.html` | Create | Growth bar chart partial |
| `app/templates/dashboard/partials/top_content.html` | Create | Top content grid partial |
| `app/templates/dashboard/partials/post_analytics_modal.html` | Create | Detailed post modal |

## Chart Specifications

### KPI Cards

```html
<div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
    <!-- Total Followers -->
    <div class="bg-white rounded-lg shadow p-4">
        <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-medium text-gray-500 uppercase">Total Followers</span>
            <span class="text-green-500">↑ 12.5%</span>
        </div>
        <p class="text-2xl font-bold text-gray-900">12,450</p>
    </div>
    <!-- Monthly Reach -->
    <div class="bg-white rounded-lg shadow p-4">
        <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-medium text-gray-500 uppercase">Monthly Reach</span>
            <span class="text-red-500">↓ 3.2%</span>
        </div>
        <p class="text-2xl font-bold text-gray-900">45,230</p>
    </div>
    <!-- Engagement Rate -->
    <div class="bg-white rounded-lg shadow p-4">
        <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-medium text-gray-500 uppercase">Engagement Rate</span>
            <span class="text-green-500">↑ 1.8%</span>
        </div>
        <p class="text-2xl font-bold text-gray-900">4.2%</p>
    </div>
</div>
```

### Chart.js Configuration

```javascript
// Reach Line Chart
new Chart(document.getElementById('reachChart'), {
    type: 'line',
    data: {
        labels: ['Jan', 'Feb', 'Mar', 'Apr'],
        datasets: [{
            label: 'Reach',
            data: [1200, 1900, 3000, 5000],
            borderColor: '#8B5CF6',
            tension: 0.3,
            fill: true,
            backgroundColor: 'rgba(139, 92, 246, 0.1)'
        }]
    },
    options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } }
    }
});

// Follower Growth Bar Chart
new Chart(document.getElementById('growthChart'), {
    type: 'bar',
    data: {
        labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
        datasets: [{
            label: 'Your Growth',
            data: [120, 150, 180, 200],
            backgroundColor: '#10B981'
        }, {
            label: 'Industry Average',
            data: [100, 110, 120, 130],
            type: 'line',
            borderColor: '#EF4444',
            borderDash: [5, 5],
            fill: false
        }]
    }
});
```

## API Routes

### GET /dashboard/analytics

Return analytics dashboard with all charts.

**Query Params**:
- `period`: `days_28` (default), `days_7`, `days_14`, `days_90`

**Response**: Full page via app_layout

### GET /dashboard/analytics/kpis

Return KPI cards partial for HTMX swap.

**Query Params**:
- `period`: `days_28`, `days_7`, `days_14`, `days_90`

**Response**: HTML fragment

### GET /dashboard/analytics/reach-chart

Return reach chart partial.

**Query Params**:
- `period`: `days_28`, `days_7`, `days_14`, `days_90`

**Response**: HTML fragment with Chart.js canvas

### GET /dashboard/analytics/growth-chart

Return growth chart partial.

**Query Params**:
- `period`: `days_28`, `days_7`, `days_14`, `days_90`

**Response**: HTML fragment with Chart.js canvas

### GET /dashboard/analytics/top-content

Return top content grid partial.

**Query Params**:
- `period`: `days_28`, `days_7`, `days_14`, `days_90`
- `limit`: int (default 6)

**Response**: HTML fragment

### GET /dashboard/analytics/media/{post_id}

Return detailed analytics for a specific post (modal content).

**Response**: HTML fragment for modal

## Industry Benchmarks (v1 - hardcoded)

Based on general Instagram benchmarks (not industry-specific for v1):

| Metric | Benchmark Value |
|--------|-----------------|
| Follower growth (weekly) | ~100 |
| Engagement rate (avg) | ~1-3% |
| Reach (monthly) | Varies by account size |

## Cache Strategy

```python
# Redis cache keys
analytics:account:{ig_account_id}:metrics:{period}  # TTL: 1 hour
analytics:media:{ig_media_id}:insights              # TTL: 24 hours

# Cache invalidation
- On new post published: invalidate account metrics
- On media insights fetched: update media cache
- On token refresh: invalidate all caches for account
```

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | Metrics aggregation logic | Mock data, test calculations |
| Unit | Chart.js configuration | Verify correct data binding |
| Integration | Analytics API with real data | TestClient with mocked Meta API |
| Integration | HTMX chart updates | Assert partial renders correctly |
| Manual | Chart interactions | Browser: hover, click, resize |

## Risk Assessment

- **Risk**: Meta API rate limits cause analytics to fail
  - **Mitigation**: Aggressive caching (1hr TTL), show cached data with warning
- **Risk**: Chart.js renders poorly on mobile
  - **Mitigation**: Responsive chart options, test on multiple viewport sizes
- **Risk**: Large datasets cause slow chart rendering
  - **Mitigation**: Limit data points (max 30), aggregate to weekly for long periods

## Rollback Plan

1. Revert analytics.html to simple placeholder
2. Remove Chart.js CDN reference
3. Remove analytics routes from routes.py
4. Keep metrics service methods (used by other features)
5. Cached data in Redis will expire naturally
