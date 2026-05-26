---
ticket: TASK-025
phase: plan
model: qwen3.6-plus
generated: 2026-05-13
status: completed
---

# Plan Tecnico: Rolling Sessions y Persistencia Extendida

## Arquitectura Actual

- **Auth**: JWT via `python-jose` con HS256, almacenado en cookie `access_token`
- **Cookie**: Sin `max_age` (session cookie), HttpOnly=True, Secure=True, SameSite=Lax
- **Token**: Expira en 60 minutos por defecto (`create_access_token` en `app/auth/security.py`)
- **Validacion**: `get_current_user_optional` en `app/auth/dependencies.py` decodifica JWT desde cookie

## Cambios Requeridos

### 1. Configuracion de Variables de Entorno

Agregar a `app/core/config.py`:
- `SESSION_INACTIVITY_LIMIT_HOURS: int = 24` — umbral de inactividad
- `SESSION_COOKIE_MAX_AGE_DAYS: int = 7` — duracion maxima de la cookie en navegador

### 2. Refactor de `create_access_token`

En `app/auth/security.py`:
- Incluir claim `iat` (issued_at) en el payload del JWT
- El `exp` se calcula como `iat + SESSION_INACTIVITY_LIMIT_HOURS`
- Esto permite calcular la inactividad real desde el token mismo

### 3. Middleware de Rolling Session

Crear `app/auth/middleware.py`:
- `BaseHTTPMiddleware` que intercepta respuestas
- Si la request tiene un token JWT valido:
  - Verificar que `iat` no exceda `SESSION_INACTIVITY_LIMIT_HOURS`
  - Si esta dentro del limite: generar un nuevo token con `iat = now()` y adjuntar `Set-Cookie` en la respuesta
  - Si excedio el limite: no refrescar (el token expirara naturalmente)
- Solo aplicar a rutas que requieren autenticacion (no a endpoints publicos como `/webhooks/*`, `/auth/login`, `/static/*`)

### 4. Actualizar Login para usar `max_age`

En `app/auth/routes.py` (endpoint POST `/login`):
- Configurar `max_age=SESSION_COOKIE_MAX_AGE_DAYS * 86400` en `set_cookie()`
- Esto permite que la cookie persista entre reinicios del navegador

### 5. Frontend: Manejo de 401 en HTMX

En `app/templates/base.html` o `layout.html`:
- Agregar listener `htmx:responseError` que detecte 401 y redirija a `/auth/login`
- Esto cubre el caso donde el token expira mientras el usuario tiene la pagina abierta

## Archivos a Modificar

| Archivo | Cambio |
|---------|--------|
| `app/core/config.py` | Agregar SESSION_INACTIVITY_LIMIT_HOURS y SESSION_COOKIE_MAX_AGE_DAYS |
| `app/auth/security.py` | Incluir `iat` en JWT, calcular `exp` desde `iat` |
| `app/auth/middleware.py` | **Nuevo** — Middleware de rolling session |
| `app/auth/routes.py` | Agregar `max_age` al set_cookie del login |
| `app/auth/dependencies.py` | Validar `iat` contra limite de inactividad |
| `app/main.py` | Registrar el middleware |
| `app/templates/base.html` | Listener HTMX para 401 → redirect a login |
| `.env` | Agregar variables de configuracion |
| `docker-compose.yml` | Agregar variables de entorno a servicios web/worker |

## Estrategia de Pruebas

- Verificar que la cookie tiene `max_age` de 7 dias
- Verificar que el token incluye claim `iat`
- Verificar que el middleware refresca la cookie en cada request valido
- Verificar que despues de 24h de inactividad el token es rechazado
- Verificar que HTMX redirige a login en 401

## Riesgos

| Riesgo | Mitigacion |
|--------|-----------|
| Middleware refresca cookie en cada request, generando overhead | Solo se genera nuevo token si han pasado >50% del tiempo de expiracion |
| Token muy largo expuesto en cookie | HttpOnly + Secure + SameSite=Lax mitigan XSS y CSRF |
| Múltiples requests simultaneos generan multiples tokens | No es problema — el ultimo token gana, todos son validos hasta su expiracion |
