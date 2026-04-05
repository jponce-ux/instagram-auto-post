# Proposal: spec-015-meta-webhooks

## Intent

Recibir notificaciones en tiempo real desde los servidores de Meta cuando una publicación cambie de estado o cuando ocurra un error post-envío. Meta envía webhooks para confirmar éxito (PUBLISHED) o reportar errores (FAILED) después del proceso de publicación.

## Scope

### In Scope
- Endpoint público GET /webhooks/instagram para verificación Hub Challenge de Meta
- Endpoint público POST /webhooks/instagram para recibir payloads
- Validación X-Hub-Signature con HMAC-SHA1 usando META_APP_SECRET
- Actualización de Post status según webhook (PUBLISHED/FAILED)
- Almacenamiento de error_message cuando webhook reporta error
- Soporte para modo configuración de Meta (subscribe to fields)

### Out of Scope
- HTMX notificaciones visuales (futuro SPEC-016)
- Reintentos automáticos por webhooks fallidos
- Verificación manual de estado post en dashboard

## Capabilities

### New Capabilities
- `instagram-webhooks`: Recepción y procesamiento de webhooks de Meta para notificaciones de estado de publicación

### Modified Capabilities
- `instagram-publishing`: Se integra con webhooks para recibir actualizaciones de estado en tiempo real (en lugar de polling)

## Approach

1. **Router público**: Crear `app/webhooks/meta.py` con router FastAPI sin autenticación JWT
2. **Verificación Hub Challenge**: GET /webhooks/instagram?hub.mode&hub.challenge&hub.verify_token
3. **Validación firma**: Decorador/t función que valida X-Hub-Signature usando META_APP_SECRET
4. **Parser de payloads**: Extraer entry.changes[].value con status, media_id, error_message
5. **Actualización Post**: Buscar Post por ig_container_id o ig_media_id, actualizar estado
6. **Cloudflare Tunnel**: Existente en instagramjp.loquinto.com permite acceso público

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/webhooks/meta.py` | New | Router para endpoints webhook |
| `app/webhooks/signature.py` | New | Validación HMAC-SHA1 X-Hub-Signature |
| `app/models/post.py` | Modified | Añadir método update_from_webhook() |
| `app/main.py` | Modified | Include webhook router |
| `app/core/config.py` | Modified | META_WEBHOOK_VERIFY_TOKEN |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Replay attacks via reused signatures | Low | Verificar timestamp, no solo firma |
| Webhook antes de Celery guardar container_id | Low | Buscar por media_url o fallback a pending |
|APP_SECRET en producción expuesta | Low | Usar env var, no hardcode |

## Rollback Plan

1. Eliminar `app/webhooks/` directorio
2. Remover webhook router de `app/main.py`
3. Eliminar método `update_from_webhook` de Post model
4. Remover META_WEBHOOK_VERIFY_TOKEN de config

## Dependencies

- **SPEC-009 (Cloudflare Tunnel)**: ✅ Completado - instagramjp.loquinto.com expuesto
- **SPEC-012 (Post Logic)**: ⏳ Pendiente - Modelo Post con estados requerido

## Success Criteria

- [ ] GET /webhooks/instagram pasa verificación Hub Challenge de Meta
- [ ] POST /webhooks/instagram valida X-Hub-Signature correctamente
- [ ] Webhook con éxito actualiza Post status → PUBLISHED
- [ ] Webhook con error actualiza Post status → FAILED con error_message
- [ ] Endpoint público accesible via instagramjp.loquinto.com
