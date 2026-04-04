# Design: Cloudflare Tunnel

## Technical Approach

Add a Cloudflared sidecar container to the existing Docker Compose stack to expose MinIO and FastAPI services through Cloudflare Tunnel. This eliminates the need for public IPs while providing secure HTTPS endpoints for Meta's Instagram Graph API to access media content.

The implementation creates an explicit Docker bridge network (`app-network`) for inter-service DNS resolution, attaches all services to it, and runs cloudflared with tunnel token authentication.

## Architecture Decisions

### Decision: Network Architecture

| Choice | Alternatives | Rationale |
|--------|-------------|-----------|
| Explicit `app-network` bridge | Default bridge network | Service names resolve to IPs; cloudflared can reference `web:8000` and `minio:9000` by hostname |
| Internal network only | Port mapping to host | Security: No ports exposed on host; all traffic flows through encrypted tunnel |

### Decision: Tunnel Configuration Location

| Choice | Alternatives | Rationale |
|--------|-------------|-----------|
| Cloudflare Dashboard only | YAML config in repo | Tunnel routes change rarely; keeping config in dashboard avoids secrets in git |
| Environment token only | Config file mount | Minimal configuration; token is the only required secret |

### Decision: Container Image

| Choice | Alternatives | Rationale |
|--------|-------------|-----------|
| `cloudflare/cloudflared:latest` | Self-built image | Official image maintained by Cloudflare; includes auto-update |

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      Cloudflare Edge                         │
│         instagramjp.domain.com  api.domain.com              │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTPS/WARP
┌─────────────────────────┴───────────────────────────────────┐
│                    cloudflared Container                     │
│              (token: ${TUNNEL_TOKEN})                        │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
        http://web:8000              http://minio:9000
               │                              │
        ┌──────┴──────┐              ┌────────┴────────┐
        │ FastAPI App │              │  MinIO Server   │
        └─────────────┘              └─────────────────┘
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `docker-compose.yml` | Modify | Add `tunnel` service, create `app-network`, attach all services to network |
| `.env.example` | Modify | Add `TUNNEL_TOKEN` placeholder |
| `app/core/config.py` | Modify | Add `TUNNEL_TOKEN` field (optional, for reference) |

## Interfaces / Contracts

### Environment Variables

```python
# .env.example additions
TUNNEL_TOKEN=your-tunnel-token-from-cloudflare-dashboard
```

### Docker Compose Network

```yaml
networks:
  app-network:
    driver: bridge
```

### Cloudflared Service

```yaml
tunnel:
  image: cloudflare/cloudflared:latest
  command: tunnel --no-autoupdate run --token ${TUNNEL_TOKEN}
  networks:
    - app-network
  depends_on:
    web:
      condition: service_started
    minio:
      condition: service_healthy
  restart: unless-stopped
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Integration | Tunnel connectivity | `docker compose ps` shows tunnel healthy; Cloudflare dashboard shows "Healthy" status |
| Integration | Public URL accessibility | `curl https://api.domain.com/api/v1/ping` from external network |
| E2E | Meta API media fetch | Upload image via app, get presigned URL, verify accessible from internet |

## Migration / Rollout

1. **Prerequisite**: Ensure SPEC-008 (storage-minio) is deployed and healthy
2. **Pre-deployment**: Obtain tunnel token from Cloudflare Zero Trust dashboard
3. **Deployment**: Add `TUNNEL_TOKEN` to `.env`, run `docker compose up -d`
4. **Verification**: Check tunnel health in Cloudflare dashboard
5. **DNS**: Configure public hostnames in Cloudflare dashboard:
   - `instagramjp.domain.com` → `http://minio:9000`
   - `api.domain.com` → `http://web:8000`

**Rollback**: Remove tunnel service from docker-compose.yml, remove TUNNEL_TOKEN from environment. Tunnel remains in Cloudflare dashboard (inactive).

## Open Questions

- [ ] What are the actual domain names to configure? (instagramjp.domain.com is placeholder)
- [ ] Should we expose MinIO console port (9001) separately or only S3 API (9000)?
