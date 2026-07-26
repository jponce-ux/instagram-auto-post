# Feature Spec: Analytics Detailed View

**Feature Branch**: `feat/spec-026-analytics-detailed`
**Created**: 2026-07-26
**Status**: Draft
**Type**: Feature
**Input**: Detailed analytics view with KPIs, charts, and top content - "Analytics" section in sidebar
**Source**: Manual input (Insight Flux design description)
**Depends On**: spec-012-publicacion-estados-post-logica, spec-023-app-sidebar-layout

## User Scenarios & Testing

### User Story 1 - KPI Overview (Priority: P1)

The user sees high-level KPIs with trend indicators on the Analytics dashboard.

**Why this priority**: Immediate insight into account performance at a glance.

**Independent Test**: User navigates to Analytics and sees KPI cards without scrolling.

**Acceptance Scenarios**:
1. **Given** a user is on the Analytics view, **When** the page loads, **Then** they see three KPI cards: Total Followers, Monthly Reach, Engagement Rate
2. **Given** a user sees a KPI card, **When** it loads, **Then** they see the current value and a percentage trend indicator (up/down arrow with color)
3. **Given** a user has insufficient data for a metric, **When** the card loads, **Then** it shows "—" instead of a value with explanation tooltip

### User Story 2 - Reach Chart (Priority: P1)

The user sees a line chart showing their reach over time.

**Why this priority**: Visual trend is easier to interpret than raw numbers.

**Independent Test**: Line chart renders with correct data points.

**Acceptance Scenarios**:
1. **Given** a user is on the Analytics view, **When** the page loads, **Then** they see a line chart of Monthly Reach for the selected period
2. **Given** a user has data for multiple periods, **When** they select a different time filter (Daily, Weekly, Monthly), **Then** the chart updates to show data for that period
3. **Given** a user has no reach data, **When** the chart loads, **Then** it shows an empty state "No reach data available"

### User Story 3 - Follower Growth Chart (Priority: P2)

The user sees a bar chart comparing their follower growth against industry average.

**Why this priority**: Context helps users understand if their growth is healthy.

**Independent Test**: Bar chart renders with user's data and industry benchmark.

**Acceptance Scenarios**:
1. **Given** a user is on the Analytics view, **When** they scroll to the growth section, **Then** they see a bar chart with their follower acquisition
2. **Given** the chart is displayed, **When** it renders, **Then** it includes an industry average benchmark line
3. **Given** a user's growth exceeds the benchmark, **When** they view the chart, **Then** their bar is colored green (positive)

### User Story 4 - Top Content Feed (Priority: P1)

The user sees a grid of their best-performing posts with individual metrics.

**Why this priority**: Understanding what content resonates helps inform future posts.

**Independent Test**: Grid displays posts sorted by performance metric.

**Acceptance Scenarios**:
1. **Given** a user is on the Analytics view, **When** they scroll to the top content section, **Then** they see a grid of their best posts (sorted by engagement)
2. **Given** a post card is displayed, **When** it renders, **Then** it shows: thumbnail, caption preview, likes count, comments count, and category tag
3. **Given** a user has no published posts, **When** they view the top content section, **Then** they see an empty state "Publish posts to see performance data"
4. **Given** a user clicks on a post card, **When** they do, **Then** they see detailed analytics for that post in a modal

### User Story 5 - Time Filter (Priority: P2)

The user can filter analytics data by time period.

**Why this priority**: Different time scales reveal different insights.

**Independent Test**: Filter selection updates all charts and KPIs.

**Acceptance Scenarios**:
1. **Given** a user is on the Analytics view, **When** they click "Daily", **Then** all charts and KPIs update to show daily data
2. **Given** a user is on the Analytics view, **When** they click "Weekly", **Then** all charts and KPIs update to show weekly aggregates
3. **Given** a user is on the Analytics view, **When** they click "Monthly", **Then** all charts and KPIs update to show monthly aggregates

## Edge Cases

- **No Instagram token**: Show "Connect Instagram to see analytics" instead of empty data
- **Token expired**: Show warning banner with "Reconnect account" action
- **API rate limit**: Show cached data with timestamp, disable filter buttons temporarily
- **Zero engagement**: Display "0" not "—" for actual zeros
- **Industry benchmark unavailable**: Omit benchmark line from growth chart

## Functional Requirements

- FR-001: The system MUST display three KPI cards: Total Followers, Monthly Reach, Engagement Rate
- FR-002: Each KPI card MUST show a trend indicator (percentage change from previous period)
- FR-003: The system MUST display a line chart for reach over time
- FR-004: The system MUST display a bar chart for follower growth with industry benchmark
- FR-005: The system MUST display a grid of top-performing posts sorted by engagement
- FR-006: Each post card MUST show: thumbnail, caption preview, likes, comments, category tag
- FR-007: The system MUST support time filters: Daily, Weekly, Monthly
- FR-008: All charts and KPIs MUST update when time filter changes
- FR-009: The system MUST show detailed post analytics in a modal when clicking a post card
- FR-010: The system MUST use HTMX for chart updates without full page reload
- FR-011: The system SHOULD cache analytics data to reduce API calls

## Key Entities

### AccountMetrics (cached)
| Field | Type | Description |
|-------|------|-------------|
| period_start | datetime | Start of measurement period |
| period_end | datetime | End of measurement period |
| follower_count | int | Total followers at period end |
| follower_delta | int | Change from previous period |
| reach | int | Total reach for period |
| reach_delta | float | Percentage change |
| engagement_rate | float | (interactions / reach) * 100 |
| engagement_delta | float | Percentage change |
| cached_at | datetime | Cache timestamp |

### MediaInsights (per post)
| Field | Type | Description |
|-------|------|-------------|
| ig_media_id | str | Instagram media ID |
| likes | int | Like count |
| comments | int | Comment count |
| saves | int | Save count |
| impressions | int | Impressions count |
| reach | int | Reach count |
| engagement | int | Total interactions |
| category | str | Post category (auto-detected or manual) |

## Design References

**Source**: User description - Insight Flux design system, Analytics Dashboard specifications

> These designs serve as **reference and inspiration** — the final implementation may diverge based on technical constraints, existing design system patterns, or developer judgment.

| Resource | Description | Relevant Stories |
|----------|-------------|-----------------|
| `resources/analytics-dashboard.png` | Full Analytics dashboard mockup | US-1, US-2, US-3, US-4 |

## Success Criteria

1. User sees KPI cards with trend indicators on Analytics view
2. Line chart shows reach over time with correct data points
3. Bar chart shows follower growth with industry benchmark
4. Top content grid displays best posts sorted by engagement
5. Clicking a post opens detailed analytics modal
6. Time filter (Daily/Weekly/Monthly) updates all visualizations
7. HTMX updates charts without full page reload
8. Empty states appear appropriately when data is unavailable
