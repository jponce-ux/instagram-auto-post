# Quickstart: TASK-028 Testing

## Prerequisites
- Docker Compose stack running (api, worker, beat, redis, postgres, minio)
- User account with linked Instagram account

## Testing Stalled Post Timeout
1. Create a post via the dashboard
2. In the database, manually set the post status to 'processing' and `processing_started_at` to 16 minutes ago:
   ```sql
   UPDATE posts SET status = 'processing', processing_started_at = NOW() - INTERVAL '16 minutes' WHERE id = <post_id>;
   ```
3. Wait up to 60 seconds for the Beat task to run
4. Verify the post status transitions to 'failed' with error message "Processing timeout exceeded"
5. Verify the dashboard updates in real-time via SSE

## Testing Retry
1. Set a post status to 'failed' in the database
2. View the dashboard — the "Reintentar" button should appear next to the failed post
3. Click "Reintentar"
4. Verify the post status changes to 'processing'
5. Verify the Celery worker picks up the task
6. Verify the dashboard updates in real-time

## Testing Token Error Detection
1. Set the Instagram account's access_token to an expired/invalid token
2. Create a post
3. Verify the worker detects the token error, deactivates the account, and marks the post as 'failed'
4. Verify the dashboard shows the account as "Inactiva" with a "Reconectar" button
