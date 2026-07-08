---
ticket: TASK-029
phase: plan
model: qwen3.6-plus
generated: 2026-06-30
status: completed
---

# Implementation Plan: Instagram Graph API Insights Integration

**Branch**: `029-instagram-insights` | **Date**: 2026-06-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `.specify/specs/task-029-instagram-insights/spec.md`

## Summary

Create an `InstagramMetricsService` that fetches account-level and media-level insights from the Instagram Graph API, caches responses in Redis for 1 hour, and exposes endpoints for the dashboard to display analytics. Includes token error handling that deactivates accounts on expired tokens (reusing TASK-028's `_is_token_error()`), cache invalidation on post publish, and graceful fallback to stale cached data on API failures.

## Technical Context

**Language/Version**: Python 3.11, JavaScript (vanilla)
**Primary Dependencies**: FastAPI, Celery, Redis (aioredis for async, redis for sync), httpx (for Instagram Graph API calls), SQLAlchemy 2.0 (async)
**Storage**: PostgreSQL (existing Post, InstagramAccount models), Redis (caching via existing SSE Redis connection)
**Testing**: pytest + pytest-asyncio
**Target Platform**: Linux server (Docker), modern web browsers
**Project Type**: Web application (FastAPI backend + Jinja2/JS frontend)
**Performance Goals**: Account analytics < 2s from cache, < 5s from API; media analytics < 3s from cache, < 5s from API
**Constraints**: Must respect Meta API rate limits (~200 calls/hour/user); must reuse existing Redis connection; must reuse TASK-028's token error detection
**Scale/Scope**: Single-user dashboard, one or more Instagram accounts per user

## Constitution Check

The project constitution at `.specify/memory/constitution.md` is still in template form. No active governance gates. Proceeding with project conventions from `AGENTS.md`.

**Gate Status**: ✅ PASS — no constitution violations.

## Project Structure

### Documentation (this feature)

```text
specs/task-029-instagram-insights/
├── plan.md              # This file
├── spec.md              # Feature specification
├── data-model.md        # Phase 1 output
├── contracts/           # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code Changes

```text
app/
├── services/
│   ├── instagram.py             # MODIFY: add get_account_insights(), get_media_insights() methods
│   └── metrics.py               # CREATE: InstagramMetricsService with caching, error handling, aggregation
├── dashboard/
│   ├── routes.py                # MODIFY: add GET /dashboard/analytics/account, GET /dashboard/analytics/media/{post_id}
│   └── service.py               # MODIFY: add cache invalidation on post publish (FR-006a)
├── worker.py                    # MODIFY: call cache invalidation when post transitions to PUBLISHED
└── templates/
    └── dashboard/
        └── layout.html          # MODIFY: add analytics section with loading states, skeleton placeholders, retry button
```

## Phase 0: Research

No research needed — Instagram Graph API `/insights` endpoint is well-documented. Key decisions:

- **API endpoint format**: `GET /{instagram-account-id}/insights?metric=impressions,reach,profile_views,follower_count&period=days_28`
- **Media insights endpoint**: `GET /{media-id}/insights?metric=engagement,impressions,reach,saved,likes,comments`
- **Response format**: JSON with `data` array containing `name`, `period`, `values` (for time-series) or `value` (for lifetime metrics)
- **Caching**: Use existing Redis connection with keys like `insights:account:{account_id}:{period}` and `insights:media:{media_id}`
- **Token error detection**: Reuse `_is_token_error()` from TASK-028 (checks for codes 463, 467, OAuthException, "token expired")

## Phase 1: Design & Contracts

### data-model.md

```markdown
# Data Model: TASK-029 Changes

## No Schema Changes

This feature does not require new database columns or tables. It reads from existing models:

| Model | Fields Used | Purpose |
|-------|-------------|---------|
| InstagramAccount | `id`, `instagram_account_id`, `access_token`, `is_active` | Authenticate API requests, check active status |
| Post | `id`, `ig_media_id`, `status`, `user_id` | Filter published posts, fetch media-level insights |

## Redis Cache Schema

| Key Pattern | TTL | Value |
|-------------|-----|-------|
| `insights:account:{account_id}:{period}` | 3600s | JSON: `{impressions, reach, profile_views, follower_count, fetched_at}` |
| `insights:media:{media_id}` | 3600s | JSON: `{engagement, impressions, reach, saved, likes, comments, fetched_at}` |

## Cache Invalidation

- On post publish: delete `insights:account:{account_id}:*` keys
- On token error: delete all cache keys for the affected account
- On manual retry: delete specific key and refetch
```

### contracts/insights-api.md

```markdown
# Contract: Insights API Endpoints

## GET /dashboard/analytics/account

Returns account-level insights for the authenticated user's active Instagram account.

### Query Parameters
- `period` (optional): `day` or `days_28` (default: `days_28`)

### Success Response (200)
```json
{
  "account_id": 1,
  "instagram_account_id": "17841400000000000",
  "period": "days_28",
  "metrics": {
    "impressions": 12500,
    "reach": 8900,
    "profile_views": 340,
    "follower_count": 1250
  },
  "cached": true,
  "fetched_at": "2026-06-30T10:00:00Z",
  "stale": false
}
```

### Error Responses
- **401**: Unauthorized (not logged in)
- **400**: No active Instagram account connected
- **403**: Account is "Inactiva" — needs reconnection
- **502**: Instagram API unavailable — cached data returned or "temporarily unavailable"

## GET /dashboard/analytics/media/{post_id}

Returns media-level insights for a specific published post (on-demand).

### Path Parameters
- `post_id`: Integer, must belong to authenticated user

### Success Response (200)
```json
{
  "post_id": 42,
  "ig_media_id": "17841400000000001",
  "metrics": {
    "engagement": 450,
    "impressions": 3200,
    "reach": 2800,
    "saved": 85,
    "likes": 320,
    "comments": 45
  },
  "cached": true,
  "fetched_at": "2026-06-30T10:00:00Z",
  "stale": false
}
```

### Error Responses
- **401**: Unauthorized
- **404**: Post not found or not owned by user
- **400**: Post not published (no media ID available)
- **403**: Account is "Inactiva"
- **502**: Instagram API unavailable
```

### quickstart.md

```markdown
# Quickstart: TASK-029 Testing

## Prerequisites
- Docker Compose stack running (api, worker, beat, redis, postgres, minio)
- User account with verified Instagram Business/Creator account
- At least one published post with a valid `ig_media_id`

## Testing Account-Level Analytics
1. Log in to the dashboard
2. View the analytics section — should show impressions, reach, profile views, follower count
3. Check Redis: `docker compose exec redis redis-cli KEYS "insights:account:*"`
4. Wait 1 hour or manually delete the cache key, then refresh — should fetch fresh data
5. Publish a new post — verify cache is invalidated and fresh data is fetched on next view

## Testing Media-Level Analytics
1. View post history in the dashboard
2. Click on a published post — should show media-level metrics
3. Check Redis: `docker compose exec redis redis-cli KEYS "insights:media:*"`
4. Click on a pending/processing post — should show "metrics not yet available"

## Testing Token Error Handling
1. Revoke the Instagram account's access token in Meta Developer Portal
2. View analytics — should see account marked "Inactiva" with reconnect prompt
3. Verify no further API calls are made for that account

## Testing Cache Fallback
1. View analytics (populates cache)
2. Disconnect from internet or block Instagram API
3. Refresh — should show cached data with "stale" indicator and "Retry" button
```

## Phase 2: Tasks

See tasks.md for the full task breakdown (created by `/speckit.tasks`).

## Complexity Tracking

No complexity beyond existing patterns. All changes follow established conventions from TASK-027/TASK-028 and the existing codebase.

| Change | Complexity | Justification |
|--------|------------|---------------|
| `InstagramMetricsService` | Low | New service class following existing `instagram.py` patterns |
| Redis caching | Low | Reuses existing Redis connection from SSE infrastructure |
| Cache invalidation on publish | Low | Single `DEL` call in existing post publish flow |
| Analytics UI section | Medium | New dashboard section with loading states, skeleton placeholders, retry logic |
