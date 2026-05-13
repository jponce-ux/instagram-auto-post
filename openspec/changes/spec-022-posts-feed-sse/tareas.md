# Tareas: Feed de Publicaciones en Tiempo Real con SSE

**Estado**: Completado  
**Progreso**: 6/6 tareas

---

## Fase 1: Infraestructura SSE

### T001 — Crear servicio SSEManager [S] ✅
**Archivo**: `app/services/sse.py`  
**Entregable**: Clase `SSEManager` con métodos `publish()` y `subscribe()`

- Crear `SSEManager` que use Redis pub/sub
- `publish(channel: str, data: dict)` → publica evento en Redis
- `subscribe(channel: str)` → async generator que yield eventos de Redis
- `format_sse_event(event_type: str, data: dict)` → formatea string SSE (`event: ...\ndata: ...\n\n`)

**Verificación**: `SSEManager.format_sse_event("post_update", {"id": 1})` retorna string SSE válido

### T002 — Crear endpoint SSE `/dashboard/posts/stream` [M] ✅
**Archivo**: `app/dashboard/routes.py`  
**Entregable**: Endpoint GET que retorna `StreamingResponse` con SSE

- Agregar ruta `@router.get("/posts/stream")`
- Autenticar usuario vía `get_current_user_optional`
- Suscribirse a canal Redis `post_update`
- Filtrar eventos por `user_id` (solo enviar eventos del usuario conectado)
- Enviar heartbeat cada 15 segundos (`:heartbeat\n\n`)
- Retornar `StreamingResponse` con `media_type="text/event-stream"`
- Manejar desconexión del cliente (cancelar suscripción)

**Verificación**: `curl -N http://localhost:8000/dashboard/posts/stream` mantiene conexión abierta y recibe heartbeats

---

## Fase 2: Publicación de Eventos desde Worker

### T003 — Publicar eventos de cambio de estado en el worker [M] ✅
**Archivo**: `app/worker.py`  
**Entregable**: El worker publica en Redis `post_update` cuando cambia el estado de un post

- En `check_scheduled_posts`: publicar evento cuando dispatcha un post (status → PROCESSING)
- En `_process_post_async`: publicar evento cuando status → PUBLISHED
- En `_process_post_async`: publicar evento cuando status → FAILED
- Incluir en el evento: `post_id`, `status`, `user_id`
- Usar Redis pub/sub (no bloqueante, fire-and-forget)

**Verificación**: Al crear un post programado, Redis channel `post_update` recibe el evento

---

## Fase 3: Integración Frontend

### T004 — Actualizar template del dashboard con HTMX SSE [M] ✅
**Archivo**: `app/templates/dashboard/layout.html`  
**Entregable**: El historial de publicaciones se actualiza vía SSE en vez de polling

- Agregar `hx-ext="sse"` al contenedor `#history-wrapper`
- Agregar atributo `sse-connect="/dashboard/posts/stream"` al contenedor
- Agregar `sse-swap="post_update"` al contenedor `#history-section`
- Eliminar `setInterval(loadPosts, 10000)` del JavaScript
- Mantener `loadPosts()` como carga inicial única en `DOMContentLoaded`
- Agregar indicador visual de conexión (punto verde/rojo)

**Verificación**: Al cargar el dashboard, se establece conexión SSE y no hay polling

### T005 — Manejar reconexión y estado de conexión [S] ✅
**Archivo**: `app/templates/dashboard/layout.html`  
**Entregable**: Reconexión automática y feedback visual al usuario

- HTMX maneja reconexión automáticamente con `hx-ext="sse"`
- Agregar indicador visual: punto verde (conectado) / rojo (desconectado)
- Al reconectar, llamar `loadPosts()` para refrescar datos completos
- Manejar evento `htmx:sseError` para mostrar mensaje de reconexión

**Verificación**: Al detener/iniciar el servidor, el indicador cambia y se reconecta automáticamente

---

## Fase 4: Limpieza y Verificación

### T006 — Eliminar código de polling y verificar funcionamiento [S] ✅
**Archivos**: `app/templates/dashboard/layout.html`, `app/dashboard/routes.py`  
**Entregable**: Código limpio sin polling, endpoint `/posts/feed` conservado como fallback

- Eliminar `setInterval` del JavaScript
- Mantener endpoint `/posts/feed` (se usa para carga inicial)
- Actualizar docstring del endpoint: "returns JSON for initial load and fallback"
- Ejecutar tests existentes para verificar que no hay regresiones
- Verificar E2E: crear post → ver cambio de estado en tiempo real

**Verificación**: 90 tests passing, dashboard muestra posts en tiempo real sin polling
