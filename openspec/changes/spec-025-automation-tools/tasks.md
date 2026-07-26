# Tasks: Automation Tools

**Status**: Not Started
**Progress**: 0/16 tasks
**Current Phase**: —

## Dependencies & Execution Order

- Phase 1 (Database) must complete before Phase 2 (Routes & Service)
- Phase 2 must complete before Phase 3 (UI)
- Phase 3 must complete before Phase 4 (Recurring Schedules)
- Tasks marked `[P]` are parallelizable within phase

---

## Phase 1: Database

### T001 [P] Create HashtagCollection model

Create `app/models/hashtag_collection.py` with SQLAlchemy model.

**Deliverable**: `app/models/hashtag_collection.py`
**File**: `app/models/hashtag_collection.py`
**Acceptance**:
- [ ] Model with id, user_id, name, hashtags, created_at
- [ ] Proper foreign key to users
- [ ] Can be imported from `app.models`

---

### T002 [P] Create ContentTemplate model

Create `app/models/content_template.py` with SQLAlchemy model.

**Deliverable**: `app/models/content_template.py`
**File**: `app/models/content_template.py`
**Acceptance**:
- [ ] Model with id, user_id, name, caption_template, created_at
- [ ] Proper foreign key to users
- [ ] Can be imported from `app.models`

---

### T003 [P] Create RecurringSchedule model

Create `app/models/recurring_schedule.py` with SQLAlchemy model.

**Deliverable**: `app/models/recurring_schedule.py`
**File**: `app/models/recurring_schedule.py`
**Acceptance**:
- [ ] Model with all fields (frequency, time_of_day, day_of_week, is_active, etc.)
- [ ] Proper foreign keys
- [ ] Can be imported from `app.models`

---

### T004 [P] Update models __init__.py

Export new models from `app/models/__init__.py`.

**Deliverable**: Updated `app/models/__init__.py`
**File**: `app/models/__init__.py`
**Acceptance**:
- [ ] HashtagCollection exported
- [ ] ContentTemplate exported
- [ ] RecurringSchedule exported

---

### T005 [P] Create Alembic migrations

Create migrations for three new tables.

**Deliverable**: Migration files in `migrations/versions/`
**File**: `migrations/versions/xxx_add_automation_tables.py`
**Acceptance**:
- [ ] Migration creates hashtag_collections table
- [ ] Migration creates content_templates table
- [ ] Migration creates recurring_schedules table
- [ ] Can apply with `alembic upgrade head`

---

## Phase 2: Routes & Service

### T006 [P] Add automation service methods

Add CRUD methods in `app/dashboard/service.py` for all three entity types.

**Deliverable**: Updated `app/dashboard/service.py`
**File**: `app/dashboard/service.py`
**Acceptance**:
- [ ] HashtagCollection CRUD methods
- [ ] ContentTemplate CRUD methods
- [ ] RecurringSchedule CRUD methods
- [ ] `calculate_best_times()` method for analytics
- [ ] Template placeholder substitution method

---

### T007 [P] Add automation API routes

Add routes in `app/dashboard/routes.py` for all automation endpoints.

**Deliverable**: Updated `app/dashboard/routes.py`
**File**: `app/dashboard/routes.py`
**Acceptance**:
- [ ] GET/POST/PUT/DELETE for /hashtags
- [ ] GET/POST/PUT/DELETE for /templates
- [ ] GET/POST/PUT/DELETE for /schedules
- [ ] POST /schedules/{id}/pause and /resume
- [ ] All routes protected by get_current_user
- [ ] HTMX request handling

---

## Phase 3: UI

### T008 Refactor automation.html with full UI

Replace placeholder content in `app/templates/dashboard/automation.html` with full Automation interface.

**Deliverable**: Updated `app/templates/dashboard/automation.html`
**File**: `app/templates/dashboard/automation.html`
**Acceptance**:
- [ ] Three tabs or sections: Hashtags, Templates, Schedules
- [ ] List views for each entity type
- [ ] Create/Edit forms (can be modals or inline)
- [ ] Responsive design

---

### T009 [P] Create hashtag form component

Create `app/templates/components/hashtag_form.html`.

**Deliverable**: `app/templates/components/hashtag_form.html`
**File**: `app/templates/components/hashtag_form.html`
**Acceptance**:
- [ ] Name input field
- [ ] Hashtags textarea (comma-separated)
- [ ] HTMX submit to appropriate endpoint

---

### T010 [P] Create template form component

Create `app/templates/components/template_form.html`.

**Deliverable**: `app/templates/components/template_form.html`
**File**: `app/templates/components/template_form.html`
**Acceptance**:
- [ ] Name input field
- [ ] Caption template textarea with {{placeholder}} hints
- [ ] HTMX submit to appropriate endpoint

---

### T011 [P] Create recurring schedule form component

Create `app/templates/components/schedule_form.html`.

**Deliverable**: `app/templates/components/schedule_form.html`
**File**: `app/templates/components/schedule_form.html`
**Acceptance**:
- [ ] Frequency selector (daily/weekly)
- [ ] Time picker
- [ ] Day of week selector (for weekly)
- [ ] Template selector dropdown
- [ ] Hashtag collection selector dropdown
- [ ] HTMX submit to appropriate endpoint

---

## Phase 4: Recurring Schedules (Celery)

### T012 [P] Add check_recurring_schedules task

Add Celery task to `app/worker.py` that processes recurring schedules.

**Deliverable**: Updated `app/worker.py`
**File**: `app/worker.py`
**Acceptance**:
- [ ] Task queries active RecurringSchedules
- [ ] Calculates next occurrence
- [ ] Creates Post with SCHEDULED status if due
- [ ] Idempotent (doesn't create duplicates)

---

### T013 [P] Register beat schedule

Add `check_recurring_schedules` to Celery Beat schedule (every 60s).

**Deliverable**: Updated `app/worker.py` beat_schedule
**File**: `app/worker.py`
**Acceptance**:
- [ ] Task runs every 60 seconds
- [ ] Can be triggered manually for testing

---

## Phase 5: Integration Testing

### T014 Test hashtag collection CRUD

Verify creating, editing, and deleting hashtag collections works.

**Deliverable**: Test checklist
**File**: Manual testing
**Acceptance**:
- [ ] Can create new collection
- [ ] Can edit collection
- [ ] Can delete collection
- [ ] Collection available in post form

---

### T015 Test content template with placeholders

Verify template creation and use with placeholder substitution.

**Deliverable**: Test checklist
**File**: Manual testing
**Acceptance**:
- [ ] Can create template with {{placeholder}}
- [ ] Placeholder appears as input field in post form
- [ ] Filled value appears in final caption

---

### T016 Test recurring schedule creation

Verify recurring schedule creates scheduled posts automatically.

**Deliverable**: Test checklist
**File**: Manual testing
**Acceptance**:
- [ ] Can create daily recurring schedule
- [ ] Can create weekly recurring schedule
- [ ] Schedule appears in list when active
- [ ] Pausing stops post creation
- [ ] Resuming resumes post creation

---

## Progress Summary

- Phase 1 (Database): 5 tasks
- Phase 2 (Routes & Service): 2 tasks
- Phase 3 (UI): 4 tasks
- Phase 4 (Celery): 2 tasks
- Phase 5 (Testing): 3 tasks

**Total**: 16 tasks
