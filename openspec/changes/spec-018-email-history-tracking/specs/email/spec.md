# Spec: Email History Tracking

## Requirements

### Requirement 1: Email Log Creation
**Priority:** P0  
**Description:** System SHALL create an email log entry before queuing any email task.

#### Scenario 1.1: Welcome email log creation
**Given** a new user registers with email `user@example.com`  
**When** the system sends a welcome email  
**Then** an `email_logs` record is created with:
- `user_id` = the new user's ID
- `email_type` = "welcome"
- `to_email` = "user@example.com"
- `status` = "queued"
- `queued_at` = current timestamp

#### Scenario 1.2: Log includes metadata
**Given** an email is queued  
**When** the log entry is created  
**Then** it includes:
- `message_id` = unique identifier (UUID)
- `template_name` = "welcome" (or other template)
- `metadata` = JSON field with additional context

### Requirement 2: Status Updates
**Priority:** P0  
**Description:** System SHALL update email log status based on Celery task outcome.

#### Scenario 2.1: Successful send
**Given** an email log with status "queued"  
**When** the Celery task successfully sends the email  
**Then** the log is updated with:
- `status` = "sent"
- `sent_at` = current timestamp
- `message_id` = Resend message ID (if available)

#### Scenario 2.2: Failed send (client error)
**Given** an email log with status "queued"  
**When** the Celery task fails with a 4xx error  
**Then** the log is updated with:
- `status` = "failed"
- `error_message` = error description
- `failed_at` = current timestamp

#### Scenario 2.3: Failed send (server error, retried)
**Given** an email log with status "queued"  
**When** the Celery task fails with a 5xx error and exhausts retries  
**Then** the log is updated with:
- `status` = "failed"
- `error_message` = error description
- `failed_at` = current timestamp
- `retry_count` = number of retries attempted

### Requirement 3: Query Interface
**Priority:** P1  
**Description:** System SHALL provide methods to query email logs.

#### Scenario 3.1: Query by user
**Given** email logs exist for multiple users  
**When** querying logs for a specific user  
**Then** only logs for that user are returned, ordered by `queued_at` descending

#### Scenario 3.2: Query by status
**Given** email logs exist with various statuses  
**When** querying logs with status filter  
**Then** only logs matching the status are returned

### Requirement 4: Idempotency
**Priority:** P1  
**Description:** System SHALL prevent duplicate email sends using message IDs.

#### Scenario 4.1: Duplicate prevention
**Given** an email log with status "sent" exists for a user and email type  
**When** the system attempts to send the same email type again within 24 hours  
**Then** the system skips sending and returns the existing log entry

## Data Model

### email_logs table
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | Unique identifier |
| user_id | UUID | FK → users.id, nullable | Associated user (nullable for system emails) |
| email_type | VARCHAR(50) | NOT NULL | Type: welcome, password_reset, notification, etc. |
| to_email | VARCHAR(255) | NOT NULL | Recipient email address |
| from_email | VARCHAR(255) | NOT NULL | Sender email address |
| status | VARCHAR(20) | NOT NULL, default 'queued' | queued, sent, delivered, bounced, failed |
| message_id | VARCHAR(255) | nullable | Resend message ID |
| template_name | VARCHAR(100) | nullable | Template used |
| metadata | JSONB | nullable | Additional context |
| error_message | TEXT | nullable | Error details if failed |
| retry_count | INTEGER | default 0 | Number of retries |
| queued_at | TIMESTAMP | NOT NULL, default now() | When queued |
| sent_at | TIMESTAMP | nullable | When successfully sent |
| failed_at | TIMESTAMP | nullable | When failed |
| created_at | TIMESTAMP | NOT NULL, default now() | Record creation |
| updated_at | TIMESTAMP | NOT NULL, default now() | Last update |

### Indexes
- `idx_email_logs_user_id` on `user_id`
- `idx_email_logs_status` on `status`
- `idx_email_logs_queued_at` on `queued_at`
- `idx_email_logs_message_id` on `message_id` (unique, partial where not null)

## Non-Goals
- Real-time email delivery tracking (webhooks from Resend)
- Email open/click tracking
- Bulk email operations
- Admin UI for email history (future spec)

## Success Metrics
- 100% of email sends have corresponding log entries
- Log creation adds < 10ms overhead to email queuing
- Queries for user email history complete in < 50ms
