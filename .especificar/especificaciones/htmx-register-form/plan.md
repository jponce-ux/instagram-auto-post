# Plan: Formulario de Registro HTMX

## Enfoque

Modificar el formulario de registro existente para:
1. Corregir el campo `username` -> `email` (el endpoint espera `email`)
2. Agregar validacion client-side para confirmacion de contrasena
3. Deshabilitar el boton de submit hasta que todas las validaciones pasen
4. Mantener el comportamiento HTMX de swap entre formularios

## Contexto Tecnico

**Stack detectado**:
- Lenguaje: Python 3.11
- Framework: FastAPI
- Motor de templates: Jinja2
- CSS: Tailwind CLI (v4.2.2)
- JavaScript: Vanilla JS (sin frameworks)

**Archivos relevantes**:
- `app/auth/routes.py` — endpoint `/auth/register` (ya existe, no modificar)
- `app/auth/schemas.py` — `UserRegister` con `email` y `password`
- `app/templates/components/register_form.html` — form a modificar
- `app/templates/components/auth_form.html` — form de login (ya tiene fetch handler)

## Arquitectura de la Solucion

### Flujo de datos

```
Formulario de Registro (register_form.html)
    |
    |-- submit --> fetch('/auth/register')
    |               |
    |               |-- 200 OK + HX-Redirect --> window.location.href = '/dashboard'
    |               |-- 200 OK + error HTML --> showToast('error', mensaje)
    |               |-- otro error --> showToast('error', 'Error de registro')
    |
    |-- click "Iniciar sesion" --> hx-get="/auth/login-form" --> swap #auth-form-box
```

### Validacion Client-Side

```
Campo email:      input[type="email"] + required + oninput validateEmail()
Campo password:   input[type="password"] + minlength="6" + required
Campo confirm:    input[type="password"] + oninput validatePasswordsMatch()
Boton submit:     disabled={!isValid} + class based on state
```

## Archivos Afectados

| Archivo | Cambio |
|---------|--------|
| `app/templates/components/register_form.html` | Validacion + handler fetch |
| `app/templates/components/auth_form.html` | Ya tiene fetch handler - no cambiar |
| `app/templates/base.html` | Ya incluye toast - no cambiar |

## Evaluacion de Riesgo

- **Riesgo bajo**: Solo se modifica frontend, endpoint existente no cambia
- **Sin impacto en otras funcionalidades**: Login y registro funcionan igual
- **Reversion simple**:git checkout del archivo si algo falla

## Dependencias

No hay nuevas dependencias. Todo es JavaScript vanilla con HTMX existente.
