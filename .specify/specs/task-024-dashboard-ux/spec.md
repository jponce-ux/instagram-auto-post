---
ticket: TASK-024
phase: spec
model: qwen3.6-plus
generated: 2026-05-13
status: draft
---

# Especificacion: Refactor UX/UI Dashboard y Correcciones Esteticas

## Problema

El dashboard presenta tres problemas de UX/UI que afectan la experiencia del usuario:

1. **Miniaturas no se visualizan** en el historial de publicaciones — la columna "Imagen" muestra un icono placeholder en lugar de la imagen real del post.
2. **Boton "Publicar" se bloquea permanentemente** en estado "Publicando..." despues del primer envio, impidiendo publicaciones consecutivas.
3. **Inputs y textareas sin padding interno** — el texto toca los bordes de los campos en el formulario de login, registro y descripcion del dashboard.

## Historias de Usuario

### HU-1: Visualizacion de Miniaturas en Historial

**Como** usuario del dashboard,
**Quiero** ver miniaturas de mis imagenes en el historial de publicaciones,
**Para** identificar rapidamente cada publicacion por su contenido visual.

**Criterios de aceptacion:**
- Dado que tengo publicaciones en el historial, cuando cargo la pagina, entonces cada fila muestra una miniatura de la imagen correspondiente.
- Dado que la imagen esta en el bucket privado de MinIO, cuando se genera la URL, entonces se usa una Presigned URL temporal (no se expone el bucket publicamente).
- Dado que una publicacion no tiene imagen asociada, cuando se renderiza la fila, entonces se muestra un placeholder generico.

### HU-2: Publicaciones Consecutivas sin Bloqueo

**Como** usuario del dashboard,
**Quiero** poder publicar multiples imagenes consecutivas sin que la interfaz se bloquee,
**Para** agilizar mi flujo de trabajo de publicacion.

**Criterios de aceptacion:**
- Dado que envio un post exitosamente, cuando el servidor responde 200 OK, entonces el formulario se limpia y el boton vuelve a estado "Publicar" inmediatamente.
- Dado que el boton esta en estado "Publicando...", cuando la peticion HTTP esta en vuelo, entonces el boton esta deshabilitado.
- Dado que envio 3 posts seguidos en menos de 1 minuto, entonces ninguno queda bloqueado y todos se encolan correctamente.

### HU-3: Padding Consistente en Inputs

**Como** usuario de la aplicacion,
**Quiero** que los campos de texto tengan espaciado interno adecuado,
**Para** que el texto no toque los bordes y sea legible.

**Criterios de aceptacion:**
- Dado que veo el textarea de "Descripcion" en el dashboard, entonces el texto tiene al menos `px-4 py-2` de padding interno.
- Dado que veo los inputs de login en la landing page, entonces el texto tiene al menos `px-4 py-2` de padding interno.
- Dado que veo los inputs de registro en la landing page, entonces el texto tiene al menos `px-4 py-2` de padding interno.

## No-Objetivos

- No se modifica la logica de procesamiento de posts (Celery worker).
- No se cambia la estructura de buckets de MinIO.
- No se modifica el flujo de autenticacion OAuth de Instagram.

## Metricas de Exito

- Las miniaturas se cargan en el 100% de las publicaciones con imagen.
- El usuario puede enviar posts consecutivos sin bloqueo visible.
- Ningun input de la aplicacion tiene texto pegado a los bordes.

## Preguntas Abiertas

- N/A — todos los requisitos estan claros.
