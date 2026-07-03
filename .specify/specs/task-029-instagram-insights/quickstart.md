# Quickstart: TASK-029 Testing

## Prerequisites
- Docker Compose stack running (api, worker, beat, redis, postgres, minio)
- User account with verified Instagram Business/Creator account
- At least one published post with a valid `ig_media_id`

## Testing Account-Level Analytics
1. Log in to the dashboard
2. View the analytics section — should show impressions, reach, profile views, follower count
3. Check Redis: `docker compose exec redis redis-cli KEYS "insights:account:*"`
4. Wait 1 hour or manually delete the cache key, then refresh — should fetch fresh data
5. Publish a new post — verify cache is invalidated and fresh data is fetched on next view

## Testing Media-Level Analytics
1. View post history in the dashboard
2. Click on a published post — should show media-level metrics
3. Check Redis: `docker compose exec redis redis-cli KEYS "insights:media:*"`
4. Click on a pending/processing post — should show "metrics not yet available"

## Testing Token Error Handling
1. Revoke the Instagram account's access token in Meta Developer Portal
2. View analytics — should see account marked "Inactiva" with reconnect prompt
3. Verify no further API calls are made for that account

## Testing Cache Fallback
1. View analytics (populates cache)
2. Disconnect from internet or block Instagram API
3. Refresh — should show cached data with "stale" indicator and "Retry" button
