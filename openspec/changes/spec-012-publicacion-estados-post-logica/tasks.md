# Tasks: Lógica de Publicación y Estados de Post

## Phase 0: Git Branch

- [ ] 0.1 `git checkout master`
- [ ] 0.2 `git pull origin master` (si hay remote)
- [ ] 0.3 `git checkout -b feat/012-instagram-publish-logic`

## Phase 1: Model & Migration (Foundation)

- [ ] 1.1 Crear `app/models/post.py` con `PostStatus` enum (PENDING, PROCESSING, PUBLISHED, FAILED)
- [ ] 1.2 Crear clase `Post` con campos: id, user_id, ig_account_id, media_file_id, caption, status, ig_container_id, ig_media_id, error_message, created_at, updated_at, published_at
- [ ] 1.3 Añadir relationships en `Post`: `user`, `instagram_account`, `media_file`
- [ ] 1.4 Exportar `Post` y `PostStatus` en `app/models/__init__.py`
- [ ] 1.5 Crear migración: `uv run alembic revision --autogenerate -m "add_posts_table"`
- [ ] 1.6 Aplicar migración: `uv run alembic upgrade head` (en Docker: `docker compose exec web uv run alembic upgrade head`)

## Phase 2: InstagramService Extensions

- [ ] 2.1 Añadir `create_media_container(ig_account_id, access_token, media_url, caption)` en `app/services/instagram.py`
- [ ] 2.2 Añadir `get_container_status(container_id, access_token)` en `app/services/instagram.py`
- [ ] 2.3 Añadir `publish_media_container(ig_account_id, access_token, container_id)` en `app/services/instagram.py`
- [ ] 2.4 Añadir manejo de errores HTTP en cada método (raise con mensaje claro)

## Phase 3: Celery Task Integration

- [ ] 3.1 Importar modelos necesarios en `app/worker.py`: `Post`, `PostStatus`, `InstagramAccount`, `MediaFile`
- [ ] 3.2 Importar servicios en `app/worker.py`: `storage_service`, Instagram methods
- [ ] 3.3 Importar `AsyncSessionLocal` en `app/worker.py` para DB access
- [ ] 3.4 Crear función `_process_post_async(post_id: int)` con lógica async completa
- [ ] 3.5 Implementar step 1: Fetch Post + InstagramAccount + MediaFile from DB
- [ ] 3.6 Implementar step 2: Update Post status → PROCESSING
- [ ] 3.7 Implementar step 3: Generate fresh presigned URL via `storage_service.get_presigned_url()`
- [ ] 3.8 Implementar step 4: Call `create_media_container()` → store `ig_container_id`
- [ ] 3.9 Implementar step 5: Poll `get_container_status()` con timeout 30s, intervalo 2s
- [ ] 3.10 Implementar step 6: Call `publish_media_container()` → store `ig_media_id`
- [ ] 3.11 Implementar step 7: Update Post status → PUBLISHED, set `published_at`
- [ ] 3.12 Implementar error handling: Update Post status → FAILED, store `error_message`
- [ ] 3.13 Crear wrapper `@celery_app.task process_instagram_post(post_id)` que llama `asyncio.run(_process_post_async(post_id))`

## Phase 4: Verification

- [ ] 4.1 Verificar migración: `docker compose exec web uv run python -c "from app.models.post import Post; print(Post.__table__)"`

## Phase 5: Git Commit

- [ ] 5.1 `git add .`
- [ ] 5.2 `git commit -m "feat(012): add Instagram publishing logic with Post model and Celery task"`
- [ ] 5.3 `git push origin feat/012-instagram-publish-logic` (opcional)
