# 📋 SPEC 005: Capa de Persistencia Asíncrona (PostgreSQL + SQLAlchemy + Alembic)

**ID del Ticket:** TASK-005  
**Nombre de la Rama:** `feat/005-db-async-setup`

## Objetivo

Configurar la conexión a la base de datos y preparar las migraciones automáticas.

---

## 🛠️ Paso 1: Gestión de Rama (Obligatorio)

Antes de escribir cualquier línea de código, asegúrate de estar en main actualizado y crea la rama específica:

```bash
git checkout main
git pull origin main
git checkout -b feat/005-db-async-setup
```

---

## 📝 Criterios de Aceptación

- [ ] Uso de SQLAlchemy 2.0 con asyncio.
- [ ] Alembic configurado para detectar cambios en `app/models/`.

---

## 🛠️ Lista de Tareas (Tasks)

- [ ] Crear la rama `feat/005-db-async-setup` desde la rama principal.
- [ ] Crear `app/core/database.py` con el `AsyncSessionLocal` y el motor `create_async_engine`.
- [ ] Configurar el modelo base en `app/models/base.py` usando `DeclarativeBase`.
- [ ] Inicializar Alembic: `uv run alembic init -t async migrations`.
- [ ] Configurar `migrations/env.py` para que `target_metadata` apunte a tu `Base` de modelos.
- [ ] Crear la revisión inicial: `uv run alembic revision --message="init_db"`.

---

## 📁 Archivos a Crear

### `app/core/database.py`
```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

### `app/models/base.py`
```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

### `app/core/config.py`
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    DEBUG: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## ✅ Verificación

1. Ejecutar `docker compose up` y verificar que la conexión a PostgreSQL funcione.
2. Correr `uv run alembic current` para confirmar que Alembic está configurado correctamente.