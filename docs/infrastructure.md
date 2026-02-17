# Infrastructure Architecture

## Overview

An MCP package is a self-contained Python application that exposes data and computation through the Model Context Protocol (MCP).  The architecture has five layers:

```
+----------------------------------+
|  AI Client (Claude, etc.)        |   JSON-RPC 2.0
+----------------------------------+
          |
+----------------------------------+
|  Reverse Proxy (Caddy)           |   TLS + Basic Auth
+----------------------------------+
          |
+----------------------------------+
|  Docker Container                |   Isolation, resource limits
|    +----------------------------+|
|    |  FastMCP HTTP/SSE Server   ||   Transport layer
|    +----------------------------+|
|    |  MCP Server (server.py)    ||   Tools, Skills, Resources
|    +----------------------------+|
|    |  Database Driver           ||   PyMySQL, psycopg2, sqlite3
|    +----------------------------+|
+----------------------------------+
          |
+----------------------------------+
|  Database (MySQL, PostgreSQL)    |   Read-only access
+----------------------------------+
```

## Component Responsibilities

### FastMCP Server (`mcp_server/server.py`)

The entry point.  Creates the `FastMCP` instance and:
- Registers static resources (hello, metadata)
- Registers core tools (health_check)
- Calls `discover_tools()` to auto-load tool modules
- Calls `discover_prompts()` to auto-load skills as MCP prompts

### Config Module (`mcp_server/config/`)

Loads `.env` at import time.  Supports `DATABASE_URL` or individual `MCP_DB_*` variables.  Validates required vars and exits early with clear errors if missing.

### Security Module (`mcp_server/security/`)

Two independent guards:
1. **SQL Whitelist** — Only allows SELECT/SHOW/DESCRIBE; blocks destructive keywords; validates table references against a whitelist.
2. **Read-Only Enforcement** — Auto-injects or caps LIMIT clauses to prevent oversized result sets.

### Tool Discovery (`mcp_server/tools/discovery.py`)

Uses `pkgutil.iter_modules()` to find all Python modules in `mcp_server/tools/`.  Each module with a `register(mcp)` function gets called at startup.

### Skill Loader (`mcp_server/skills/loader.py`)

Scans `mcp_server/skills/` for `.md` files with YAML frontmatter.  Each skill is registered as an MCP prompt, making it discoverable by remote clients.

### Database Layer (`mcp_server/db.py`)

Wraps PyMySQL with security validation.  Every query passes through `validate_sql()` and `enforce_limit()` before execution.

## Network Architecture

```
Internet
    |
    v
[Caddy :443]  -- TLS termination, Basic Auth
    |
    | http://127.0.0.1:HOST_PORT
    v
[Docker :PORT]  -- Container boundary
    |
    | TCP
    v
[Database :3306/5432]  -- Read-only user
```

- The container binds to `127.0.0.1` only — not exposed to the internet.
- Caddy handles TLS certificates automatically.
- Each MCP gets a unique `HOST_PORT` and Caddy route.

## File System Layout

```
/opt/mcps/my-mcp/
  repo/                    # Git repository
    .env                   # Credentials (not in git)
    docker-compose.yml     # Container config
    mcp_server/            # Application code
    metadata/              # manifest.json
  backups/                 # Auto-created by deploy script
```
