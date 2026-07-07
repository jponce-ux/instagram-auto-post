# Data Model: TASK-028 Changes

## Post Table — New Column

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `processing_started_at` | TIMESTAMP WITH TIME ZONE | Yes | NULL | Set when status transitions to "processing" or "retrying". Cleared when status transitions to "published" or "failed". Used for stalled post timeout calculation. |

### Migration Notes
- Column is nullable to support existing rows
- Fallback: if NULL and status is "processing"/"retrying", use `created_at` for timeout calculation
- No index needed — periodic check scans by status + timestamp comparison

## State Transitions

```
pending → processing (processing_started_at = NOW)
processing → published (processing_started_at = NULL)
processing → failed (processing_started_at = NULL)
processing → retrying (processing_started_at = NOW) [via Celery retry]
retrying → processing (processing_started_at = NOW) [via Celery retry attempt]
retrying → failed (processing_started_at = NULL)
failed → processing (processing_started_at = NOW) [via retry endpoint]
```

### Stalled Post Detection Logic

- **Processing timeout**: `status = 'processing' AND processing_started_at < NOW() - INTERVAL '15 minutes'`
- **Retrying timeout**: `status = 'retrying' AND processing_started_at < NOW() - INTERVAL '5 minutes'`
- **Fallback for NULL**: `status = 'processing' AND (processing_started_at IS NULL OR processing_started_at < NOW() - INTERVAL '15 minutes')`
