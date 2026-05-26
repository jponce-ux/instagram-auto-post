---
ticket: TASK-025
phase: tasks
model: qwen3.6-plus
generated: 2026-05-13
status: completed
---

# Tareas: Rolling Sessions y Persistencia Extendida

Estado: ✅ Completado
Progreso: 8/8 tareas

## Fase 1: Configuracion

### T001 - Agregar variables de sesion a config.py [S]
**Archivo**: `app/core/config.py`
**Entregable**: `SESSION_INACTIVITY_LIMIT_HOURS=24` y `SESSION_COOKIE_MAX_AGE_DAYS=7`
**Aceptacion**: Las variables son accesibles via `settings.SESSION_INACTIVITY_LIMIT_HOURS`

### T002 - Incluir claim iat en JWT [S]
**Archivo**: `app/auth/security.py`
**Entregable**: `create_access_token` incluye `iat` en el payload y calcula `exp` desde `iat`
**Aceptacion**: El token decodificado contiene `iat` y `exp` donde `exp - iat = inactivity_limit`

## Fase 2: Middleware de Rolling Session

### T003 - Crear middleware de rolling session [M]
**Archivo**: `app/auth/middleware.py` (nuevo)
**Entregable**: `RollingSessionMiddleware` que refresca la cookie en cada request autenticado
**Aceptacion**: Si el token es valido y no expirado, la respuesta incluye `Set-Cookie` con nuevo token

### T004 - Registrar middleware en app/main.py [S]
**Archivo**: `app/main.py`
**Entregable**: Middleware agregado a la app de FastAPI
**Aceptacion**: El middleware se ejecuta en cada request

## Fase 3: Login con Cookie Persistente

### T005 - Agregar max_age al set_cookie del login [S]
**Archivo**: `app/auth/routes.py`
**Entregable**: `set_cookie` incluye `max_age=SESSION_COOKIE_MAX_AGE_DAYS * 86400`
**Aceptacion**: La cookie persiste entre reinicios del navegador

## Fase 4: Validacion de Inactividad

### T006 - Validar iat contra limite de inactividad en dependencies [S]
**Archivo**: `app/auth/dependencies.py`
**Entregable**: `get_current_user_optional` rechaza tokens con `iat` mas viejo que el limite
**Aceptacion**: Token con iat > 24h retorna None (no autenticado)

## Fase 5: Frontend - Manejo de 401

### T007 - Listener HTMX para redirigir en 401 [S]
**Archivo**: `app/templates/base.html`
**Entregable**: Script que detecta 401 en respuestas HTMX y redirige a /auth/login
**Aceptacion**: Si el token expira, el usuario es redirigido automaticamente al login

## Fase 6: Docker y Env

### T008 - Agregar variables a docker-compose.yml [S]
**Archivo**: `docker-compose.yml`
**Entregable**: `SESSION_INACTIVITY_LIMIT_HOURS` y `SESSION_COOKIE_MAX_AGE_DAYS` en servicios web
**Aceptacion**: Los contenedores reciben las variables de entorno
