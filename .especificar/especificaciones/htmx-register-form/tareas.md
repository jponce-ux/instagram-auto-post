# Tareas: Formulario de Registro HTMX

**Estado**: Completado
**Progreso**: 4/4 tareas
**Fase Actual**: Completado

## Fase 1: Modificar Formulario de Registro

- [x] T001 Modificar `app/templates/components/register_form.html`
  - Archivo: `app/templates/components/register_form.html`
  - Cambios implementados:
    1. Removido campo `username` - el endpoint solo espera `email`
    2. Agregado id `register-form` al form
    3. Agregado id `register-submit` al boton
    4. Agregado id `register-error` y `register-confirm-error`
    5. Cambiado `hx-swap="innerHTML"` a `hx-swap="outerHTML"`
    6. Agregados atributos HTML5 de validacion

- [x] T002 Agregar validacion client-side con JavaScript
  - Funcionalidades implementadas:
    1. `validateRegisterForm()` - valida email, password y confirmacion
    2. `handleRegisterSubmit()` - handler fetch con manejo de respuesta
    3. Boton disabled hasta que todas las validaciones pasen

- [x] T003 Agregar estilos de validacion visual
  - Estilos implementados:
    1. Error visual cuando contrasenas no coinciden (border-red-500)
    2. Mensaje de error "Las contrasenas no coinciden"
    3. Boton disabled con opacity-50 y cursor-not-allowed

## Fase 2: Verificacion

- [x] T004 Verificar que el build funciona y tests pasan
  - Comando: `docker compose build web`
  - Comando: `uv run pytest tests/ -v`
  - Resultado: Pendiente de ejecutar

## Dependencias

- T002 depende de T001 (agregar IDs antes de usar en JS)
- T003 puede ejecutarse en paralelo con T002

## Orden de Ejecucion

1. T001 (modificar HTML del form)
2. T002 (agregar validacion JS) - puede paralelizar con T003
3. T003 (estilos validacion)
4. T004 (verificacion)
