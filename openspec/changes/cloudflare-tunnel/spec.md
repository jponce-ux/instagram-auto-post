# SPEC 009: Infraestructura de Túnel (Cloudflare Tunnel en Docker)

**ID del Ticket:** TASK-009  
**Nombre de la Rama:** `feat/009-cloudflare-tunnel`

## Objetivo

Exponer los servicios de API y MinIO a internet de forma segura para que Meta pueda acceder a las imágenes mediante el CNAME instagramjp.

---

## 🛠️ Paso 1: Gestión de Rama (Obligatorio)

```bash
git checkout main
git pull origin main
git checkout -b feat/009-cloudflare-tunnel
```

---

## 📝 Criterios de Aceptación

- [ ] El contenedor `cloudflared` debe conectarse a tu túnel existente usando un Tunnel Token.
- [ ] El tráfico que llega a `instagramjp.tudominio.com` debe redirigirse internamente al contenedor de MinIO o de la App según configuración en Cloudflare.

---

## 🛠️ Lista de Tareas (Tasks)

- [ ] Crear la rama `feat/009-cloudflare-tunnel` desde la rama principal.
- [ ] **Docker**: Agregar el servicio `tunnel` al `docker-compose.yml` usando la imagen `cloudflare/cloudflared:latest`.
- [ ] **Configuración**: Pasar el `TUNNEL_TOKEN` a través del archivo `.env` para no exponerlo en el código.
- [ ] **Comando Docker**: El contenedor debe ejecutar: `tunnel --no-autoupdate run --token ${TUNNEL_TOKEN}`.
- [ ] **Red Docker**: Crear una red explícita para que los servicios se comuniquen por nombre.
- [ ] **Verificación**: Comprobar que desde el panel de Cloudflare (Zero Trust) el túnel aparece como "Healthy" y apunta correctamente al servicio MinIO (ej: `http://minio:9000`) y a la API (ej: `http://web:8000`).

---

## 📁 Archivos a Modificar

### `docker-compose.yml`

```yaml
services:
  # ... servicios existentes (db, web, minio) ...
  
  tunnel:
    image: cloudflare/cloudflared:latest
    container_name: mi-app-instagram-tunnel
    restart: unless-stopped
    env_file:
      - .env
    command: tunnel --no-autoupdate run --token ${TUNNEL_TOKEN}
    networks:
      - app-network
    depends_on:
      - web
      - minio

networks:
  app-network:
    driver: bridge
```

### `.env.example`

```bash
# ... variables existentes ...

# Cloudflare Tunnel
TUNNEL_TOKEN=your-cloudflare-tunnel-token-here
```

### `app/core/config.py`

```python
class Settings(BaseSettings):
    # ... campos existentes ...
    
    # Cloudflare Tunnel (opcional, para referencias)
    TUNNEL_TOKEN: str = ""
```

---

## ⚠️ Dependencia

**Este cambio requiere que SPEC-008 (storage-minio) esté implementado primero.**

MinIO debe estar corriendo en Docker antes de configurar el túnel para exponerlo.

---

## ✅ Verificación

1. Ejecutar `docker compose up` y verificar que todos los servicios levanten correctamente.
2. Acceder al panel de Cloudflare Zero Trust y verificar el estado del túnel.
3. Configurar los servicios públicos en Cloudflare:
   - `instagramjp.tudominio.com` → `http://minio:9000` (para imágenes)
   - `api.tudominio.com` → `http://web:8000` (para API)
4. Verificar que la API de Meta puede descargar imágenes desde la URL pública del túnel.

---

## 🔗 Referencias

- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [cloudflared Docker Image](https://hub.docker.com/r/cloudflare/cloudflared)