# Plan: App Sidebar Layout (spec-023-app-sidebar-layout)

## Summary

Refactor the monolithic dashboard (`dashboard/layout.html`) into a multi-view app with a persistent sidebar navigation. The sidebar provides access to Dashboard, Agenda, Automation, and Analytics sections. Navigation uses HTMX for seamless transitions without full page reloads. Layout is responsive with collapsible sidebar on mobile.

## Technical Context

**Language/Framework**: Python 3.11+ / FastAPI
**Primary Dependencies**: FastAPI, Jinja2, HTMX, Tailwind CSS (CDN)
**Storage**: PostgreSQL + SQLAlchemy 2.0 (async)
**Testing**: pytest with async support

**Target Platform**: Web (responsive: mobile-first, desktop-optimized)
**Project Type**: FastAPI HTML dashboard with HTMX interactivity
**Performance Goals**: 
- Sidebar loads with page shell (static HTML) - no loading state needed
- Content sections load progressively
- Navigation transitions < 200ms perceived latency

**Constraints**:
- Keep using Tailwind CDN (no build step)
- Maintain backward compatibility with existing auth patterns (`get_current_user`)
- Existing SSE endpoints for real-time updates should continue working

## Applied Lessons

None yet — this is a new refactoring effort with no prior lessons.

## Architecture Decisions

| Decision | Options | Tradeoffs | Choice |
|----------|---------|-----------|--------|
| Sidebar state management | Cookie (server-rendered) vs URL fragment vs localStorage | Cookie: persists across refresh; URL: shareable state; localStorage: simple | URL fragment (`#section`) for active state, localStorage for collapsed state on mobile |
| Navigation approach | Full page reload vs HTMX swap vs client-side router | Full reload: simple, SEO-friendly; HTMX: seamless; Router: app-like feel | HTMX `hx-get` with `hx-target="main"` and `hx-swap="innerHTML"` for content area |
| Mobile sidebar | Slide-out drawer vs modal overlay vs persistent mini-sidebar | Drawer: cleanest UX; Modal: simpler to implement; Mini-sidebar: always visible | Slide-out drawer triggered by hamburger button |
| Active section indicator | Server-side (template context) vs client-side (URL matching) | Server: accurate but requires page reload concept; Client: simpler with HTMX | Client-side URL matching with `aria-current="page"` |
| Layout structure | Single base template with blocks vs separate layout per section | Single:DRY but complex blocks; Separate: clearer but repetitive | Single `app_layout.html` base with sidebar/topbar and `{% block content %}` for section content |

## Project Structure

```
app/
├── templates/
│   ├── app_layout.html          # NEW: Base layout with sidebar + topbar shell
│   ├── dashboard/
│   │   ├── layout.html          # MODIFY: Remove sidebar/topbar, keep content sections
│   │   ├── index.html           # MODIFY: Extends app_layout.html
│   │   ├── schedule.html        # NEW: Agenda view
│   │   ├── automation.html      # NEW: Automation view  
│   │   └── analytics.html       # EXISTING: Keep as-is, extend app_layout.html
├── dashboard/
│   └── routes.py                # MODIFY: Add /schedule, /automation routes, refactor index
```

## Data Flow

```
User Browser
    │
    ├──► GET /dashboard ──► Auth Guard ──► app_layout.html (shell)
    │                           │                    │
    │                           │                    └──► Initial content: dashboard/index.html fragment
    │
    ├──► HTMX: Click "Agenda" in sidebar
    │         hx-get="/dashboard/schedule"
    │         hx-target="main-content"
    │         hx-swap="innerHTML"
    │                           │
    │                           └──► Returns: schedule.html fragment (no full page reload)
    │
    ├──► HTMX: Click "Analytics" in sidebar
    │                           │
    │                           └──► Returns: analytics.html fragment
    │
    └──► Mobile: Click hamburger
              Toggles sidebar visibility (CSS transform, no server call)
```

## Phase 1: Foundation

### 1.1 Create app_layout.html base template

Create `app/templates/app_layout.html` with:
- Full HTML document structure (doctype, head, body)
- Tailwind CDN (already in base.html, keep it)
- Sidebar HTML (hidden on mobile by default)
- Top bar HTML with user info
- `<main id="main-content">{% block content %}{% endblock %}</main>` container
- Mobile hamburger button + drawer JavaScript
- HTMX CDN (already in project)

**File**: `app/templates/app_layout.html`

### 1.2 Add navigation routes

Add new dashboard routes for `/schedule` and `/automation`. Refactor existing routes to return fragments when HTMX request.

**File**: `app/dashboard/routes.py`

### 1.3 Create schedule view

Create `schedule.html` template extending `app_layout.html`.

**File**: `app/templates/dashboard/schedule.html`

### 1.4 Create automation view

Create `automation.html` template extending `app_layout.html`.

**File**: `app/templates/dashboard/automation.html`

## Phase 2: Dashboard Refactor

### 2.1 Refactor dashboard/layout.html

Remove sidebar and topbar from current layout. Keep only the content sections (accounts, post form, analytics, history) as blocks that can be included in the new layout.

**File**: `app/templates/dashboard/layout.html`

### 2.2 Create dashboard/index.html

Main dashboard view that shows:
- KPI cards (followers, reach, engagement rate) - extracted from current analytics section
- Quick action button for new post
- Recent posts preview

**File**: `app/templates/dashboard/index.html`

### 2.3 Update analytics.html

Make existing analytics.html extend app_layout.html instead of base.html.

**File**: `app/templates/dashboard/analytics.html`

## Phase 3: Polish

### 3.1 Add active state styling

Add Tailwind classes for `aria-current="page"` to highlight active sidebar item.

### 3.2 Mobile drawer animation

Add smooth slide transition for mobile sidebar.

### 3.3 Test all navigation flows

Verify:
- Sidebar navigation works on desktop
- Hamburger menu works on mobile
- Active section is highlighted
- Content loads via HTMX (no full reload)

## Affected Files

| File | Action | Description |
|------|--------|-------------|
| `app/templates/app_layout.html` | Create | Base layout with sidebar + topbar shell |
| `app/templates/dashboard/layout.html` | Refactor | Remove shell, keep content sections |
| `app/templates/dashboard/index.html` | Refactor | Extends app_layout, dashboard overview |
| `app/templates/dashboard/schedule.html` | Create | Agenda view |
| `app/templates/dashboard/automation.html` | Create | Automation view |
| `app/templates/dashboard/analytics.html` | Refactor | Extends app_layout |
| `app/dashboard/routes.py` | Modify | Add schedule/automation routes |

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | Sidebar navigation items render correctly | Template render test |
| Integration | Auth guard protects all dashboard routes | TestClient with/without JWT |
| Integration | HTMX navigation between sections | Assert HX-Request header handling |
| Manual | Mobile sidebar drawer | Browser DevTools device emulation |

## Risk Assessment

- **Risk**: HTMX navigation may break SSE connections (real-time updates)
  - **Mitigation**: SSE connects at `window` level, not per-section. Test that SSE survives section changes.
- **Risk**: Back/forward browser navigation may not work as expected with HTMX
  - **Mitigation**: Accept this limitation for now. History management via `hx-push-url` can be added later if needed.
- **Risk**: Multiple views loading same data (e.g., accounts) creates redundant queries
  - **Mitigation**: Accept for now. Caching layer can be added in future optimization phase.

## Rollback Plan

1. Revert `app/templates/app_layout.html` deletion
2. Restore `dashboard/layout.html` with original sidebar/topbar
3. Remove `/schedule` and `/automation` routes
4. All other views continue working since they already exist
