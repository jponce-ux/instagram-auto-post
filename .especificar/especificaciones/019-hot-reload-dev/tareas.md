# Tareas: Entorno de Desarrollo con Hot-Reload (DX)

**Estado**: En Progreso
**Progreso**: 4/5 tareas
**Fase Actual**: Fase 2: Verificacion

## Fase 1: Implementacion

- [x] T001 [P] Crear archivo `docker-compose.override.yml` con bind mounts selectivos para `templates/` y subpaquetes Python (`auth/`, `dashboard/`, `webhooks/`, `core/`)
- [x] T002 [P] Configurar command `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` en servicio web
- [x] T003 [P] Agregar variables de entorno `ENV=development` y `PYTHONDONTWRITEBYTECODE=1` al servicio web
- [x] T004 [P] Montar pyproject.toml y uv.lock como volumenes de solo lectura en servicio web

## Fase 2: Verificacion

- [ ] T005 [P] Probar flujo de hot-reload: modificar archivo .py y verificar reinicio de Uvicorn en logs

---

## Dependencias de Fases

**Fase 1 → Fase 2**: Fase 1 debe completarse antes de comenzar Fase 2

## Archivos a Crear/Modificar

| Tarea | Archivo | Accion |
|-------|---------|--------|
| T001-T004 | `docker-compose.override.yml` | CREAR |
| T005 | Ninguno | VERIFICACION MANUAL |
