from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.auth.routes import router as auth_router

app = FastAPI(title="Mi App Instagram", version="0.1.0")

app.include_router(auth_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/v1/ping")
async def ping():
    return "<p class='text-green-500'>¡Conexión exitosa!</p>"
