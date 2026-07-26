# Feature Spec: App Sidebar Layout

**Feature Branch**: `feat/spec-023-app-sidebar-layout`
**Created**: 2026-07-26
**Status**: Draft
**Type**: Feature
**Input**: Dashboard refactoring - separate monolithic dashboard into multi-view app with sidebar navigation
**Source**: Manual input

## User Scenarios & Testing

### User Story 1 - Sidebar Navigation (Priority: P1)

The user accesses the authenticated app and sees a persistent sidebar for navigating between sections.

**Why this priority**: Navigation is the primary interaction pattern - without it, users cannot access any other views.

**Independent Test**: User can see sidebar immediately after login and navigate to any section.

**Acceptance Scenarios**:
1. **Given** a user is authenticated, **When** they access any dashboard route, **Then** they see a sidebar on the left with navigation links
2. **Given** a user is on the Dashboard view, **When** they click "Analytics" in the sidebar, **Then** they navigate to the Analytics view
3. **Given** a user is on any view, **When** they click "Dashboard" in the sidebar, **Then** they return to the Dashboard overview
4. **Given** a user is on mobile viewport (<768px), **When** the page loads, **Then** the sidebar is hidden by default and accessible via hamburger menu

### User Story 2 - Multi-View App Structure (Priority: P1)

The user sees distinct views for Dashboard, Schedule (Agenda), Automation, and Analytics sections.

**Why this priority**: Core requirement to separate the monolithic dashboard into focused sections.

**Independent Test**: Each view loads independently and displays its specific content.

**Acceptance Scenarios**:
1. **Given** a user is authenticated, **When** they access `/dashboard`, **Then** they see the Dashboard overview with KPIs and quick actions
2. **Given** a user clicks "Agenda" in sidebar, **When** they access `/dashboard/schedule`, **Then** they see scheduled posts management
3. **Given** a user clicks "Automation" in sidebar, **When** they access `/dashboard/automation`, **Then** they see automation tools
4. **Given** a user clicks "Analytics" in sidebar, **When** they access `/dashboard/analytics`, **Then** they see detailed metrics

### User Story 3 - Top Bar Integration (Priority: P2)

The user sees a top bar with user context and actions, consistent across all views.

**Why this priority**: Provides global actions (notifications, profile) without duplicating in each view.

**Independent Test**: Top bar renders identically across all views with correct user info.

**Acceptance Scenarios**:
1. **Given** a user is authenticated, **When** they view any dashboard section, **Then** the top bar shows their email/name
2. **Given** a user is on any view, **When** they click the user profile area, **Then** they see a dropdown with logout option

## Edge Cases

- **No linked accounts**: Sidebar still visible, but relevant sections show empty states
- **Session expired**: Redirect to login, preserve intended destination for post-login redirect
- **Slow network**: Sidebar loads immediately (static HTML), content loads progressively
- **Mobile orientation change**: Sidebar state (open/closed) persists across orientation changes

## Functional Requirements

- FR-001: The system MUST render a sidebar on all authenticated dashboard routes (`/dashboard/*`)
- FR-002: The sidebar MUST contain navigation links for: Dashboard, Agenda, Automation, Analytics
- FR-003: The sidebar MUST highlight the current active section
- FR-004: The sidebar MUST be collapsible on mobile (<768px) via hamburger button
- FR-005: The system MUST maintain authentication state across all sidebar navigation
- FR-006: The sidebar MUST NOT cause full page reloads when switching sections (HTMX or client-side routing)
- FR-007: The top bar MUST display user identification and logout option
- FR-008: The layout MUST be responsive from 320px mobile to desktop

## Key Entities

### SidebarNavItem
- `id`: string (unique identifier)
- `label`: string (display text)
- `icon`: string (SVG path or icon name)
- `href`: string (route path)
- `active`: boolean (current route flag)

### AppLayout
- `sidebar`: SidebarNavItem[] (navigation items)
- `topBar`: TopBar (user info + actions)
- `mainContent`: slot (view-specific content)

## Design References

**Source**: User description (Insight Flux design system mentioned)
**Resources**: See `resources/` directory for reference designs

> These designs serve as **reference and inspiration** — the final implementation may diverge based on technical constraints, existing design system patterns, or developer judgment.

| Resource | Description | Relevant Stories |
|----------|-------------|-----------------|
| `resources/sidebar-layout.png` | Sidebar with nav items + top bar layout | US-1, US-2, US-3 |

## Success Criteria

1. User can navigate between all four sections (Dashboard, Agenda, Automation, Analytics) using the sidebar
2. Sidebar is visible and functional on desktop (>=768px)
3. Sidebar collapses to hamburger menu on mobile (<768px)
4. Current section is visually highlighted in sidebar
5. No full page reload when switching sections
6. All views maintain consistent layout shell (sidebar + top bar + content)
7. User can log out from any view via top bar
