# Tasks: Email History Tracking

## Phase 1: Database & Model
- [x] **T1.1** Create Alembic migration for `email_logs` table
  - File: `migrations/versions/xxx_create_email_logs.py`
  - Deliverable: Migration file with table, indexes, constraints
  - Acceptance: `uv run alembic upgrade head` succeeds
  - Size: S

- [x] **T1.2** Create `EmailLog` SQLAlchemy model
  - File: `app/models/email_log.py`
  - Deliverable: Model with all columns, relationships, status enum
  - Acceptance: Model imports without errors, matches migration
  - Size: S

- [x] **T1.3** Register model in `app/models/__init__.py`
  - File: `app/models/__init__.py`
  - Deliverable: EmailLog imported and available
  - Acceptance: `from app.models import EmailLog` works
  - Size: XS

## Phase 2: EmailService Updates
- [x] **T2.1** Update `EmailService.send_welcome_email()` to create log
  - File: `app/services/email.py`
  - Deliverable: Log entry created before queuing Celery task
  - Acceptance: Registration creates email_logs record with status "queued"
  - Size: M

- [x] **T2.2** Add idempotency check to EmailService
  - File: `app/services/email.py`
  - Deliverable: Skip send if successful email exists within 24h
  - Acceptance: Duplicate registration within 24h doesn't send second email
  - Size: M

- [x] **T2.3** Pass `log_id` to Celery task
  - File: `app/services/email.py`
  - Deliverable: Celery task receives log_id parameter
  - Acceptance: Task signature includes log_id
  - Size: S

## Phase 3: Celery Task Updates
- [x] **T3.1** Update `task_dispatch_resend_email()` to accept log_id
  - File: `app/worker.py`
  - Deliverable: Task accepts optional log_id parameter
  - Acceptance: Task runs with and without log_id
  - Size: S

- [x] **T3.2** Update log status on success
  - File: `app/worker.py`
  - Deliverable: Log updated to "sent" with sent_at timestamp
  - Acceptance: Successful send updates log correctly
  - Size: M

- [x] **T3.3** Update log status on failure
  - File: `app/worker.py`
  - Deliverable: Log updated to "failed" with error_message
  - Acceptance: Failed send updates log with error details
  - Size: M

- [x] **T3.4** Track retry count in log
  - File: `app/worker.py`
  - Deliverable: retry_count incremented on each retry
  - Acceptance: Log shows correct retry count after failures
  - Size: S

## Phase 4: Query Methods
- [x] **T4.1** Add `EmailLog.get_by_user()` class method
  - File: `app/models/email_log.py`
  - Deliverable: Query method returns user's email logs
  - Acceptance: Returns logs ordered by queued_at desc
  - Size: S

- [x] **T4.2** Add `EmailLog.get_by_status()` class method
  - File: `app/models/email_log.py`
  - Deliverable: Query method filters by status
  - Acceptance: Returns only logs matching status
  - Size: S

- [x] **T4.3** Add `EmailLog.check_idempotency()` class method
  - File: `app/models/email_log.py`
  - Deliverable: Checks for recent successful sends
  - Acceptance: Returns True if sent within 24h, False otherwise
  - Size: S

## Phase 5: Tests
- [x] **T5.1** Unit tests for EmailLog model methods
  - File: `tests/test_email_log_model.py`
  - Deliverable: Tests for get_by_user, get_by_status, check_idempotency
  - Acceptance: All tests pass
  - Size: M

- [x] **T5.2** Integration tests for log creation during registration
  - File: `tests/test_email.py`
  - Deliverable: Test verifies email_logs record created
  - Acceptance: Registration creates log with correct fields
  - Size: M

- [x] **T5.3** Celery task tests for status updates
  - File: `tests/test_email.py`
  - Deliverable: Tests for success/failure/retry status updates
  - Acceptance: All status update scenarios covered
  - Size: M

- [x] **T5.4** Idempotency tests
  - File: `tests/test_email.py`
  - Deliverable: Test for duplicate prevention
  - Acceptance: Second send within 24h is skipped
  - Size: S

## Phase 6: Verification
- [x] **T6.1** Run full test suite
  - Deliverable: All tests pass (78+ new tests)
  - Acceptance: `uv run pytest tests/ -v` passes
  - Size: S

- [x] **T6.2** Docker verification
  - Deliverable: Email logging works in Docker
  - Acceptance: Registration creates log, worker updates status
  - Size: S

## Dependencies
- SPEC-017 (Email Notifications) must be complete
- T1.1 → T1.2 → T1.3 (sequential)
- T2.1, T2.2, T2.3 depend on T1.x
- T3.x depend on T2.x
- T4.x depend on T1.2
- T5.x depend on T2.x, T3.x, T4.x
- T6.x depend on T5.x
