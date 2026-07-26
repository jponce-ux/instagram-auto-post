# Tasks: Post Scheduler Agenda

**Status**: Not Started
**Progress**: 0/12 tasks
**Current Phase**: —

## Dependencies & Execution Order

- Phase 1 (Database) must complete before Phase 2 (Routes)
- Phase 2 (Routes) must complete before Phase 3 (UI)
- Phase 3 (UI) must complete before Phase 4 (Beat)
- Tasks marked `[P]` are parallelizable within phase

---

## Phase 1: Database

### T001 [P] Add scheduled_at to Post model

Modify `app/models/post.py` to add `scheduled_at` field and SCHEDULED status to PostStatus enum.

**Deliverable**: Updated `app/models/post.py`
**File**: `app/models/post.py`
**Acceptance**:
- [ ] `scheduled_at` field added as nullable DateTime(timezone=True)
- [ ] `SCHEDULED = "scheduled"` added to PostStatus enum
- [ ] Model imports work correctly

---

### T002 [P] Create Alembic migration

Create migration to add `scheduled_at` column to posts table.

**Deliverable**: Migration file in `migrations/versions/`
**File**: `migrations/versions/xxx_add_scheduled_at_to_posts.py`
**Acceptance**:
- [ ] Migration created with `alembic revision --autogenerate -m "add_scheduled_at_to_posts"`
- [ ] `scheduled_at` column is nullable (backward compatible)
- [ ] Can apply with `alembic upgrade head`

---

## Phase 2: Routes & Service

### T003 [P] Add schedule routes to dashboard service

Add service methods in `app/dashboard/service.py` for schedule operations.

**Deliverable**: Updated `app/dashboard/service.py`
**File**: `app/dashboard/service.py`
**Acceptance**:
- [ ] `create_scheduled_post()` method
- [ ] `get_scheduled_posts()` method (returns list sorted by scheduled_at)
- [ ] `update_scheduled_post()` method
- [ ] `delete_scheduled_post()` method
- [ ] Validation: scheduled_at must be in future

---

### T004 [P] Add schedule API routes

Add/modify routes in `app/dashboard/routes.py` for schedule endpoints.

**Deliverable**: Updated `app/dashboard/routes.py`
**File**: `app/dashboard/routes.py`
**Acceptance**:
- [ ] POST `/dashboard/schedule/post` - create scheduled post
- [ ] GET `/dashboard/schedule` - return agenda view
- [ ] PATCH `/dashboard/schedule/post/{id}` - update scheduled post
- [ ] DELETE `/dashboard/schedule/post/{id}` - delete scheduled post
- [ ] All routes protected by `get_current_user` dependency
- [ ] HTMX request handling for partial updates

---

## Phase 3: UI

### T005 Refactor schedule.html with full Agenda UI

Replace placeholder content in `app/templates/dashboard/schedule.html` with full Agenda interface.

**Deliverable**: Updated `app/templates/dashboard/schedule.html`
**File**: `app/templates/dashboard/schedule.html`
**Acceptance**:
- [ ] Post creation form with schedule date/time picker
- [ ] Scheduled posts list (or empty state)
- [ ] Edit and delete actions on each scheduled post
- [ ] HTMX form submission
- [ ] Responsive design (mobile-friendly)

---

### T006 Add schedule post form component

Create the schedule form component that can be reused in the Agenda view.

**Deliverable**: `app/templates/components/schedule_form.html`
**File**: `app/templates/components/schedule_form.html`
**Acceptance**:
- [ ] Image upload field
- [ ] Caption textarea
- [ ] Date/time picker for scheduled_at
- [ ] Account selector dropdown
- [ ] Validation: scheduled_at must be in future
- [ ] HTMX submit to `/dashboard/schedule/post`

---

## Phase 4: Celery Beat

### T007 [P] Add check_scheduled_posts task

Add Celery Beat task in `app/worker.py` to check and transition due scheduled posts.

**Deliverable**: Updated `app/worker.py`
**File**: `app/worker.py`
**Acceptance**:
- [ ] `check_scheduled_posts()` task defined
- [ ] Task queries: SCHEDULED posts WHERE scheduled_at <= now
- [ ] Task transitions each to PENDING status
- [ ] Task dispatches `process_instagram_post.delay(post_id)` for each
- [ ] Idempotent: skips already-PENDING posts

---

### T008 [P] Register beat schedule

Update Celery Beat configuration to run `check_scheduled_posts` every 60 seconds.

**Deliverable**: Updated `app/worker.py` beat_schedule
**File**: `app/worker.py`
**Acceptance**:
- [ ] `check_scheduled_posts` runs every 60 seconds
- [ ] Beat schedule registered correctly
- [ ] Task can be triggered manually for testing

---

## Phase 5: Integration Testing

### T009 Test create scheduled post

Verify creating a post with future date/time saves correctly.

**Deliverable**: Test checklist
**File**: Manual testing
**Acceptance**:
- [ ] Post created with SCHEDULED status
- [ ] scheduled_at matches selected time
- [ ] Post appears in Agenda list

---

### T010 Test edit scheduled post

Verify editing scheduled time of unpublished post works.

**Deliverable**: Test checklist
**File**: Manual testing
**Acceptance**:
- [ ] Can change scheduled_at to different future time
- [ ] Validation error if trying to set past time
- [ ] Changes persist after page reload

---

### T011 Test delete scheduled post

Verify deleting scheduled post removes it and prevents publishing.

**Deliverable**: Test checklist
**File**: Manual testing
**Acceptance**:
- [ ] Deleted post does not appear in list
- [ ] Deleted post does not publish at scheduled time
- [ ] Cannot delete post that is PROCESSING or PUBLISHED

---

### T012 Test beat task transition

Verify Celery Beat task transitions due posts to PENDING.

**Deliverable**: Test checklist
**File**: Manual testing
**Acceptance**:
- [ ] `check_scheduled_posts` task can be triggered manually
- [ ] Due posts transition from SCHEDULED to PENDING
- [ ] Transitioned posts enter publishing flow

---

## Progress Summary

- Phase 1 (Database): 2 tasks
- Phase 2 (Routes & Service): 2 tasks
- Phase 3 (UI): 2 tasks
- Phase 4 (Celery Beat): 2 tasks
- Phase 5 (Testing): 4 tasks

**Total**: 12 tasks
