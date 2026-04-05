# Proposal: Motor de Tareas Asíncronas (Celery + Redis)

## Intent

FastAPI bloquea el hilo principal durante operaciones pesadas como publicación de medios en Meta API. Necesitamos un sistema de colas para ejecutar estas tareas en background, liberando el request-response cycle y mejorando la experiencia del usuario.

## Scope

### In Scope
- Contenedor Redis 7 Alpine como message broker
- Contenedor Celery Worker compartiendo código con FastAPI
- Configuración de Celery compatible con código async (asgiref)
- Tarea de prueba `debug_task` para validar integración
- Dependencias: `celery` y `redis` vía UV

### Out of Scope
- Monitoreo de tareas (Celery Beat, Flower) —future work
- Rate limiting de tareas —future work
- Retry policies avanzadas —future work

## Capabilities

### New Capabilities
- `async-tasks`: Sistema de colas para operaciones en background

### Modified Capabilities
- None (infraestructura nueva, no modifica comportamiento existente)

## Approach

1. **Docker**: Añadir `redis` y `worker` services a docker-compose.yml
2. **Dependencies**: `uv add celery redis`
3. **Celery Config**: Crear `app/worker.py` con Celery app, broker URL desde env
4. **Async Bridge**: Usar `asgiref.sync_to_async` o loop de asyncio para integrar con SQLAlchemy async
5. **Test Task**: `debug_task(name)` que retorna saludo y se registra en logs

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `docker-compose.yml` | Modified | Añadir servicios redis y worker |
| `app/worker.py` | New | Configuración de Celery app |
| `pyproject.toml` | Modified | Dependencias celery y redis |
| `.env.example` | Modified | Variable CELERY_BROKER_URL |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| CeleryWorker no puede usar async SQLAlchemy | Medium | Usar `asgiref` o sync session factory |
| Redis connection refused | Low | Healthcheck y depends_on en docker-compose |
| Memory leak en worker | Low | Configurar CELERY_WORKER_MAX_TASKS_PER_CHILD |

## Rollback Plan

1. Detener contenedores: `docker compose down`
2. Eliminar servicios redis y worker de docker-compose.yml
3. Revertir dependencias: `uv remove celery redis`
4. Eliminar `app/worker.py`

## Dependencies

- SPEC-003 (Docker Setup) —✅ Completado
- SPEC-008 (Storage MinIO) — ✅ Completado (worker necesita acceso a MinIO)

## Success Criteria

- [ ] `docker compose up` levanta redis y worker sin errores
- [ ] `debug_task("test")` ejecuta y registra en logs del worker
- [ ] Worker puede acceder a PostgreSQL y MinIO (conexiones funcionan)
- [ ] FastAPI puede enviar tareas a la cola via `debug_task.delay()`