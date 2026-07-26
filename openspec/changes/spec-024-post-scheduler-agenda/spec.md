# Feature Spec: Post Scheduler Agenda

**Feature Branch**: `feat/spec-024-post-scheduler-agenda`
**Created**: 2026-07-26
**Status**: Draft
**Type**: Feature
**Input**: Post scheduling for future publications - separate "Agenda de Publicaciones" section
**Source**: Manual input
**Depends On**: spec-012-publicacion-estados-post-logica, spec-023-app-sidebar-layout

## User Scenarios & Testing

### User Story 1 - Schedule a Post (Priority: P1)

The user can create a post and schedule it for a future date/time instead of publishing immediately.

**Why this priority**: Core feature of the Agenda section - allows users to plan content ahead of time.

**Independent Test**: User can create a scheduled post and see it in the agenda list.

**Acceptance Scenarios**:
1. **Given** a user is on the Agenda view with linked accounts, **When** they fill the post form and select a future date/time, **Then** the post is saved with status SCHEDULED and `scheduled_at` is set
2. **Given** a user creates a post without selecting schedule date, **When** they submit the form, **Then** the post is saved with status PENDING (immediate publish)
3. **Given** a user tries to schedule a post in the past, **When** they select a past date/time, **Then** the system shows validation error "Scheduled date must be in the future"

### User Story 2 - View Scheduled Posts (Priority: P1)

The user can see all their scheduled posts in a calendar or list view.

**Why this priority**: Users need visibility into upcoming scheduled content.

**Independent Test**: Scheduled posts appear in the Agenda view without requiring page reload.

**Acceptance Scenarios**:
1. **Given** a user has scheduled posts, **When** they navigate to the Agenda section, **Then** they see a list of scheduled posts sorted by scheduled date (nearest first)
2. **Given** a user has no scheduled posts, **When** they navigate to the Agenda section, **Then** they see an empty state "No hay publicaciones programadas"
3. **Given** a scheduled post is approaching its scheduled time, **When** the time arrives, **Then** the post status changes from SCHEDULED to PENDING and enters the publish queue

### User Story 3 - Edit Scheduled Post (Priority: P2)

The user can modify the content or scheduled time of an unpublished scheduled post.

**Why this priority**: Flexibility to adjust plans without deleting and recreating.

**Independent Test**: User can change scheduled time and see updated time reflected immediately.

**Acceptance Scenarios**:
1. **Given** a user has a SCHEDULED post, **When** they click "Edit" on that post, **Then** they can modify caption, media, or scheduled time
2. **Given** a user changes the scheduled time to a new future time, **When** they save, **Then** `scheduled_at` is updated and status remains SCHEDULED
3. **Given** a user modifies a post within 1 hour of scheduled time, **When** they save, **Then** the system warns "Changes within 1 hour of publishing may cause delays"

### User Story 4 - Cancel Scheduled Post (Priority: P2)

The user can cancel/delete a scheduled post before it publishes.

**Why this priority**: Plans change - users need ability to remove scheduled content.

**Independent Test**: Deleted scheduled posts no longer appear in agenda and do not publish.

**Acceptance Scenarios**:
1. **Given** a user has a SCHEDULED post, **When** they click "Delete" and confirm, **Then** the post is removed from database and does not publish
2. **Given** a user tries to delete a post that is already PROCESSING, **When** they click delete, **Then** the system shows error "Cannot delete post that is being published"

## Edge Cases

- **Scheduled post with expired media URL**: Regenerate presigned URL before publish
- **Scheduled post for account that lost token**: Mark as FAILED with "account disconnected" error
- **Multiple posts scheduled for same time**: Process in order of creation (FIFO)
- **System restart during scheduled time**: Celery Beat handles missed tasks via idempotency check

## Functional Requirements

- FR-001: The system MUST allow users to select a future date/time when creating a post
- FR-002: The system MUST save posts with `scheduled_at` as SCHEDULED status
- FR-003: The system MUST display all SCHEDULED posts in the Agenda view sorted by `scheduled_at`
- FR-004: The system MUST allow editing `scheduled_at` for posts in SCHEDULED status
- FR-005: The system MUST allow deletion of posts in SCHEDULED status
- FR-006: The system MUST transition SCHEDULED posts to PENDING when `scheduled_at` time arrives
- FR-007: The Celery Beat scheduler MUST check for due scheduled posts every 60 seconds
- FR-008: The system MUST validate that `scheduled_at` is in the future when creating/editing
- FR-009: The system MUST prevent deletion of posts in PROCESSING or PUBLISHED status via Agenda UI

## Key Entities

### Post (extended from SPEC-012)

| Field | Type | Description |
|-------|------|-------------|
| `scheduled_at` | DateTime (nullable) | When to transition to PENDING |
| `status` | PostStatus enum | PENDING, SCHEDULED, PROCESSING, PUBLISHED, FAILED |

### PostStatus Enum (extended)

```python
class PostStatus(enum.Enum):
    PENDING = "pending"      # Ready to process
    SCHEDULED = "scheduled" # Waiting for scheduled time
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"
```

## Design References

**Source**: User description - "Agenda de Publicaciones" as section in sidebar
**Resources**: See `resources/` directory for reference designs

| Resource | Description | Relevant Stories |
|----------|-------------|-----------------|
| `resources/agenda-view.png` | Agenda list view mockup | US-1, US-2 |

## Success Criteria

1. User can create a post with a future scheduled date/time
2. Scheduled posts appear in Agenda view sorted by scheduled date
3. User can edit scheduled time of unpublished scheduled posts
4. User can delete scheduled posts before they publish
5. Scheduled posts automatically transition to PENDING when time arrives
6. Celery Beat processes due scheduled posts every 60 seconds
7. Validation prevents scheduling in the past
