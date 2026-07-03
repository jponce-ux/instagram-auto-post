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

## Extended JSON API Response (GET /dashboard/analytics/account)

The existing JSON API response is extended to include `trends` and `timeline` fields:

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
    "labels": ["2026-06-05", "2026-06-06", "...", "2026-07-03"],
    "datasets": {
      "impressions": [400, 450, 380, "..."],
      "reach": [300, 320, 290, "..."],
      "profile_views": [10, 15, 12, "..."],
      "follower_count": [1200, 1205, 1210, "..."]
    }
  },
  "cached": true,
  "fetched_at": "2026-07-03T10:00:00Z",
  "stale": false
}
```

### Trend Field Semantics

| Value | Meaning | UI Indicator |
|-------|---------|--------------|
| `> 0` | Metric increased vs. previous period | Green upward arrow + percentage |
| `< 0` | Metric decreased vs. previous period | Red downward arrow + percentage |
| `0` | No change | Gray dash or "0%" |
| `null` | Cannot calculate (no previous data) | "—" (no indicator) |
