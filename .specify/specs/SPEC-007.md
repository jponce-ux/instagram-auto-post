# 📋 SPEC 007: Integración con Meta SDK (OAuth & Long-Lived Tokens)

**ID del Ticket:** TASK-007  
**Nombre de la Rama:** `feat/007-meta-oauth-flow`

## Objetivo

Permitir que el usuario vincule su cuenta de Instagram Business.

---

## 🛠️ Paso 1: Gestión de Rama (Obligatorio)

Crea la rama para la integración externa:

```bash
git checkout main
git pull origin main
git checkout -b feat/007-meta-oauth-flow
```

---

## 📝 Criterios de Aceptación

- [ ] Flujo completo: Code -> Short Token -> Long-Lived Token (60 días).
- [ ] Persistencia del token de 60 días cifrado en la DB.

---

## 🛠️ Lista de Tareas (Tasks)

- [ ] Crear la rama `feat/007-meta-oauth-flow` desde la rama principal.
- [ ] Crear el modelo `InstagramAccount` en `app/models/instagram.py`.
- [ ] Desarrollar `app/services/instagram.py` usando HTTPX asíncrono para llamadas a Meta.
- [ ] Implementar endpoint `/auth/instagram/login` (Redirección a Facebook).
- [ ] Implementar endpoint `/auth/instagram/callback` (Intercambio de tokens y guardado en DB).
- [ ] Generar migración de Alembic para la nueva tabla: `uv run alembic revision --autogenerate -m "add_instagram_account"`.

---

## 📁 Archivos a Crear

### `app/models/instagram.py`
```python
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base

class InstagramAccount(Base):
    __tablename__ = "instagram_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    instagram_account_id = Column(String, unique=True, nullable=False)
    access_token = Column(String, nullable=False)  # Debe cifrarse en producción
    token_expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="instagram_accounts")
```

### `app/services/instagram.py`
```python
import httpx
from app.core.config import settings

META_API_BASE = "https://graph.facebook.com/v18.0"

async def exchange_short_token(code: str, redirect_uri: str) -> dict:
    """Intercambia el código de autorización por un token de acceso de corta duración."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{META_API_BASE}/oauth/access_token",
            params={
                "client_id": settings.META_APP_ID,
                "client_secret": settings.META_APP_SECRET,
                "redirect_uri": redirect_uri,
                "code": code,
            },
        )
        response.raise_for_status()
        return response.json()

async def get_long_lived_token(short_token: str) -> dict:
    """Intercambia un token de corta duración por uno de larga duración (60 días)."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{META_API_BASE}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": settings.META_APP_ID,
                "client_secret": settings.META_APP_SECRET,
                "fb_exchange_token": short_token,
            },
        )
        response.raise_for_status()
        return response.json()
```

### `app/auth/instagram.py`
```python
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.services.instagram import exchange_short_token, get_long_lived_token

router = APIRouter(prefix="/auth/instagram", tags=["instagram"])

@router.get("/login")
async def instagram_login():
    """Redirige al usuario a la página de autorización de Facebook."""
    redirect_uri = f"{settings.BASE_URL}/auth/instagram/callback"
    auth_url = (
        f"https://www.facebook.com/v18.0/dialog/oauth"
        f"?client_id={settings.META_APP_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=instagram_basic,instagram_manage_comments"
    )
    return RedirectResponse(url=auth_url)

@router.get("/callback")
async def instagram_callback(
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Intercambia el código por tokens y los guarda en la DB."""
    redirect_uri = f"{settings.BASE_URL}/auth/instagram/callback"
    
    # Intercambiar código por token de corta duración
    short_token_data = await exchange_short_token(code, redirect_uri)
    short_token = short_token_data["access_token"]
    
    # Intercambiar por token de larga duración
    long_token_data = await get_long_lived_token(short_token)
    
    # TODO: Guardar en DB con cifrado
    # TODO: Vincular al usuario actual
    
    return {"status": "success", "token_type": long_token_data.get("token_type")}
```

---

## 🔐 Variables de Entorno Adicionales

Agregar al `.env`:
```bash
META_APP_ID=your_facebook_app_id
META_APP_SECRET=your_facebook_app_secret
BASE_URL=http://localhost:8000
```

---

## ✅ Verificación

1. Acceder a `GET /auth/instagram/login` y completar el flujo en Facebook.
2. Verificar que el token de larga duración se intercambia correctamente.
3. Confirmar que el token se guarda en la base de datos (cifrado).