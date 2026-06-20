# Deploy ProductGPT to DigitalOcean

Recommended approach: **one Droplet running Docker Compose** (backend + frontend + Neo4j).

## Architecture

```
Internet → :80 nginx (frontend) → /api/* → FastAPI (backend) → SQLite + Neo4j
```

The React app is built to static files and served by nginx. API calls go to `/api/v1/...` on the same host (no CORS issues).

## 1. Create a Droplet

1. Go to [DigitalOcean Droplets](https://cloud.digitalocean.com/droplets/new)
2. Choose:
   - **Image**: Ubuntu 24.04 LTS
   - **Plan**: Basic — **2 GB RAM / 1 vCPU** minimum (4 GB recommended for Neo4j)
   - **Authentication**: SSH key (recommended)
3. Create the droplet and note the **public IP**

## 2. Install Docker on the Droplet

SSH in:

```bash
ssh root@YOUR_DROPLET_IP
```

Install Docker:

```bash
apt-get update && apt-get install -y ca-certificates curl
curl -fsSL https://get.docker.com | sh
```

## 3. Deploy the app

On your **local machine**, copy the project to the droplet:

```bash
rsync -av --exclude node_modules --exclude .venv --exclude data/*.db \
  "/Users/uditshukla/Desktop/Office projects/ProductGPT/" \
  root@YOUR_DROPLET_IP:/opt/productgpt/
```

On the **droplet**:

```bash
cd /opt/productgpt

# Set production secrets
cp .env.production.example .env
nano .env   # change NEO4J_PASSWORD and CORS_ORIGINS to your droplet IP/domain

# Build and start everything
docker compose -f docker-compose.prod.yml up -d --build
```

First startup takes 1–2 minutes (Neo4j boot + Excel seed into SQLite + graph sync).

## 4. Verify

Open in browser:

- **App**: `http://YOUR_DROPLET_IP`
- **API health**: `http://YOUR_DROPLET_IP/api/v1/health`
- **API docs**: `http://YOUR_DROPLET_IP/docs`

Check containers:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend
```

## 5. Add HTTPS (recommended)

Point a domain's **A record** to your droplet IP, then:

```bash
apt-get install -y certbot
# Stop nginx briefly, get cert, then configure — or use Caddy/Traefik as reverse proxy
```

Simplest option: put **DigitalOcean Load Balancer** or **Cloudflare** in front for TLS termination.

## 6. Useful commands

```bash
# Restart after code update
docker compose -f docker-compose.prod.yml up -d --build

# Re-sync Neo4j graph
docker compose -f docker-compose.prod.yml exec backend python scripts/sync_neo4j.py

# Upload new Goodman Excel via API
curl -X POST "http://YOUR_DROPLET_IP/api/v1/ingest/upload" \
  -F "file=@Goodman November Ratings_cleaned.xlsx" \
  -F "source_type=goodman_ratings" \
  -F "replace=true"

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Stop
docker compose -f docker-compose.prod.yml down
```

## Persistent data

Docker volumes preserve data across restarts:

| Volume | Contents |
|--------|----------|
| `app_data` | SQLite DB (`productgpt.db`) |
| `neo4j_data` | Neo4j graph |
| `neo4j_logs` | Neo4j logs |

## Firewall

In DigitalOcean **Networking → Firewalls**, allow:

- **22** (SSH)
- **80** (HTTP)
- **443** (HTTPS, if using TLS)

Do **not** expose Neo4j ports (7474/7687) publicly.

## Alternative: DigitalOcean App Platform

App Platform works for backend + static frontend separately, but **Neo4j is not supported** as a managed component. You would need a separate Droplet for Neo4j anyway. Docker Compose on one Droplet is simpler for this project.
