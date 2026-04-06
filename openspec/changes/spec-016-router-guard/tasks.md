# Tasks: spec-016-router-guard

## Phase 0: Git

- [ ] 0.1 Create feature branch `feature/016-navigation-guards` from `main`

## Phase 1: Dependencies

- [ ] 1.1 Add `get_current_user_optional` to `app/auth/dependencies.py`
  - Read JWT from `access_token` cookie (not Authorization header)
  - Return `User | None` (None if missing/invalid/expired)
  - Never raise HTTPException

## Phase 2: Root Route

- [ ] 2.1 Modify `app/main.py` - update root endpoint `/`
  - Accept `get_current_user_optional` dependency
  - If user returned → 303 redirect to /dashboard
  - If None returned → 200 with landing.html

## Phase 3: Dashboard Protection

- [ ] 3.1 Modify dashboard routes to redirect unauthenticated users to `/` instead of returning 401
  - This may require a custom exception handler or modifying the auth dependency behavior
  - Alternative: Create a `require_auth` dependency that redirects instead of raising

## Phase 4: Auth Guards

- [ ] 4.1 Modify `app/auth/routes.py` - add guards to login and register routes
  - GET /auth/login: if authenticated → 303 redirect to /dashboard
  - GET /auth/register: if authenticated → 303 redirect to /dashboard

- [ ] 4.2 Add `/auth/logout` endpoint
  - Clear `access_token` cookie
  - Redirect 303 to /

## Phase 5: Landing Page

- [ ] 5.1 Create `app/templates/landing.html`
  - Minimal placeholder with login/register CTAs
  - NOTE: Full content comes in SPEC-017; this is a minimal working page

## Phase 6: Tests

- [ ] 6.1 Create `tests/test_router_guard.py`
  - Test `get_current_user_optional` with valid/invalid/no token
  - Test root route: authenticated → 303 to dashboard, unauthenticated → 200 landing
  - Test /auth/login guard: authenticated → 303 to dashboard
  - Test /auth/register guard: authenticated → 303 to dashboard
  - Test /auth/logout: clears cookie, redirects to /
  - Test /dashboard/*: unauthenticated → 303 to /

## Phase 7: Commit

- [ ] 7.1 Stage all modified files
- [ ] 7.2 Commit with message: `feat(router): add navigation guards and conditional routing`
- [ ] 7.3 Push branch to remote
- [ ] 7.4 Create PR if applicable

---

## Summary

| Phase | Tasks | Focus |
|-------|-------|-------|
| Phase 0 | 1 | Git |
| Phase 1 | 1 | Dependencies (get_current_user_optional) |
| Phase 2 | 1 | Root Route |
| Phase 3 | 1 | Dashboard Protection |
| Phase 4 | 2 | Auth Guards + Logout |
| Phase 5 | 1 | Landing Page (minimal) |
| Phase 6 | 1 | Tests |
| Phase 7 | 4 | Commit |
| **Total** | **12** | |

## Implementation Order

1. Git (branch)
2. Dependencies (foundation)
3. Root Route
4. Dashboard Protection
5. Auth Guards + Logout
6. Landing Page
7. Tests
8. Commit

## Open Questions

- [x] Dashboard redirects to / (login) not 401 — RESOLVED in design
- [x] Logout clears cookie — RESOLVED in design
- [x] Landing content in SPEC-017 — RESOLVED, minimal placeholder only
