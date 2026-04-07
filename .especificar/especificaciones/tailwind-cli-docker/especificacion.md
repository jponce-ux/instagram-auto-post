# Especificacion de Tarea: Tailwind CLI en Contenedor Docker

**Rama de Funcionalidad**: `tailwind-cli-docker`
**Creado**: 2026-04-06
**Estado**: Completado
**Tipo**: Tarea
**Entrada**: Entrada manual
**Fuente**: SDD Planificador

## Objetivo

Instalar y configurar Tailwind CSS CLI (standalone binary) dentro del contenedor Docker "web" para generar CSS estatico durante el build, eliminando la dependencia del CDN y asegurando que todas las clases Tailwind de los templates Jinja2 se apliquen correctamente.

## Problema Actual

El proyecto usa Tailwind via CDN:
```html
<script src="https://cdn.tailwindcss.com?plugins=forms,typography,aspect-ratio,line-clamp"></script>
```

**Problema**: Tailwind CDN solo reconoce clases que existen en el HTML en el momento del parse. Los templates Jinja2 (`{% for %}`, `{% if %}`, `{% include %}`) generan HTML dinámicamente, por lo que las clases usadas dentro de estos bloques no son detectadas por el CDN.

**Sintoma**: Solo una pequeña parte de la pagina tiene estilos aplicados.

## Alcance

- **Dentro del alcance**:
  - Configurar Tailwind CLI standalone en el contenedor Docker
  - Generar CSS estatico antes de servir la aplicacion
  - Reemplazar el script CDN con el CSS compilado localmente
  - Asegurar que todas las clases Tailwind de los templates Jinja2 funcionen

- **Fuera del alcance**:
  - Modificar templates Jinja2 existentes
  - Agregar nuevas clases o funcionalidades CSS
  - Configuracion de PostCSS o build tools adicionales

## Requisitos

- RF-001: El CLI de Tailwind debe descargarse automaticamente durante el build del contenedor
- RF-002: El proceso de build de Tailwind debe escanear todos los templates en `app/templates/`
- RF-003: El CSS generado debe servirse estaticamente desde `app/static/css/app.css`
- RF-004: El script CDN de Tailwind debe ser removido de `base.html`
- RF-005: El comando de build de Tailwind debe ejecutarse antes de iniciar la aplicacion FastAPI

## Criterios de Completitud

1. El contenedor "web" hace build sin errores
2. El CSS generado incluye todas las clases Tailwind usadas en los templates
3. La pagina renderiza correctamente con todos los estilos aplicados
4. No hay dependencias de CDN en el codigo final
