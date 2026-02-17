# Admin Guide

## Server Administration

### Starting and Stopping

```bash
# Start
docker compose up -d

# Stop
docker compose down

# Restart
docker compose restart

# Rebuild (after code changes)
docker compose down
docker compose up --build -d
```

### Viewing Logs

```bash
# Follow logs in real time
docker compose logs -f

# Last 100 lines
docker compose logs --tail=100

# Filter by time
docker compose logs --since="2026-01-01T00:00:00"
```

### Health Monitoring

```bash
# Container health status
docker inspect --format='{{.State.Health.Status}}' my-mcp

# Resource usage
docker stats my-mcp --no-stream

# Process list inside container
docker exec my-mcp ps aux
```

## Configuration Changes

### Changing Database Credentials

1. Edit `.env` with new credentials.
2. Restart: `docker compose restart`
3. Verify: `bash scripts/smoke_test.sh http://localhost:8001/mcp`

### Changing the Port

1. Edit `.env`: `HOST_PORT=8002`
2. Update Caddy: `reverse_proxy localhost:8002`
3. Restart both: `docker compose restart && systemctl reload caddy`

### Adding Tables to the Whitelist

1. Edit `mcp_server/security/sql_whitelist.py`:
   ```python
   ALLOWED_TABLES = {
       "existing_table",
       "new_table",  # <-- add here
   }
   ```
2. Rebuild: `docker compose up --build -d`

### Adjusting Resource Limits

Edit `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      memory: 1G      # increase from 512M
      cpus: "2.0"     # increase from 1.0
```

## User Management

### Caddy Basic Auth

Add users:
```bash
caddy hash-password --plaintext 'user-password'
```

Edit Caddyfile:
```caddy
basicauth {
    admin   $2a$14$HASH_FOR_ADMIN
    analyst $2a$14$HASH_FOR_ANALYST
}
```

Reload: `systemctl reload caddy`

## Backup

### Database Credentials

The `.env` file contains all credentials.  Back it up securely:

```bash
# Copy .env to secure location
cp /opt/mcps/my-mcp/repo/.env /backups/my-mcp-env-$(date +%Y%m%d)
```

### Application State

MCP servers are stateless — the database is the source of truth.  Back up:
1. `.env` file
2. `docker-compose.yml` (if customised)
3. Any custom tool or skill files

## Troubleshooting

See [troubleshooting.md](troubleshooting.md) for common issues.

### Quick Diagnostic

```bash
# 1. Is the container running?
docker ps | grep my-mcp

# 2. Is it healthy?
docker inspect --format='{{.State.Health.Status}}' my-mcp

# 3. What do the logs say?
docker compose logs --tail=50

# 4. Can it reach the database?
docker exec my-mcp python -c "from mcp_server.db import test_connection; print(test_connection())"

# 5. Is the port listening?
curl -sf http://localhost:8001/mcp && echo "OK" || echo "FAIL"
```
