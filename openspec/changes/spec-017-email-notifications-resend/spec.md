---
ticket: TASK-021
phase: spec
model: qwen3.6-plus
generated: 2026-05-11
status: draft
---

# Feature Specification: Sistema de Notificaciones por Email (Resend + Celery)

**Feature Branch**: `spec-017-email-notifications-resend`  
**Created**: 2026-05-11  
**Status**: Draft  
**Input**: TASK-021 - Implementar servicio de mensajería con Resend SDK + Celery para envío asíncrono de correos electrónicos

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Envío de Email de Bienvenida al Registrarse (Priority: P1)

Un nuevo usuario se registra en la plataforma y recibe automáticamente un correo electrónico de bienvenida confirmando la creación de su cuenta. El envío ocurre de forma asíncrona sin afectar el tiempo de respuesta del registro.

**Why this priority**: Es el primer punto de contacto con el usuario después del registro. Confirma que la cuenta fue creada exitosamente y mejora la experiencia de onboarding.

**Independent Test**: Se puede probar registrando un usuario nuevo y verificando que recibe el email de bienvenida en menos de 5 segundos después del registro, sin que el endpoint de registro se vea ralentizado.

**Acceptance Scenarios**:

1. **Given** un usuario completa el formulario de registro exitosamente, **When** el registro se procesa, **Then** el sistema envía un email de bienvenida de forma asíncrona y el usuario recibe la respuesta del registro en menos de 50ms adicionales.
2. **Given** el servicio de Resend está temporalmente caído, **When** se intenta enviar el email de bienvenida, **Then** la tarea de Celery reintenta automáticamente sin afectar la experiencia del usuario.
3. **Given** un usuario se registra con un email inválido, **When** el sistema intenta enviar el email, **Then** la tarea registra el error en los logs y no reintenta indefinidamente.

---

### User Story 2 - Servicio de Email Reutilizable para Futuras Notificaciones (Priority: P2)

El equipo de desarrollo puede importar y usar el servicio de email desde cualquier parte del código para enviar nuevos tipos de notificaciones sin duplicar lógica.

**Why this priority**: Crea la base infraestructural para todas las notificaciones futuras (recuperación de contraseña, confirmación de publicación, alertas de error, etc.).

**Independent Test**: Se puede importar `EmailService` desde cualquier módulo del proyecto y llamar a `send_transactional_email()` con parámetros personalizados, verificando que la tarea se enqueue en Celery correctamente.

**Acceptance Scenarios**:

1. **Given** un desarrollador importa `EmailService` desde `app.services.email`, **When** llama a `send_transactional_email(to, subject, html)`, **Then** la tarea se enqueue en Redis y retorna inmediatamente.
2. **Given** el servicio se importa desde un módulo que no tiene dependencias circulares, **When** se ejecuta, **Then** no se producen errores de importación circular.

---

### User Story 3 - Observabilidad y Monitoreo de Envíos (Priority: P3)

El equipo puede monitorear el estado de los envíos de email a través de los logs de Celery, incluyendo IDs de mensaje de Resend y errores detallados.

**Why this priority**: Permite debugging proactivo y detección temprana de problemas en la entrega de emails.

**Independent Test**: Se puede revisar los logs del worker de Celery después de enviar un email y encontrar entradas con el ID del mensaje de Resend o el error específico.

**Acceptance Scenarios**:

1. **Given** un email se envía exitosamente, **When** se revisan los logs del worker, **Then** se encuentra un log INFO con el message_id devuelto por Resend.
2. **Given** un email falla después de los reintentos, **When** se revisan los logs del worker, **Then** se encuentra un log ERROR con el detalle del fallo y el email destinatario.

---

### Edge Cases

- **¿Qué pasa si la API de Resend devuelve un error 4xx (bad request)?** → La tarea NO reintenta (error del cliente), registra el error y marca como fallido.
- **¿Qué pasa si la API de Resend devuelve un error 5xx o timeout?** → La tarea reintenta con backoff exponencial (máximo 3 intentos).
- **¿Qué pasa si Redis está caído y no se puede enqueue la tarea?** → El servicio captura la excepción y registra un warning; el flujo del usuario no se rompe.
- **¿Qué pasa si el email destinatario está en la lista de bounces de Resend?** → Resend rechaza el envío; la tarea registra el error y no reintenta.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE enviar correos electrónicos utilizando el SDK oficial de Resend (`resend` package).
- **FR-002**: El envío de emails DEBE ser asíncrono mediante Celery, retornando en menos de 50ms al llamador.
- **FR-003**: El API Key de Resend DEBE leerse exclusivamente de variables de entorno (`RESEND_API_KEY`), nunca hardcodeado.
- **FR-004**: El sistema DEBE soportar contenido HTML en los correos electrónicos.
- **FR-005**: La tarea de Celery DEBE implementar reintentos automáticos con backoff exponencial para errores 5xx de la API de Resend (máximo 3 intentos).
- **FR-006**: El servicio DEBE registrar logs de éxito (con message_id de Resend) y error (con detalle del fallo).
- **FR-007**: El servicio DEBE poder importarse desde cualquier módulo del proyecto sin causar dependencias circulares.
- **FR-008**: El sistema DEBE incluir un método `send_welcome_email()` con plantilla HTML predefinida para nuevos registros.
- **FR-009**: Las variables de entorno `RESEND_API_KEY`, `MAIL_FROM_ADDRESS`, y `MAIL_FROM_NAME` DEBEN estar configuradas en `app/core/config.py`.
- **FR-010**: El servicio DEBE estar preparado para usar Jinja2 para renderizar templates HTML desde `app/templates/email/` en el futuro.

### Key Entities

- **EmailService**: Clase singleton con métodos estáticos para enviar emails. Centraliza la lógica de negocio y delega el envío real a Celery.
- **task_dispatch_resend_email**: Tarea de Celery que invoca el SDK de Resend. Maneja reintentos y logging.
- **EmailTemplate**: Estructura de datos que representa un template de email (asunto, cuerpo HTML, destinatario, remitente).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El tiempo adicional agregado al endpoint de registro por el envío de email es menor a 50ms (medido con logging).
- **SC-002**: Los emails de bienvenida se entregan exitosamente al 95%+ de los registros (medido por logs de éxito vs total).
- **SC-003**: Las tareas fallidas se reintentan automáticamente hasta 3 veces con backoff exponencial antes de marcar como error permanente.
- **SC-004**: Todos los logs de envío incluyen el message_id de Resend para trazabilidad.

## Assumptions

- Resend está configurado con un dominio verificado o se usa `onboarding@resend.dev` para desarrollo.
- Durante desarrollo local, Resend solo permite enviar emails a la dirección registrada en la cuenta (limitación de sandbox).
- La infraestructura de Celery + Redis ya está operativa (SPEC-011 completado).
- No se requiere persistencia de historial de emails en base de datos en esta iteración.
- El template de bienvenida será HTML inline (no se requiere sistema de templates complejo en esta fase).
