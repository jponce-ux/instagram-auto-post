# Especificacion: Formulario de Registro HTMX

**Rama de Funcionalidad**: `htmx-register-form`
**Creado**: 2026-04-06
**Estado**: Completado
**Tipo**: Funcionalidad
**Entrada**: Entrada manual
**Fuente**: SDD Planificador

## Objetivo

Agregar un formulario de registro que se muestre/oculte dentro del contenedor de autenticacion usando HTMX, sin recargar la pagina. El formulario tendra validacion client-side y estados disabled para el boton de submit.

## Problema/Situacion Actual

El proyecto ya tiene un formulario de registro basico (`register_form.html`) pero:
1. El campo `username` no existe en el endpoint - usa `email`
2. No hay validacion client-side de confirmacion de contrasena
3. El boton de submit no se deshabilita mientras las validaciones fallen
4. El swap entre login/register funciona pero la UX puede mejorar

## Alcance

- **Dentro del alcance**:
  - Crear componente register_form.html con validacion client-side
  - Validar que password y confirm_password sean identicos
  - Deshabilitar boton de submit hasta que todas las validaciones pasen
  - Mantener el swap HTMX entre login y register
  - Endpoint `/auth/register` ya existe y acepta `email` y `password`

- **Fuera del alcance**:
  - Modificar el endpoint de registro (ya existe y funciona)
  - Agregar validacion server-side adicional
  - Persistencia de datos del form entre switches

## Historias de Usuario

### HU-1: Registro de usuario con validacion client-side
**Como** usuario no registrado  
**Quiero** registrarme con validacion en tiempo real  
**Para** asegurarme de que mis contrasenas coinciden antes de enviar

**Criterios de aceptacion**:
- [ ] Campo email acepta formato de email valido
- [ ] Campo password tiene minimo 6 caracteres
- [ ] Campo confirm_password muestra error si no coincide con password
- [ ] Boton "Crear Cuenta" esta deshabilitado si las validaciones fallan
- [ ] Boton "Crear Cuenta" esta habilitado solo cuando email es valido Y password >= 6 Y password == confirm_password

### HU-2: Switch entre login y register via HTMX
**Como** usuario  
**Quiero** cambiar entre formulario de login y registro sin recargar  
**Para** tener una experiencia fluida

**Criterios de aceptacion**:
- [ ] Click en "Registrate" muestra el form de registro en el contenedor `#auth-form-box`
- [ ] Click en "Iniciar sesion" (desde register) muestra el form de login en `#auth-form-box`
- [ ] No hay recarga de pagina durante el switch
- [ ] El contenedor `#auth-form-box` se actualiza con el nuevo formulario

## Requisitos Tecnicos

- **Stack**: FastAPI + Jinja2 + HTMX + Tailwind CSS
- **Endpoint registro**: POST `/auth/register` recibe `{"email": "...", "password": "..."}`
- **Parametros del body**: `email` (EmailStr), `password` (str min 6 chars)
- **Nota**: El campo `username` del form actual NO existe en el endpoint - debe removerse

## Criterios de Completitud

1. Formulario de registro tiene validacion client-side
2. Boton disabled hasta validaciones pasen
3. Switch HTMX funcional entre login y register
4. Mensaje de error generico del backend (sin detalles de validacion)
5. Tests existentes siguen pasando
