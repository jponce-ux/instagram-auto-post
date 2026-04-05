# Design: User Dashboard (spec-013-user-dashboard)

## Technical Approach

Build a protected HTML dashboard using FastAPI + Jinja2 with HTMX for interactivity and Tailwind CSS (CDN) for mobile-first responsive styling. The dashboard follows the existing codebase patterns: JWT auth via `get_current_user`, async SQLAlchemy queries, and HTMX partials for dynamic updates.

**Key pattern**: All dashboard routes return either full HTML pages (for direct navigation) or HTML fragments (for HTMX swaps), using the `HX-Request` header to differentiate.

## Architecture Decisions

| Decision | Options | Tradeoffs | Choice |
|----------|---------|-----------|--------|
| Tailwind CDN vs Build | CDN (simpler) vs Build step (smaller bundle) | CDN adds 80KB, zero config; Build requires Node, better for prod | CDN with pinned version + integrity hash |
| HTMX Polling vs WebSocket | Polling (10s) vs WebSocket (real-time) | Polling: simple, works everywhere; WS: complex, needs connection mgmt | Polling via `hx-trigger="every 10s"` |
| Post Model Dependency | Create stub model now vs Wait for SPEC-012 | Stub: UI works end-to-end; Wait: cleaner but blocks testing | Create minimal Post model in this change |
| File Upload Strategy | Direct to MinIO vs Via endpoint | Direct: faster, no proxy; Via endpoint: unified auth, validation | Via `/api/v1/debug/upload` endpoint with HTMX |
| Router Organization | Separate `dashboard/` module vs Inline in main.py | Module: cleaner, testable; Inline: simpler for small features | Separate `app/dashboard/` module |

## Data Flow

```
User Browser
    │
    ├──► GET /dashboard ──► Auth Guard ──► Dashboard Index
    │                           │
    ├──► GET /dashboard/accounts ──► Fetch InstagramAccounts ──► Render List
    │
    ├──► GET /auth/instagram/login ──► Redirect to Meta OAuth
    │
    ├──► POST /dashboard/post ──► Upload File ──► Create Post ──► Return HTML
    │
    └──► GET /dashboard/posts/feed (HX-Request) ──► Query Posts ──► Return Fragment
                                          │
                                          └──► HTMX polls every 10s
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/dashboard/__init__.py` | Create | Module init |
| `app/dashboard/routes.py` | Create | Protected dashboard routes: GET /dashboard, /accounts, /posts/feed; POST /post |
| `app/dashboard/service.py` | Create | Business logic: fetch accounts, create post, get posts with status |
| `app/templates/dashboard/layout.html` | Create | Dashboard base template extending base.html with Tailwind |
| `app/templates/dashboard/index.html` | Create | Main dashboard with accounts + post form + history sections |
| `app/templates/dashboard/accounts_partial.html` | Create | HTMX fragment for linked accounts list |
| `app/templates/dashboard/posts_feed.html` | Create | HTMX fragment for post history with polling |
| `app/templates/dashboard/post_form.html` | Create | HTMX-enabled post creation form |
| `app/models/post.py` | Create | Post model: id, user_id, media_file_id, caption, status, created_at |
| `app/models/__init__.py` | Modify | Export Post model |
| `app/templates/base.html` | Modify | Add Tailwind CDN + dashboard link |
| `app/main.py` | Modify | Register dashboard router |

## Interfaces / Contracts

### Post Model
```python
class Post(Base):
    __tablename__ = "posts"
    
    id: int  # PK
    user_id: int  # FK → users.id
    media_file_id: int  # FK → media_files.id
    caption: str | None
    status: str  # PENDING | PROCESSING | PUBLISHED | FAILED
    created_at: datetime
    updated_at: datetime | None
```

### Dashboard Routes
```python
@router.get("/dashboard")
async def dashboard_index(request: Request, user: User = Depends(get_current_user))

@router.get("/dashboard/accounts")
async def dashboard_accounts(request: Request, user: User = Depends(get_current_user))

@router.get("/dashboard/posts/feed")
async def posts_feed(request: Request, user: User = Depends(get_current_user))
# Returns HTML fragment if HX-Request header present

@router.post("/dashboard/post")
async def create_post(
    request: Request,
    caption: str = Form(""),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user)
)
```

### HTMX Patterns
- **Polling**: `<div hx-get="/dashboard/posts/feed" hx-trigger="every 10s" hx-swap="innerHTML">`
- **Form upload**: `hx-post="/dashboard/post" hx-encoding="multipart/form-data"`
- **Fragment swap**: Routes check `request.headers.get("HX-Request")` to return partial HTML

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | Post model creation | Pytest with async SQLAlchemy session |
| Unit | Dashboard service functions | Mock DB, test business logic |
| Integration | Route protection | TestClient with/without JWT |
| Integration | HTMX fragments | Assert HX-Request handling |
| Manual | Mobile responsive | Browser DevTools device emulation |

## Migration / Rollback

**Migration**: Alembic migration for Post table (nullable fields for forward compatibility).

**Rollback Plan**:
1. Remove `app/dashboard/` directory
2. Remove Post model and migration
3. Revert `base.html` changes
4. Remove dashboard router from `main.py`

## Open Questions

- None – design ready for implementation.

## Size Budget

Target: <800 words (excluding tables/code). Actual: ~650 words.
