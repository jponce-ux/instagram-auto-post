# Plan: Autenticacion Basada en Cookies con JWT

## Resumen

Simplificar la autenticacion usando cookies HttpOnly en lugar de localStorage. El login retorna un redirect 303 con cookie, el frontend no procesa JSON ni guarda token, y todo el flujo de autenticacion es manejado por el servidor via cookies.

## Enfoque

1. **Modificar POST /auth/login**: Retornar `RedirectResponse` + `set_cookie`, sin JSON body
2. **Actualizar flags de cookie**: `secure=True` (antes `False`)
3. **Simplificar frontend**: Eliminar todo codigo que maneje token en JavaScript
4. **Mantener compatibilidad HTMX**: El header `HX-Redirect` puede seguir presente para que HTMX procese la redireccion

## Stack Tecnologico

- **Lenguaje**: Python 3.11
- **Framework**: FastAPI
- **Autenticacion**: JWT via python-jose + cookies HttpOnly
- **Frontend**: Jinja2 templates + HTMX

## Archivos a Modificar

| Archivo | Accion |
|---------|--------|
| `app/auth/routes.py` | Modificar POST /auth/login para retornar solo redirect + cookie |
| `app/templates/components/auth_form.html` | Eliminar logica de localStorage y procesamiento JSON |
| `app/templates/auth/login.html` | Eliminar logica de localStorage y procesamiento JSON |

## Cambios en Detalle

### 1. POST /auth/login (app/auth/routes.py)

**Antes**:
```python
response = JSONResponse(
    content={
        "access_token": access_token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "is_active": user.is_active},
    },
    status_code=200,
)
response.headers["HX-Redirect"] = "/dashboard"
response.set_cookie(
    key="access_token",
    value=f"Bearer {access_token}",
    httponly=True,
    secure=False,  # <-- cambiar a True
    samesite="lax",
)
return response
```

**Despues**:
```python
response = RedirectResponse(url="/dashboard", status_code=303)
response.set_cookie(
    key="access_token",
    value=f"Bearer {access_token}",
    httponly=True,
    secure=True,  # <-- Cambiado
    samesite="lax",
)
return response
```

**Nota**: Ya no retornamos JSON ni HX-Redirect header. El redirect 303 es suficiente.

### 2. auth_form.html (landing page)

**Eliminar**:
- `localStorage.setItem('access_token', ...)`
- `localStorage.setItem('user', ...)`
- `const json = await response.json()`
- Procesamiento de respuesta JSON

**Mantener**:
- El form submit basico (puede seguir usando fetch para mejor UX)
- La redireccion si hay error (pero sin procesar JSON)

### 3. login.html

Mismos cambios que auth_form.html - eliminar toda logica de localStorage y procesamiento JSON.

## Evaluacion de Riesgo

| Riesgo | Probabilidad | Impacto | Mitigacion |
|--------|-------------|---------|------------|
| Drop-in compatibility con fetch() | Baja | Media | Redirect 303 funciona igual con fetch o form submit normal |
| secure=True rompe local dev | Media | Baja | El browser no enforce secure en localhost, solo en produccion con HTTPS real |
| HTMX no procesa redirect | Baja | Media | HTMX sigue redirects automaticamente |

## Flujo de Prueba

1. Ir a / - muestra landing.html
2. Ir a /dashboard - redirige a /auth/login
3. Hacer login con credenciales validas
4. Verificar en DevTools que la cookie `access_token` esta seteada con httponly
5. Verificar que la cookie tiene `secure=True` y `samesite=lax`
6. Verificar que NO hay token en localStorage
7. Navegar a /dashboard - carga correctamente
8. Hacer logout - cookie se borra, redirige a /
