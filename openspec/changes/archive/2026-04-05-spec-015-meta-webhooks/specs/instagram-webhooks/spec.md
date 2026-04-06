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