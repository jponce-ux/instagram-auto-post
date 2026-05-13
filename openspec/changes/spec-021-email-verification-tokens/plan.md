# Plan Técnico: Sistema de Verificación de Email y Tokens

## Stack Tecnológico

- **Framework**: FastAPI (Python 3.11+)
- **Tokens**: python-jose (ya instalada) — reutilizar `create_access_token` con expiración de 20 min
- **Base de datos**: PostgreSQL + SQLAlchemy async
- **Rate limiting**: Redis (ya disponible como Celery broker)
- **Templates**: Jinja2 + HTMX para re-envío sin recarga
- **Migraciones**: Alembic

## Arquitectura

### Nuevos archivos

```
app/auth/tokens.py              ← NUEVO: Generación y validación de tokens de verificación
migrations/versions/add_is_verified_to_users.py  ← NUEVO: Migración DB
```

### Archivos modificados

```
app/models/user.py              ← is_verified, verified_at
app/auth/routes.py              ← verify-email, resend-verification, login check
app/services/email.py           ← send_verification_email method
app/templates/auth/confirm_email.html  ← botón re-envío HTMX
app/templates/email/welcome.html       ← incluir enlace de verificación
```

### Flujo de datos

```
Registro → Generar token → Email con enlace → Usuario clic → Verificar → is_verified=True → Login
                                    ↓
                            Re-envío (HTMX + Redis rate limit)
```

## 1. Módulo de Tokens (`app/auth/tokens.py`)

```python
from datetime import datetime, timedelta
from jose import jwt, JWTError, ExpiredSignatureError
from app.core.config import settings

VERIFICATION_TOKEN_EXPIRE_MINUTES = 20

def create_verification_token(user_id: int, email: str) -> str:
    """Genera un JWT de verificación con expiración de 20 minutos."""
    expire = datetime.utcnow() + timedelta(minutes=VERIFICATION_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "email": email,
        "type": "email_verification",
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

def decode_verification_token(token: str) -> dict | None:
    """Decodifica y valida el token. Retorna None si expiró o es inválido."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "email_verification":
            return None
        return payload
    except (ExpiredSignatureError, JWTError):
        return None
```

## 2. Modelo User — Nuevos campos

```python
is_verified = Column(Boolean, default=False, nullable=False)
verified_at = Column(DateTime(timezone=True), nullable=True)
```

## 3. EmailService — Nuevo método

```python
@staticmethod
def send_verification_email(to: str, user_name: str, user_id: int) -> None:
    """Genera token y envía email con enlace de verificación."""
    token = create_verification_token(user_id, to)
    verify_url = f"{settings.BASE_URL}/auth/verify-email/{token}"
    # Renderizar template con verify_url y enviar
```

## 4. Endpoints nuevos

### GET /auth/verify-email/{token}
- Decodifica token
- Si válido: `user.is_verified = True`, `user.verified_at = now()`, redirect → `/auth/login?verified=1`
- Si expirado: redirect → `/auth/confirm-email?error=expired`
- Si inválido: redirect → `/auth/confirm-email?error=invalid`

### POST /auth/resend-verification-email
- Recibe email via form
- Verifica que usuario existe y no está verificado
- Rate limit con Redis: clave `resend:{email}`, TTL 120s
- Si permitido: genera nuevo token, re-envía email
- Si rate limited: retorna JSON con error 429

## 5. Login — Verificación requerida

```python
if not user.is_verified:
    return RedirectResponse(url="/auth/confirm-email?error=not_verified", status_code=303)
```

## 6. UI — confirm_email.html con HTMX

```html
<!-- Botón de re-envío con HTMX -->
<button hx-post="/auth/resend-verification-email"
        hx-vals='{"email": "{{ email }}"}'
        hx-target="#resend-status"
        hx-swap="innerHTML">
    ¿No recibiste el correo? Reenviar
</button>
<div id="resend-status"></div>
```

## Rate Limiting con Redis

```python
import redis
from app.core.config import settings

r = redis.Redis.from_url(settings.CELERY_BROKER_URL)

def check_resend_rate_limit(email: str) -> bool:
    key = f"resend:{email}"
    if r.exists(key):
        return False  # Rate limited
    r.setex(key, 120, "1")  # 2 minutos TTL
    return True
```

## Dependencias

- **Nuevas**: `redis` (ya instalada como dependencia de Celery)
- **Existentes**: python-jose, FastAPI, Jinja2, HTMX

## Migración DB

```python
op.add_column("users", sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"))
op.add_column("users", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
```

## Estrategia de Pruebas

- Unit tests: token creation, token expiry, token tampering
- Unit tests: rate limiting logic
- Integration tests: verify endpoint with valid/expired/invalid tokens
- Integration tests: resend endpoint with rate limiting
- Integration tests: login blocked for unverified users

## Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Usuarios existentes no pueden login | Alta | Alto | Migración: setear `is_verified=True` para usuarios existentes |
| Redis no disponible para rate limit | Baja | Medio | Fallback: log warning, permitir re-envío |
| Token expira antes de que usuario abra email | Media | Bajo | Mensaje claro en UI para solicitar nuevo token |

## Rollout

1. Migración DB (is_verified default False para nuevos, True para existentes)
2. Módulo de tokens
3. EmailService con verification email
4. Endpoint de verificación
5. Endpoint de re-envío con rate limiting
6. Login requiere verificación
7. UI updates (confirm_email.html + welcome email template)
8. Tests + Docker verification
