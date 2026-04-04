# Delta for scheduled-post-scheduler (NEW)

## Purpose

Beat-driven scheduler that polls the database for posts due to be published and dispatches processing tasks automatically.

---

## scheduled-post-scheduler (NEW)

### Requirement: Celery Beat Scheduler Service

The system MUST provide a Celery Beat scheduler service running as a separate container.

The beat service SHALL run the `celery beat` command with the app from `app/worker.py`.

#### Scenario: Beat container starts

- GIVEN docker-compose.yml defines a `beat` service
- WHEN `docker compose up -d beat` is executed
- THEN beat container starts successfully
- AND logs show "celery beat started"
- AND beat begins polling on schedule

---

### Requirement: Beat Schedule Configuration

The system MUST configure `beat_schedule` in the Celery app to run `check_scheduled_posts` every 60 seconds.

The configuration SHALL use `celery.schedules.interval` for the 60-second interval.

#### Scenario: Beat schedule registered

- GIVEN `app/worker.py` has `beat_schedule` configured
- WHEN Celery Beat starts
- THEN `check_scheduled_posts` task is registered
- AND task is scheduled to run every 60 seconds
- AND logs confirm schedule entry

---

### Requirement: Scheduled Post Query

The system MUST query for posts with `status=PENDING` and `scheduled_at <= now()`.

The query SHALL be executed in a thread-safe context to avoid blocking the event loop.

#### Scenario: Query finds due posts

- GIVEN posts exist with status PENDING and scheduled_at in the past
- WHEN `check_scheduled_posts` executes
- THEN query returns all posts where status=PENDING AND scheduled_at <= now()
- AND posts are ordered by scheduled_at ASC

#### Scenario: Query skips future posts

- GIVEN posts exist with status PENDING but scheduled_at in the future
- WHEN `check_scheduled_posts` executes
- THEN future posts are NOT returned by the query

---

### Requirement: Dispatch Processing Tasks

The system MUST dispatch `process_instagram_post.delay(post_id)` for each eligible post found.

The dispatch SHALL be non-blocking and use Celery's delay method.

#### Scenario: Dispatch for single post

- GIVEN one post is found with status=PENDING and scheduled_at <= now()
- WHEN `check_scheduled_posts` runs
- THEN `process_instagram_post.delay(post_id)` is called once
- AND task is queued in Redis

#### Scenario: Dispatch for multiple posts

- GIVEN multiple posts are found due for publishing
- WHEN `check_scheduled_posts` runs
- THEN `process_instagram_post.delay()` is called for EACH post
- AND all tasks are dispatched in a single beat cycle

---

### Requirement: Status Transition to PROCESSING

The system MUST update post status to PROCESSING before dispatching to prevent duplicate processing.

If a post is already PROCESSING, it SHALL be skipped.

#### Scenario: Transition from PENDING to PROCESSING

- GIVEN a post with status=PENDING and scheduled_at <= now()
- WHEN `check_scheduled_posts` dispatches the task
- THEN post status is updated to PROCESSING first
- AND then task is dispatched

#### Scenario: Skip already PROCESSING post

- GIVEN a post with status=PROCESSING and scheduled_at <= now()
- WHEN `check_scheduled_posts` runs
- THEN the post is NOT dispatched again
- AND no duplicate task is created