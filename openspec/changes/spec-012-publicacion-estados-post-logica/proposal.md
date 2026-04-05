# Proposal: Lógica de Publicación y Estados de Post

## Intent

El usuario puede subir imágenes pero no tiene forma de publicarlas en Instagram. Necesitamos un modelo `Post` con estados y una tarea de Celery que ejecute el flujo completo de Meta Graph API (crear container, verificar status, publicar).

## Scope

### In Scope
- Modelo `Post` con estados: PENDING, PROCESSING, PUBLISHED, FAILED
- Métodos en `InstagramService`: `create_media_container`, `publish_media_container`
- Tarea Celery `process_instagram_post(post_id)` con flujo completo de Meta
- Manejo de errores: token expirado, rate limits, errores de Meta
- Migración Alembic para tabla `posts`

### Out of Scope
- Scheduling de publicaciones (Celery Beat) — future work
- Story publishing — future work
- Reels publishing — future work

## Capabilities

### New Capabilities
- `instagram-publishing`: Flujo completo de publicación de contenido en Instagram

### Modified Capabilities
- `async-tasks`: Se añade `process_instagram_post` task para procesar publicaciones

## Approach

1. **Model**: Crear `app/models/post.py` con `Post` model y estados enum
2. **Service**: Extender `app/services/instagram.py` con métodos de publishing
3. **Celery Task**: Añadir `process_instagram_post` en `app/worker.py` con flujo Meta
4. **Migration**: Alembic para crear tabla `posts`
5. **Integration**: StorageService para generar presigned URLs

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/models/post.py` | New | Modelo Post con estados |
| `app/models/__init__.py` | Modified | Exportar Post |
| `app/services/instagram.py` | Modified | Añadir create/publish methods |
| `app/worker.py` | Modified | Añadir process_instagram_post task |
| `migrations/versions/` | New | Migración add_posts_table |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Token expired during publish | Medium | Check token_expiry before processing, mark FAILED |
| Meta API rate limit | Low | Implement retry with exponential backoff |
| Presigned URL expired | Low | Generate fresh URL before publish |

## Rollback Plan

1. `alembic downgrade -1` para eliminar tabla posts
2. Revertir cambios en `app/services/instagram.py`
3. Eliminar `app/models/post.py`
4. `uv remove` dependencias si se añadieron

## Dependencies

- **SPEC-007 (Meta OAuth)**: ✅ InstagramAccount con access_token
- **SPEC-008 (MinIO)**: ✅ StorageService y MediaFile
- **SPEC-011 (Celery)**: ⏳ Celery worker funcionando

## Success Criteria

- [ ] Tabla `posts` creada con estados PENDING, PROCESSING, PUBLISHED, FAILED
- [ ] `process_instagram_post(post_id)` ejecuta flujo completo de Meta
- [ ] Post con token expirado se marca como FAILED con mensaje claro
- [ ] Post publicado actualiza estado a PUBLISHED con `ig_container_id`
