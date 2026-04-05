# mi-app-instagram

Instagram Graph API integration application.

## Development Setup

### Prerequisites

- Docker and Docker Compose
- UV package manager (for local development)
- Cloudflare account with Zero Trust enabled (for public access)

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### Running Locally

```bash
docker compose up --build
```

Services will be available at:
- **API**: http://localhost:8000
- **MinIO Console**: http://localhost:9001
- **PostgreSQL**: localhost:5432

## Cloudflare Tunnel Setup

The application uses Cloudflare Tunnel to expose the API and MinIO to the internet for Meta Instagram Graph API integration.

### Prerequisites

1. A domain managed by Cloudflare
2. Cloudflare Zero Trust enabled on your account

### Steps

#### 1. Create a Tunnel

1. Go to [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/)
2. Navigate to **Networks** → **Tunnels**
3. Click **Create a tunnel**
4. Choose **Cloudflared** as the connector
5. Name your tunnel (e.g., `instagramjp-tunnel`)
6. Save and copy the **Tunnel Token**

#### 2. Configure Environment

Add the tunnel token to your `.env` file:

```env
TUNNEL_TOKEN=your-tunnel-token-here
```

#### 3. Configure Public Hostnames

In the Cloudflare Tunnel dashboard, add public hostnames:

**MinIO (for media access)**:
- Subdomain: `instagramjp`
- Domain: `yourdomain.com`
- Service: `http://minio:9000`

**API (for webhook callbacks)**:
- Subdomain: `api`
- Domain: `yourdomain.com`
- Service: `http://web:8000`

#### 4. Start the Tunnel

```bash
docker compose up -d
```

The tunnel container will start and connect to Cloudflare. Verify the tunnel status shows **Healthy** in the Cloudflare dashboard.

#### 5. Verify Access

```bash
# Test MinIO public access
curl -I https://instagramjp.yourdomain.com

# Test API public access
curl -I https://api.yourdomain.com/api/v1/ping
```

### Architecture

```
Internet → Cloudflare Tunnel → app-network (Docker bridge)
                                     ├── web:8000 (FastAPI)
                                     └── minio:9000 (MinIO)
```

All services communicate via the `app-network` Docker bridge network, enabling DNS resolution by service name.