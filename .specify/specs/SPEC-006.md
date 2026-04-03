# 📋 SPEC 006: Sistema de Autenticación Pro (Argon2 + JWT + Cookies)

**ID del Ticket:** TASK-006  
**Nombre de la Rama:** `feat/006-auth-argon2-jwt`

## Objetivo

Implementar el registro e inicio de sesión de usuarios con máxima seguridad.

---

## 🛠️ Paso 1: Gestión de Rama (Obligatorio)

Una vez mergeado el ticket anterior en main, crea la nueva rama de trabajo:

```bash
git checkout main
git pull origin main
git checkout -b feat/006-auth-argon2-jwt
```

---

## 📝 Criterios de Aceptación

- [ ] Contraseñas hasheadas con Argon2 ID.
- [ ] JWT con expiración de 60 minutos entregado vía HTTP-Only Cookie.

---

## 🛠️ Lista de Tareas (Tasks)

- [ ] Crear la rama `feat/006-auth-argon2-jwt` desde la rama principal.
- [ ] Crear el modelo `User` en `app/models/user.py`.
- [ ] Implementar `app/auth/security.py`: funciones de hash (Argon2) y creación de tokens (JWT).
- [ ] Crear el endpoint `POST /auth/register` con validación de email único.
- [ ] Crear el endpoint `POST /auth/login` que valide y emita la cookie `access_token`.
- [ ] Implementar la dependencia `get_current_user` para proteger rutas.
- [ ] Crear una migración de Alembic para la tabla de usuarios: `uv run alembic revision --autogenerate -m "create_user_table"`.

---

## 📁 Archivos a Crear

### `app/models/user.py`
```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.models.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### `app/auth/security.py`
```python
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=60))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
```

### `app/auth/dependencies.py`
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.config import settings
from app.models.user import User

security = HTTPBearer()

async def get_current_user(
    token: str = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    try:
        payload = jwt.decode(token.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user
```

---

## ✅ Verificación

1. Registrar un usuario vía `POST /auth/register`.
2. Iniciar sesión vía `POST /auth/login` y verificar que la cookie `access_token` se establece.
3. Acceder a una ruta protegida usando el token.