---
ticket: TASK-030
phase: spec
model: qwen3.6-plus
generated: 2026-07-03
status: draft
---

# Feature Specification: Global Account Analytics View Dashboard

**Feature Branch**: `feat/task-030-analytics-dashboard`  
**Created**: 2026-07-03  
**Status**: Draft  
**Input**: User description: "TASK-030 - Frontend Feature: Global Account Analytics View Dashboard. Build a comprehensive Analytics View tab within the user dashboard displaying historical and current whole-account performance using interactive graphical representations."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Full-Page Analytics Dashboard (Priority: P1)

The user navigates to a dedicated Analytics page from the dashboard and sees a comprehensive overview of their Instagram account performance. The page displays summary cards with key metrics (Total Reach, Impressions, Profile Views, Follower Growth) and interactive timeline charts showing historical data over a selectable period (7 or 28 days). If cached data is available, the page renders immediately; otherwise, it shows skeleton loading placeholders while fetching fresh data.

**Why this priority**: This is the core deliverable — a dedicated analytics view that gives users a complete, visual understanding of their account performance. Without this, users only see the basic inline metrics in the main dashboard layout.

**Independent Test**: Log in to the dashboard. Navigate to the Analytics page. Verify that summary cards display correct metric values and that at least one timeline chart renders with historical data. The page should load within 3 seconds from cache.

**Acceptance Scenarios**:

1. **Given** a user has a connected, active Instagram account with published content, **When** they navigate to the Analytics page, **Then** they see summary cards for Total Reach, Impressions, Profile Views, and Follower Growth, along with interactive timeline charts showing historical data.
2. **Given** the user has viewed analytics within the last hour (cached data exists), **When** they navigate to the Analytics page, **Then** the page renders immediately with cached data and no loading state is shown.
3. **Given** no valid cached data exists, **When** the user navigates to the Analytics page, **Then** skeleton loading placeholders are displayed while data is fetched, and charts populate once the data arrives.
4. **Given** the user changes the time period selector (e.g., from 28 days to 7 days), **When** the selection changes, **Then** the summary cards and charts update to reflect the new period.

---

### User Story 2 - Interpret Metric Trends with Visual Indicators (Priority: P2)

Each summary card on the Analytics page shows not only the current metric value but also a trend indicator (positive/negative) comparing the current period to the previous period. Positive trends are shown in green, negative trends in red, helping the user quickly understand performance direction.

**Why this priority**: Raw numbers alone don't tell the full story. Trend indicators help users understand whether their performance is improving or declining, which is essential for content strategy decisions.

**Independent Test**: View the Analytics page with data that shows metric changes between periods. Verify that each summary card displays a trend indicator (arrow or percentage) with appropriate color coding (green for positive, red for negative).

**Acceptance Scenarios**:

1. **Given** the user's reach increased compared to the previous period, **When** they view the Total Reach card, **Then** a green upward indicator is shown alongside the metric value.
2. **Given** the user's follower count decreased compared to the previous period, **When** they view the Follower Growth card, **Then** a red downward indicator is shown alongside the metric value.
3. **Given** a metric has no change compared to the previous period, **When** the user views that card, **Then** a neutral indicator (e.g., gray dash or "0%") is shown.

---

### User Story 3 - Handle Error and Edge States Gracefully (Priority: P3)

When the analytics data cannot be fetched (API failure, no connected account, inactive account, or rate limit exceeded), the Analytics page displays appropriate error messages with actionable guidance rather than a blank or broken page.

**Why this priority**: Users must understand why data isn't available and what action to take. A broken or blank page erodes trust in the analytics feature.

**Independent Test**: Disconnect the Instagram account or simulate an API failure. Navigate to the Analytics page. Verify that a clear error message is displayed with guidance on how to resolve the issue.

**Acceptance Scenarios**:

1. **Given** the user has no Instagram account connected, **When** they navigate to the Analytics page, **Then** a message indicates they need to connect an Instagram account, with a link or button to start the connection flow.
2. **Given** the user's Instagram account is inactive (token expired), **When** they navigate to the Analytics page, **Then** a message indicates the account needs to be reconnected, with a button to start re-authentication.
3. **Given** the Instagram API is temporarily unavailable or rate-limited, **When** the user navigates to the Analytics page, **Then** the last cached data is shown with a "stale" indicator and a "Retry" button, or if no cache exists, a message indicates analytics are temporarily unavailable.

---

### Edge Cases

- **What happens if the user has multiple Instagram accounts?** The Analytics page displays data for the primary (first active) account, with a selector to switch between accounts if multiple are connected.
- **What happens if the Instagram API returns partial data (some metrics missing)?** Available metrics are displayed; missing metrics show "N/A" or "—" on the card, and the chart renders only the available data series.
- **What happens if the user has no published posts yet?** Account-level metrics that don't require posts (follower count, profile views) are still displayed. Metrics that require posts (reach, impressions) show "No data available yet" with an encouraging message to publish their first post.
- **What happens if the chart data has zero values for all time points?** The chart renders with a flat line at zero and a message indicating "No activity recorded for this period."
- **What happens if the user navigates away while data is still loading?** The in-flight request is cancelled to avoid unnecessary API calls.
- **What happens if the user rapidly changes the period selector?** Only the last selected period triggers an API call; intermediate selections are debounced to avoid redundant requests.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a dedicated Analytics page accessible from the dashboard navigation, protected by authentication.
- **FR-002**: The Analytics page MUST display summary cards for at least four key metrics: Total Reach, Impressions, Profile Views, and Follower Growth.
- **FR-003**: Each summary card MUST show a trend indicator comparing the current period to the previous period, with color-coded visual feedback (positive = green, negative = red, neutral = gray).
- **FR-004**: The Analytics page MUST include at least one interactive timeline chart that plots historical metric data over the selected time period.
- **FR-005**: Users MUST be able to select between at least two time periods: 7 days and 28 days.
- **FR-006**: When valid cached data exists, the page MUST render immediately without showing a loading state.
- **FR-007**: When no valid cached data exists, the page MUST display skeleton loading placeholders while data is being fetched.
- **FR-008**: When the Instagram API is unavailable but cached data exists, the page MUST display the cached data with a "stale" indicator and a "Retry" button.
- **FR-009**: When the user has no connected Instagram account, the page MUST display a message prompting them to connect an account, with a clear call-to-action.
- **FR-010**: When the user's Instagram account is inactive (expired token), the page MUST display a message prompting reconnection, with a button to start the re-authentication flow.
- **FR-011**: The page MUST only display analytics for the authenticated user's own Instagram accounts — no cross-user data leakage.
- **FR-012**: When the user changes the time period, the summary cards and charts MUST update to reflect the new period's data.
- **FR-013**: The page MUST handle rapid period selector changes by debouncing requests, ensuring only the final selection triggers an API call.
- **FR-014**: When metrics are partially available (some returned, some missing from the API), available metrics MUST be displayed and missing metrics MUST show a placeholder (e.g., "N/A" or "—").

### Key Entities

- **Account Analytics Summary**: Aggregated metric values (reach, impressions, profile views, follower count) for a selected time period, with trend comparison to the previous period.
- **Timeline Data Points**: Time-series data for each metric, plotted on interactive charts, with one data point per day within the selected period.
- **Period Selection**: User-selected time range (7 days or 28 days) that determines which data is fetched and displayed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can view the full Analytics page with all summary cards and charts rendered within 3 seconds when served from cache.
- **SC-002**: Users can view the full Analytics page with all summary cards and charts rendered within 6 seconds when fetching fresh data from the API.
- **SC-003**: 90% of users can correctly identify whether their account performance is improving or declining based on the trend indicators within 10 seconds of viewing the page.
- **SC-004**: The page displays appropriate error messages with actionable guidance in 100% of error scenarios (no connected account, inactive account, API failure, rate limit exceeded).
- **SC-005**: Users can switch between 7-day and 28-day views and see updated data within 3 seconds (from cache) or 6 seconds (fresh fetch).

## Assumptions

- The backend analytics API endpoints from TASK-029 (`GET /dashboard/analytics/account`) are fully functional and return the expected JSON response structure.
- The Instagram Graph API provides historical time-series data for account-level metrics (impressions, reach, profile_views, follower_count) broken down by day.
- The user has at least one connected, active Instagram Business or Creator account with the `instagram_business_manage_insights` permission.
- Tailwind CSS is already configured and available in the project for styling.
- A lightweight charting library (e.g., Chart.js or ApexCharts) can be loaded via CDN without significant performance impact.
- The existing dashboard navigation pattern (sidebar or tabs) can be extended to include an "Analytics" tab/link.
- Redis caching infrastructure from TASK-029 is operational and provides sub-second cache reads.
- The trend comparison is calculated by comparing the current period's metrics to the immediately preceding period of equal length (e.g., last 7 days vs. the 7 days before that).
