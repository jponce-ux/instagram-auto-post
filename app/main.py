from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, UploadFile, File, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.routes import router as auth_router
from app.auth.instagram import router as instagram_router
from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.media_file import MediaFile
from app.services.storage import storage_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    # Startup: ensure MinIO bucket exists
    await storage_service.ensure_bucket_exists()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(title="Mi App Instagram", version="0.1.0", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(instagram_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/v1/ping")
async def ping():
    return "<p class='text-green-500'>¡Conexión exitosa!</p>"


@app.post("/api/v1/debug/upload")
async def debug_upload(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Debug endpoint to test file upload to MinIO.

    Uploads a file with user-scoped path and creates MediaFile record.
    Returns a presigned URL valid for 10 minutes.

    Requires JWT authentication.
    """
    # Upload file and create MediaFile record
    media_file = await storage_service.upload_file_for_user(file, current_user.id, db)

    # Generate presigned URL
    url = await storage_service.get_presigned_url(media_file.key)

    return {
        "url": url,
        "key": media_file.key,
        "file_id": media_file.id,
        "filename": media_file.original_filename,
        "expires_in": 600,
    }


@app.get("/dashboard/media/{file_id}")
async def get_media_url(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get presigned URL for user's own media file.

    Validates JWT authentication and file ownership before returning
    a short-lived presigned URL (10-minute expiration).

    Args:
        file_id: The media file ID
        current_user: Authenticated user (injected via JWT)
        db: Database session

    Returns:
        JSON with presigned URL and expiration time

    Raises:
        404: File not found
        403: Access denied (not file owner)
        401: Unauthorized (no JWT)
    """
    # Get MediaFile with ownership verification
    media_file = await storage_service.get_media_file(file_id, current_user.id, db)

    if media_file is None:
        raise HTTPException(status_code=404, detail="File not found")

    # Generate presigned URL
    url = await storage_service.get_presigned_url(media_file.key)

    return {"url": url, "expires_in": 600}
