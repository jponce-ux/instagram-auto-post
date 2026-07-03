# Contract: Insights API Endpoints

## GET /dashboard/analytics/account

Returns account-level insights for the authenticated user's active Instagram account.

### Query Parameters
- `period` (optional): `day` or `days_28` (default: `days_28`)

### Success Response (200)
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
  "cached": true,
  "fetched_at": "2026-06-30T10:00:00Z",
  "stale": false
}
```

### Error Responses
- **401**: Unauthorized (not logged in)
- **400**: No active Instagram account connected
- **403**: Account is "Inactiva" — needs reconnection
- **502**: Instagram API unavailable — cached data returned or "temporarily unavailable"

## GET /dashboard/analytics/media/{post_id}

Returns media-level insights for a specific published post (on-demand).

### Path Parameters
- `post_id`: Integer, must belong to authenticated user

### Success Response (200)
```json
{
  "post_id": 42,
  "ig_media_id": "17841400000000001",
  "metrics": {
    "engagement": 450,
    "impressions": 3200,
    "reach": 2800,
    "saved": 85,
    "likes": 320,
    "comments": 45
  },
  "cached": true,
  "fetched_at": "2026-06-30T10:00:00Z",
  "stale": false
}
```

### Error Responses
- **401**: Unauthorized
- **404**: Post not found or not owned by user
- **400**: Post not published (no media ID available)
- **403**: Account is "Inactiva"
- **502**: Instagram API unavailable
