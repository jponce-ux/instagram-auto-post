---
ticket: TASK-021
phase: tasks
model: qwen3.6-plus
generated: 2026-05-11
status: completed
---

# Tasks: spec-017-email-notifications-resend

**Input**: `openspec/changes/spec-017-email-notifications-resend/spec.md`, `plan.md`
**Prerequisites**: SPEC-011 (Celery + Redis) completado

## Phase 1: Setup & Dependencies

**Purpose**: Instalar dependencia y configurar variables de entorno

- [x] T001 Instalar paquete `resend` con `uv add resend` y verificar que `pyproject.toml` y `uv.lock` se actualizan
- [x] T002 [P] Agregar `RESEND_API_KEY`, `MAIL_FROM_ADDRESS`, `MAIL_FROM_NAME` a `.env.example`
- [x] T003 Agregar campos `RESEND_API_KEY`, `MAIL_FROM_ADDRESS`, `MAIL_FROM_NAME` a `Settings` en `app/core/config.py`

**Checkpoint**: Dependencia instalada y configuración lista

---

## Phase 2: Email Template

**Purpose**: Crear template HTML de bienvenida

- [x] T004 Crear directorio `app/templates/email/`
- [x] T005 Crear `app/templates/email/welcome.html` con template de bienvenida (HTML inline, responsive, con logo placeholder y mensaje de confirmación de registro)

**Checkpoint**: Template de bienvenida listo

---

## Phase 3: Celery Task (Worker)

**Purpose**: Implementar la tarea física que invoca el SDK de Resend

- [x] T006 Crear `task_dispatch_resend_email` en `app/worker.py` con:
  - Parámetros: `to`, `subject`, `html_body`, `from_email`, `from_name`
  - Invocación de `resend.Emails.send()` con los parámetros
  - `autoretry_for=(Exception,)` con `max_retries=3` y backoff exponencial
  - Log INFO con `message_id` en éxito
  - Log ERROR con detalle en fallo
  - No reintentar para errores 4xx (validar status code si disponible)

**Checkpoint**: Tarea Celery funcional y testeable independientemente

---

## Phase 4: EmailService

**Purpose**: Implementar el servicio compartido que centraliza el envío de emails

- [x] T007 Crear `app/services/email.py` con clase `EmailService`:
  - Método estático `send_transactional_email(to, subject, html_body)` → llama a `task_dispatch_resend_email.delay()`
  - Método estático `send_welcome_email(to, user_name)` → renderiza template welcome.html y llama a `send_transactional_email()`
  - Usar `jinja2.Environment` con `FileSystemLoader("app/templates/email")` para renderizar templates
  - Capturar excepción si Celery no está disponible (Redis caído) y loguear warning
- [x] T008 Verificar que `app/services/email.py` no causa dependencias circulares (no importa routers, solo config y worker)

**Checkpoint**: Servicio importable desde cualquier módulo sin dependencias circulares

---

## Phase 5: Integration with Auth Register

**Purpose**: Conectar el servicio de email con el flujo de registro

- [x] T009 Modificar `app/auth/routes.py` → en el endpoint `POST /auth/register`, después de crear el usuario exitosamente, llamar a `EmailService.send_welcome_email(user.email)`
- [x] T010 Verificar que el registro no se ralentiza significativamente (el `delay()` de Celery retorna inmediatamente)

**Checkpoint**: Email de bienvenida se envía automáticamente al registrar un usuario

---

## Phase 6: Tests

**Purpose**: Verificar funcionamiento correcto

- [x] T011 [P] Crear `tests/test_email.py` con:
  - Test unitario: `EmailService.send_transactional_email()` encola tarea Celery (mock `task_dispatch_resend_email.delay`)
  - Test unitario: `EmailService.send_welcome_email()` renderiza template y encola tarea
  - Test unitario: `task_dispatch_resend_email` llama a `resend.Emails.send()` correctamente (mock Resend SDK)
  - Test de reintento: simular error 5xx y verificar que la tarea reintenta
  - Test de no-reintento: simular error 4xx y verificar que la tarea NO reintenta
- [x] T012 Ejecutar `uv run pytest tests/test_email.py -v` y verificar que todos pasan
- [x] T013 Ejecutar `uv run pytest tests/ -v` y verificar que no se rompen tests existentes

**Checkpoint**: Todos los tests pasan (nuevos + existentes)

---

## Phase 7: Docker & Verification

**Purpose**: Verificar funcionamiento en entorno Docker

- [x] T014 Ejecutar `docker compose build web worker` para incluir el paquete `resend`
- [x] T015 Ejecutar `docker compose up` y verificar que el worker inicia sin errores de importación
- [x] T016 Registrar un usuario nuevo y verificar en logs del worker que el email se envió (o falló con log apropiado)

**Checkpoint**: Sistema funcionando en Docker compose

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — puede empezar inmediatamente
- **Phase 2 (Template)**: No dependencies — puede empezar en paralelo con Phase 1
- **Phase 3 (Celery Task)**: Depende de Phase 1 (paquete `resend` instalado)
- **Phase 4 (EmailService)**: Depende de Phase 2 (template) y Phase 3 (tarea Celery)
- **Phase 5 (Integration)**: Depende de Phase 4 (servicio listo)
- **Phase 6 (Tests)**: Depende de Phase 4 y 5 (código implementado)
- **Phase 7 (Docker)**: Depende de Phase 5 (integración completa)

### Parallel Opportunities

- T001, T002, T003 pueden correr en paralelo
- T004, T005 pueden correr en paralelo con Phase 1
- T011 tests pueden correr en paralelo entre sí

### Implementation Strategy

1. **Phase 1 + 2** → Foundation lista (dependencia + template)
2. **Phase 3** → Tarea Celery funcional
3. **Phase 4** → Servicio compartido funcional
4. **Phase 5** → Integración con registro
5. **Phase 6** → Tests verifican todo
6. **Phase 7** → Docker verification

---

## Notes

- [P] tasks = diferentes archivos, sin dependencias entre sí
- Para evitar dependencias circulares: `email.py` importa la tarea usando `celery_app.send_task("task_dispatch_resend_email")` o importa desde `app.worker` al final del archivo (después de definir la clase)
- Resend sandbox: durante desarrollo, solo se pueden enviar emails a la dirección registrada en la cuenta de Resend
- El template welcome.html debe ser HTML inline (CSS inline) para máxima compatibilidad con clientes de email
