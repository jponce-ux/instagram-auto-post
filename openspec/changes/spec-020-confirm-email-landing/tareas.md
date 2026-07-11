# Tareas: Vista de Confirmación de Registro

**Ticket**: TASK-022  
**Especificación**: spec-020-confirm-email-landing  
**Prerequisitos**: Ninguno (independiente)

---

## Fase 1: Template Jinja2

**Propósito**: Crear la página HTML de confirmación con diseño centrado y Tailwind CSS

- [x] **T001** Crear `app/templates/auth/confirm_email.html`
  - Extender `base.html`
  - Icono SVG inline (Heroicons envelope o check-circle)
  - Título: "¡Casi listo!"
  - Mensaje explicativo sobre verificación de email
  - Mención de revisar carpeta de spam
  - Botón "Ir al Login" → `/auth/login`
  - Meta tag `<meta name="robots" content="noindex, nofollow">` en el bloque head
  - Diseño responsive con Tailwind (centrado elástico)
  - **Archivo**: `app/templates/auth/confirm_email.html`
  - **Entregable**: Template funcional que extiende base.html
  - **Verificación**: Abrir `/auth/confirm-email` en navegador y verificar diseño
  - **Tamaño**: S

---

## Fase 2: Ruta GET /auth/confirm-email

**Propósito**: Exponer el template como endpoint público

- [x] **T002** Agregar ruta `@router.get("/confirm-email")` en `app/auth/routes.py`
  - Usar `get_current_user_optional` como router guard
  - Si usuario autenticado → redirect 303 a `/dashboard`
  - Si no → retornar `TemplateResponse` con `auth/confirm_email.html`
  - **Archivo**: `app/auth/routes.py`
  - **Entregable**: Endpoint GET funcional
  - **Verificación**: `curl http://localhost:8000/auth/confirm-email` retorna HTML 200
  - **Tamaño**: XS

---

## Fase 3: Refactor de Redirección

**Propósito**: Cambiar el flujo post-registro para usar la nueva página

- [x] **T003** Cambiar redirect en `POST /auth/register`
  - De: `RedirectResponse(url="/auth/login?registered=1", status_code=303)`
  - A: `RedirectResponse(url="/auth/confirm-email", status_code=303)`
  - **Archivo**: `app/auth/routes.py`
  - **Entregable**: Registro redirige a confirm-email
  - **Verificación**: Registrar usuario → verificar redirect a `/auth/confirm-email`
  - **Tamaño**: XS

---

## Fase 4: Limpieza

**Propósito**: Eliminar código obsoleto del login

- [x] **T004** Eliminar bloque JavaScript de `?registered=1` en `app/templates/auth/login.html`
  - Remover el `document.addEventListener('DOMContentLoaded', ...)` que maneja `registered=1`
  - **Archivo**: `app/templates/auth/login.html`
  - **Entregable**: Login page sin lógica de toast post-registro
  - **Verificación**: Login page funciona sin errores JS en consola
  - **Tamaño**: XS

---

## Fase 5: Verificación

**Propósito**: Validar flujo completo

- [x] **T005** Ejecutar suite de tests existente
  - Comando: `uv run pytest tests/ -v`
  - **Entregable**: Todos los tests pasan (90+)
  - **Verificación**: 0 fallos
  - **Tamaño**: S

- [x] **T006** Verificación manual del flujo completo
  - Registrar nuevo usuario → confirmar que redirige a `/auth/confirm-email`
  - Verificar diseño en viewport móvil (Chrome DevTools)
  - Click en "Ir al Login" → verificar que llega a `/auth/login`
  - Usuario autenticado navega a `/auth/confirm-email` → verifica redirect a dashboard
  - **Entregable**: Flujo E2E funcional
  - **Tamaño**: S

---

## Dependencias y Orden de Ejecución

```
T001 (Template)
   ↓
T002 (Ruta GET)
   ↓
T003 (Redirect POST)
   ↓
T004 (Limpieza login.html)
   ↓
T005 + T006 (Verificación, paralelizables [P])
```

### Oportunidades de Paralelismo

- T005 y T006 son paralelizables `[P]` — pueden ejecutarse simultáneamente
