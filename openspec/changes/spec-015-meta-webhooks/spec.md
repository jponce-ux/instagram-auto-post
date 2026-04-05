# Specs: Meta Webhooks Integration

## instagram-webhooks (NEW)

### Requirement: Hub Challenge Verification

The system MUST expose a public endpoint to verify webhook subscription with Meta.

The endpoint SHALL respond to GET requests with `hub.challenge` parameter.

#### Scenario: Verification request from Meta

- GIVEN Meta servers send GET to /webhooks/instagram
- WHEN query contains `hub.mode=subscribe`, `hub.challenge`, and `hub.verify_token`
- THEN system returns 200 with plain text `hub.challenge` value
- AND webhook subscription is confirmed

#### Scenario: Verification with invalid token

- GIVEN request contains incorrect `hub.verify_token`
- THEN system returns 403 Forbidden
- AND subscription is not confirmed

---

### Requirement: Webhook Payload Reception

The system MUST receive and parse POST webhook payloads from Meta.

The endpoint SHALL parse `entry[].changes[].value` for status information.

#### Scenario: Receive published notification

- GIVEN Meta sends POST with entry containing status=PUBLISHED
- WHEN payload is validated and parsed
- THEN Post status is updated to PUBLISHED
- AND `ig_media_id` is stored if present

#### Scenario: Receive error notification

- GIVEN Meta sends POST with entry containing status=ERROR
- WHEN payload is validated and parsed
- THEN Post status is updated to FAILED
- AND `error_message` is extracted and stored

---

### Requirement: HMAC-SHA1 Signature Validation

The system MUST validate webhook authenticity using X-Hub-Signature header.

The validation SHALL use HMAC-SHA1 with META_APP_SECRET.

#### Scenario: Valid signature

- GIVEN POST request with valid X-Hub-Signature header
- WHEN HMAC-SHA1 computed over body matches signature
- THEN payload is processed
- AND webhook is considered authentic

#### Scenario: Invalid or missing signature

- GIVEN POST request with tampered body or missing X-Hub-Signature
- WHEN signature validation fails
- THEN system returns 401 Unauthorized
- AND payload is not processed

#### Scenario: Replay attack prevention

- GIVEN webhook payload with timestamp older than 5 minutes
- WHEN X-Hub-Signature-256 timestamp check fails
- THEN system returns 403 Forbidden
- AND replay is rejected

---

### Requirement: Post Status Update from Webhook

The system MUST update Post records based on webhook data.

The update SHALL use `ig_container_id` or `ig_media_id` to locate the Post.

#### Scenario: Post found by container ID

- GIVEN webhook contains `ig_container_id`
- WHEN Post with matching `ig_container_id` exists
- THEN Post is updated with new status
- AND `updated_at` timestamp is refreshed

#### Scenario: Post found by media ID

- GIVEN webhook contains `ig_media_id`
- WHEN no Post matches container_id but media_id matches
- THEN Post is updated with new status

#### Scenario: Post not found

- GIVEN webhook references unknown container_id or media_id
- THEN webhook is acknowledged (200)
- AND error is logged without crashing

---

## instagram-publishing (MODIFIED)

### Requirement: Container Status Verification

The system MUST verify container status before publishing.

The status check SHALL now rely on webhook callbacks instead of polling.

(Previously: Polled GET /{container_id}?fields=status_code)

#### Scenario: Container created and waiting for webhook

- GIVEN a Post has container_id stored after container creation
- WHEN `ig_container_id` is set and status is PROCESSING
- THEN system waits for webhook callback
- AND does NOT poll Meta API for status

#### Scenario: Webhook confirms publish success

- GIVEN container was created and published
- WHEN webhook received with status=PUBLISHED
- THEN Post status is set to PUBLISHED
- AND `published_at` timestamp is set

---

### Requirement: Media Publish

The system MUST publish the container to Instagram feed.

Publishing SHALL use `POST /{ig_id}/media_publish`.

(Previously: Set PUBLISHED immediately after API success)

#### Scenario: Publish successful and confirmed via webhook

- GIVEN container with status "FINISHED" is published
- WHEN `publish_media_container` succeeds
- THEN Post status remains PROCESSING (not yet PUBLISHED)
- AND waits for webhook confirmation
- AND `ig_media_id` is stored when received

#### Scenario: Webhook reports publish failure

- GIVEN Post status is PROCESSING after publish API call
- WHEN webhook received with status=ERROR or FAILED
- THEN Post status is set to FAILED
- AND error message from webhook is stored
