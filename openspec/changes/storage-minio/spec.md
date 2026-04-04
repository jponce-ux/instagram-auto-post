# 📋 SPEC 008: Almacenamiento de Objetos con MinIO (S3-Compatible)

**ID del Ticket:** TASK-008  
**Nombre de la Rama:** `feat/008-storage-minio`

## Objetivo

Configurar MinIO en Docker y crear un servicio asíncrono para subir imágenes y generar URLs públicas para la API de Meta.

---

## 🛠️ Paso 1: Gestión de Rama (Obligatorio)

Antes de comenzar, asegúrate de tener tu rama main limpia y actualizada:

```bash
git checkout main
git pull origin main
git checkout -b feat/008-storage-minio
```

---

## 📝 Criterios de Aceptación

- [ ] El servicio de MinIO debe levantarse automáticamente con `docker compose`.
- [ ] Se debe crear automáticamente un bucket llamado `instagram-uploads`.
- [ ] El backend debe poder subir archivos de forma asíncrona.
- [ ] El servicio debe generar URLs firmadas (Presigned URLs) que sean accesibles por la API de Meta para que Instagram pueda descargar la imagen.

---

## 🛠️ Lista de Tareas (Tasks)

- [ ] Crear la rama `feat/008-storage-minio` desde la rama principal.
- [ ] **Infraestructura (Docker)**: Modificar `docker-compose.yml` para añadir el servicio `minio` (puertos 9000 para API y 9001 para consola).
- [ ] Añadir un volumen persistente para MinIO: `minio_data:/data`.
- [ ] Configurar variables de entorno: `MINIO_ROOT_USER` y `MINIO_ROOT_PASSWORD`.
- [ ] **Dependencias**: Ejecutar `uv add aioboto3` (el cliente asíncrono más robusto para S3/MinIO).
- [ ] **Configuración (`app/core/config.py`)**: Añadir campos para `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` y `MINIO_BUCKET_NAME`.
- [ ] **Servicio de Almacenamiento (`app/services/storage.py`)**: Implementar una clase `StorageService`.
- [ ] Implementar método `upload_file(file_data, file_name)`: Sube el buffer de la imagen a MinIO.
- [ ] Implementar método `get_public_url(file_name)`: Genera una URL con expiración (ej. 1 hora) para que la API de Meta la consuma.
- [ ] **Integración con FastAPI**: Crear un endpoint de prueba `POST /api/v1/debug/upload` que reciba una imagen y devuelva la URL de MinIO para verificar que funciona.

---

## 📁 Archivos a Crear/Modificar

### `docker-compose.yml` (modificar)

```yaml
services:
  # ... servicios existentes ...
  
  minio:
    image: minio/minio:latest
    container_name: mi-app-instagram-minio
    ports:
      - "9000:9000"  # API
      - "9001:9001"  # Console
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

volumes:
  # ... volúmenes existentes ...
  minio_data:
```

### `.env.example` (modificar)

```bash
# ... variables existentes ...

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=instagram-uploads
```

### `app/core/config.py` (modificar)

```python
class Settings(BaseSettings):
    # ... campos existentes ...
    
    # MinIO
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET_NAME: str = "instagram-uploads"
```

### `app/services/storage.py` (crear)

```python
import aioboto3
from io import BytesIO
from app.core.config import settings


class StorageService:
    def __init__(self):
        self.endpoint_url = settings.MINIO_ENDPOINT
        self.access_key = settings.MINIO_ACCESS_KEY
        self.secret_key = settings.MINIO_SECRET_KEY
        self.bucket_name = settings.MINIO_BUCKET_NAME

    async def upload_file(self, file_data: bytes, file_name: str, content_type: str = "image/jpeg") -> str:
        """Upload a file to MinIO and return the object key."""
        session = aioboto3.Session()
        async with session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        ) as client:
            # Ensure bucket exists
            try:
                await client.create_bucket(Bucket=self.bucket_name)
            except client.exceptions.BucketAlreadyOwnedByYou:
                pass
            except client.exceptions.BucketAlreadyExists:
                pass

            # Upload file
            await client.put_object(
                Bucket=self.bucket_name,
                Key=file_name,
                Body=file_data,
                ContentType=content_type,
            )

        return file_name

    async def get_public_url(self, file_name: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for the file."""
        session = aioboto3.Session()
        async with session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        ) as client:
            url = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": file_name},
                ExpiresIn=expires_in,
            )
        return url


storage_service = StorageService()
```

### `app/api/debug.py` (crear)

```python
from fastapi import APIRouter, UploadFile, File, Depends
from app.services.storage import storage_service

router = APIRouter(prefix="/api/v1/debug", tags=["debug"])


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file to MinIO and return the public URL."""
    file_data = await file.read()
    file_name = f"uploads/{file.filename}"
    
    await storage_service.upload_file(file_data, file_name, file.content_type)
    url = await storage_service.get_public_url(file_name)
    
    return {"url": url, "file_name": file_name}
```

---

## ✅ Verificación

1. Ejecutar `docker compose up` y verificar que MinIO levanta correctamente.
2. Acceder a `http://localhost:9001` para verificar la consola de MinIO.
3. Hacer un `POST /api/v1/debug/upload` con una imagen y verificar que devuelve una URL accesible.
4. Verificar que la URL generada es accesible públicamente.