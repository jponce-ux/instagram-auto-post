from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.auth.routes import router as auth_router
from app.auth.instagram import router as instagram_router
from app.dashboard.routes import router as dashboard_router
from app.services.storage import storage_service
from app.worker import debug_task
import uuid


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
app.include_router(dashboard_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/v1/ping")
async def ping():
    return "<p class='text-green-500'>¡Conexión exitosa!</p>"


@app.post("/api/v1/debug/upload")
async def debug_upload(file: UploadFile = File(...)):
    """
    Debug endpoint to test file upload to MinIO.

    Uploads a file and returns a presigned URL.
    """
    # Generate unique key with original extension
    file_ext = file.filename.split(".")[-1] if "." in file.filename else "bin"
    key = f"uploads/{uuid.uuid4()}.{file_ext}"

    # Upload and get presigned URL
    await storage_service.upload_file(file, key)
    url = await storage_service.get_presigned_url(key)

    return {"url": url, "key": key, "filename": file.filename}


@app.post("/api/v1/debug/task")
async def trigger_debug_task():
    """
    Debug endpoint to dispatch Celery task.

    Queues a debug_task and returns immediately with task ID.
    """
    task = debug_task.delay(name="test")
    return {"task_id": task.id, "status": "queued"}
