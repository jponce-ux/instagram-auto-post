# Data Model: TASK-030 Changes

## No Database Schema Changes

This feature does not require new database columns or tables. It reads from existing models and extends the metrics service.

## Extended Response Schema (Backend → Frontend JS)

The existing `GET /dashboard/analytics/account` response is extended with trend and timeline data:

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

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `trends.*` | number (percentage) | Percentage change vs. previous period. Positive = growth, negative = decline, 0 = no change |
| `timeline.labels` | string[] | ISO date strings for each day in the period |
| `timeline.datasets.*` | number[] | Daily metric values aligned with labels |

### Trend Calculation Formula

```
trend_percentage = ((current_value - previous_value) / previous_value) * 100
```

Edge cases:
- `previous_value == 0` → `trend_percentage = 0` (avoid division by zero)
- `current_value == 0 && previous_value > 0` → `trend_percentage = -100`
- Both zero → `trend_percentage = 0`

## Redis Cache Schema (Extended)

| Key Pattern | TTL | Value |
|-------------|-----|-------|
| `insights:account:{account_id}:{period}` | 3600s | JSON with metrics + trends + timeline (extended from TASK-029) |
| `insights:account:{account_id}:{period}:previous` | 3600s | JSON with previous period metrics (for trend calculation) |

## Existing Models Used (No Changes)

| Model | Fields Used | Purpose |
|-------|-------------|---------|
| InstagramAccount | `id`, `instagram_account_id`, `access_token`, `is_active` | Authenticate API requests, check active status |
| User | `id` | Ownership verification |
