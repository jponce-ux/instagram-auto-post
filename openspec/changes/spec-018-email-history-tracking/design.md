# Design: Email History Tracking

## Architecture

### Component Overview
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   EmailService  │────▶│  email_logs DB   │────▶│  Celery Task    │
│  (create log)   │     │  (queued)        │     │ (update status) │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### Implementation Plan

#### 1. Database Migration
- Create `email_logs` table with all columns from spec
- Add indexes for performance
- Use Alembic for migration

#### 2. SQLAlchemy Model
- New `EmailLog` model in `app/models/email_log.py`
- Relationship to `User` model (optional, nullable FK)
- Status enum for type safety

#### 3. EmailService Updates
- `EmailService.send_welcome_email()` creates log entry before queuing
- Pass `log_id` to Celery task for status updates
- Add idempotency check (skip if recent successful send exists)

#### 4. Celery Task Updates
- `task_dispatch_resend_email()` accepts optional `log_id`
- Updates log status on success/failure
- Handles retry count tracking

#### 5. Query Methods
- Add `EmailLog.get_by_user()` class method
- Add `EmailLog.get_by_status()` class method
- Add `EmailLog.check_idempotency()` class method

## Data Flow

### Registration Flow (Updated)
```
1. User registers → POST /auth/register
2. Create user in DB
3. EmailService.send_welcome_email():
   a. Check idempotency (skip if sent within 24h)
   b. Create email_logs record (status: queued)
   c. Queue Celery task with log_id
4. Return success response
5. Celery worker processes task:
   a. Send email via Resend
   b. Update email_logs record (status: sent/failed)
```

## Security Considerations
- Email logs contain PII (email addresses) - ensure proper access controls
- Consider encryption for sensitive metadata
- Log retention policy (future: auto-archive after 90 days)

## Performance
- Log creation uses same DB session as user creation (minimal overhead)
- Status updates happen asynchronously in Celery task
- Indexes ensure fast queries for user history

## Testing Strategy
- Unit tests for EmailLog model methods
- Integration tests for log creation during registration
- Celery task tests for status updates
- Idempotency tests for duplicate prevention

## Rollout Plan
1. Create migration and model
2. Update EmailService to create logs
3. Update Celery task to update logs
4. Add query methods
5. Add tests
6. Deploy and verify logs are created for new emails

## Risks
- **Migration on large DB**: email_logs table starts empty, no risk
- **Celery task failure**: Log stays in "queued" status - acceptable
- **Idempotency window**: 24h window may need adjustment based on use case
