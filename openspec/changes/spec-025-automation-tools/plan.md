# Plan: Automation Tools (spec-025-automation-tools)

## Summary

Implement automation tools for maintaining Instagram account activity: hashtag collections, content templates, and recurring post schedules. These features allow users to streamline their posting workflow and maintain consistent engagement.

## Technical Context

**Language/Framework**: Python 3.11+ / FastAPI
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0 (async), Celery, Redis, Alembic
**Storage**: PostgreSQL
**Testing**: pytest with async support

**Target Platform**: Web (responsive, mobile-first)
**Project Type**: FastAPI HTML dashboard with HTMX

**Depends On**: 
- SPEC-012 (Post model with states)
- SPEC-023 (Sidebar layout with Automation route)

## Applied Lessons

None yet — new feature work.

## Architecture Decisions

| Decision | Options | Tradeoffs | Choice |
|----------|---------|-----------|--------|
| Placeholder syntax | `{{name}}` Mustache-style | Custom regex simpler | `{{name}}` Mustache-style |
| Recurring schedule storage | Recurrence rule string vs explicit fields | Explicit: easier queries; RRULE: more flexible | Explicit fields (frequency, time, day_of_week) |
| Schedule occurrence generation | On-demand (at publish time) vs ahead-of-time | On-demand: less storage; Ahead: predictable | On-demand when checking due schedules |
| Best times algorithm | Simple avg engagement by hour vs ML | Simple: works with small data; ML: more accurate | Simple avg engagement by hour |

## Data Flow

### Hashtag Collections
```
User creates collection
        │
        ▼
   POST /dashboard/automation/hashtags
        │
        ▼
   HashtagCollection saved
        │
        ▼
   Available in post form dropdown
```

### Content Templates
```
User creates template "Promo: {{product}} is {{discount}}% off!"
        │
        ▼
   POST /dashboard/automation/templates
        │
        ▼
   ContentTemplate saved
        │
        ▼
   Available in post form (with placeholder inputs)
```

### Recurring Schedules
```
Celery Beat (every 60s)
        │
        ├──► Query active RecurringSchedules
        │
        ├──► For each schedule:
        │         │
        │         ▼
        │    Calculate next occurrence
        │         │
        │         ▼
        │    If occurrence is due (not yet created):
        │         │
        │         ▼
        │    Create Post with SCHEDULED status
        │    (use template + hashtags if configured)
        │
        ▼
    Posts appear in Agenda view
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/models/hashtag_collection.py` | Create | HashtagCollection model |
| `app/models/content_template.py` | Create | ContentTemplate model |
| `app/models/recurring_schedule.py` | Create | RecurringSchedule model |
| `app/models/__init__.py` | Modify | Export new models |
| `migrations/versions/` | New | Migrations for new tables |
| `app/dashboard/routes.py` | Modify | Add automation CRUD routes |
| `app/dashboard/service.py` | Modify | Add automation service methods |
| `app/templates/dashboard/automation.html` | Modify | Replace placeholder with full UI |
| `app/templates/components/hashtag_form.html` | Create | Hashtag collection form |
| `app/templates/components/template_form.html` | Create | Template form |
| `app/templates/components/schedule_form.html` | Create | Recurring schedule form |
| `app/worker.py` | Modify | Add recurring schedule check task |

## Models

### HashtagCollection
```python
class HashtagCollection(Base):
    __tablename__ = "hashtag_collections"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    hashtags = Column(Text, nullable=False)  # Comma-separated
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### ContentTemplate
```python
class ContentTemplate(Base):
    __tablename__ = "content_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    caption_template = Column(Text, nullable=False)  # With {{placeholder}}
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### RecurringSchedule
```python
class RecurringSchedule(Base):
    __tablename__ = "recurring_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ig_account_id = Column(Integer, ForeignKey("instagram_accounts.id"), nullable=False)
    frequency = Column(String(20), nullable=False)  # "daily", "weekly"
    time_of_day = Column(Time, nullable=False)
    day_of_week = Column(Integer, nullable=True)  # 0-6, only for weekly
    template_id = Column(Integer, ForeignKey("content_templates.id"), nullable=True)
    hashtag_collection_id = Column(Integer, ForeignKey("hashtag_collections.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

## API Routes

### Hashtags
- `GET /dashboard/automation/hashtags` - List all collections
- `POST /dashboard/automation/hashtags` - Create collection
- `PUT /dashboard/automation/hashtags/{id}` - Update collection
- `DELETE /dashboard/automation/hashtags/{id}` - Delete collection

### Templates
- `GET /dashboard/automation/templates` - List all templates
- `POST /dashboard/automation/templates` - Create template
- `PUT /dashboard/automation/templates/{id}` - Update template
- `DELETE /dashboard/automation/templates/{id}` - Delete template

### Recurring Schedules
- `GET /dashboard/automation/schedules` - List all schedules
- `POST /dashboard/automation/schedules` - Create schedule
- `PUT /dashboard/automation/schedules/{id}` - Update schedule
- `DELETE /dashboard/automation/schedules/{id}` - Delete schedule
- `POST /dashboard/automation/schedules/{id}/pause` - Pause schedule
- `POST /dashboard/automation/schedules/{id}/resume` - Resume schedule

## Best Times Algorithm

```python
def calculate_best_times(posts: list[Post]) -> list[dict]:
    """Calculate best posting times based on engagement data."""
    if len(posts) < 10:
        return []  # Not enough data
    
    # Group by hour of day
    hourly_engagement = defaultdict(list)
    for post in posts:
        if post.published_at and post.ig_media_id:
            hour = post.published_at.hour
            # Engagement = likes + comments (from media insights if available)
            engagement = get_post_engagement(post.ig_media_id)
            hourly_engagement[hour].append(engagement)
    
    # Calculate average per hour
    averages = [
        {"hour": h, "avg_engagement": sum(v) / len(v)}
        for h, v in hourly_engagement.items()
    ]
    
    # Sort and return top 3
    return sorted(averages, key=lambda x: x["avg_engagement"], reverse=True)[:3]
```

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | HashtagCollection model | SQLAlchemy model test |
| Unit | ContentTemplate placeholder substitution | Mock template, test regex |
| Unit | Best times calculation | Mock posts, assert top 3 |
| Integration | CRUD operations via API | TestClient |
| Integration | Recurring schedule task | Mock AsyncSession, assert Post created |
| Manual | Full automation flow | End-to-end testing |

## Risk Assessment

- **Risk**: Recurring schedules create too many posts (user confusion)
  - **Mitigation**: Show warning when schedule would create >7 posts/week
- **Risk**: Templates with wrong placeholders cause post failure
  - **Mitigation**: Validate template syntax on save, validate placeholders on use
- **Risk**: Best times calculation is wrong with sparse data
  - **Mitigation**: Require minimum 10 published posts before showing suggestions

## Rollback Plan

1. Remove new model tables (Alembic downgrade)
2. Remove automation routes from routes.py
3. Remove automation service methods
4. Revert automation.html to placeholder
5. Posts created with automation settings retain template/hashtag refs (now orphaned - acceptable for v1)
