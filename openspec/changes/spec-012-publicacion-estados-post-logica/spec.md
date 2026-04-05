# Specs: Lógica de Publicación y Estados de Post

## instagram-publishing (NEW)

### Requirement: Post Model with States

The system MUST provide a `Post` model with status tracking.

The model SHALL support states: PENDING, PROCESSING, PUBLISHED, FAILED.

#### Scenario: Post created in PENDING state

- GIVEN a user uploads media to MinIO
- WHEN a Post record is created
- THEN status is set to PENDING
- AND `ig_container_id` is NULL

#### Scenario: Post transitions to PROCESSING

- GIVEN a Post in PENDING state
- WHEN Celery task begins processing
- THEN status changes to PROCESSING
- AND `updated_at` timestamp is set

---

### Requirement: Media Container Creation

The system MUST create an IG Media Container before publishing.

The container SHALL be created via Meta Graph API `POST /{ig_id}/media`.

#### Scenario: Create container with image URL

- GIVEN a Post with `media_url` and `ig_account_id`
- WHEN `create_media_container` is called
- THEN Meta API returns a container ID
- AND container ID is stored in Post record

#### Scenario: Container creation fails

- GIVEN invalid media URL or expired token
- WHEN `create_media_container` is called
- THEN Post status is set to FAILED
- AND error message is stored

---

### Requirement: Container Status Verification

The system MUST verify container status before publishing.

The status check SHALL poll `GET /{container_id}?fields=status_code`.

#### Scenario: Container finished processing

- GIVEN a container ID from create step
- WHEN status is polled
- THEN status_code becomes "FINISHED"
- AND publishing can proceed

#### Scenario: Container processing timeout

- GIVEN container status remains "IN_PROGRESS" after timeout
- WHEN max retries exceeded
- THEN Post status is set to FAILED
- AND error indicates timeout

---

### Requirement: Media Publish

The system MUST publish the container to Instagram feed.

Publishing SHALL use `POST /{ig_id}/media_publish`.

#### Scenario: Publish successful

- GIVEN container with status "FINISHED"
- WHEN `publish_media_container` is called
- THEN Meta API returns IG Media ID
- AND Post status is set to PUBLISHED
- AND `published_at` timestamp is set

#### Scenario: Publish fails with rate limit

- GIVEN Meta API returns rate limit error
- WHEN publish is attempted
- THEN Post status is set to FAILED
- AND error includes retry guidance

---

### Requirement: Error Handling

The system MUST handle all error conditions gracefully.

Errors SHALL be captured with clear messages for troubleshooting.

#### Scenario: Token expired during publish

- GIVEN InstagramAccount token has expired
- WHEN processing attempts to use token
- THEN Post status is set to FAILED
- AND error message includes "token expired"
- AND user is prompted to reconnect Instagram account

#### Scenario: Presigned URL expired

- GIVEN media URL has expired (10-minute window)
- WHEN processing attempts to create container
- THEN fresh presigned URL is generated
- AND processing continues

---

### Requirement: Celery Task Integration

The system MUST provide `process_instagram_post` Celery task.

The task SHALL orchestrate the complete publish flow.

#### Scenario: Task processes post end-to-end

- GIVEN a Post ID in PENDING state
- WHEN `process_instagram_post.delay(post_id)` is called
- THEN Post status transitions: PENDING → PROCESSING → PUBLISHED
- AND all Meta API calls succeed
- AND Post record is updated with final state

#### Scenario: Task handles errors and retries

- GIVEN a Post fails during processing
- WHEN error is caught
- THEN Post status is set to FAILED
- AND error message is persisted
- AND no unhandled exception crashes the worker

---

## async-tasks (MODIFIED - DELTA)

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
