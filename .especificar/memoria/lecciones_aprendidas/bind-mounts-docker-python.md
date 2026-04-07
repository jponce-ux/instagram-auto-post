# Leccion: Bind Mounts y Estructura de Proyecto Docker

**Fecha**: 2026-04-07
**Proyecto**: mi-app-instagram

## Que paso

Se intentó configurar hot-reload con bind mounts para desarrollo local sin necesidad de rebuilds.

## Problema 1: .venv local con rutas Linux

**Error**: `open C:\Users\...\app\.venv\lib64: The file cannot be accessed by the system`

**Causa**: Montar `./app:/app:rw` hacia que UV cree `.venv` dentro de `./app/` local. `.venv` contiene carpetas `lib64` (sintaxis Linux) que Windows no puede acceder.

**Solucion**: Bind mounts selectivos que solo mapean subcarpetas especificas (`./app/templates:/app/app/templates`, `./app/auth:/app/app/auth`, etc.)

## Problema 2: Ruta de templates no coincidian

**Causa**: El codigo usa `Jinja2Templates(directory="app/templates")` que resuelve a `/app/app/templates` dentro del contenedor.

Los binds debian ser `./app/templates:/app/app/templates:rw` (NO `/app/templates:/app/templates`).

## Estructura de Directorios

**Dentro del contenedor**:
```
/app/                    <- WORKDIR
├── pyproject.toml
├── uv.lock
└── app/                 <- aqui estan auth/, dashboard/, templates/, etc.
```

**Localmente**:
```
mi-app-instagram/        <- raiz del proyecto
├── pyproject.toml
├── uv.lock
└── app/                 <- esta carpeta NO es el root del contenedor
```

## Leccion

Para bind mounts en Docker con proyectos Python:
1. Nunca montar toda la carpeta `app/` si el proyecto crea `.venv`
2. Usar bind mounts selectivos para subcarpetas que cambian frecuentemente
3. Verificar que las rutas del bind mount coincidan con lo que espera el codigo (`/app/app/templates` no `/app/templates`)
