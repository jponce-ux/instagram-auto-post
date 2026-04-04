# Tasks: Cloudflare Tunnel Infrastructure

> **BLOCKER**: SPEC-008 (storage-minio) must be implemented first. MinIO service required.

## Phase 0: Git Branch

- [ ] 0.1 `git checkout main`
- [ ] 0.2 `git pull origin main`
- [ ] 0.3 `git checkout -b feat/009-cloudflare-tunnel`

## Phase 1: Foundation - Docker Network & Environment

- [ ] 1.1 Add `app-network` bridge network to `docker-compose.yml` for inter-service DNS resolution
- [ ] 1.2 Attach existing `db` and `web` services to `app-network`
- [ ] 1.3 Add `TUNNEL_TOKEN=` placeholder to `.env.example` with documentation comment

## Phase 2: Core Implementation - Cloudflared Service

- [ ] 2.1 Add `tunnel` service to `docker-compose.yml` using `cloudflare/cloudflared:latest`
- [ ] 2.2 Configure tunnel with command: `tunnel --no-autoupdate run --token ${TUNNEL_TOKEN}`
- [ ] 2.3 Attach `tunnel` service to `app-network`
- [ ] 2.4 Add dependency chain: `tunnel` depends on `web` and `minio` with `service_healthy` condition
- [ ] 2.5 Add restart policy `unless-stopped` to tunnel service

## Phase 3: Verification

- [ ] 3.1 Run `docker compose up --build` and verify no errors in tunnel logs
- [ ] 3.2 Check Cloudflare Zero Trust dashboard → Tunnels → Status shows "Healthy"
- [ ] 3.3 Configure public hostname in Cloudflare dashboard: `instagramjp.domain.com` → `http://minio:9000`
- [ ] 3.4 Configure public hostname in Cloudflare dashboard: `api.domain.com` → `http://web:8000`
- [ ] 3.5 Test: `curl -I https://instagramjp.domain.com` from external network returns 200/302
- [ ] 3.6 Test: Meta API can fetch presigned image URLs from public domain
- [ ] 3.7 Verify no host ports exposed (except 5432 for db) - security check

## Phase 4: Documentation

- [ ] 4.1 Add tunnel setup instructions to README.md (environment variables, Cloudflare dashboard steps)

## Phase 5: Git Commit

- [ ] 5.1 `git add .`
- [ ] 5.2 `git commit -m "feat(009): add Cloudflare Tunnel for public access to API and MinIO"`
- [ ] 5.3 `git push origin feat/009-cloudflare-tunnel` (optional)
- [ ] 5.4 Return to main: `git checkout main` (wait for PR review before merge)