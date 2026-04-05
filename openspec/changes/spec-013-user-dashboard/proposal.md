# Proposal: spec-013-user-dashboard

## Intent

Crear la interfaz visual del dashboard de usuario para gestionar cuentas vinculadas de Instagram y realizar publicaciones. El dashboard es el punto central donde el usuario autenticado interactúa con la aplicación.

## Scope

### In Scope
- Dashboard protegido con autenticación JWT (reutilizando `get_current_user`)
- Plantilla base `layout.html` con Tailwind CSS CDN (mobile-first responsive)
- Sección "Cuentas": lista de InstagramAccounts vinculadas + botón OAuth
- Sección "Nuevo Post": formulario con upload de imagen (HTMX) + caption (async)
- Sección "Historial": lista de posts con estados (HTMX polling cada 10s)
- Rutas protegidas: GET /dashboard, GET /dashboard/accounts, POST /dashboard/post
- Formulario `post_form.html` con progressive file upload

### Out of Scope
- Integración con posting real (depende de SPEC-012)
- Scheduling de publicaciones (SPEC-011 futuro)
- Stories o Reels publishing
- Gestión de comentarios

## Capabilities

### New Capabilities
- `user-dashboard`: Interfaz HTML/Jinja2 protegida para gestión de cuentas y posts

### Modified Capabilities
- Ninguno (no cambia specs existentes)

## Approach

1. **Tailwind**: Añadir CDN en `base.html` (no build step para simplicidad)
2. **Dashboard Router**: Crear `app/dashboard/routes.py` con rutas protegidas
3. **Templates**: Crear `app/templates/dashboard/layout.html`, `index.html`, `post_form.html`
4. **HTMX Polling**: Implementar endpoint `GET /dashboard/posts/feed` para historial
5. **File Upload**: Reutilizar `/api/v1/debug/upload` con HTMX swap

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/templates/base.html` | Modified | Añadir Tailwind CDN |
| `app/templates/dashboard/` | New | layout.html, index.html, post_form.html, accounts.html |
| `app/dashboard/` | New | routes.py, templates.py |
| `app/main.py` | Modified | Registrar dashboard router |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| SPEC-012 no completado | High | UI funciona sin posting; botón muestra estado disabled |
| Tailwind CDN en producción | Low | Usar versión pinned con integrity hash |
| HTMX polling excesivo | Low | Throttle en cliente, 10s mínimo |

## Rollback Plan

1. Eliminar `app/dashboard/` y `app/templates/dashboard/`
2. Revertir `base.html` a versión anterior
3. Eliminar dashboard router de `main.py`
4. No hay migración de DB (solo UI)

## Dependencies

- **SPEC-004 (HTMX)**: ✅ Script HTMX ya en base.html
- **SPEC-006 (Auth)**: ✅ `get_current_user` y JWT working
- **SPEC-008 (MinIO)**: ✅ `storage_service` para upload
- **SPEC-012 (Instagram Publishing)**: ⏳ Post model no existe aún — UI sin posting funcional

## Success Criteria

- [ ] GET /dashboard returns 401 si no hay JWT
- [ ] Dashboard muestra cuentas vinculadas del usuario
- [ ] Formulario de post permite seleccionar imagen y caption
- [ ] Historial muestra posts con estados (PENDING/PROCESSING/etc)
- [ ] HTMX polling actualiza historial cada 10s
- [ ] Mobile responsive con Tailwind CSS
