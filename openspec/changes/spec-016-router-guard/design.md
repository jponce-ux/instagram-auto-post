# Design: Router Guard and Root Route Logic

## Technical Approach

Implement JWT cookie-based router guards that control access flow between public landing pages and authenticated dashboard areas. The approach introduces an optional authentication dependency that gracefully handles missing/invalid tokens without raising 401 errors, enabling conditional redirects at the root route and auth page guards.

**Mapping to proposal**: Directly implements the intent to "decidir qué ve el usuario al entrar a la raíz basándose en la validez de su JWT".

## Architecture Decisions

| Decision | Options | Tradeoffs | Choice |
|----------|---------|-----------|--------|
| Token source | Cookie vs Header | Header is stateless REST-friendly; Cookie enables seamless browser redirects | Cookie `access_token` — aligns with HTMX/server-rendered architecture |
| Optional auth pattern | Return None vs raise exception | Exceptions interrupt flow; None allows conditional logic | Return `User \| None` from `get_current_user_optional` |
| Redirect status code | 302 vs 303 vs 307 | 302 may change POST to GET; 303 explicitly preserves method | 303 See Other for all redirects |
| Dashboard auth failure | Redirect to / vs 401 page | 401 requires handling; Redirect to / provides better UX | Redirect to / (login page) |
| Logout behavior | Clear cookie vs keep | Clear cookie is proper logout | Clear `access_token` cookie |

### Decision: Cookie-based JWT over Header
**Choice**: Read JWT from `access_token` cookie, not Authorization header
**Rationale**: The application uses HTMX and server-side rendering. Cookie-based auth provides seamless browser redirects without requiring JavaScript to manage tokens.

### Decision: Dashboard Redirects to / Instead of 401
**Choice**: When `get_current_user` fails (no/invalid JWT), redirect to `/` instead of returning 401
**Rationale**: Provides better UX — user sees the login page rather than an error. The redirect is cleaner for the HTMX flow.

### Decision: Logout Clears Cookie
**Choice**: `/auth/logout` clears the `access_token` cookie
**Rationale**: Proper logout behavior. User is unauthenticated after logout.

## Data Flow

### Root Route (`/`)
```
User visits /
    │
    └─► get_current_user_optional(cookie: access_token)
            │
            ├─► Valid JWT ──► User ──► Redirect 303 to /dashboard
            │
            └─► Invalid/No JWT ──► None ──► Render landing.html
```

### Dashboard Protection
```
User visits /dashboard/*
    │
    └─► get_current_user (existing)
            │
            ├─► Valid JWT ──► User ──► Allow access
            │
            └─► Invalid/No JWT ──► Redirect 303 to /
```

### Auth Guards (`/auth/login`, `/auth/register`)
```
Authenticated user visits /auth/login
    │
    └─► get_current_user_optional(cookie: access_token)
            │
            └─► Valid JWT ──► Redirect 303 to /dashboard (guard)
```

### Logout
```
User visits /auth/logout
    │
    └─► Clear access_token cookie
            │
            └─► Redirect 303 to /
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/auth/dependencies.py` | Modify | Add `get_current_user_optional` function |
| `app/auth/routes.py` | Modify | Add guards to `/login` and `/register`, add `/logout` endpoint |
| `app/main.py` | Modify | Update `/` route to use optional dependency |
| `app/templates/landing.html` | Create | Minimal placeholder (content in SPEC-017) |

## Interfaces / Contracts

### New Dependency: `get_current_user_optional`

```python
async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Extract and validate JWT from 'access_token' cookie.
    Returns User if valid, None if missing/invalid/expired.
    Never raises HTTPException.
    """
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email = payload.get("sub")
        if not email:
            return None
    except JWTError:
        return None
    
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()
```

### Route Signatures

```python
# app/main.py - Root route
@app.get("/")
async def root(
    request: Request,
    user: User | None = Depends(get_current_user_optional),
):
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(request=request, name="landing.html")

# app/auth/routes.py - Auth guards
@router.get("/login")
async def login_page(
    request: Request,
    user: User | None = Depends(get_current_user_optional),
):
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    # ... render login form

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `get_current_user_optional` | Mock Request.cookies and db. Valid/invalid/no token |
| Integration | `/` route | TestClient with/without cookie. Assert 303 redirect or 200 |
| Integration | `/auth/login` guard | Valid cookie → 303 to /dashboard. No cookie → 200 |
| Integration | `/auth/logout` | Assert cookie cleared, 303 redirect |
| Integration | `/dashboard/*` auth | No cookie → 303 to / |

## Migration / Rollout

**No database migration required.**

**Behavior changes**:
1. Currently, `/` always renders index.html. After: authenticated → dashboard, unauthenticated → landing.html
2. Currently, unauthenticated `/dashboard` access returns 401. After: redirects to `/`
3. New endpoint `/auth/logout` clears cookie

**Rollout**:
1. Ensure login sets `access_token` cookie before this is deployed
2. Landing page must exist (minimal placeholder even if content comes later)
