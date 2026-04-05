# Design: Motor de Tareas Asíncronas (Celery + Redis)

## Technical Approach

Añadir Redis como message broker y Celery worker contenedor compartiendo el código FastAPI. El worker se conecta a PostgreSQL y MinIO vía la misma configuración. Para tareas async, usar `asgiref.sync_to_async` como bridge entre Celery sync y SQLAlchemy async.

## Architecture Decisions

### Decision: Redis as Message Broker

| Option | Tradeoff | Decision |
|--------|----------|------|
| Redis | Simple, fast, widely supported | ✅ Chosen |
| RabbitMQ | More features, heavier | Rejected - overkill for current needs |
| SQS | Cloud-native, AWS lock-in | Rejected - want self-hosted |

**Rationale**: Redis is lightweight, already used for caching in many setups, and sufficient for task queue. Alpine image keeps container small.

### Decision: Shared Codebase for Worker

| Option | Tradeoff | Decision |
|--------|----------|------|
| Same Dockerfile | Simple, consistent dependencies | ✅ Chosen |
| Separate image | Smaller worker image | Rejected - complexity outweighs benefit |

**Rationale**: Worker needs same models, services, and config as FastAPI. Sharing Dockerfile ensures consistency.

### Decision: asgiref for Async Bridge

| Option | Tradeoff | Decision |
|--------|----------|------|
| `asgiref.sync_to_async` | Standard, well-tested | ✅ Chosen |
| Sync SQLAlchemy session | Simpler but loses async benefits | Rejected |
| Celery 5.3+ native async | Beta, requires newer Celery | Rejected - stability priority |

**Rationale**: Worker functions are sync by default. `sync_to_async` allows reusing existing async services (storage, database) inside tasks without rewriting.

### Decision: No Result Backend (Initial)

| Option | Tradeoff | Decision |
|--------|----------|------|
| None | Tasks fire-and-forget | ✅ Chosen for MVP |
| Redis | Track task status | Deferred - add when needed |

**Rationale**: `debug_task` doesn't need status tracking. Add result backend when implementing real async jobs.

## Data Flow

```
FastAPI Endpoint
       │
       │ debug_task.delay(name)
       ▼
    Redis Queue  ◄───────┐
       │                 │
       │                 │
       ▼                 │
 Celery Worker           │
       │                 │
       │ sync_to_async   │
       ▼                 │
 async SQLAlchemy ───────┘
```

**Flow**:
1. FastAPI endpoint calls `task.delay()` → returns immediately
2. Task serialized to Redis queue
3. Worker picks up task from queue
4. Worker executes task (sync context)
5. For async operations: `sync_to_async(async_func)()`

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `docker-compose.yml` | Modify | Add `redis` and `worker` services |
| `app/worker.py` | Create | Celery app instance and `debug_task` |
| `app/core/config.py` | Modify | Add `CELERY_BROKER_URL` setting |
| `pyproject.toml` | Modify | Add `celery` and `redis` dependencies |
| `.env.example` | Modify | Document `CELERY_BROKER_URL` |

## Interfaces / Contracts

### app/worker.py

```python
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery_app.task
def debug_task(name: str) -> str:
    """Validates Celery integration."""
    return f"Hello, {name}!"
```

### app/core/config.py additions

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
```

### docker-compose.yml additions

```yaml
services:
  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - app-network

  worker:
    build: .
    command: celery -A app.worker.celery_app worker --loglevel=info
    environment:
      DATABASE_URL: ${DATABASE_URL}
      CELERY_BROKER_URL: ${CELERY_BROKER_URL:-redis://redis:6379/0}
      # ... same as web service ...
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
    networks:
      - app-network
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `debug_task` returns greeting | Import and call directly |
| Integration | Worker connects to Redis | `docker compose logs worker` |
| Integration | Worker accesses DB | Task that queries User table |
| E2E | FastAPI dispatches task | Endpoint triggers task, check logs |

**Test commands**:
```bash
# Unit test
docker compose exec web uv run python -c "from app.worker import debug_task; print(debug_task('test'))"

# Integration - check Redis connection
docker compose exec redis redis-cli ping

# E2E - dispatch from FastAPI
curl -X POST http://localhost:8000/api/v1/debug/task -d '{"name":"test"}'
```

## Migration / Rollout

No migration required. New infrastructure only.

## Open Questions

- [ ] ¿Necesitamos Celery Beat para tareas programadas? → Deferred to future spec
- [ ] ¿Rate limiting con Redis? → Deferred to future spec
- [ ] ¿Flower para monitoreo? → Deferred to future spec
