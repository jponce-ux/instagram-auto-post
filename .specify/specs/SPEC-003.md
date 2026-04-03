# 📋 SPEC 003: Dockerización (Entorno de Desarrollo)

**ID del Ticket:** TASK-003  
**Nombre de la Rama:** `feat/003-docker-setup`

## Objetivo

Levantar el entorno de contenedores dejando aislada la base de datos de Postgres y preparando el contenedor monolítico de FastAPI + Frontend.

---

## 📝 Criterios de Aceptación

- [x] El comando `docker compose up` debe levantar Postgres y la app de FastAPI sin fallos.
- [x] La base de datos debe persistir sus datos en un volumen nombrado de Docker.

---

## 🛠️ Lista de Tareas (Tasks)

- [x] Crear la rama `feat/003-docker-setup` desde la rama principal.
- [x] Crear el archivo `Dockerfile` en la raíz utilizando la imagen oficial de `astral-sh/uv` (para aprovechar la velocidad de instalación en el build).
- [x] Configurar el `Dockerfile` para que exponga el puerto 8000 y ejecute Uvicorn apuntando a `app.main:app`.
- [x] Crear el archivo `docker-compose.yml` definiendo dos servicios:
  - **db**: Imagen de PostgreSQL 16+, con credenciales por variables de entorno y mapeo de volumen para persistencia.
  - **web**: Construido desde el Dockerfile local, enlazado a la red de la base de datos.
- [x] Crear un archivo `.env.example` con las variables necesarias para que el desarrollador las clone a su propio `.env`.

---

## 🐳 Servicios Docker

### Servicio: db (PostgreSQL)

| Configuración | Valor |
|---------------|-------|
| Imagen | `postgres:16-alpine` |
| Puerto | `5432:5432` |
| Volumen | `postgres_data` |

### Servicio: web (FastAPI)

| Configuración | Valor |
|---------------|-------|
| Build | Contexto local (Dockerfile) |
| Puerto | `8000:8000` |
| Dependencias | `db` |

---

## 📄 Variables de Entorno (.env.example)

```bash
# Base de datos
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=instagram_app
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/instagram_app

# App
DEBUG=true
SECRET_KEY=your-secret-key-here
```
