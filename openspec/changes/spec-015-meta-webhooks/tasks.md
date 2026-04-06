# Tasks: spec-015-meta-webhooks

## Phase 0: Git

- [x] 0.1 Create feature branch `feature/spec-015-meta-webhooks` from `main`

## Phase 1: Config

- [x] 1.1 Modify `app/core/config.py` to add `META_WEBHOOK_VERIFY_TOKEN: str` setting from environment variable `META_WEBHOOK_VERIFY_TOKEN`

## Phase 2: Security

- [x] 2.1 Create `app/webhooks/__init__.py` with package exports
- [x] 2.2 Create `app/webhooks/security.py` with `verify_webhook_signature` decorator implementing HMAC-SHA1 validation against `X-Hub-Signature` header
- [x] 2.3 Implement 5-minute timestamp window validation in decorator to prevent replay attacks
- [x] 2.4 Decorator returns 401 for invalid signature, 403 for timestamp too old

## Phase 3: Schemas

- [x] 3.1 Create `app/webhooks/schemas.py` with `WebhookValue` model (media_id, container_id, status, error_message, timestamp)
- [x] 3.2 Create `WebhookChange` model (value, field)
- [x] 3.3 Create `WebhookEntry` model (id, time, changes list)
- [x] 3.4 Create `WebhookPayload` model (object, entry list)
- [x] 3.5 Add `WebhookChallengeResponse` model for GET endpoint

## Phase 4: Router

- [x] 4.1 Create `app/webhooks/meta.py` with FastAPI router instance
- [x] 4.2 Implement GET `/webhooks/instagram` handler accepting hub.mode, hub.challenge, hub.verify_token query params
- [x] 4.3 GET handler validates hub.verify_token matches config, returns 200 with hub.challenge plain text or 403 for invalid token
- [x] 4.4 Implement POST `/webhooks/instagram` endpoint applying `@verify_webhook_signature` decorator
- [x] 4.5 POST handler parses payload using webhook schemas, returns 200 always after signature validation
- [x] 4.6 POST handler logs warning if Post not found by ig_container_id or ig_media_id (orphaned webhook)

## Phase 5: Integration

- [x] 5.1 Modify `app/main.py` to import webhook router from `app.webhooks.meta`
- [x] 5.2 Mount router with `app.include_router(webhook_router, tags=["webhooks"])` — NO authentication dependency (public endpoint)
- [x] 5.3 Verify router is mounted at `/webhooks/instagram` path

## Phase 6: Verification

- [x] 6.1 Create `tests/test_webhooks.py` with unit tests for `verify_webhook_signature` decorator
- [x] 6.2 Test valid signature: known payload + correct META_APP_SECRET → passes validation
- [x] 6.3 Test invalid signature: tampered body → returns 401
- [x] 6.4 Test missing signature: no X-Hub-Signature header → returns 401
- [x] 6.5 Test replay attack: timestamp > 5 minutes old → returns 403
- [x] 6.6 Test valid timestamp boundary: 4min59s old → passes, 5min1s → fails
- [x] 6.7 Create integration test for GET hub.challenge with correct token → returns 200 with challenge
- [x] 6.8 Create integration test for GET hub.challenge with wrong token → returns 403
- [x] 6.9 Test Post lookup by ig_container_id (mock DB session)
- [x] 6.10 Test Post lookup fallback to ig_media_id when container_id not found
- [x] 6.11 Test Post not found scenario → logs warning, returns 200 (acknowledges without crashing)

## Phase 7: Commit

- [x] 7.1 Stage all new and modified files
- [x] 7.2 Commit with conventional message: `feat(webhooks): add Meta Instagram webhook receiver`
- [x] 7.3 Push branch to remote
- [x] 7.4 Create PR if applicable

---

## Summary

| Phase | Tasks | Focus |
|-------|-------|-------|
| Phase 0 | 1 | Git setup |
| Phase 1 | 1 | Config (META_WEBHOOK_VERIFY_TOKEN) |
| Phase 2 | 3 | Security (HMAC-SHA1 decorator + timestamp validation) |
| Phase 3 | 5 | Schemas (Pydantic models for payload) |
| Phase 4 | 5 | Router (GET/POST endpoints) |
| Phase 5 | 3 | Integration (mount in main.py) |
| Phase 6 | 11 | Verification (unit + integration tests) |
| Phase 7 | 4 | Commit |
| **Total** | **33** | |

## Implementation Order

1. **Config first** — settings needed by other components
2. **Security layer** — decorator depends on config, used by router
3. **Schemas** — Pydantic models for parsing, dependency for router
4. **Router** — main endpoint logic, uses security + schemas
5. **Integration** — wire into FastAPI app
6. **Verification** — tests verify all above
7. **Git** — commit at the end

## Dependencies

- SPEC-012 (Post Logic) ⏳ — Post model with `ig_container_id`, `ig_media_id`, `status`, `error_message` fields required before Phase 4 router logic can fully work
- SPEC-009 (Cloudflare Tunnel) ✅ — instagramjp.loquinto.com already accessible for Meta webhook delivery
