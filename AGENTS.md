# AGENTS.md — mi-app-instagram

## Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with asyncpg driver + SQLAlchemy 2.0 (async) + Alembic migrations
- **Storage**: MinIO (S3-compatible) for media files
- **Task Queue**: Celery + Redis (broker) + Celery Beat (scheduler)
- **Auth**: JWT (python-jose) with Argon2 password hashing
- **Package Manager**: UV (not pip)

## Key Commands

```bash
# Install dependencies (in container or with UV)
uv sync --frozen

# Run the API server
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run Celery worker
uv run celery -A app.worker.celery_app worker --loglevel=info

# Run Celery Beat (scheduler)
uv run celery -A app.worker.celery_app beat --loglevel=info

# Run tests
uv run pytest tests/ -v

# Run a single test file
uv run pytest tests/test_webhooks.py -v

# Apply migrations
uv run alembic upgrade head

# Docker Compose (full stack)
docker compose up --build
```

## Architecture

- **API entrypoint**: `app/main.py` — FastAPI app with `app` variable
- **Worker entrypoint**: `app/worker.py` — Celery app with `celery_app` variable
- **Database**: `app/core/database.py` — AsyncSession (FastAPI) and SyncSessionLocal (Celery Beat)
- **Webhooks**: `app/webhooks/meta.py` — public endpoint (no JWT), HMAC-SHA1 signature validation
- **Auth**: JWT via `app/auth/dependencies.py` — `get_current_user` dependency

## Database Patterns

- **Async for FastAPI**: `AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)`
- **Sync for Celery**: `SyncSessionLocal` uses `postgresql+psycopg2://` driver
- **Dependency injection**: `async def get_db()` yields `AsyncSession`
- **Never import `get_db` in Celery tasks** — use `AsyncSessionLocal()` directly with `asyncio.run()`

## Celery Gotchas

- Beat task `check_scheduled_posts` runs every 60 seconds
- Celery tasks use sync session, not async — wrap async operations with `asyncio.run()`
- On error, task retries 3x with exponential backoff (60s → 120s → 240s)
- DEBUG logging for worker: check `app/worker.py` log statements

## Webhook Security

- `POST /webhooks/instagram` uses HMAC-SHA1 via `X-Hub-Signature` header (not JWT)
- `GET /webhooks/instagram` handles Hub Challenge verification
- Verify token: `META_WEBHOOK_VERIFY_TOKEN` env var
- App secret: `META_APP_SECRET` env var
- Missing signature or invalid signature → 401; replay attacks → 403

## Environment Variables

Critical vars (see `.env.example`):
- `DATABASE_URL`: async format: `postgresql+asyncpg://...@db:5432/instagram_app`
- `CELERY_BROKER_URL`: `redis://redis:6379/0`
- `META_WEBHOOK_VERIFY_TOKEN`: random token for Meta webhook verification
- `META_APP_SECRET`: from Meta developer portal
- `MINIO_ENDPOINT`: `http://minio:9000` (internal Docker) or localhost for dev

## Testing

- Tests in `tests/` directory
- `pytest.ini_options` in `pyproject.toml`: `asyncio_mode = "auto"`
- Set env vars BEFORE importing app modules in tests:
  ```python
  os.environ["META_APP_SECRET"] = "test_secret"
  os.environ["META_WEBHOOK_VERIFY_TOKEN"] = "test_token"
  ```
- Use `TestClient` from `fastapi.testclient` for sync endpoint tests
- Use `AsyncMock` + `MagicMock` for async database session tests

## Migrations

- `alembic.ini` at project root
- Head at `migrations/versions/`
- Run: `uv run alembic upgrade head`
- Create: `uv run alembic revision --autogenerate -m "message"`

## Project Structure

```
app/
├── main.py              # FastAPI app entrypoint
├── worker.py            # Celery app + tasks
├── core/
│   ├── config.py       # Settings (pydantic-settings)
│   └── database.py     # AsyncSession + SyncSessionLocal
├── models/             # SQLAlchemy models
├── services/
│   ├── instagram.py     # Meta Graph API client
│   └── storage.py      # MinIO/S3 operations
├── auth/               # JWT auth routes + dependencies
├── dashboard/          # HTMX dashboard routes
└── webhooks/           # Meta webhook handlers (public)
tests/
├── test_webhooks.py    # Webhook tests (all passing)
├── test_dashboard.py
└── test_beat_scheduler.py
```

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
`.specify/specs/task-028-post-timeout-retry/plan.md`
<!-- SPECKIT END -->

## Spec-Driven Development (SDD) Workflow

This project uses **Spec-Driven Development** with hybrid artifact storage (files + Engram memory).

### SDD Lifecycle

```
proposal → spec → design → tasks → apply → verify → archive
```

### Artifact Storage

| Artifact | Location | Purpose |
|----------|----------|---------|
| Proposal | `openspec/changes/{spec-name}/proposal.md` | Problem statement, scope, capabilities |
| Spec | `openspec/changes/{spec-name}/specs/{domain}/spec.md` | Requirements with Given/When/Then scenarios |
| Design | `openspec/changes/{spec-name}/design.md` | Technical approach, architecture decisions |
| Tasks | `openspec/changes/{spec-name}/tasks.md` | Implementation checklist by phase |
| Progress | Engram `sdd/{spec-name}/apply-progress` | Cross-session implementation tracking |

### Git Workflow

```bash
# Start new spec
git checkout master
git checkout -b feat/{spec-number}-{name}

# After implementation
git add .
git commit -m "{type}({number}): {description}"
git push origin feat/{spec-number}-{name}
```

### Spec Numbering Convention

- Format: `spec-XXX-{kebab-case-name}`
- Examples: `spec-011-celery-redis`, `spec-012-publicacion-estados-post-logica`

### SDD Commands

```bash
# Fast-forward planning (all phases at once)
/sdd-ff spec-{number}-{name}

# Individual phases
/sdd-propose {spec-name}     # Create proposal
/sdd-spec {spec-name}         # Write specifications
/sdd-design {spec-name}       # Create technical design
/sdd-tasks {spec-name}        # Break down into tasks
/sdd-apply {spec-name}        # Implement tasks
/sdd-verify {spec-name}       # Verify implementation
/sdd-archive {spec-name}      # Archive completed spec
```

### Completed Specs (Archived)

| Spec | Name | Status |
|------|------|--------|
| SPEC-001 | scaffolding-init | ✅ Archived |
| SPEC-002 | base-dependencies | ✅ Archived |
| SPEC-003 | docker-setup | ✅ Archived |
| SPEC-004 | hello-world-htmx | ✅ Archived |
| SPEC-005 | db-async-setup | ✅ Archived |
| SPEC-006 | auth-argon2-jwt | ✅ Archived |
| SPEC-007 | meta-oauth-flow | ✅ Archived |
| SPEC-008 | storage-minio | ✅ Archived |
| SPEC-009 | cloudflare-tunnel | ✅ Archived |
| SPEC-010 | privacidad-minio | ✅ Archived |

### Pending Specs (Ready to Apply)

| Spec | Name | Dependencies |
|------|------|--------------|
| SPEC-011 | celery-redis | None |
| SPEC-012 | publicacion-estados-post-logica | SPEC-011 |
| SPEC-013 | user-dashboard | SPEC-011, SPEC-012 |
| SPEC-014 | celery-beat-scheduler | SPEC-011, SPEC-012 |
| SPEC-015 | meta-webhooks | SPEC-009, SPEC-012 |

### Implementation Order

```
SPEC-011 (Celery + Redis)
       ↓
SPEC-012 (Post Model + Publishing Logic)
       ↓
SPEC-013 (Dashboard UI) ─┬─→ SPEC-014 (Beat Scheduler)
                         └─→ SPEC-015 (Meta Webhooks)
```

### Key SDD Rules

1. **Never skip phases**: proposal → spec → design → tasks → apply → verify → archive
2. **One spec per branch**: Each spec gets its own `feat/XXX-{name}` branch
3. **Hybrid mode**: Files in `openspec/changes/`, cross-session memory in Engram
4. **Specs are contracts**: Implementation must match spec scenarios exactly
5. **Archive after verify**: Only archive specs that pass verification
