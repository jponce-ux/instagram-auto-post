---
ticket: TASK-024
phase: plan
model: qwen3.6-plus
generated: 2026-05-13
status: completed
---

# Plan Tecnico: Refactor UX/UI Dashboard

## Arquitectura Actual

- **Backend**: FastAPI con SQLAlchemy async, MinIO (S3-compatible) para almacenamiento
- **Frontend**: Jinja2 templates + JavaScript vanilla + SSE para actualizaciones en tiempo real
- **Worker**: Celery con Redis para procesamiento de posts

## Cambios Requeridos

### 1. Miniaturas con Presigned URLs (Backend + Frontend)

**Problema**: El endpoint `GET /dashboard/posts/feed` retorna posts sin URL de imagen. El frontend renderiza un placeholder SVG.

**Solucion**:
- Agregar metodo `get_presigned_url_for_post(post_id, user_id)` en `app/dashboard/service.py` que:
  1. Obtiene el `MediaFile` asociado al post
  2. Verifica que el usuario es dueno del archivo
  3. Genera una presigned URL con expiracion de 1 hora via `storage_service.get_presigned_url()`
- Modificar `posts_feed` en `app/dashboard/routes.py` para incluir `image_url` en la respuesta JSON
- Actualizar `renderPosts()` en `app/templates/dashboard/layout.html` para mostrar `<img>` con la presigned URL

**Seguridad**: Las presigned URLs expiran en 1 hora. No se expone el bucket privado publicamente.

### 2. Reset de Formulario Post-Submit (Frontend)

**Problema**: El boton queda en "Publicando..." despues del envio exitoso.

**Solucion**:
- El codigo actual ya llama `clearPostForm()` en el bloque `if response.ok && data.success`, pero el boton no se re-habilita explicitamente antes del reset.
- Agregar `submitBtn.disabled = false; submitBtn.textContent = 'Publicar';` antes de `clearPostForm()` para asegurar que el boton se resetea incluso si `clearPostForm()` falla.
- Agregar toast de confirmacion "Tarea encolada" para feedback inmediato.

### 3. Padding en Inputs (Frontend - Templates)

**Problema**: Inputs y textareas usan clases de Tailwind sin padding interno explicito.

**Solucion**:
- Agregar `px-4 py-2.5` a todos los `<input>` y `<textarea>` en:
  - `app/templates/components/auth_form.html` (login)
  - `app/templates/components/register_form.html` (registro)
  - `app/templates/dashboard/post_form.html` (textarea de descripcion)

## Archivos a Modificar

| Archivo | Cambio |
|---------|--------|
| `app/dashboard/service.py` | Agregar funcion para obtener presigned URL de post |
| `app/dashboard/routes.py` | Incluir `image_url` en respuesta de `/posts/feed` |
| `app/templates/dashboard/layout.html` | Mostrar miniatura con `<img>` en `renderPosts()` |
| `app/templates/dashboard/post_form.html` | Reset explicito del boton + padding en textarea |
| `app/templates/components/auth_form.html` | Padding en inputs de login |
| `app/templates/components/register_form.html` | Padding en inputs de registro |

## Estrategia de Pruebas

- Verificar que `/dashboard/posts/feed` retorna `image_url` para posts con imagen
- Verificar que las presigned URLs son accesibles (HTTP 200)
- Verificar que el formulario se resetea despues de un envio exitoso
- Verificar visualmente el padding en todos los inputs

## Riesgos

| Riesgo | Mitigacion |
|--------|-----------|
| Presigned URL expira mientras el usuario ve el dashboard | Expiracion de 1 hora es suficiente; SSE refresca la pagina cuando hay cambios |
| Performance: generar presigned URL por cada post en cada request | Solo se genera cuando se carga el feed; cacheable a nivel de sesion |
