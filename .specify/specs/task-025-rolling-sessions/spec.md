---
ticket: TASK-025
phase: spec
model: qwen3.6-plus
generated: 2026-05-13
status: completed
---

# Especificacion: Rolling Sessions y Persistencia Extendida

## Problema

Actualmente la sesion del usuario expira en 60 minutos y la cookie es de sesion (se borra al cerrar el navegador). Esto obliga al usuario a reautenticarse frecuentemente, interrumpiendo su flujo de trabajo de publicacion.

## Historias de Usuario

### HU-1: Persistencia de Sesion entre Reinicios del Navegador

**Como** usuario de la plataforma,
**Quiero** que mi sesion persista aunque cierre y vuelva a abrir el navegador,
**Para** no tener que iniciar sesion cada vez que abro la aplicacion.

**Criterios de aceptacion:**
- Dado que inicio sesion exitosamente, cuando cierro el navegador y vuelvo en 2 horas, entonces sigo autenticado sin necesidad de reingresar credenciales.
- Dado que mi cookie de sesion tiene atributos HttpOnly, Secure y SameSite=Lax, entonces no es accesible via JavaScript y se envia solo en peticiones same-site.

### HU-2: Refresco Automatico de Sesion (Rolling Session)

**Como** usuario activo de la plataforma,
**Quiero** que mi sesion se extienda automaticamente mientras interactuo con la aplicacion,
**Para** no ser desconectado mientras estoy trabajando.

**Criterios de aceptacion:**
- Dado que mi ultima actividad fue hace 23 horas, cuando realizo cualquier peticion al backend, entonces el "reloj de inactividad" se resetea a 0 y obtengo otras 24 horas de sesion.
- Dado que realizo una peticion con un token valido, cuando el backend responde, entonces la cookie se refresca con una nueva fecha de expiracion de forma transparente (sin redireccion ni parpadeo).

### HU-3: Expiracion por Inactividad (Hard Timeout)

**Como** usuario de la plataforma,
**Quiero** que mi sesion se invalide despues de 24 horas de inactividad total,
**Para** que mi cuenta este protegida si dejo la sesion abierta en un dispositivo compartido.

**Criterios de aceptacion:**
- Dado que no he interactuado con la aplicacion en 25 horas, cuando intento acceder al dashboard, entonces soy redirigido automaticamente a /auth/login.
- Dado que cualquier peticion HTMX recibe un 401, cuando el frontend detecta el error, entonces redirige al usuario a /auth/login sin mostrar contenido protegido.

## No-Objetivos

- No se implementa arquitectura de Access/Refresh token separados (se usa un solo JWT con rolling).
- No se modifica el flujo de autenticacion OAuth de Instagram.
- No se agrega "remember me" como opcion separada.

## Metricas de Exito

- El usuario puede mantener sesion activa indefinidamente mientras interactua con la app.
- La sesion expira exactamente despues de 24 horas de inactividad.
- El refresco de cookie es invisible para el usuario (0 redirecciones innecesarias).

## Preguntas Abiertas

- N/A — todos los requisitos estan claros.
