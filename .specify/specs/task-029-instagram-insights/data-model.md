# Data Model: TASK-029 Changes

## No Schema Changes

This feature does not require new database columns or tables. It reads from existing models:

| Model | Fields Used | Purpose |
|-------|-------------|---------|
| InstagramAccount | `id`, `instagram_account_id`, `access_token`, `is_active` | Authenticate API requests, check active status |
| Post | `id`, `ig_media_id`, `status`, `user_id` | Filter published posts, fetch media-level insights |

## Redis Cache Schema

| Key Pattern | TTL | Value |
|-------------|-----|-------|
| `insights:account:{account_id}:{period}` | 3600s | JSON: `{impressions, reach, profile_views, follower_count, fetched_at}` |
| `insights:media:{media_id}` | 3600s | JSON: `{engagement, impressions, reach, saved, likes, comments, fetched_at}` |

## Cache Invalidation

- On post publish: delete `insights:account:{account_id}:*` keys
- On token error: delete all cache keys for the affected account
- On manual retry: delete specific key and refetch
