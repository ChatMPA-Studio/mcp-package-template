# Infrastructure Architecture

## Overview

```
                 Client (Claude, a platform's orchestrator, …)
                        |  HTTPS, JSON-RPC 2.0
                        |  Authorization: Bearer <key>   (AUTH_ENABLED)
                        v
                 [Load balancer]  TLS, path routing to MCP_BASE_PATH
                        v
     [ECS service: N stateless replicas of the container]
        python -m mcp_server  (uvicorn, JSON responses, gzip)
                        |
        auth (FastMCP TokenVerifier) ──> [Key table: SHA-256 hashes, read-only]
                        |
        timing middleware -> tool (tools/*.py)
                        |
              mcp_server/source.py
           ┌────────────┴────────────┐
   A: db.py + security.py     B: api_client.py + params.py (+ cache.py)
           |                         |
   [Database, read-only user]  [External API]
```

Replicas share nothing: no session state (`stateless_http=True`), no shared cache unless you add one (see `mcp_server/cache.py`). Any replica can answer any request.

## Component Responsibilities

### FastMCP Server (`mcp_server/server.py`)
- Creates `TemplateMCP` (tools without output schema: each result travels once).
- Attaches auth (if `AUTH_ENABLED`) and `ToolTimingMiddleware`.
- Registers metadata resources, `health_check`, and — with the db source — the schema tools.
- Imports every module in `tools/` and calls its `register(mcp)`; registers `skills/` as prompts.

### HTTP Runner (`mcp_server/__main__.py`)
- `check_required()` before binding the port: a misconfigured container stops at once.
- `source.warmup()` (opens the DB pool with A).
- `build_app()`: stateless HTTP, JSON instead of SSE, gzip level 6; uvicorn keep-alive 65 s (longer than a typical load balancer idle timeout, avoiding sporadic 502s).

### Config (`mcp_server/config.py`)
- Every setting from environment variables; nothing exits at import.
- `missing_required()` / `check_required()` know what each source and auth need.

### Data Source (`mcp_server/source.py`)
- The only module that knows `MCP_DATA_SOURCE`. `health()` and `warmup()`.

### Option A — Database (`db.py`, `security.py`, `schema.py`)
- Connection pool (DBUtils) with liveness ping, autocommit reads, optional TLS.
- Every query validated (read-only, whitelisted tables) and capped (LIMIT).

### Option B — External API (`api_client.py`, `params.py`, `cache.py`)
- One HTTP client: timeout, pacing, retries for network errors / 429 / 5xx, translated errors, key never exposed, pagination with truncation, provenance.
- Parameters validated before any request.
- Optional in-memory response cache.

### Auth (`mcp_server/auth.py`)
- Bearer key → SHA-256 → lookup in a DynamoDB table shared by the platform's servers (read-only, cached 60 s, misses cached too). The key must carry `AUTH_REQUIRED_SCOPE`.

### Timing (`mcp_server/timing.py`)
- One log line per tool call; the data source adds its time with `record_source_call()`.

### Skill Loader (`mcp_server/prompts.py`)
- Registers `skills/<name>/SKILL.md` (+ `references/*.md`) as MCP prompts.

### stdio entry point (`run_stdio.py`)
- The same server over stdio, for Claude Desktop / Claude Code on the researcher's machine. The plugin in `.claude-plugin/` (+ `.mcp.json`, `scripts/install_skills.sh`) distributes the skills.

## Network Architecture

- **Production:** the container listens on `PORT` inside a private network; only the load balancer reaches it. TLS terminates at the load balancer. Outbound: the database (A) or the external API (B), and the key table (auth).
- **Local Docker:** `docker-compose.yml` binds the port to `127.0.0.1` only (`HOST_PORT`, default 8001).
- **Single server (alternative):** Docker Compose behind Caddy, which terminates TLS and routes a path to the container (`Caddyfile.snippet`).

## File System Layout (container)

```
/app/
  mcp_server/   tools/   skills/   resources/   metadata/
  healthcheck.py   pyproject.toml
```

Runs as the non-root `mcp` user. Tests, docs, scripts and `.env*` are excluded from the image (`.dockerignore`).
