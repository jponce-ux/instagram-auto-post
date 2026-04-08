# Especificacion de Tarea: Autenticacion Basada en Cookies con JWT

**Rama de Funcionalidad**: `feat/020-jwt-cookie-auth`
**Creado**: 2026-04-07
**Estado**: Completado
**Tipo**: Tarea
**Entrada**: TASK-020 - Autenticacion Basada en Cookies con JWT
**Fuente**: Entrada manual

## Objetivo

Modificar el sistema de autenticacion para que el JWT se almacene en una cookie HttpOnly. Esto permite que el navegador envie automaticamente la identidad del usuario en cada peticion, simplificando la navegacion y eliminando la necesidad de almacenar el token en localStorage.

## Estado Actual (spec-019 y anterior)

El login actual:
- Retorna JSON con `access_token`, `token_type` y `user`
- Setea cookie con `secure=False`
- El frontend guarda el token en localStorage

## Cambios Requeridos

### Login: Solo cookie + redirect

El endpoint POST /auth/login debe:
- Retornar un `RedirectResponse(url="/dashboard", status_code=303)`
- NO retornar JSON body
- Settear cookie con `httponly=True`, `secure=True`, `samesite="lax"`

### Frontend: Sin localStorage

- Eliminar la logica de guardar token en localStorage
- Eliminar la logica de leer token desde localStorage
- El formulario puede enviarse via form submit normal o fetch (sin procesar respuesta JSON)

### Cookie Flags

- `httponly=True` - No accesible por JavaScript
- `secure=True` - Solo en HTTPS (produccion)
- `samesite="lax"` - Permite navegacion normal del navegador

## Alcance

- **Dentro del alcance**:
  - Modificar endpoint POST /auth/login para retornar solo redirect + cookie
  - Actualizar flags de cookie a `secure=True`
  - Eliminar logica de localStorage en landing.html y auth/login.html
  - Verificar que /dashboard cargue correctamente con cookie
  - Verificar que / redirija correctamente segun estado de autenticacion

- **Fuera del alcance**:
  - Cambiar estructura de JWT (el token sigue siendo el mismo)
  - Modificar get_current_user (ya lee de cookies)
  - Cambios en el flujo de registro

## Dependencias

- TASK-006 (Auth Base) - Implementado
- TASK-017 (Landing Page) - Implementado
- TASK-019 (Hot-Reload) - Implementado

## Requisitos

- RF-001: POST /auth/login debe retornar RedirectResponse con status 303 y Set-Cookie
- RF-002: La cookie debe tener `httponly=True`, `secure=True`, `samesite="lax"`
- RF-003: La ruta / debe verificar cookie y redirigir a /dashboard si usuario esta autenticado
- RF-004: La ruta /dashboard debe cargar correctamente extrayendo el usuario desde la cookie
- RF-005: El frontend NO debe guardar token en localStorage

## Criterios de Completitud

1. **Login redirect**: Al hacer login exitoso, el navegador redirige a /dashboard y la cookie esta seteada
2. **Cookie segura**: La cookie tiene los flags correctos (verificable en DevTools > Application > Cookies)
3. **Navegacion protegida**: La ruta / muestra landing.html solo si NO hay cookie valida
4. **Dashboard accesible**: /dashboard carga correctamente cuando la cookie esta presente
5. **Sin localStorage**: No hay codigo que guarde o lea token desde localStorage en los templates de login/landing
6. **Logout funciona**: /auth/logout borra la cookie y redirige a /
