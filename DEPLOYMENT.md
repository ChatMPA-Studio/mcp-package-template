# Deployment Guide

Full deployment workflow for MCP servers built from this template.

## Deployment Options

| Method | Best For | Requirements |
|--------|----------|-------------|
| Docker Compose (localhost) | Development, testing | Docker |
| Docker + Caddy (VPS) | Production, single server | VPS with Docker + Caddy |
| Docker + Nginx | Production, existing Nginx | VPS with Docker + Nginx |

## Production Deployment (Docker + Caddy on VPS)

### 1. Provision a Server

Any Linux VPS works (DigitalOcean Droplet, AWS EC2, Linode, etc.):
- Ubuntu 22.04+ recommended
- 1 vCPU, 1 GB RAM minimum
- Docker and Docker Compose installed
- Caddy installed for TLS + reverse proxy

### 2. Clone Repository

```bash
ssh root@your-server
mkdir -p /opt/mcps/my-mcp
cd /opt/mcps/my-mcp
git clone git@github.com:your-org/my-data-mcp.git repo
cd repo
```

### 3. Configure Environment

```bash
cp .env.example .env
nano .env
# Fill in:
#   MCP_DB_HOST, MCP_DB_PASSWORD (or DATABASE_URL)
#   HOST_PORT (unique per MCP on this server)
#   COMPOSE_PROJECT_NAME
```

### 4. Build and Start

```bash
docker compose up --build -d
docker compose logs -f  # watch for errors
```

### 5. Verify Container Health

```bash
docker inspect --format='{{.State.Health.Status}}' my-mcp
# Should show: healthy
```

### 6. Configure Caddy

Add to `/etc/caddy/Caddyfile`:

```caddy
your-domain.com {
    route /my-mcp/* {
        basicauth {
            mcp_user $2a$14$YOUR_BCRYPT_HASH
        }
        uri strip_prefix /my-mcp
        reverse_proxy localhost:8001
    }
}
```

```bash
caddy hash-password --plaintext 'your-secure-password'
systemctl reload caddy
```

### 7. Test Production Endpoint

```bash
curl -u mcp_user:your-password \
  https://your-domain.com/my-mcp/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

## Updating a Deployed MCP

```bash
cd /opt/mcps/my-mcp/repo

# Pull latest
git pull origin main

# Rebuild and restart
docker compose down
docker compose up --build -d

# Verify
docker compose logs --tail=50
bash scripts/smoke_test.sh http://localhost:8001/mcp
```

## Multiple MCPs on One Server

Each MCP gets:
- Its own `HOST_PORT` (8001, 8002, 8003, etc.)
- Its own Caddy route block (`/mcp-a/*`, `/mcp-b/*`, etc.)
- Its own `.env` and `docker-compose.yml`

```
/opt/mcps/
  mcp-a/repo/    # HOST_PORT=8001, route /mcp-a/*
  mcp-b/repo/    # HOST_PORT=8002, route /mcp-b/*
  mcp-c/repo/    # HOST_PORT=8003, route /mcp-c/*
```

## Monitoring

### Container logs
```bash
docker compose logs -f --tail=100
```

### Health check
```bash
docker inspect --format='{{.State.Health.Status}}' my-mcp
```

### Resource usage
```bash
docker stats my-mcp --no-stream
```

## Rollback

If a deployment goes wrong:

```bash
# Check what changed
git log --oneline -5

# Revert to previous commit
git checkout HEAD~1

# Rebuild
docker compose down
docker compose up --build -d
```

## Security Checklist

- [ ] Database user is read-only (no INSERT, UPDATE, DELETE grants)
- [ ] `.env` file is not committed to git (check `.gitignore`)
- [ ] Caddy has Basic Auth enabled
- [ ] Caddy has TLS enabled (automatic with domain)
- [ ] Container runs as non-root user (`mcp:1000`)
- [ ] Docker resource limits set (memory, CPU)
- [ ] SQL whitelist configured in `security/sql_whitelist.py`
