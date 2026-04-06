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
