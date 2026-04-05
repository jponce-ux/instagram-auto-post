# Tasks: spec-014-celery-beat-scheduler

## Phase 0: Git Branch

- [x] 0.1 Create branch `feat/014-celery-beat-scheduler` from current HEAD

## Phase 1: App (worker.py)

- [x] 1.1 Import `interval` from `celery.schedules` in `app/worker.py`
- [x] 1.2 Add `beat_schedule` config to Celery app with 60-second interval for `check_scheduled_posts` task
- [x] 1.3 Create `check_scheduled_posts` task with `@celery_app.task(bind=True, max_retries=0)` decorator
- [x] 1.4 Implement `_query_and_dispatch()` inner function using SQLAlchemy Session to query Post model
- [x] 1.5 Query posts with `status == PostStatus.PENDING` and `scheduled_at <= datetime.utcnow()`, ordered by `scheduled_at.asc()`
- [x] 1.6 In the loop: update post status to `PostStatus.PROCESSING` before dispatching `process_instagram_post.delay(post_id)`
- [x] 1.7 Wrap DB operations in try/catch with rollback on failure, log errors without crashing beat
- [x] 1.8 Use `asyncio.to_thread(_query_and_dispatch)` to run sync query non-blocking
- [x] 1.9 Return dict with `{"found": count, "dispatched": dispatched_count, "error": null}`

## Phase 2: Docker (docker-compose.yml)

- [x] 2.1 Add `beat` service to docker-compose.yml with same `build: .` as worker
- [x] 2.2 Set `command: celery -A app.worker.celery_app beat --loglevel=info`
- [x] 2.3 Include environment vars: `DATABASE_URL`, `CELERY_BROKER_URL`, `DEBUG`, `SECRET_KEY`
- [x] 2.4 Add `depends_on` for `db` (condition: service_healthy) and `redis` (condition: service_healthy)
- [x] 2.5 Add `networks: - app-network` to attach beat to existing network

## Phase 3: Verification

- [x] 3.1 Run `docker compose build beat` to verify Dockerfile image builds
- [x] 3.2 Run `docker compose up -d beat` to start beat container
- [x] 3.3 Run `docker compose logs beat` and verify "celery beat started" in output
- [x] 3.4 Wait 60+ seconds and check logs for periodic `check_scheduled_posts` task execution
- [x] 3.5 Create a test post with `status=PENDING` and `scheduled_at` in past, verify `process_instagram_post.delay()` is called
- [x] 3.6 Verify no duplicate dispatches occur on next beat cycle for already-PROCESSING posts

## Phase 4: Commit

- [x] 4.1 Run `git status` to verify modified files: `app/worker.py`, `docker-compose.yml`
- [x] 4.2 Run `git diff` to review changes
- [x] 4.3 Commit with message: `feat: add Celery Beat scheduler for automatic post publishing`
