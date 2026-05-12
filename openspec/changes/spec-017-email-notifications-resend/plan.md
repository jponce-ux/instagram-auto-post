---
ticket: TASK-021
phase: plan
model: qwen3.6-plus
generated: 2026-05-11
status: draft
---

# Implementation Plan: Sistema de Notificaciones por Email (Resend + Celery)

**Branch**: `spec-017-email-notifications-resend` | **Date**: 2026-05-11 | **Spec**: `openspec/changes/spec-017-email-notifications-resend/spec.md`

## Summary

Implementar un servicio de email asíncrono usando Resend SDK + Celery. El servicio centraliza el envío de correos, delega la ejecución real a una tarea de Celery para no bloquear el request/response, e incluye un template de bienvenida para nuevos registros.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: `resend` (SDK oficial), Celery (ya existente), Redis (ya existente)  
**Storage**: N/A (no persiste emails en DB en esta iteración)  
**Testing**: pytest + unittest.mock para mockear Resend API y Celery  
**Target Platform**: Linux server (Docker compose)  
**Project Type**: Web service (FastAPI)  
**Performance Goals**: <50ms overhead al enqueue de tarea Celery  
**Constraints**: API Key via env var, reintentos solo para 5xx, no dependencias circulares  
**Scale/Scope**: 1 servicio, 1 tarea Celery, 1 template de email

## Constitution Check

- **No dependencias circulares**: `app/services/email.py` solo importa de `app.core.config` y `app.worker` (tarea Celery). No importa routers ni modelos.
- **Async first**: El servicio usa `delay()` de Celery, retornando inmediatamente.
- **Env vars**: `RESEND_API_KEY`, `MAIL_FROM_ADDRESS`, `MAIL_FROM_NAME` en `Settings`.
- **Logging**: INFO para éxito (con message_id), ERROR para fallos (con detalle).

## Project Structure

### Documentation (this feature)

```text
openspec/changes/spec-017-email-notifications-resend/
├── spec.md              # This file
├── plan.md              # This file
└── tasks.md             # Task breakdown
```

### Source Code (repository root)

```text
app/
├── core/
│   └── config.py              # Agregar RESEND_API_KEY, MAIL_FROM_ADDRESS, MAIL_FROM_NAME
├── services/
│   └── email.py               # EmailService class (nuevo)
├── templates/
│   └── email/
│       └── welcome.html       # Template de bienvenida (nuevo)
└── worker.py                  # Agregar task_dispatch_resend_email

tests/
└── test_email.py              # Tests del servicio y tarea (nuevo)
```

**Structure Decision**: Single project. El servicio vive en `app/services/email.py` siguiendo el patrón existente de `app/services/storage.py` y `app/services/instagram.py`. La tarea Celery se agrega a `app/worker.py` junto a las tareas existentes.

## Architecture

```
User → POST /auth/register → Auth Router
                              ↓
                         Create User in DB
                              ↓
                    EmailService.send_welcome_email()
                              ↓
                    celery_app.send_task("task_dispatch_resend_email")
                              ↓ (async, <50ms)
                    Response to User (redirect to login)
                              ↓
                    [Celery Worker picks up task from Redis]
                              ↓
                    task_dispatch_resend_email()
                              ↓
                    resend.Emails.send()
                              ↓
                    Log success/failure with message_id
```

## Data Model Changes

Ninguna. No se persisten emails en base de datos en esta iteración.

## API Changes

Ninguna. No se exponen nuevos endpoints HTTP. El servicio se invoca internamente desde el router de auth.

## Dependencies

| Paquete | Proposito | Aprobado Por |
|---------|-----------|-------------|
| `resend` | SDK oficial de Resend para enviar emails | Ticket TASK-021 |

## Security & Auth Implications

- `RESEND_API_KEY` es un secreto que NUNCA debe estar en código ni logs.
- Se lee exclusivamente via `settings.RESEND_API_KEY` (pydantic-settings desde `.env`).
- El email de bienvenida se envía solo después de confirmar que el usuario fue creado exitosamente en DB.

## Test Strategy

1. **Unit tests** para `EmailService.send_transactional_email()` — mockear `task_dispatch_resend_email.delay()`
2. **Unit tests** para `task_dispatch_resend_email` — mockear `resend.Emails.send()`
3. **Integration test** para el flujo completo: registro → email encolado → (mock) Resend responde
4. **Test de reintentos**: simular error 5xx de Resend y verificar que la tarea reintenta

## Rollout Plan

1. Instalar `resend` con `uv add resend`
2. Agregar env vars a `.env.example`
3. Implementar `EmailService` y tarea Celery
4. Integrar con endpoint de registro
5. Probar localmente con cuenta sandbox de Resend
6. Verificar logs del worker

## Risk Register

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Resend sandbox solo envía a email registrado | Alta | Bajo | Documentar limitación; usar email registrado para pruebas |
| Celery worker no ve el paquete `resend` tras rebuild | Media | Medio | Ejecutar `docker compose build web worker` después de `uv add` |
| Error 4xx de Resend (bad request) causa reintentos infinitos | Baja | Alto | Configurar `autoretry_for` solo para excepciones 5xx/network |
| Dependencia circular entre `email.py` y `worker.py` | Media | Alto | `email.py` importa la tarea por string name, no por import directo |
