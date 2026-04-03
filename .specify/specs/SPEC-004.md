# 📋 SPEC 004: Hola Mundo Full-Stack (FastAPI + Jinja2 + HTMX)

**ID del Ticket:** TASK-004  
**Nombre de la Rama:** `feat/004-hello-world-htmx`

## Objetivo

Unir el backend y el frontend por primera vez para validar que las rutas y el motor de plantillas funcionan de forma asíncrona.

---

## 📝 Criterios de Aceptación

- [ ] El usuario debe poder entrar a `localhost:8000` y ver una página HTML procesada por Jinja2.
- [ ] Debe existir un botón que use HTMX para consultar un endpoint de FastAPI y actualizar una parte de la pantalla sin recargar la página.

---

## 🛠️ Lista de Tareas (Tasks)

- [ ] Crear la rama `feat/004-hello-world-htmx` desde la rama principal.
- [ ] En `app/main.py`, inicializar la app de FastAPI y montar la carpeta de archivos estáticos (`app/static`).
- [ ] Descargar el archivo `htmx.min.js` y colocarlo en `app/static/js/`.
- [ ] Crear la plantilla base `app/templates/base.html` incluyendo la estructura HTML5 y la etiqueta `<script>` apuntando a HTMX.
- [ ] Crear `app/templates/index.html` que herede de la base, mostrando un título y un botón interactivo de HTMX.
- [ ] Crear un endpoint `/` en FastAPI que devuelva el template renderizado.
- [ ] Crear un endpoint `/api/v1/ping` que devuelva un fragmento de HTML (ej. `<p class="text-green-500">¡Conexión exitosa!</p>`) para ser consumido por el botón de HTMX.

---

## 📁 Archivos a Crear

### `app/main.py`
```python
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/v1/ping")
async def ping():
    return "<p class='text-green-500'>¡Conexión exitosa!</p>"
```

### `app/templates/base.html`
```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Mi App{% endblock %}</title>
    <script src="/static/js/htmx.min.js"></script>
</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>
```

### `app/templates/index.html`
```html
{% extends "base.html" %}

{% block title %}Hola Mundo{% endblock %}

{% block content %}
<h1>¡Bienvenido a FastAPI + HTMX!</h1>
<button hx-get="/api/v1/ping" hx-target="#result">
    Probar Conexión
</button>
<div id="result"></div>
{% endblock %}
```

---

## ✅ Verificación

1. Levantar la aplicación: `docker compose up`
2. Visitar `http://localhost:8000`
3. Hacer clic en el botón "Probar Conexión"
4. Verificar que aparece el mensaje de éxito sin recargar la página
