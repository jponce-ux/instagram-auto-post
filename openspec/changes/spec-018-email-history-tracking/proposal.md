# Proposal: Email History Tracking

## Problem
Currently, emails are sent asynchronously via Celery but there's no persistent record of:
- Which emails were sent to which users
- Delivery status (sent, delivered, bounced, failed)
- When emails were sent
- Email type (welcome, password reset, notification, etc.)

This makes it impossible to:
- Debug email delivery issues
- Track user engagement
- Prevent duplicate sends
- Provide audit trails for compliance

## Solution
Add an `email_logs` table to track all email sends with status, timestamps, and metadata. The EmailService will create a log entry before queuing the Celery task, and the task will update the status after attempting to send.

## Capabilities

### New Capabilities
1. **Email Logging**: Persist email send attempts with status tracking
2. **Status Updates**: Track lifecycle from queued → sent → delivered/failed
3. **Query Interface**: Allow querying email history by user, type, or status
4. **Idempotency**: Prevent duplicate sends using unique message IDs

## Impact
- **Database**: New `email_logs` table
- **Models**: New `EmailLog` SQLAlchemy model
- **Services**: EmailService updated to create/update log entries
- **Worker**: task_dispatch_resend_email updated to update log status
- **API**: Optional admin endpoint to view email history (future)
- **Tests**: New tests for logging behavior

## Dependencies
- SPEC-017 (Email Notifications) must be complete
- PostgreSQL database
- Celery worker
