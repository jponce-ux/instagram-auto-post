---
ticket: TASK-029
phase: spec
model: qwen3.6-plus
generated: 2026-06-30
status: draft
---

# Feature Specification: Instagram Graph API Insights Integration

**Feature Branch**: `029-instagram-insights`  
**Created**: 2026-06-30  
**Status**: Draft  
**Input**: User description: "Create a unified, resilient backend data service to fetch, parse, and structure account-level and media-level insights from the Instagram Graph API, ensuring efficient processing using cached data or background jobs."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Account-Level Analytics (Priority: P1)

The user views their connected Instagram account's performance metrics (impressions, reach, profile views, follower count) on the dashboard. The system fetches fresh data from the Instagram Graph API or returns cached data if available within the last hour.

**Why this priority**: Account-level metrics are the primary value proposition — users need to see how their content is performing at a glance. Without this, the dashboard has no analytics value.

**Independent Test**: Connect an Instagram account with existing posts. View the dashboard analytics section. Verify that impressions, reach, profile views, and follower count are displayed with correct values matching the Instagram Professional Dashboard.

**Acceptance Scenarios**:

1. **Given** a user has an active Instagram account with published content, **When** they view the analytics section, **Then** account-level metrics (impressions, reach, profile views, follower count) are displayed with data from the last 28 days.
2. **Given** the user views analytics within 1 hour of a previous fetch, **When** the page loads, **Then** cached data is returned instantly without calling the Instagram API.
3. **Given** the cached data is older than 1 hour, **When** the user views analytics, **Then** fresh data is fetched from the Instagram API and the cache is updated.
4. **Given** the user's Instagram token has expired, **When** they view analytics, **Then** the account is marked "Inactiva" and a message prompts them to reconnect.

---

### User Story 2 - View Media-Level Analytics On-Demand (Priority: P2)

The user clicks on an individual post in their history to see its specific performance metrics (engagement, impressions, reach, saves, likes, comments). Media insights are fetched on-demand only when the user requests details for a specific post, not in batch.

**Why this priority**: Users need to understand which specific posts perform best to optimize their content strategy. On-demand fetching respects API rate limits while providing detailed data when needed.

**Independent Test**: View the post history (populated from local database). Click on a published post. Verify that media-level metrics are fetched and displayed for that specific post.

**Acceptance Scenarios**:

1. **Given** the user views their post history, **When** they click on a published post, **Then** media-level metrics (engagement, impressions, reach, saves, likes, comments) are fetched on-demand and displayed.
2. **Given** a post has not yet been published on Instagram (status is pending/processing), **When** the user clicks on it, **Then** a message indicates that metrics are not yet available.
3. **Given** the Instagram API returns partial metrics for a media item, **When** the user views analytics, **Then** available metrics are displayed and missing metrics show "N/A" or "0".

---

### User Story 3 - Token Error Handling and Account Deactivation (Priority: P3)

When the Instagram Graph API returns a token error during any insights fetch, the system automatically deactivates the account and prevents further API calls until the user reconnects.

**Why this priority**: Prevents repeated API failures from expired tokens and provides a clear signal to the user that re-authentication is needed. Builds on TASK-028's token error handling.

**Independent Test**: Revoke an Instagram account's access token. Attempt to view analytics. Verify the account is marked "Inactiva" and no further API calls are made.

**Acceptance Scenarios**:

1. **Given** an Instagram account's token has expired, **When** the system attempts to fetch insights, **Then** the account is marked "Inactiva" and the user sees a prompt to reconnect.
2. **Given** an account is "Inactiva", **When** the user attempts to view analytics, **Then** no API call is made and a message indicates the account needs reconnection.

---

### Edge Cases

- **What happens if the Instagram API rate limit is reached?** The system returns cached data if available, or displays a message indicating that analytics are temporarily unavailable and will refresh later.
- **What happens if a media ID no longer exists on Instagram?** The system gracefully handles the 404 response and displays "Media no longer available" for that specific post.
- **What happens if the user has multiple Instagram accounts?** Analytics are fetched independently for each account using the correct token for each.
- **What happens if the Instagram API returns an empty metrics array?** The system displays zeros for all metrics and logs a warning for debugging.
- **What happens if the user's account has no published media?** Account-level metrics are still fetched (follower count, profile views), but media-level analytics show "No published posts yet."
- **What happens if the Instagram API fetch fails while loading analytics?** The system displays the last cached data with a subtle indicator that the data may be stale, along with a "Retry" button.
- **What happens if the user clicks on multiple posts rapidly?** Each click triggers an independent on-demand fetch. If a fetch is already in progress for the same post, the system reuses the in-flight request rather than starting a duplicate call.
- **What happens if the Instagram API returns a 500 server error?** The system treats it as a transient failure, displays cached data if available, or shows "Analytics temporarily unavailable. Please try again later."
- **What happens if the user's token permissions are downgraded (e.g., loses insights permission)?** The system detects the permission error, displays a message indicating that analytics are no longer available, and prompts the user to reconnect their account to restore permissions.
- **What happens when the "Retry" button is clicked?** The system attempts a fresh API fetch, shows a loading spinner, and updates the display with new data on success. If the retry fails, the stale data indicator remains and the button is available for another attempt. There is no limit on retry attempts.

## Clarifications

### Session 2026-06-30

- Q: Should the cache be invalidated immediately when a new post is published, or only expire after 1 hour? → A: Invalidate on post publish + time expiry — fresh data after publishing.
- Q: Should the analytics section show a loading spinner or stale cached data during API fetch? → A: Loading spinner + skeleton placeholders, with fallback to last cached data if fetch fails.
- Q: How many posts' media insights should be fetched in a single dashboard view? → A: Always on-demand — media insights are fetched only when user clicks on a specific post, not in batch.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST fetch account-level insights (impressions, reach, profile_views, follower_count) from the Instagram Graph API for active accounts.
- **FR-002**: The system MUST support two time periods for account insights: daily (`period=day`) and 28-day (`period=days_28`).
- **FR-003**: The system MUST fetch media-level insights (engagement, impressions, reach, saved, likes, comments) for individual published posts on-demand when the user requests details for a specific post. On-demand requests MUST respect the cache (FR-005, FR-006) and only call the Instagram API when cached data is expired or missing.
- **FR-004**: Account-level insights MUST be cached for up to 1 hour to stay within Meta API rate limits.
- **FR-005**: Media-level insights MUST be cached for up to 1 hour per media item.
- **FR-006**: When cached data is available and not expired, the system MUST return cached data immediately without calling the Instagram API and without showing a loading state.
- **FR-006a**: When a new post is successfully published, the system MUST invalidate the account-level insights cache for that user so the next analytics view fetches fresh data.
- **FR-006b**: When cached data exists but is expired, the system MUST display the cached data immediately with a "Refreshing..." indicator, then update the display with fresh data when the API fetch completes. If the fetch fails, the stale cached data remains visible.
- **FR-007**: When the Instagram API returns a token-related error (OAuthException, error codes 463, 467), the system MUST deactivate the associated Instagram account (set `is_active=False`).
- **FR-008**: When an account is "Inactiva", the system MUST NOT attempt to fetch insights from the Instagram API.
- **FR-009**: The system MUST gracefully handle API rate limit responses and return cached data or a user-friendly error message.
- **FR-010**: The system MUST aggregate media-level metrics from individual API responses into a unified, sanitized data structure.
- **FR-011**: The system MUST only fetch insights for posts that have a valid Instagram media ID (published posts only).
- **FR-012**: All analytics data MUST be associated with the authenticated user's account — users can only view metrics for their own Instagram accounts.
- **FR-013**: When analytics are being fetched from the API and no valid cached data exists, the system MUST display a loading state (spinner + skeleton placeholders). If valid cached data exists but is expired, the system MUST display it immediately with a "Refreshing..." indicator (FR-006b). If the API fetch fails, the system MUST display the last cached data with an indicator that the data may be stale.
- **FR-014**: The system MUST log all insights API calls (success, failure, cache hit, cache miss) with the account ID, metric type, response time, and error details for debugging and rate limit monitoring.

### Key Entities

- **InstagramAccount**: Has `access_token`, `instagram_account_id`, `is_active`. Used to authenticate API requests for insights.
- **Post**: Has `ig_media_id` (Instagram media ID), `status`. Only posts with a valid `ig_media_id` and `published` status have media-level insights.
- **InsightsCache**: Stores cached API responses with expiration timestamps. Keyed by account ID + metric type + period, or media ID.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Account-level analytics load within 2 seconds when served from cache, and within 5 seconds when fetching fresh data from the Instagram API.
- **SC-002**: Media-level analytics for a single post load within 3 seconds when served from cache, and within 5 seconds when fetching fresh data from the Instagram API.
- **SC-003**: The system respects Meta API rate limits — no more than 1 account insights fetch per account per hour, and media insights are fetched on-demand with caching to minimize API calls.
- **SC-004**: Token errors result in account deactivation within 5 seconds of the failed API call, preventing further unnecessary API requests.
- **SC-005**: Users can view analytics for all their published posts without encountering unhandled errors or blank data.

## Assumptions

- The Instagram Graph API `/insights` endpoint is available for the connected Business/Creator accounts (requires `instagram_business_manage_insights` permission, already requested in the OAuth scope).
- The `instagram_account_id` stored in the database is the correct ID for the Graph API insights endpoint.
- The `ig_media_id` stored in posts after successful publication is the correct media ID for fetching media-level insights.
- The existing `_is_token_error()` helper from TASK-028 can be reused for token error detection in the insights service.
- Redis is available for caching (already used for SSE and Celery). Cache keys MUST be namespaced by account ID to prevent collisions between users.
- The user's access token has not been revoked or downgraded in permissions since the initial OAuth connection.
- Meta API rate limits are approximately 200 calls per hour per app-user combination (standard for Instagram Graph API).
