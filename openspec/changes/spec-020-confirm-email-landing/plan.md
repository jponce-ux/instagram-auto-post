# Plan Técnico: Vista de Confirmación de Registro

## Stack Tecnológico

- **Framework**: FastAPI (Python 3.11+)
- **Templates**: Jinja2
- **CSS**: Tailwind CSS (pre-compilado en `app/static/css/app.css`)
- **Iconos**: Heroicons (SVG inline, sin dependencia externa)

## Arquitectura

### Cambios Mínimos

Esta es una funcionalidad pequeña que requiere 3 cambios puntuales:

```
app/templates/auth/confirm_email.html  ← NUEVO: Template Jinja2
app/auth/routes.py                     ← MODIFICADO: Nueva ruta GET + cambio de redirect
```

### Estructura del Template

El template `confirm_email.html` seguirá el patrón existente de `login.html` y `register.html`:

- Extiende `base.html` (hereda navbar, toast component, CSS)
- Usa Tailwind CSS para layout centrado (`min-h-[80vh] flex items-center justify-center`)
- Icono SVG inline (Heroicons `envelope` o `check-circle`)
- Sin JavaScript necesario (página puramente estática)
- Meta tag `robots` para evitar indexación: `<meta name="robots" content="noindex, nofollow">`

### Diseño Visual

```
┌─────────────────────────────────────────┐
│           [Navbar de base.html]         │
│                                         │
│         ┌───────────────────┐          │
│         │   📧 (icono SVG)  │          │
│         │                   │          │
│         │  ¡Casi listo!     │          │
│         │                   │          │
│         │  Hemos enviado    │          │
│         │  un enlace de     │          │
│         │  confirmación...  │          │
│         │                   │          │
│         │  [Ir al Login]    │          │
│         └───────────────────┘          │
│                                         │
└─────────────────────────────────────────┘
```

### Clases Tailwind a usar

- Contenedor: `min-h-[80vh] flex items-center justify-center px-4`
- Card: `bg-white shadow-md rounded-lg p-8 max-w-md w-full text-center`
- Icono: `w-16 h-16 mx-auto text-green-500`
- Título: `text-2xl font-bold text-gray-900 mt-4`
- Texto: `text-gray-600 mt-2`
- Botón: `mt-6 w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors`

### Ruta GET /auth/confirm-email

```python
@router.get("/confirm-email")
async def confirm_email_page(
    request: Request,
    user: User | None = Depends(get_current_user_optional),
):
    """Confirm email page with router guard for authenticated users."""
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="auth/confirm_email.html",
    )
```

### Cambio en POST /auth/register

Línea actual:
```python
return RedirectResponse(url="/auth/login?registered=1", status_code=303)
```

Nueva línea:
```python
return RedirectResponse(url="/auth/confirm-email", status_code=303)
```

### Limpieza del parámetro ?registered=1

El bloque JavaScript en `login.html` que maneja `?registered=1` puede eliminarse ya que la confirmación ahora ocurre en una página dedicada:

```javascript
// ELIMINAR este bloque de login.html:
document.addEventListener('DOMContentLoaded', function() {
    const params = new URLSearchParams(window.location.search);
    if (params.get('registered') === '1') {
        showToast('success', 'Cuenta creada exitosamente. Inicia sesión.');
        window.history.replaceState({}, '', '/auth/login');
    }
});
```

## Dependencias

- **Nuevas**: Ninguna
- **Existentes**: Jinja2Templates (ya configurado), Tailwind CSS (ya compilado), Heroicons (SVG inline)

## Estrategia de Pruebas

- Test unitario: GET `/auth/confirm-email` retorna 200 con HTML
- Test unitario: GET `/auth/confirm-email` con usuario autenticado retorna 303 → /dashboard
- Test de integración: POST `/auth/register` exitoso redirige a `/auth/confirm-email`
- Test visual: Verificar que el template renderiza correctamente (manual o Playwright)

## Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| El usuario no entiende que debe verificar email | Baja | Medio | Mensaje claro con icono visual |
| La página se indexa en buscadores | Baja | Bajo | Meta tag `robots` noindex |
| El parámetro `?registered=1` queda huérfano | Media | Bajo | Eliminar el bloque JS de login.html |

## Rollout

1. Crear template `confirm_email.html`
2. Agregar ruta GET `/auth/confirm-email`
3. Cambiar redirect de POST `/auth/register`
4. Limpiar `?registered=1` de `login.html`
5. Verificar flujo completo: registro → confirmación → login
