# Tareas: Autenticacion Basada en Cookies con JWT

**Estado**: Completado
**Progreso**: 5/5 tareas
**Fase Actual**: —

## Fase 1: Implementacion

- [x] T001 Modificar POST /auth/login en `app/auth/routes.py` para retornar RedirectResponse + set_cookie (sin JSON)
- [x] T002 Cambiar flag `secure=False` a `secure=True` en el set_cookie de login
- [x] T003 Eliminar logica de localStorage en `app/templates/components/auth_form.html`
- [x] T004 Eliminar logica de localStorage en `app/templates/auth/login.html`
- [x] T005 Verificar que /dashboard carga correctamente con cookie y / redirige segun estado

---

## Dependencias de Fases

**Fase 1**: Todas las tareas son independientes y pueden ejecutarse en paralelo

## Archivos a Crear/Modificar

| Tarea | Archivo | Accion |
|-------|---------|--------|
| T001 | `app/auth/routes.py` | MODIFICAR |
| T002 | `app/auth/routes.py` | MODIFICAR |
| T003 | `app/templates/components/auth_form.html` | MODIFICAR |
| T004 | `app/templates/auth/login.html` | MODIFICAR |
| T005 | Ninguno | VERIFICACION MANUAL |
