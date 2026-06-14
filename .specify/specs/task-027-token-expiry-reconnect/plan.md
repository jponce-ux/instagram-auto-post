---
ticket: TASK-027
phase: plan
model: qwen3.6-plus
generated: 2026-06-13
status: draft
---

# Implementation Plan: Instagram Token Expiry Detection and Account Reconnection

**Branch**: `027-token-expiry-reconnect` | **Date**: 2026-06-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `.specify/specs/task-027-token-expiry-reconnect/spec.md`

## Summary

Detect Instagram token expiry errors in the Celery worker, automatically deactivate the affected account, display a "Reconnect" button on the dashboard for inactive accounts, and reactivate the account when the user successfully completes the OAuth flow again.

## Technical Context

**Language/Version**: Python 3.11, JavaScript (vanilla)
**Primary Dependencies**: FastAPI, Celery, SQLAlchemy, Jinja2, SSE (Redis pub/sub)
**Storage**: PostgreSQL (InstagramAccount.is_active already exists)
**Testing**: pytest + pytest-asyncio
**Target Platform**: Linux server (Docker), modern web browsers
**Project Type**: Web application (FastAPI backend + Jinja2/JS frontend)
**Performance Goals**: Account deactivation within 5s of error; dashboard update within 2s via SSE
**Constraints**: Must use existing OAuth flow; no new database migrations needed
**Scale/Scope**: Single-user dashboard, one or more Instagram accounts per user

## Constitution Check

The project constitution at `.specify/memory/constitution.md` is still in template form. No active governance gates. Proceeding with project conventions from `AGENTS.md`.

**Gate Status**: ✅ PASS — no constitution violations.

## Project Structure

### Source Code Changes

```text
app/
├── worker.py                    # MODIFY: detect token expiry, set is_active=False, publish SSE event
├── dashboard/
│   ├── routes.py                # MODIFY: add POST /dashboard/accounts/reconnect endpoint, check is_active before post
│   └── service.py               # MODIFY: add deactivate_account() helper
├── auth/
│   └── instagram.py             # MODIFY: set is_active=True on successful OAuth callback
├── services/
│   └── sse.py                   # MODIFY: add ACCOUNT_UPDATE_CHANNEL constant
└── templates/
    └── dashboard/
        ├── layout.html          # MODIFY: renderAccounts() — show reconnect button for inactive accounts
        └── accounts_partial.html # MODIFY: show reconnect button for inactive accounts (server-rendered)
```

## Phase 0: Research

No research needed — all technical decisions are straightforward based on existing code patterns.

## Phase 1: Design & Contracts

### data-model.md

No changes to data model. `InstagramAccount.is_active` already exists.

### contracts/account-status-api.md

```markdown
# Contract: Account Status API

## GET /dashboard/accounts (EXISTING — no changes)

Returns JSON array of accounts with `is_active` field.

### Response Format (unchanged)
```json
{
  "accounts": [
    {
      "id": 1,
      "instagram_account_id": "17841400000000000",
      "username": "my_instagram",
      "is_active": false
    }
  ]
}
```

## POST /dashboard/accounts/reconnect (NEW)

Redirects user to Instagram OAuth flow for reconnection.

### Response
- 303 Redirect to `/auth/instagram/login`

## POST /dashboard/post (MODIFIED)

Now checks `is_active` before dispatching Celery task.

### Error Response (new)
```json
{
  "error": "Instagram account is inactive. Please reconnect your account."
}
```
Status: 400
```

### SSE Event Contract (NEW)

```json
{
  "event": "account_update",
  "data": {
    "account_id": 1,
    "is_active": false,
    "reason": "token_expired"
  }
}
```

## Phase 2: Tasks

See tasks.md for the full task breakdown.

## Complexity Tracking

No complexity beyond existing patterns. All changes follow established conventions.
