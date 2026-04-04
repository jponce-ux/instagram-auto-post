# Tasks: Motor de Tareas Asíncronas (Celery + Redis)

## Phase 0: Git Branch

- [ ] 0.1 `git checkout master`
- [ ] 0.2 `git pull origin master` (si hay remote)
- [ ] 0.3 `git checkout -b feat/011-celery-redis`

## Phase 1: Dependencies & Config

- [ ] 1.1 Ejecutar `uv add celery redis` para añadir dependencias
- [ ] 1.2 Añadir `CELERY_BROKER_URL: str = "redis://redis:6379/0"` a `app/core/config.py` Settings
- [ ] 1.3 Añadir `CELERY_BROKER_URL=${CELERY_BROKER_URL:-redis://redis:6379/0}` a `.env.example`

## Phase 2: Docker Infrastructure

- [ ] 2.1 Añadir servicio `redis` a `docker-compose.yml` con imagen `redis:7-alpine`
- [ ] 2.2 Añadir healthcheck a `redis`: `["CMD", "redis-cli", "ping"]`
- [ ] 2.3 Añadir `redis` a `app-network`
- [ ] 2.4 Crear servicio `worker` en `docker-compose.yml` usando el mismo Dockerfile
- [ ] 2.5 Configurar comando del worker: `celery -A app.worker.celery_app worker --loglevel=info`
- [ ] 2.6 Añadir variables de entorno al worker: `DATABASE_URL`, `CELERY_BROKER_URL`, `SECRET_KEY`, config de MinIO
- [ ] 2.7 Configurar `depends_on` del worker: `db`, `redis`, `minio` con `condition: service_healthy`
- [ ] 2.8 Añadir `worker` a `app-network`

## Phase 3: Celery Configuration

- [ ] 3.1 Crear `app/worker.py` con instancia de Celery
- [ ] 3.2 Configurar broker URL desde `settings.CELERY_BROKER_URL`
- [ ] 3.3 Configurar serialization: `task_serializer="json"`, `accept_content=["json"]`, `result_serializer="json"`
- [ ] 3.4 Configurar timezone: `timezone="UTC"`, `enable_utc=True`
- [ ] 3.5 Implementar `debug_task(name: str) -> str` con decorador `@celery_app.task`

## Phase 4: Integration

- [ ] 4.1 Añadir endpoint `POST /api/v1/debug/task` en `app/main.py` para disparar `debug_task`
- [ ] 4.2 Importar `debug_task` desde `app.worker` en `app/main.py`
- [ ] 4.3 Endpoint retorna `{"task_id": task.id, "status": "queued"}` inmediatamente

## Phase 5: Verification

- [ ] 5.1 Ejecutar `docker compose up --build` y verificar que redis y worker inician sin errores
- [ ] 5.2 Verificar healthcheck de Redis: `docker compose exec redis redis-cli ping` → PONG
- [ ] 5.3 Verificar logs del worker: `docker compose logs worker` muestra "celery@... ready"
- [ ] 5.4 Test unit: `docker compose exec web uv run python -c "from app.worker import debug_task; print(debug_task('test'))"`
- [ ] 5.5 Test dispatch: `curl -X POST http://localhost:8000/api/v1/debug/task -d '{"name":"test"}'`
- [ ] 5.6 Verificar que el task se ejecuta en logs del worker

## Phase 6: Git Commit

- [ ] 6.1 `git add .`
- [ ] 6.2 `git commit -m "feat(011): add Celery + Redis async task engine"`
- [ ] 6.3 `git push origin feat/011-celery-redis` (opcional)