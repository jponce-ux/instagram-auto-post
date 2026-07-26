# Tasks: App Sidebar Layout

**Status**: Not Started
**Progress**: 0/14 tasks
**Current Phase**: —

## Dependencies & Execution Order

- Phase 1 (Foundation) must complete before Phase 2 (Dashboard Refactor)
- Phase 2 should complete before Phase 3 (Polish)
- Tasks within a phase marked `[P]` are parallelizable

---

## Phase 1: Foundation

### T001 [P] Create app_layout.html base template

Create the main layout shell with sidebar, topbar, and main content area.

**Deliverable**: `app/templates/app_layout.html`
**File**: `app/templates/app_layout.html`
**Acceptance**: 
- Template extends base.html (Tailwind CDN)
- Sidebar HTML with 4 nav items (Dashboard, Agenda, Automation, Analytics)
- Topbar with user email and logout button
- `<main id="main-content">` container with `{% block content %}{% endblock %}`
- Mobile hamburger button
- Sidebar drawer CSS (hidden on desktop, slide-out on mobile)

---

### T002 [P] Add schedule and automation routes

Add GET routes for `/dashboard/schedule` and `/dashboard/automation`. When `HX-Request` header is present, return only the content fragment. Otherwise return full page via app_layout.

**Deliverable**: New routes in `app/dashboard/routes.py`
**File**: `app/dashboard/routes.py`
**Acceptance**:
- GET `/dashboard/schedule` returns full page (app_layout + schedule content) on regular request
- GET `/dashboard/schedule` returns only content fragment when `HX-Request` header is present
- Same behavior for `/dashboard/automation`

---

### T003 [P] Create schedule.html template

Create the Agenda view template extending app_layout.html. This is a placeholder for now (actual scheduling logic in spec-024).

**Deliverable**: `app/templates/dashboard/schedule.html`
**File**: `app/templates/dashboard/schedule.html`
**Acceptance**:
- Extends `app_layout.html`
- Shows section title "Agenda de Publicaciones"
- Shows empty state: "Próximamente: Programación de posts"

---

### T004 [P] Create automation.html template

Create the Automation view template extending app_layout.html. This is a placeholder for now (actual automation logic in spec-025).

**Deliverable**: `app/templates/dashboard/automation.html`
**File**: `app/templates/dashboard/automation.html`
**Acceptance**:
- Extends `app_layout.html`
- Shows section title "Automation"
- Shows empty state: "Próximamente: Herramientas de automatización"

---

## Phase 2: Dashboard Refactor

### T005 Refactor dashboard/layout.html

Remove the old sidebar, topbar, and shell from the existing layout. Convert it to just contain the content sections as Jinja2 blocks.

**Deliverable**: Refactored `app/templates/dashboard/layout.html`
**File**: `app/templates/dashboard/layout.html`
**Acceptance**:
- No `<html>`, `<head>`, `<body>` tags (only content blocks)
- Contains blocks for: `accounts_section`, `post_form_section`, `analytics_section`, `history_section`
- All JavaScript for accounts, posts, analytics is preserved

---

### T006 Create dashboard/index.html overview

Create the main Dashboard view that shows KPI summary and quick actions. Extracted from current layout analytics section.

**Deliverable**: `app/templates/dashboard/index.html`
**File**: `app/templates/dashboard/index.html`
**Acceptance**:
- Extends `app_layout.html`
- Shows 3 KPI cards: Total Followers, Monthly Reach, Engagement Rate
- Shows "New Post" quick action button
- Shows recent posts preview (last 5)

---

### T007 Update analytics.html to extend app_layout

Make the existing analytics.html template extend app_layout instead of base.html.

**Deliverable**: Updated `app/templates/dashboard/analytics.html`
**File**: `app/templates/dashboard/analytics.html`
**Acceptance**:
- Now extends `app_layout.html`
- Content remains the same (detailed analytics)
- Works with new sidebar navigation

---

## Phase 3: Polish

### T008 Add active section highlighting

Style the sidebar nav items using Tailwind `aria-current="page"` to visually indicate the active section.

**Deliverable**: CSS classes added to nav items in `app/templates/app_layout.html`
**File**: `app/templates/app_layout.html`
**Acceptance**:
- Active nav item has distinct background color
- Inactive nav items have hover state

---

### T009 Add mobile drawer animation

Add smooth slide transition for the mobile sidebar drawer using CSS transforms.

**Deliverable**: CSS transitions in `app/templates/app_layout.html`
**File**: `app/templates/app_layout.html`
**Acceptance**:
- Sidebar slides in from left when hamburger clicked
- Sidebar slides out when clicking X or outside
- Transition duration ~300ms

---

### T010 Add sidebar state persistence (optional)

Store sidebar collapsed state in localStorage so it persists across page reloads on mobile.

**Deliverable**: JavaScript in `app/templates/app_layout.html`
**File**: `app/templates/app_layout.html`
**Acceptance**:
- Mobile sidebar state persists after page reload
- Desktop sidebar state not affected

---

## Phase 4: Integration & Testing

### T011 Test sidebar navigation desktop

Verify sidebar navigation works correctly on desktop viewport (>=768px).

**Deliverable**: Test checklist completion
**File**: Manual testing
**Acceptance**:
- [ ] All 4 nav items visible in sidebar
- [ ] Clicking each nav item loads correct content via HTMX
- [ ] Active section is highlighted
- [ ] No full page reload

---

### T012 Test sidebar navigation mobile

Verify sidebar hamburger menu works correctly on mobile viewport (<768px).

**Deliverable**: Test checklist completion
**File**: Manual testing
**Acceptance**:
- [ ] Hamburger button visible
- [ ] Clicking hamburger opens drawer
- [ ] Clicking nav item closes drawer and loads content
- [ ] Drawer can be closed by clicking X or backdrop

---

### T013 Test SSE persistence

Verify that SSE real-time updates continue working after navigating between sections.

**Deliverable**: Test checklist completion
**File**: Manual testing
**Acceptance**:
- [ ] SSE connection established on initial page load
- [ ] SSE survives HTMX content swaps (section navigation)
- [ ] Post status updates appear without manual refresh

---

### T014 Update existing tests

Ensure existing dashboard tests still pass with the new layout structure.

**Deliverable**: `tests/test_dashboard.py` passes
**File**: `tests/test_dashboard.py`
**Acceptance**:
- All existing tests pass
- No test failures due to layout changes

---

## Progress Summary

- Phase 1 (Foundation): 4 tasks
- Phase 2 (Dashboard Refactor): 3 tasks
- Phase 3 (Polish): 3 tasks
- Phase 4 (Testing): 4 tasks

**Total**: 14 tasks
