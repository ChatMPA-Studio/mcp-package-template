# Tutorial 05: Dockerize and Run

## Goal

Build a Docker image and run the MCP server with Docker Compose.

## Prerequisites

- Docker and Docker Compose installed
- `.env` file configured
- Server runs locally without Docker

## Steps

### 1. Review Docker Configuration

The template includes a pre-configured `Dockerfile` (multi-stage) and `docker-compose.yml`.

Key settings in `.env`:
```env
PORT=8000           # Container internal port
HOST_PORT=8001      # Host-accessible port
COMPOSE_PROJECT_NAME=my-weather-mcp
```

### 2. Build and Start

```bash
docker compose up --build -d
```

### 3. Check Logs

```bash
docker compose logs -f
```

You should see:
```
=== MCP Server Configuration ===
  Port:        8000
  DB Host:     your-host
  ...
================================
```

### 4. Wait for Health Check

```bash
# Wait up to 30 seconds
for i in {1..6}; do
  STATUS=$(docker inspect --format='{{.State.Health.Status}}' my-weather-mcp 2>/dev/null || echo "starting")
  echo "Health: $STATUS"
  [ "$STATUS" = "healthy" ] && break
  sleep 5
done
```

### 5. Test

```bash
# Via Docker Compose port
curl -s http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Full smoke test
bash scripts/smoke_test.sh http://localhost:8001/mcp
```

### 6. Stop

```bash
docker compose down
```

## Customising the Docker Build

### Adding System Dependencies

If your tools need system packages (e.g., `libpq-dev` for PostgreSQL):

```dockerfile
# In the runtime stage, before COPY commands:
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
```

### Adding Python Dependencies

Edit `pyproject.toml`:

```toml
dependencies = [
    "fastmcp>=2.0.0",
    "pymysql>=1.1.0",
    "python-dotenv>=1.0.0",
    "pandas>=2.0.0",        # add your deps
]
```

Then rebuild: `docker compose up --build -d`

### Troubleshooting Build Issues

If the container crashes with `ModuleNotFoundError`:
1. Check that `--force-reinstall` is in the builder stage.
2. Verify the module is in `pyproject.toml` dependencies.
3. Rebuild with `--no-cache`: `docker compose build --no-cache`

## Next Steps

- [Tutorial 06: Deploy with Caddy](06_deploy_with_caddy_subpath.md)
