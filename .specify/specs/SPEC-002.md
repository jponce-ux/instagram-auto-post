# 📋 SPEC 002: Configuración de Dependencias Base (Async Stack)

**ID del Ticket:** TASK-002  
**Nombre de la Rama:** `feat/002-base-dependencies`

## Objetivo

Instalar todas las librerías necesarias para el desarrollo asíncrono y de seguridad sin levantar servicios aún.

---

## 📝 Criterios de Aceptación

- [x] No se debe usar `pip`. Toda adición debe ser mediante `uv add`.
- [x] El archivo `uv.lock` debe autogenerarse y quedar registrado en Git.

---

## 🛠️ Lista de Tareas (Tasks)

- [x] Crear la rama `feat/002-base-dependencies` desde la rama principal.
- [x] Agregar FastAPI y Uvicorn:  
  ```bash
  uv add fastapi "uvicorn[standard]"
  ```

- [x] Agregar las librerías para la base de datos asíncrona:  
  ```bash
  uv add "sqlalchemy[asyncio]" asyncpg alembic
  ```

- [x] Agregar las librerías de seguridad (Argon2 y JWT):  
  ```bash
  uv add "passlib[argon2]" "python-jose[cryptography]"
  ```

- [x] Agregar HTTPX para las futuras conexiones a Meta:  
  ```bash
  uv add httpx
  ```

- [x] Agregar soporte para variables de entorno:  
  ```bash
  uv add pydantic-settings
  ```

- [x] Agregar Jinja2 para renderizar el frontend:  
  ```bash
  uv add jinja2
  ```

- [x] Ejecutar `uv sync` para congelar el entorno y verificar que no existan conflictos de dependencias.

---

## 📦 Dependencias a Instalar

| Paquete | Propósito |
|---------|-----------|
| `fastapi` | Framework web asíncrono |
| `uvicorn[standard]` | Servidor ASGI |
| `sqlalchemy[asyncio]` | ORM con soporte async |
| `asyncpg` | Driver PostgreSQL async |
| `alembic` | Migraciones de base de datos |
| `passlib[argon2]` | Hashing de contraseñas |
| `python-jose[cryptography]` | Manejo de JWT |
| `httpx` | Cliente HTTP async |
| `pydantic-settings` | Configuración por variables de entorno |
| `jinja2` | Motor de plantillas HTML |
