# 📋 SPEC 001: Scaffolding e Inicialización del Proyecto

**ID del Ticket:** TASK-001  
**Nombre de la Rama:** `feat/001-scaffolding-init`

## Objetivo

Inicializar el repositorio Git, la estructura de carpetas vacía y el entorno virtual ultrarrápido con UV.

---

## 📝 Criterios de Aceptación

- [x] El proyecto debe usar `uv` como gestor de paquetes (sin pip).
- [x] El archivo `pyproject.toml` debe estar creado y configurado.
- [x] Las carpetas estructurales deben existir (aunque contengan archivos `.gitkeep` temporales).
- [x] El historial de Git debe comenzar de manera limpia en esta rama.

---

## 🛠️ Lista de Tareas (Tasks)

- [x] Crear la rama `feat/001-scaffolding-init` desde la rama principal.
- [x] Crear la carpeta raíz del proyecto `mi-app-instagram` e inicializar el repositorio Git con `git init`.
- [x] Crear la estructura de carpetas completa según el diseño acordado:
  - `app/`
  - `app/auth/`
  - `app/core/`
  - `app/models/`
  - `app/services/`
  - `app/static/css/`
  - `app/static/js/`
  - `app/templates/components/`
- [x] Agregar archivos `.gitkeep` en las carpetas vacías para que Git pueda rastrearlas.
- [x] Ejecutar `uv init --app` en la raíz para generar el archivo `pyproject.toml`.
- [x] Crear un archivo `.gitignore` adecuado para Python (excluyendo `.venv`, `__pycache__`, `.env`, etc.).
- [x] Hacer el primer commit de la estructura y abrir el PR a la rama principal (ej. `main` o `develop`).

---

## 📁 Estructura de Carpetas Esperada

```
mi-app-instagram/
├── app/
│   ├── auth/
│   ├── core/
│   ├── models/
│   ├── services/
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   └── templates/
│       └── components/
├── .gitignore
├── pyproject.toml
└── README.md
```
