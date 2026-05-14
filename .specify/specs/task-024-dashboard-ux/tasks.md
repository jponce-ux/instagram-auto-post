---
ticket: TASK-024
phase: tasks
model: qwen3.6-plus
generated: 2026-05-13
status: draft
---

# Tareas: Refactor UX/UI Dashboard

Estado: Completado
Progreso: 7/7 tareas

## Fase 1: Backend - Presigned URLs para Miniaturas

### T001 - Agregar helper para obtener presigned URL de un post [S]
**Archivo**: `app/dashboard/service.py`
**Entregable**: Funcion `get_post_image_url(db, user, post)` que retorna una presigned URL o None.
**Aceptacion**: La funcion verifica ownership del usuario y retorna URL valida por 1 hora.

### T002 - Incluir image_url en respuesta de /posts/feed [S]
**Archivo**: `app/dashboard/routes.py`
**Entregable**: El endpoint `GET /dashboard/posts/feed` incluye campo `image_url` en cada post del JSON.
**Aceptacion**: La respuesta JSON contiene `image_url: "https://..."` para posts con imagen, `null` para posts sin imagen.

## Fase 2: Frontend - Miniaturas en Historial

### T003 - Mostrar miniaturas en renderPosts() [S]
**Archivo**: `app/templates/dashboard/layout.html`
**Entregable**: La funcion `renderPosts()` muestra `<img src="image_url">` en lugar del placeholder SVG.
**Aceptacion**: Las imagenes se visualizan correctamente en la columna "Imagen" del historial.

## Fase 3: Frontend - Reset de Formulario

### T004 - Reset explicito del boton despues de envio exitoso [S]
**Archivo**: `app/templates/dashboard/post_form.html`
**Entregable**: El boton se re-habilita y el formulario se limpia inmediatamente despues de respuesta 200 OK.
**Aceptacion**: El usuario puede enviar un segundo post inmediatamente sin que el boton quede bloqueado.

## Fase 4: Estilos - Padding en Inputs

### T005 - Padding en textarea de descripcion del dashboard [S]
**Archivo**: `app/templates/dashboard/post_form.html`
**Entregable**: El `<textarea>` tiene clase `px-4 py-2.5`.
**Aceptacion**: El texto no toca los bordes del textarea.

### T006 - Padding en inputs de login [S]
**Archivo**: `app/templates/components/auth_form.html`
**Entregable**: Los `<input>` de email y password tienen clase `px-4 py-2.5`.
**Aceptacion**: El texto no toca los bordes de los inputs de login.

### T007 - Padding en inputs de registro [S]
**Archivo**: `app/templates/components/register_form.html`
**Entregable**: Los `<input>` de email, password y confirm tienen clase `px-4 py-2.5`.
**Aceptacion**: El texto no toca los bordes de los inputs de registro.
