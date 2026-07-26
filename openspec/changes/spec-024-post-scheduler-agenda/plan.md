# Plan: Post Scheduler Agenda (spec-024-post-scheduler-agenda)

## Summary

Extend the Post model (from SPEC-012) with a `scheduled_at` field and SCHEDULED status. Create the Agenda view for managing scheduled posts. Implement Celery Beat task to transition due scheduled posts to PENDING status, which triggers the existing publishing workflow.

## Technical Context

**Language/Framework**: Python 3.11+ / FastAPI
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0 (async), Celery, Redis, Alembic
**Storage**: PostgreSQL
**Testing**: pytest with async support

**Target Platform**: Web (responsive, mobile-first)
**Project Type**: FastAPI HTML dashboard with HTMX

**Depends On**: 
- SPEC-012 (Post model with states)
- SPEC-023 (Sidebar layout with Agenda route)

## Applied Lessons

None yet — new feature work.

## Architecture Decisions

| Decision | Options | Tradeoffs | Choice |
|----------|---------|-----------|--------|
| Schedule time precision | Minute-level | Second-level adds complexity without benefit | Minute-level |
| Scheduler check interval | 60s (Celery Beat) | 30s more responsive but more DB load | 60s (matches beat interval from SPEC-014) |
| Idempotency | Check if already PENDING before transition | Extra DB write but prevents duplicates | Check before transition |
| Edit grace period | Block edits <1hr before publish | Simplifies but limits flexibility | Warning only, not block |

## Data Flow

```
User Creates Scheduled Post
         │
         ▼
    POST /dashboard/schedule/post
         │
         ▼
    Validation: scheduled_at > now
         │
         ▼
    Post created with SCHEDULED status
    AND scheduled_at = user_selected_time
         │
         ▼
    HTMX response → Agenda view updates
         │
         ▼
    Celery Beat (every 60s)
         │
         ├──► Query: SCHEDULED posts WHERE scheduled_at <= now
         │
         ├──► For each due post:
         │         │
         │         ▼
         │    Update status: SCHEDULED → PENDING
         │         │
         │         ▼
         │    dispatch process_instagram_post.delay(post_id)
         │
         ▼
    Post enters normal publishing flow (SPEC-012)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/models/post.py` | Modify | Add `scheduled_at` field, SCHEDULED status |
| `migrations/versions/` | New | Migration for `scheduled_at` column |
| `app/dashboard/routes.py` | Modify | Add POST /schedule/post, GET /schedule, PATCH /schedule/post/:id |
| `app/dashboard/service.py` | Modify | Add schedule-related service methods |
| `app/templates/dashboard/schedule.html` | Modify | Replace placeholder with full Agenda UI |
| `app/worker.py` | Modify | Add `check_scheduled_posts` Celery Beat task |

## Post Model Changes

```python
# app/models/post.py - additions

class PostStatus(enum.Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"  # NEW
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"

class Post(Base):
    # ... existing fields ...
    
    scheduled_at = Column(DateTime(timezone=True), nullable=True)  # NEW
    
    # Relationships
    # ... existing relationships ...
```

## Celery Beat Task

```python
# app/worker.py - additions

@celery_app.task
def check_scheduled_posts():
    """Check for due scheduled posts and transition them to PENDING."""
    asyncio.run(_check_scheduled_posts_async())

async def _check_scheduled_posts_async():
    async with AsyncSessionLocal() as db:
        # Query: SCHEDULED posts where scheduled_at <= now
        # For each: update status to PENDING
        # dispatch process_instagram_post.delay(post_id)
        pass
```

## API Routes

### POST /dashboard/schedule/post

Create a new scheduled post.

**Request**:
```
caption: str (optional)
scheduled_at: ISO datetime string (required for scheduled)
ig_account_id: int
file: UploadFile
```

**Response**: HTML fragment (HTMX swap of agenda list)

### GET /dashboard/schedule

Return agenda view with all scheduled posts.

**Response**: Full page (app_layout + schedule content)

### PATCH /dashboard/schedule/post/:id

Update scheduled post (caption, scheduled_at, or ig_account_id).

**Request**:
```
caption?: str
scheduled_at?: ISO datetime string
```

**Response**: HTML fragment or redirect

### DELETE /dashboard/schedule/post/:id

Delete a scheduled post (only if status is SCHEDULED).

**Response**: HTMX trigger to refresh list

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | Post model with scheduled_at | SQLAlchemy model test |
| Unit | scheduled_at validation | Mock datetime, test validation |
| Integration | Create scheduled post via API | TestClient POST |
| Integration | Celery Beat task | Mock AsyncSession, assert PENDING transition |
| Manual | Full flow: schedule → publish | End-to-end with staging |

## Risk Assessment

- **Risk**: Celery Beat misses due posts after restart
  - **Mitigation**: Beat has persistence. On restart, catches up with due posts.
- **Risk**: Double-processing if task runs twice
  - **Mitigation**: Idempotency check (if already PENDING, skip)
- **Risk**: Race condition between web edit and beat transition
  - **Mitigation**: Use `with_for_update()` row lock when transitioning

## Rollback Plan

1. Remove `scheduled_at` column (Alembic downgrade)
2. Remove SCHEDULED from PostStatus enum
3. Remove `check_scheduled_posts` task from worker
4. Revert schedule.html to placeholder content
5. Posts created with scheduled_at retain column but it's ignored
