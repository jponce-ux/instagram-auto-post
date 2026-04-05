# Delta for async-tasks

## ADDED Requirements

### Requirement: Instagram Post Processing Task

The system MUST provide a `process_instagram_post` Celery task for Instagram publishing.

The task SHALL orchestrate the complete publish flow: create container, verify status, publish.

#### Scenario: Task dispatches post for processing

- GIVEN a Post record exists with status PENDING
- WHEN `process_instagram_post.delay(post_id)` is called
- THEN task is queued in Redis
- AND worker begins processing

#### Scenario: Task updates post status

- GIVEN task is processing a Post
- WHEN each step completes (create container, verify status, publish)
- THEN Post status is updated (PROCESSING → PUBLISHED or FAILED)
- AND error message is stored if FAILED

#### Scenario: Task retrieves Instagram token

- GIVEN a Post with `ig_account_id`
- WHEN task executes
- THEN task fetches access_token from InstagramAccount table
- AND token is validated before use

#### Scenario: Task generates fresh presigned URL

- GIVEN a Post with `media_file_id`
- WHEN task begins processing
- THEN fresh presigned URL is generated via StorageService
- AND URL is valid for Meta API to download

#### Scenario: Task handles expired token

- GIVEN InstagramAccount token has expired
- WHEN task attempts to create media container
- THEN Post status is set to FAILED
- AND error message includes "token expired"
- AND task completes without crashing worker