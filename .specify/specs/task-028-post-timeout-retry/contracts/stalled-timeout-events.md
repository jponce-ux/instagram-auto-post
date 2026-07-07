# Contract: Stalled Post Timeout SSE Events

## Event Format (reuses existing post_update channel)

When a post transitions to "failed" due to stalled timeout:

```json
{
  "post_id": 1,
  "status": "failed",
  "user_id": 42,
  "error_message": "Processing timeout exceeded"
}
```

When a post transitions to "failed" due to retry timeout:

```json
{
  "post_id": 1,
  "status": "failed",
  "user_id": 42,
  "error_message": "Retry timeout exceeded"
}
```

Note: These use the same SSE channel (`post_update`) and event format as existing post status events. The dashboard's existing SSE handler already refreshes the post feed on any `post_update` event.
