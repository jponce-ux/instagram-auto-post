# Proposal: spec-014-celery-beat-scheduler

## Intent

Enable automatic database inspection every 60 seconds to find scheduled posts and trigger their publication. This transforms posts from manual-trigger to time-based publishing.

## Scope

### In Scope
- New `beat` container in docker-compose.yml
- `beat_schedule` configuration in Celery app (every 60s)
- `check_scheduled_posts` task querying PENDING posts with `scheduled_at <= now`
- Dispatch `process_instagram_post.delay(post_id)` for each eligible post

### Out of Scope
- Scheduling UI or API (user sets `scheduled_at` directly on Post)
- Recurring/scheduled posts (one-time only)
- Beat persistence (in-memory scheduler, loses state on restart — add later with `--schedule` flag)

## Capabilities

### New Capabilities
- `scheduled-post-scheduler`: Beat-driven task that polls database for due posts and dispatches publishing tasks

### Modified Capabilities
- None (delta spec only — adds scheduling infrastructure)

## Approach

**Beat + Interval Schedule**: Add Celery Beat service with `beat_schedule` interval (60s). The scheduler task runs `check_scheduled_posts` which queries PostgreSQL for posts where:
- `status = PENDING`  
- `scheduled_at <= now()`

For each post found, dispatch `process_instagram_post.delay(post_id)`.

**Dependency Order**: 
1. SPEC-011 creates `app/worker.py` with Celery app
2. SPEC-012 adds Post model + `process_instagram_post` task
3. SPEC-014 adds beat_schedule + `check_scheduled_posts` task

**Query Pattern**: Use `asyncio.to_thread()` or `sync_to_async` to run sync SQLAlchemy query from beat task context.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `docker-compose.yml` | Modified | Add `beat` service |
| `app/worker.py` | Modified | Add `beat_schedule` config + `check_scheduled_posts` task |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Beat scheduler loses state on restart (missed tasks) | Medium | Warn user; add persistent scheduler (django-celery-beat) in future |
| Database connection pool exhaustion | Low | Beat task is short-lived; ensure connection limits |
| Duplicate dispatches if worker is slow | Low | Query filters `scheduled_at <= now` and status PENDING; task updates status to PROCESSING quickly |

## Rollback Plan

1. Remove `beat` service from docker-compose.yml
2. Remove `beat_schedule` and `check_scheduled_posts` from worker.py
3. Restart worker container (beat config changes don't require migration)

## Dependencies

- **SPEC-011** (Celery): Must be complete — requires `app/worker.py` with Celery app instance
- **SPEC-012** (Post Logic): Must be complete — requires Post model with `scheduled_at` field and `process_instagram_post` task

## Success Criteria

- [ ] `beat` container starts successfully via `docker compose up beat`
- [ ] `check_scheduled_posts` runs every 60 seconds (visible in logs)
- [ ] Posts with `status=PENDING` and `scheduled_at <= now()` trigger `process_instagram_post.delay()`
- [ ] No duplicate dispatches for the same post in same beat cycle
- [ ] Beat survives worker restart (in-memory scheduler, no persistence needed for MVP)
