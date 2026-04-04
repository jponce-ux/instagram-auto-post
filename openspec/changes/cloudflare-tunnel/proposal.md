# Proposal: Cloudflare Tunnel

## Intent

Meta's Instagram Graph API requires publicly accessible URLs for media content. The application and MinIO storage are currently only accessible locally (localhost). This change exposes both services to the internet securely via Cloudflare Tunnel, eliminating the need for public IPs, port forwarding, or firewall configuration.

## Scope

### In Scope
- Cloudflared container in Docker Compose connecting to existing Cloudflare tunnel
- Explicit Docker network (`app-network`) for inter-service communication
- Tunnel token management via environment variables
- Configuration of public hostname mapping (instagramjp.domain.com → MinIO, api.domain.com → FastAPI)

### Out of Scope
- Cloudflare account setup and tunnel creation (assumes existing tunnel)
- DNS configuration (assumes CNAME already configured in Cloudflare)
- SSL/TLS certificate management (handled by Cloudflare)
- Production hardening (rate limiting, DDoS protection)

## Capabilities

> No existing capability specs in `openspec/specs/`. This change modifies infrastructure only.

### New Capabilities
None - purely infrastructure change.

### Modified Capabilities
None - no spec-level behavior changes.

## Approach

1. **Docker Network**: Create explicit `app-network` bridge network so services can communicate by name (currently using default bridge)
2. **Cloudflared Service**: Add `cloudflare/cloudflared:latest` container with tunnel token from environment
3. **Network Attachment**: Attach db, web, minio, and tunnel services to `app-network`
4. **Dependency Chain**: tunnel depends on web and minio being healthy
5. **Public Hostname Mapping**: Configure in Cloudflare dashboard (not in code): `instagramjp.domain.com` → `http://minio:9000`, `api.domain.com` → `http://web:8000`

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `docker-compose.yml` | Modified | Add tunnel service, app-network, attach all services |
| `.env.example` | Modified | Add TUNNEL_TOKEN variable |
| `app/core/config.py` | Modified | Add TUNNEL_TOKEN field (optional, for reference) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Tunnel token exposure | Medium | Store in .env (gitignored), never commit |
| MinIO not implemented | High | **BLOCKER**: Requires SPEC-008 (storage-minio) first |
| Network connectivity issues | Low | Use explicit network with bridge driver, service names as hostnames |
| Tunnel disconnection | Low | Cloudflared has built-in reconnection, container restart policy |

## Rollback Plan

1. Remove tunnel service from docker-compose.yml
2. Remove app-network definition (or keep for future use)
3. Remove TUNNEL_TOKEN from .env.example
4. Remove TUNNEL_TOKEN from config.py
5. Tunnel remains in Cloudflare dashboard (inactive) — can be deleted manually if needed

## Dependencies

- **SPEC-008 (storage-minio) MUST be implemented first**
- Existing Cloudflare account with tunnel already created
- Tunnel token available from Cloudflare Zero Trust dashboard

## Success Criteria

- [ ] `docker compose up` starts tunnel service successfully
- [ ] Tunnel status shows "Healthy" in Cloudflare Zero Trust dashboard
- [ ] Public URL `instagramjp.domain.com` serves MinIO console or presigned URLs
- [ ] Meta API can fetch images from public URLs (verified via curl from external network)
- [ ] No ports exposed on host machine (security: all traffic through tunnel)