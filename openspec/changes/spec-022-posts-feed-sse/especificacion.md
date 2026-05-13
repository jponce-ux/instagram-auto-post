# Especificación: Feed de Publicaciones en Tiempo Real con SSE

**Estado**: Completado

## Problema

El dashboard consulta `/dashboard/posts/feed` cada 10 segundos mediante `setInterval` para actualizar el historial de publicaciones. Esto genera:
- Requests innecesarios cuando no hay cambios (90%+ de las consultas devuelven datos idénticos)
- Latencia de hasta 10 segundos entre un cambio de estado y su visualización
- Carga innecesaria en la base de datos y el servidor
- Experiencia de usuario subóptima: el usuario no ve los cambios de estado en tiempo real

## Historias de Usuario

### HU-1: Actualización en tiempo real del historial de publicaciones
**Como** usuario del dashboard  
**Quiero** ver los cambios de estado de mis publicaciones instantáneamente  
**Para** no tener que esperar el próximo ciclo de polling ni recargar la página

#### Criterios de Aceptación

**CA-1.1: Conexión SSE al cargar el dashboard**
- **Dado** que el usuario abre el dashboard
- **Cuando** la página termina de cargar
- **Entonces** se establece una conexión SSE con `/dashboard/posts/stream` que permanece activa

**CA-1.2: Actualización automática al cambiar estado**
- **Dado** que una publicación cambia de estado (PENDING → PROCESSING → PUBLISHED/FAILED)
- **Cuando** el worker de Celery completa la transición de estado
- **Entonces** el historial de publicaciones en el dashboard se actualiza automáticamente en menos de 1 segundo

**CA-1.3: Reconexión automática**
- **Dado** que la conexión SSE se pierde (timeout de red, reinicio del servidor)
- **Cuando** la conexión se restablece
- **Entonces** el cliente se reconecta automáticamente y refresca los datos actuales

**CA-1.4: Eliminación del polling**
- **Dado** que SSE está activo
- **Cuando** el dashboard carga
- **Entonces** NO se ejecuta `setInterval` para `/dashboard/posts/feed`

### HU-2: Publicación de eventos desde el worker
**Como** sistema de procesamiento de publicaciones  
**Quiero** notificar al dashboard cuando una publicación cambia de estado  
**Para** que el usuario vea el progreso en tiempo real

#### Criterios de Aceptación

**CA-2.1: Evento al iniciar procesamiento**
- **Dado** que `check_scheduled_posts` dispatcha una publicación
- **Cuando** el estado cambia a PROCESSING
- **Entonces** se publica un evento SSE con el post_id y nuevo estado

**CA-2.2: Evento al publicar exitosamente**
- **Dado** que `_process_post_async` completa exitosamente
- **Cuando** el estado cambia a PUBLISHED
- **Entonces** se publica un evento SSE con el post_id y nuevo estado

**CA-2.3: Evento al fallar**
- **Dado** que `_process_post_async` falla
- **Cuando** el estado cambia a FAILED
- **Entonces** se publica un evento SSE con el post_id, nuevo estado y mensaje de error

## No-Objetivos

- Notificaciones push al navegador (solo actualización del componente de historial)
- SSE para otras secciones del dashboard (cuentas conectadas, formulario de post)
- Persistencia de eventos SSE (si el cliente se desconecta, pierde los eventos intermedios)
- Autenticación por canal SSE separado (usa la misma sesión del dashboard)

## Métricas de Éxito

- Latencia de actualización < 1 segundo desde cambio de estado hasta renderizado
- Cero requests de polling a `/dashboard/posts/feed` después de la carga inicial
- Reconexión automática en menos de 3 segundos tras pérdida de conexión
- Carga de CPU del servidor reducida (sin polling cada 10s por usuario conectado)

## Preguntas Abiertas

1. ¿Se debe mantener el endpoint `/dashboard/posts/feed` como fallback o eliminarlo?
2. ¿Se debe mostrar una notificación toast cuando una publicación se publica/falla, o solo actualizar la tabla?
