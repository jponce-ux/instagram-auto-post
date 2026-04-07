# Plan: Entorno de Desarrollo con Hot-Reload (DX)

## Resumen

Configurar hot-reload para desarrollo dentro de Docker, sin instalar nada en local. El enfoque usa **bind mounts selectivos** que solo sincronizan las carpetas que cambian frecuentemente (`.py`, `.html`), evitando sincronizar archivos generados como `.venv` o `__pycache__`.

## Problema Identificado

Montar `./app:/app:rw` causa que:
- UV cree `.venv` dentro de `./app/` local (en la carpeta `app` del proyecto)
- `.venv` contiene rutas Linux (`lib64`) que Windows no puede acceder
- Error: "open app\.venv\lib64: The file cannot be accessed by the system"

## Enfoque: Bind Mounts Selectivos

En lugar de montar toda la carpeta `app/`, montamos **solo las subcarpetas** que necesitamos cambiar en tiempo real:

```yaml
services:
  web:
    volumes:
      - ./app/templates:/app/templates:rw
      - ./app/auth:/app/app/auth:rw
      - ./app/dashboard:/app/app/dashboard:rw
      - ./app/webhooks:/app/app/webhooks:rw
      - ./app/core:/app/app/core:rw
      - ./pyproject.toml:/app/pyproject.toml:ro
      - ./uv.lock:/app/uv.lock:ro
    command: uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      - ENV=development
      - PYTHONDONTWRITEBYTECODE=1
```

**Carpeta `app/src/`**: Contiene `input.css` de Tailwind. Esta carpeta NO necesita hot-reload, solo se modifica cuando hay cambios intencionales de estilos.

**Carpeta `app/static/`**: Contiene `app.css` compilado. NO se monta porque es generado durante build.

## NO Hay tailwind-watch

Tailwind CSS se compila durante el build de la imagen (`RUN ./tailwindcss ...`). No hay watcher porque:
- Los cambios de estilos son intencionales y poco frecuentes
- Requieren rebuild cuando hay cambios de CSS (no es daily workflow)
- Evitamos complexity del servicio adicional

## Stack Tecnologico

- **Lenguaje**: Python 3.11
- **Framework**: FastAPI con Uvicorn
- **Contenedores**: Docker Compose
- **Estilos**: Tailwind CSS CLI (compila durante build)
- **Gestor de dependencias**: UV (dentro del contenedor)

## Archivos Afectados

| Archivo | Accion |
|---------|--------|
| `docker-compose.override.yml` | **CREAR** - Configuracion de desarrollo con bind mounts selectivos |
| `app/static/css/app.css` | **COPIAR** - Desde imagen Docker al host (existe solo en imagen) |

## Servicios del Override

### Servicio `web` (sobrescribe)

```yaml
services:
  web:
    volumes:
      # Bind mounts selectivos para carpetas que cambian frecuentemente
      - ./app/templates:/app/templates:rw
      - ./app/auth:/app/app/auth:rw
      - ./app/dashboard:/app/app/dashboard:rw
      - ./app/webhooks:/app/app/webhooks:rw
      - ./app/core:/app/app/core:rw
      # Archivos de proyecto (solo lectura para sincronizar deps)
      - ./pyproject.toml:/app/pyproject.toml:ro
      - ./uv.lock:/app/uv.lock:ro
    command: uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      - ENV=development
      - PYTHONDONTWRITEBYTECODE=1
```

## Evaluacion de Riesgo

| Riesgo | Probabilidad | Impacto | Mitigacion |
|--------|-------------|---------|------------|
| Carpeta `app/` del host se llena con `.venv` | **Eliminada** | - | Bind mounts selectivos evitan que UV cree venv en `app/` |
| `.venv` con rutas Linux en Windows | **Eliminada** | - | Misma razon - no se monta toda la carpeta `app/` |
| Archivos estáticos no se actualizan | Baja | Media | Copiar manualmente `app.css` cuando sea necesario |

## Flujo de Prueba

1. `docker compose up` (sin build)
2. Modificar `app/templates/landing.html` — cambio visible al refrescar
3. Modificar `app/auth/routes.py` — Uvicorn reinicia automaticamente
4. Cambiar estilos — requiere `docker compose build` (no es frecuente)

## Criterios de Aceptacion Cubiertos

| Criterio | Como se aborda |
|----------|---------------|
| Hot-reload Python (.py) | Bind mounts selectivos + Uvicorn --reload |
| Hot-reload HTML | Bind mount `./app/templates:/app/templates:rw` |
| Hot-reload Tailwind | NO - cambios de CSS requieren rebuild (poco frecuente) |
| Docker Compose override | `docker-compose.override.yml` existe |
| Sincronizacion deps | `pyproject.toml` y `uv.lock` montados :ro |
