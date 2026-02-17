# Deployment Workflow

## Pre-Deployment Checklist

Before deploying, verify:

- [ ] `.env` file configured with production credentials
- [ ] `ALLOWED_TABLES` updated in `security/sql_whitelist.py`
- [ ] `metadata/template.json` filled with real metadata
- [ ] `pyproject.toml` version matches intended release
- [ ] Line endings validated: `bash scripts/validate_line_endings.sh`
- [ ] Smoke tests pass locally: `bash scripts/smoke_test.sh`

## Step-by-Step Deployment

### 1. Prepare the Server

```bash
# SSH into your VPS
ssh root@your-server

# Install Docker (if not already)
curl -fsSL https://get.docker.com | sh

# Install Caddy (if not already)
apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
  gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
  tee /etc/apt/sources.list.d/caddy-stable.list
apt update && apt install caddy
```

### 2. Clone and Configure

```bash
mkdir -p /opt/mcps/my-mcp
cd /opt/mcps/my-mcp
git clone git@github.com:your-org/my-data-mcp.git repo
cd repo

cp .env.example .env
nano .env
```

### 3. Build and Deploy

```bash
docker compose up --build -d
```

### 4. Configure Reverse Proxy

Add to `/etc/caddy/Caddyfile`:

```caddy
your-domain.com {
    route /my-mcp/* {
        basicauth {
            admin $2a$14$YOUR_HASH
        }
        uri strip_prefix /my-mcp
        reverse_proxy localhost:8001
    }
}
```

```bash
caddy hash-password --plaintext 'your-password'
systemctl reload caddy
```

### 5. Verify

```bash
# Internal (no auth)
bash scripts/smoke_test.sh http://localhost:8001/mcp

# External (with auth)
curl -u admin:your-password https://your-domain.com/my-mcp/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## Update Workflow

```bash
cd /opt/mcps/my-mcp/repo
git pull origin main
docker compose down
docker compose up --build -d
bash scripts/smoke_test.sh http://localhost:8001/mcp
```

## Rollback Workflow

```bash
# Find the previous working commit
git log --oneline -10

# Roll back
git checkout <previous-commit-hash>
docker compose down
docker compose up --build -d
```

## Monitoring

```bash
# Follow logs
docker compose logs -f --tail=50

# Check health
docker inspect --format='{{.State.Health.Status}}' my-mcp

# Resource usage
docker stats my-mcp --no-stream
```
