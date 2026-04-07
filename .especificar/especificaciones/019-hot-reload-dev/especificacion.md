# Especificacion de Tarea: Entorno de Desarrollo con Hot-Reload (DX)

**Rama de Funcionalidad**: `feat/019-hot-reload-dev`
**Creado**: 2026-04-06
**Estado**: En Progreso
**Tipo**: Tarea
**Entrada**: TASK-019 - Entorno de Desarrollo con Hot-Reload (DX)
**Fuente**: Entrada manual

## Objetivo

Configurar hot-reload para desarrollo dentro de Docker, sin instalar nada en local. Bind mounts selectivos para carpetas `templates/` y subpaquetes Python (`auth/`, `dashboard/`, etc.) permiten cambios en tiempo real sin rebuild. Los estilos CSS se compilan durante build, no en watch.

## Alcance

- **Dentro del alcance**:
  - Bind mounts selectivos (solo carpetas que cambian frecuentemente)
  - Habilitacion de hot-reload en Uvicorn para archivos Python
  - Sincronizacion de dependencias (pyproject.toml, uv.lock)
  - Creacion de docker-compose.override.yml para entorno de desarrollo

- **Fuera del alcance**:
  - Tailwind watcher (estilos se compilan durante build)
  - Instalacion local de dependencias
  - Modificacion del Dockerfile principal

## Dependencias

- TASK-003 (Docker Setup) - Ya implementado
- TASK-018 (Tailwind Setup) - Ya implementado

## Requisitos

- RF-001: El contenedor debe mapear `./app/templates` y subpaquetes Python (`./app/auth`, `./app/dashboard`, etc.) via bind mount para sincronizar cambios en tiempo real
- RF-002: Uvicorn debe ejecutarse con flag `--reload` para detectar cambios en archivos .py
- RF-003: El servicio web debe tener configurados `ENV=development` y `PYTHONDONTWRITEBYTECODE=1`
- RF-004: Los archivos `pyproject.toml` y `uv.lock` deben estar montados como volumenes de solo lectura
- RF-005: El archivo `docker-compose.override.yml` debe existir junto a `docker-compose.yml`

## Criterios de Completitud

1. **Hot-reload Python**: Al guardar un archivo `.py`, Uvicorn detecta el cambio y reinicia automaticamente (visible en logs del contenedor)
2. **Hot-reload HTML**: Al modificar un archivo `.html` en la carpeta `app/templates/`, los cambios son visibles al refrescar el navegador
3. **Docker Compose override**: Al ejecutar `docker compose up`, la configuracion de desarrollo se aplica automaticamente si `docker-compose.override.yml` existe
4. **Sincronizacion de dependencias**: Al ejecutar `uv add` desde la maquina host, el contenedor detecta los cambios en `pyproject.toml` y `uv.lock`
5. **Flujo de prueba completo**:
   - Cambiar un texto en landing page y verificar que cambia en el navegador
   - Cambiar una logica en un endpoint y verificar que Uvicorn detecta el cambio en los logs
