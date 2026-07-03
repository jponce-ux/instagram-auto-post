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

## Testing Chart Interactivity
1. Hover over chart data points — verify tooltips show exact values
2. Click legend items — verify metric series toggle on/off
3. Resize browser window — verify chart resizes responsively
