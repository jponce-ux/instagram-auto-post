# Plan: Tailwind CLI en Contenedor Docker

## Enfoque

Descargar el binario standalone de Tailwind CLI durante el build de Docker, configurarlo para escanear los templates Jinja2, y generar el CSS estatico que se servire junto con la aplicacion.

## Contexto Tecnico

**Stack detectado**:
- Lenguaje: Python 3.11
- Framework: FastAPI
- Motor de templates: Jinja2
- CSS actual: Tailwind CDN (roto para templates dinamicos)
- Docker: python:3.11-slim base

**Archivos relevantes**:
- `Dockerfile` — necesita modificacion para agregar Tailwind CLI
- `app/templates/base.html` — tiene el script CDN
- `app/templates/` — contiene los templates Jinja2 a escanear
- `app/static/` — directorio para CSS estatico

## Arquitectura de la Solucion

```
Contenedor Docker (web):
  ├── Descarga tailwindcss-linux-x64 (standalone CLI)
  ├── Crea tailwind.config.js (apunta a templates/)
  ├── Crea src/input.css (@import tailwindcss)
  ├── Ejecuta: tailwindcss -i ./src/input.css -o ./app/static/css/app.css
  ├── Modifica base.html para usar el CSS local en lugar del CDN
  └── Inicia FastAPI
```

## Archivos Afectados

| Archivo | Cambio |
|---------|--------|
| `Dockerfile` | Agregar descarga de Tailwind CLI, creacion de config, comando de build |
| `app/templates/base.html` | Reemplazar script CDN con link a CSS local |
| `app/templates/` (nuevos) | `tailwind.config.js`, `src/input.css` |

## Evaluacion de Riesgo

- **Riesgo bajo**: Tailwind CLI es un binario standalone sin dependencias adicionales
- **Sin impacto en runtime**: El CSS se genera durante build, no hay overhead en ejecucion
- **Reversion simple**: Si algo falla, se puede volver al CDN modificando una linea en base.html

## Estructura de Archivos Resultante

```
app/
├── static/
│   └── css/
│       └── app.css          # CSS generado por Tailwind CLI
├── src/
│   └── input.css           # Entry point para Tailwind
└── templates/
    └── tailwind.config.js  # Config de Tailwind CLI
```

## Dependencias Externas

| Recurso | Uso | Fuente |
|---------|-----|--------|
| Tailwind CSS CLI | Binario standalone para generar CSS | github.com/tailwindlabs/tailwindcss/releases |

**Nota**: No se usa npm/node. El binario se descarga directamente en el contenedor.
