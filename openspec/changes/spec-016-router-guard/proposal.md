# Proposal: spec-016-router-guard

## Intent

Implementar la lógica que decide qué ve el usuario al entrar a la raíz (/) basándose en la validez de su JWT en la cookie.

## Scope

### In Scope
- Crear función `get_current_user_optional` que devuelva None si no hay token
- Modificar endpoint `/` para redirigir usuarios autenticados a /dashboard
- Mostrar landing.html a usuarios no autenticados en /
- Proteger rutas bajo /dashboard con `get_current_user` - redirige a `/` si no hay auth
- Redirigir usuarios autenticados de `/login` y `/register` a /dashboard
- Endpoint `/auth/logout` que limpie la cookie de autenticación

### Out of Scope
- Contenido de landing.html (viene en SPEC-017)
- Cambios en el sistema de autenticación (JWT ya existe en TASK-006)

## Acceptance Criteria

1. Usuario con JWT válido en / → redirige a /dashboard (303)
2. Usuario sin JWT en / → muestra landing.html
3. Usuario sin JWT en /dashboard → redirige a / (login page)
4. Usuario autenticado en /login → redirige a /dashboard
5. Usuario autenticado en /register → redirige a /dashboard
6. Usuario en /auth/logout → limpia cookie y redirige a /

## Dependencies

- TASK-006 (Auth JWT) - existente

## Approach

1. **Nueva dependencia**: `get_current_user_optional` que retorna `User | None` (no lanza 401)
2. **Ruta `/`**: Usa la nueva dependencia - si hay usuario redirige a dashboard, si no muestra landing
3. **Dashboard protection**: Modificar para redirigir a `/` en vez de retornar 401
4. **Auth guards**: `/auth/login` y `/auth/register` redirigen autenticados a /dashboard
5. **Logout**: Nuevo endpoint `/auth/logout` que limpia la cookie `access_token`
