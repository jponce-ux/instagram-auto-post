# Plan Técnico: Feed de Publicaciones en Tiempo Real con SSE

## Stack Tecnológico

- **Backend**: FastAPI (Python 3.11+) con `StreamingResponse` nativo para SSE
- **Message Broker**: Redis pub/sub (ya disponible como `CELERY_BROKER_URL`)
- **Frontend**: HTMX con extensión SSE (`hx-ext="sse"`) + JavaScript vanilla
- **Worker**: Celery (ya usa Redis como broker)

## Arquitectura

```
┌─────────────┐     status change      ┌──────────────┐
│  Celery     │ ──────────────────────► │  Redis       │
│  Worker     │   PUBLISH post_update   │  pub/sub     │
└─────────────┘                         │  channel:    │
                                        │  post_update │
┌─────────────┐     SSE events           └──────┬───────┘
│  Browser    │ ◄───────────────────────────────┘
│  (HTMX)     │   event: post_update
│             │   data: {post_id, status, ...}
└─────────────┘
```

### Flujo de Datos

1. **Worker** cambia estado de post en DB → publica en Redis channel `post_update`
2. **FastAPI SSE endpoint** mantiene conexiones abiertas, suscritas a `post_update`
3. **Cuando llega un evento** de Redis, el endpoint lo formatea como SSE event y lo envía al cliente
4. **HTMX** recibe el evento y dispara un swap que refresca el componente de historial

## Cambios en el Código

### 1. Nuevo servicio: `app/services/sse.py`
- Clase `SSEManager` que gestiona conexiones activas
- Método `publish()` para enviar eventos desde el worker
- Método `subscribe()` async generator para el endpoint SSE

### 2. Nuevo endpoint: `app/dashboard/routes.py` → `/posts/stream`
- Endpoint GET que retorna `StreamingResponse` con `text/event-stream`
- Autenticación vía cookie (misma que el dashboard)
- Suscribe al canal Redis `post_update`
- Envía heartbeat cada 15 segundos para mantener la conexión viva

### 3. Modificación del worker: `app/worker.py`
- Después de cada cambio de estado de post, publicar en Redis:
  ```python
  redis_client.publish("post_update", json.dumps({
      "post_id": post_id,
      "status": new_status,
      "user_id": user_id,
  }))
  ```

### 4. Modificación del template: `app/templates/dashboard/layout.html`
- Agregar `hx-ext="sse"` al contenedor del historial
- Reemplazar `setInterval(loadPosts, 10000)` con escucha SSE
- Mantener `loadPosts()` como carga inicial única

### 5. Mantener endpoint `/posts/feed`
- Se conserva para la carga inicial y como fallback
- Se elimina el polling (`setInterval`)

## Dependencias

| Paquete | Proposito | Estado |
|---------|-----------|--------|
| `redis` | Pub/sub para eventos SSE | Ya instalado (Celery broker) |
| `htmx-sse` | Extensión HTMX para SSE | CDN ya disponible (htmx.org) |

No se requieren nuevas dependencias.

## Estrategia de Testing

- **Unit tests**: Mock de Redis pub/sub en `SSEManager`
- **Integration tests**: Verificar que el worker publica eventos al cambiar estado
- **Manual testing**: Conectar dashboard, crear post, verificar actualización en tiempo real

## Riesgos

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Conexiones SSE consumen memoria del servidor | Medio | Timeout de 5 min, reconexión automática |
| Redis pub/sub pierde eventos si no hay suscriptores | Bajo | El cliente refresca datos completos al reconectar |
| Múltiples tabs del mismo usuario | Bajo | Cada tab tiene su propia conexión SSE, sin conflicto |
| Worker sin acceso a Redis pub/sub | Bajo | Usa la misma conexión de Redis que Celery |

## Rollout Plan

1. Implementar SSE endpoint y servicio
2. Agregar publicación de eventos al worker
3. Actualizar template del dashboard con HTMX SSE
4. Eliminar polling JavaScript
5. Verificar en Docker compose completo
