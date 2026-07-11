# Tareas: Sistema de Verificación de Email y Tokens

**Ticket**: TASK-023  
**Especificación**: spec-021-email-verification-tokens  
**Prerequisitos**: SPEC-020 (confirm-email landing) completado

---

## Fase 1: Base de Datos y Modelo

**Propósito**: Agregar campos de verificación al modelo User

- [x] **T001** Crear migración Alembic para `is_verified` y `verified_at` en users
  - `is_verified`: Boolean, default=False, server_default="false"
  - `verified_at`: DateTime nullable
  - **Archivo**: `migrations/versions/add_is_verified_to_users.py`
  - **Entregable**: Migración aplicada exitosamente
  - **Verificación**: `docker compose exec web uv run alembic upgrade head`
  - **Tamaño**: S

- [x] **T002** Actualizar modelo `User` con nuevos campos
  - **Archivo**: `app/models/user.py`
  - **Entregable**: Modelo con `is_verified` y `verified_at`
  - **Verificación**: `from app.models.user import User; print(User.is_verified)`
  - **Tamaño**: XS

---

## Fase 2: Módulo de Tokens

**Propósito**: Crear lógica de generación y validación de tokens de verificación

- [x] **T003** Crear `app/auth/tokens.py` con `create_verification_token()` y `decode_verification_token()`
  - Usar python-jose (ya instalada) con SECRET_KEY existente
  - Expiración: 20 minutos
  - Payload: user_id, email, type="email_verification"
  - **Archivo**: `app/auth/tokens.py`
  - **Entregable**: Funciones de token funcionales
  - **Verificación**: Tests unitarios de creación, decodificación y expiración
  - **Tamaño**: M

---

## Fase 3: Email de Verificación

**Propósito**: Integrar token en el flujo de email

- [x] **T004** Agregar método `EmailService.send_verification_email()` en `app/services/email.py`
  - Genera token con `create_verification_token()`
  - Construye URL: `{BASE_URL}/auth/verify-email/{token}`
  - Renderiza template con enlace de verificación
  - Encola tarea Celery
  - **Archivo**: `app/services/email.py`
  - **Entregable**: Método funcional que envía email con enlace
  - **Verificación**: Mock test que verifica URL en el email
  - **Tamaño**: M

- [x] **T005** Actualizar `POST /auth/register` para enviar email de verificación en lugar de welcome email
  - Llamar a `EmailService.send_verification_email()` en lugar de `send_welcome_email()`
  - **Archivo**: `app/auth/routes.py`
  - **Entregable**: Registro envía email con enlace de verificación
  - **Verificación**: Registrar usuario → verificar email contiene enlace
  - **Tamaño**: XS

---

## Fase 4: Endpoint de Verificación

**Propósito**: Implementar GET /auth/verify-email/{token}

- [x] **T006** Crear endpoint `@router.get("/verify-email/{token}")`
  - Decodifica token con `decode_verification_token()`
  - Si válido: `user.is_verified = True`, `user.verified_at = now()`, redirect → `/auth/login?verified=1`
  - Si expirado: redirect → `/auth/confirm-email?error=expired`
  - Si inválido: redirect → `/auth/confirm-email?error=invalid`
  - **Archivo**: `app/auth/routes.py`
  - **Entregable**: Endpoint funcional con 3 caminos
  - **Verificación**: Tests con token válido, expirado e inválido
  - **Tamaño**: M

---

## Fase 5: Re-envío con Rate Limiting

**Propósito**: Implementar POST /auth/resend-verification-email con protección

- [x] **T007** Crear endpoint `@router.post("/resend-verification-email")`
  - Recibe email via Form
  - Verifica usuario existe y no está verificado
  - Rate limit con Redis: clave `resend:{email}`, TTL 120s
  - Si permitido: genera nuevo token, re-envía email, retorna JSON éxito
  - Si rate limited: retorna JSON error 429
  - Si ya verificado: retorna JSON error 400
  - **Archivo**: `app/auth/routes.py`
  - **Entregable**: Endpoint con rate limiting funcional
  - **Verificación**: Tests de rate limiting y re-envío
  - **Tamaño**: M

---

## Fase 6: Login Requiere Verificación

**Propósito**: Bloquear login para usuarios no verificados

- [x] **T008** Actualizar `POST /auth/login` para verificar `is_verified`
  - Si `not user.is_verified`: redirect → `/auth/confirm-email?error=not_verified`
  - **Archivo**: `app/auth/routes.py`
  - **Entregable**: Login bloqueado para no verificados
  - **Verificación**: Intentar login con usuario no verificado → redirect a confirm-email
  - **Tamaño**: XS

---

## Fase 7: UI Updates

**Propósito**: Agregar botón de re-envío con HTMX a confirm_email.html

- [x] **T009** Actualizar `app/templates/auth/confirm_email.html` con botón de re-envío HTMX
  - Botón secundario: "¿No recibiste el correo? Reenviar"
  - `hx-post="/auth/resend-verification-email"`
  - `hx-target="#resend-status"`
  - `hx-swap="innerHTML"`
  - Div `#resend-status` para mensajes de feedback
  - **Archivo**: `app/templates/auth/confirm_email.html`
  - **Entregable**: Botón funcional con feedback visual
  - **Verificación**: Click en re-envío → mensaje sin recarga
  - **Tamaño**: S

- [x] **T010** Actualizar `app/templates/email/welcome.html` para incluir enlace de verificación
  - Agregar botón/enlace: "Verifica tu email" con URL de verificación
  - **Archivo**: `app/templates/email/welcome.html`
  - **Entregable**: Template con enlace de verificación
  - **Verificación**: Renderizar template → verificar enlace presente
  - **Tamaño**: S

---

## Fase 8: Verificación

**Propósito**: Validar flujo completo

- [x] **T011** Ejecutar suite de tests existente
  - Comando: `uv run pytest tests/ -v`
  - **Entregable**: Todos los tests pasan
  - **Verificación**: 0 fallos
  - **Tamaño**: S

- [x] **T012** Verificación manual E2E [P]
  - Registrar usuario → verificar email con enlace → login exitoso
  - Intentar login sin verificar → redirect a confirm-email
  - Solicitar re-envío → verificar rate limiting
  - Token expirado → mensaje de error
  - **Entregable**: Flujo E2E funcional
  - **Tamaño**: S

---

## Dependencias y Orden de Ejecución

```
T001 (Migración DB)
   ↓
T002 (Modelo User)
   ↓
T003 (Módulo de Tokens)
   ↓
T004 (Email de verificación)
   ↓
T005 (Register → verification email)
   ↓
T006 (Endpoint verificación)
   ↓
T007 (Re-envío con rate limit)
   ↓
T008 (Login requiere verificación)
   ↓
T009 (UI re-envío HTMX)
T010 (Email template)
   ↓
T011 + T012 (Verificación, paralelizables [P])
```

### Oportunidades de Paralelismo

- T009 y T010 son paralelizables `[P]`
- T011 y T012 son paralelizables `[P]`
