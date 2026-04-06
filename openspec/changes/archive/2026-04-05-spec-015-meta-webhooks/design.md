# Design: Meta Webhooks Integration

## Technical Approach

Create a standalone webhook router (`app/webhooks/meta.py`) that operates **without JWT authentication** — Meta servers cannot authenticate with our JWT system. Use HMAC-SHA1 signature validation via `X-Hub-Signature` header to verify webhook authenticity. Implement a decorator pattern for signature validation that can be reused across webhook endpoints.

The flow: Meta sends webhook → FastAPI receives → signature validated → payload parsed → Post record located by `ig_container_id` → status updated (PUBLISHED/FAILED).

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|----------|--------|--------------|-----------|
| Auth method | HMAC-SHA1 signature | JWT (rejected) | Meta servers can't use our JWT tokens |
| Signature validation | Decorator pattern | Middleware (rejected) | Decorator is explicit, testable, per-route |
| Timestamp validation | 5-minute window | No validation (rejected) | Prevents replay attacks per Meta security guidelines |
| Post lookup | ig_container_id primary, ig_media_id fallback | Single field lookup | Meta sends different IDs at different lifecycle stages |
| Webhook response | Always 200 for valid signature | Different codes per outcome | Meta retries on non-2xx; we must acknowledge even if Post not found |
| Missing Post handling | Log warning, return 200 | Return 404 (rejected) | Prevents Meta retry storms for orphaned webhooks |

## Data Flow

```
Meta Servers → POST /webhooks/instagram
                    ↓
         ┌─────────────────────┐
         │  Signature Validate │ ← HMAC-SHA1(META_APP_SECRET, body)
         └─────────────────────┘
                    ↓
         ┌─────────────────────┐
         │   Parse Payload     │ → entry[0].changes[0].value
         └─────────────────────┘
                    ↓
         ┌─────────────────────┐
         │  Lookup Post Model  │ → WHERE ig_container_id = ?
         └─────────────────────┘
                    ↓
         ┌─────────────────────┐
         │   Update Status     │ → PUBLISHED / FAILED + error_message
         └─────────────────────┘
                    ↓
              Return 200 OK
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/webhooks/__init__.py` | Create | Package init |
| `app/webhooks/meta.py` | Create | FastAPI router with GET/POST endpoints |
| `app/webhooks/signature.py` | Create | HMAC-SHA1 validation decorator + timestamp check |
| `app/webhooks/schemas.py` | Create | Pydantic models for Meta webhook payloads |
| `app/core/config.py` | Modify | Add `META_WEBHOOK_VERIFY_TOKEN` setting |
| `app/main.py` | Modify | Include webhook router without JWT dependency |

## Interfaces / Contracts

### Signature Validation Decorator

```python
def verify_webhook_signature(func):
    """
    Decorator that validates X-Hub-Signature header.
    
    - Computes HMAC-SHA1(payload, META_APP_SECRET)
    - Compares against X-Hub-Signature (sha1=<hash>)
    - Validates timestamp is within 5 minutes
    - Returns 401 if signature invalid
    - Returns 403 if timestamp too old (replay)
    """
```

### Webhook Payload Schema

```python
class WebhookValue(BaseModel):
    media_id: Optional[str]
    container_id: Optional[str]  # ig_container_id
    status: str  # PUBLISHED, ERROR, etc.
    error_message: Optional[str]
    timestamp: int  # Unix timestamp for replay protection

class WebhookChange(BaseModel):
    value: WebhookValue
    field: str  # e.g., "mentions", "story_insights"

class WebhookEntry(BaseModel):
    id: str  # Instagram Business Account ID
    time: int
    changes: List[WebhookChange]

class WebhookPayload(BaseModel):
    object: str  # "instagram"
    entry: List[WebhookEntry]
```

### Hub Challenge Verification

```python
@router.get("/webhooks/instagram")
async def verify_hub_challenge(
    hub_mode: str,
    hub_challenge: str,
    hub_verify_token: str
):
    """
    Meta webhook subscription verification.
    
    - hub_mode must be "subscribe"
    - hub_verify_token must match META_WEBHOOK_VERIFY_TOKEN
    - Returns hub_challenge as plain text
    """
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | HMAC signature computation | Mock requests with known payload/secret pairs |
| Unit | Timestamp validation | Test boundaries (4min59s OK, 5min1s reject) |
| Unit | Payload parsing | Valid/invalid JSON structures |
| Integration | Full webhook flow | Mock Meta request → verify DB update |
| Integration | Hub Challenge | Test token validation logic |

### Test Cases Required

1. **Valid signature**: Known payload + correct secret → 200
2. **Invalid signature**: Tampered body → 401
3. **Missing signature**: No X-Hub-Signature header → 401
4. **Replay attack**: Timestamp > 5 minutes old → 403
5. **Valid verification**: Correct hub.verify_token → returns challenge
6. **Invalid verification**: Wrong token → 403
7. **Post found by container_id**: Updates status correctly
8. **Post found by media_id**: Fallback lookup works
9. **Post not found**: Logs warning, returns 200 (acknowledges)
10. **Error payload**: Updates to FAILED with error_message

## Migration / Rollout

1. **Configuration**: Add `META_WEBHOOK_VERIFY_TOKEN` to `.env` file
2. **Meta App Dashboard**: 
   - Configure webhook URL: `https://instagramjp.loquinto.com/webhooks/instagram`
   - Set verify token to match `META_WEBHOOK_VERIFY_TOKEN`
   - Subscribe to `instagram` object with relevant fields
3. **Test in Meta Events Tester** before enabling live subscriptions
4. **Monitor logs** for signature validation failures

## Open Questions

- [ ] Should we store raw webhook payloads for audit/debugging? (add `webhook_logs` table?)
- [ ] What's the retry behavior if Post lookup fails due to timing? (Celery task not yet saved container_id)
- [ ] Do we need idempotency (duplicate webhook detection) beyond timestamp validation?

## Dependencies Note

**SPEC-012 (Post Logic) is required** — this design assumes:
- `Post` model with `ig_container_id`, `ig_media_id`, `status`, `error_message` fields
- `update_from_webhook()` method on Post model
- Async SQLAlchemy session available via `get_db` dependency
