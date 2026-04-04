# 📋 SPEC 009: Infraestructura de Túnel (Cloudflare Tunnel en Docker)

**ID del Ticket:** TASK-009  
**Nombre de la Rama:** `feat/009-cloudflare-tunnel`

## Objetivo

Exponer los servicios de API y MinIO a internet de forma segura para que Meta pueda acceder a las imágenes mediante el CNAME instagramjp.

## Criterios de Aceptación

- [ ] El contenedor `cloudflared` debe conectarse a tu túnel existente usando un Tunnel Token.
- [ ] El tráfico que llega a `instagramjp.tudominio.com` debe redirigirse internamente al contenedor de MinIO o de la App según configuración en Cloudflare.

## Tareas

1. Crear la rama `feat/009-cloudflare-tunnel`
2. Agregar servicio `tunnel` al docker-compose.yml
3. Pasar `TUNNEL_TOKEN` por `.env`
4. Ejecutar `tunnel --no-autoupdate run --token ${TUNNEL_TOKEN}`
5. Crear red Docker explícita `app-network`
6. Verificar túnel "Healthy" en Cloudflare Zero Trust

## Dependencia

**SPEC-008 (storage-minio) debe estar implementado primero.**

## Rama: feat/009-cloudflare-tunnel
## Estado: pending