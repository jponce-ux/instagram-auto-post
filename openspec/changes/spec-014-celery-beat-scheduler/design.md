# Design: Celery Beat Scheduler for Scheduled Posts

## Technical Approach

Add a dedicated Celery Beat container that polls the database every 60 seconds for posts ready to be published. When posts with `status=PENDING` and `scheduled_at <= now()` are found, the scheduler transitions them to `PROCESSING` and dispatches `process_instagram_post.delay(post_id)` for each. This enables time-based publishing without manual intervention.

Beat runs as a separate container using the same Docker image as the worker but with the `celery beat` command. The schedule is configured in `app/worker.py` via `beat_schedule`, and the task runs sync DB queries wrapped with proper error handling to ensure beat stability.

## Architecture Decisions

### Decision: Beat Schedule Storage (In-Memory)

| Option | Tradeoff | Decision |
|--------|----------|----------|
| In-memory (default) | Simple, no extra deps, loses schedule on restart | ✅ Chosen for MVP |
| django-celery-beat | Persistent, dynamic schedules, adds complexity | Rejected - overkill for fixed 60s interval |
| Database table | Persistent, custom implementation | Rejected - not needed for simple polling |

**Rationale**: Fixed 60-second interval doesn't need persistence. If beat restarts, it resumes from the schedule definition. Future specs may add dynamic scheduling requiring django-celery-beat.

### Decision: Query Pattern (Sync with Threading)

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `asyncio.to_thread()` | Run sync query in thread, non-blocking | ✅ Chosen |
| `sync_to_async()` | Django-style bridge | Rejected - `to_thread()` is native Python 3.9+ |
| Pure async SQLAlchemy | Complex with Celery sync tasks | Rejected - Celery tasks run sync |

**Rationale**: Celery tasks execute synchronously. Using `asyncio.to_thread()` allows running the sync SQLAlchemy query without blocking the event loop, enabling graceful shutdown and concurrent task handling.

### Decision: Status Transition Order

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Update status → Dispatch | Prevents duplicates even if dispatch fails | ✅ Chosen |
| Dispatch → Update status | Race condition possible | Rejected - duplicate tasks risk |

**Rationale**: Updating status to `PROCESSING` BEFORE dispatching ensures that even if the dispatch fails or the worker crashes, the post won't be picked up again in the next beat cycle. This guarantees at-most-once semantics.

### Decision: Error Handling Strategy

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Try/catch + log, continue | Beat survives DB failures, retries next cycle | ✅ Chosen |
| Fail task, let Celery retry | Could block beat with many failures | Rejected - beat must stay healthy |
| Circuit breaker | Prevents cascade failures | Deferred - not needed for single task |

**Rationale**: Beat scheduler must stay healthy to maintain the schedule. Database connection failures are logged and the task completes normally, allowing the next beat cycle to retry. This prevents a transient DB issue from crashing the scheduler.

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Celery Beat Container                                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Every 60 seconds                                     │  │
│  │                                                       │  │
│  │  check_scheduled_posts()                              │  │
│  │       │                                               │  │
│  │       ▼                                               │  │
│  │  ┌─────────────────┐                                  │  │
│  │  │ Query PostgreSQL│                                  │  │
│  │  │ status=PENDING  │                                  │  │
│  │  │ scheduled_at <= │                                  │  │
│  │  │ now()           │                                  │  │
│  │  └────────┬────────┘                                  │  │
│  │           │                                           │  │
│  │           ▼                                           │  │
│  │  For each post:                                       │  │
│  │  ┌─────────────────┐    ┌──────────────────────┐     │  │
│  │  │ Update status   │───►│ process_instagram_   │     │  │
│  │  │ PROCESSING      │    │ post.delay(post_id)  │     │  │
│  │  └─────────────────┘    └──────────┬───────────┘     │  │
│  │                                    │                  │  │
│  └────────────────────────────────────┼──────────────────┘  │
│                                       │                     │
└───────────────────────────────────────┼─────────────────────┘
                                        │
                                        ▼
                              ┌─────────────────┐
                              │   Redis Queue   │
                              │   (broker)      │
                              └────────┬────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │  Worker Container│
                              │                 │
                              │ process_instagram│
                              │ _post task      │
                              └─────────────────┘
```

**Flow**:
1. Beat scheduler wakes every 60 seconds (configured in `beat_schedule`)
2. `check_scheduled_posts` queries PostgreSQL for eligible posts
3. For each post found:
   - Update status to `PROCESSING` (prevents duplicates)
   - Call `process_instagram_post.delay(post_id)` to queue task
4. Worker picks up task from Redis and executes publishing flow

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `docker-compose.yml` | Modify | Add `beat` service running `celery beat` command |
| `app/worker.py` | Modify | Add `beat_schedule` config and `check_scheduled_posts` task |

## Interfaces / Contracts

### app/worker.py Additions

```python
from celery import Celery
from celery.schedules import interval
from app.core.config import settings

# Existing Celery app from SPEC-011
celery_app = Celery("worker", broker=settings.CELERY_BROKER_URL)

# Beat schedule configuration
celery_app.conf.beat_schedule = {
    "check-scheduled-posts": {
        "task": "app.worker.check_scheduled_posts",
        "schedule": interval(seconds=60),
    },
}

@celery_app.task(bind=True, max_retries=0)
def check_scheduled_posts(self) -> dict:
    """Query for scheduled posts and dispatch processing tasks."""
    import asyncio
    import logging
    from datetime import datetime
    from sqlalchemy.orm import Session
    from sqlalchemy import select, update
    from app.models.post import Post, PostStatus
    from app.core.database import engine
    
    logger = logging.getLogger(__name__)
    dispatched_count = 0
    
    def _query_and_dispatch():
        """Sync function to query posts and dispatch tasks."""
        with Session(engine) as session:
            # Query posts ready to be published
            stmt = select(Post).where(
                Post.status == PostStatus.PENDING,
                Post.scheduled_at <= datetime.utcnow()
            ).order_by(Post.scheduled_at.asc())
            
            posts = session.execute(stmt).scalars().all()
            
            for post in posts:
                try:
                    # Transition to PROCESSING first (prevents duplicates)
                    post.status = PostStatus.PROCESSING
                    session.commit()
                    
                    # Dispatch to worker
                    process_instagram_post.delay(post.id)
                    dispatched_count += 1
                    logger.info(f"Dispatched post {post.id} for processing")
                    
                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to dispatch post {post.id}: {e}")
                    # Continue with next post
            
            return len(posts)
    
    try:
        # Run sync query in thread to avoid blocking
        total_found = asyncio.to_thread(_query_and_dispatch)
        logger.info(f"Beat cycle complete: {dispatched_count}/{total_found} posts dispatched")
        return {"found": total_found, "dispatched": dispatched_count}
        
    except Exception as e:
        logger.error(f"Beat task failed: {e}")
        # Don't retry - beat will run again in 60 seconds
        return {"error": str(e), "found": 0, "dispatched": 0}

# Existing task from SPEC-012
@celery_app.task
def process_instagram_post(post_id: int) -> str:
    # ... implementation from SPEC-012
    pass
```

### docker-compose.yml Additions

```yaml
services:
  # ... existing services (db, minio, web, tunnel, redis, worker) ...

  beat:
    build: .
    command: celery -A app.worker.celery_app beat --loglevel=info
    environment:
      DATABASE_URL: ${DATABASE_URL}
      CELERY_BROKER_URL: ${CELERY_BROKER_URL:-redis://redis:6379/0}
      DEBUG: ${DEBUG}
      SECRET_KEY: ${SECRET_KEY}
      # ... same env vars as worker ...
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - app-network
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `check_scheduled_posts` queries correctly | Mock SQLAlchemy session, verify query filters |
| Unit | Status transition PENDING → PROCESSING | Assert status update before dispatch |
| Unit | Error handling doesn't crash | Mock DB failure, verify graceful return |
| Integration | Beat container starts | `docker compose up -d beat`, check logs for "celery beat started" |
| Integration | Task runs every 60 seconds | Check logs show periodic execution |
| E2E | Full scheduled post flow | Create post with past scheduled_at, verify processing triggered |

## Migration / Rollout

No database migration required. This change:
1. Adds infrastructure only (new container + task)
2. Uses existing Post model (from SPEC-012)
3. Uses existing Celery app (from SPEC-011)

Rollout steps:
1. Ensure SPEC-011 (Celery + Redis) is deployed
2. Ensure SPEC-012 (Post model + process_instagram_post) is deployed
3. Deploy beat container: `docker compose up -d beat`
4. Verify: `docker compose logs -f beat` should show "celery beat started"
5. Test: Create PENDING post with past scheduled_at, verify task dispatched

## Open Questions

- [ ] ¿Necesitamos rate limiting entre beat y worker? → No, worker procesa a su ritmo
- [ ] ¿Qué pasa si hay miles de posts pendientes? → Considerar batching en futura versión
- [ ] ¿Persistir estado del scheduler? → Deferido a django-celery-beat si se necesitan schedules dinámicos
