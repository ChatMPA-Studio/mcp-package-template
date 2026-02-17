# Quick Launch Guide

One-page onboarding for the MCP Package Template.

## What This Template Is

A production-ready starter for building MCP (Model Context Protocol) servers.  Copy it, customise it, deploy it.  Your AI assistants connect via HTTP/SSE and call tools, read resources, and follow guided skill workflows.

## Prerequisites

- Python 3.10+
- Docker and Docker Compose (for containerised deployment)
- A database (MySQL, PostgreSQL, or SQLite) — optional if your tools don't need one
- `curl` and `jq` (for smoke tests)

## Copy to a New MCP

```bash
# Copy the template directory
cp -r mcp-package-template/ my-new-mcp/
cd my-new-mcp/

# Initialise git
git init && git add -A && git commit -m "Initial MCP from template"

# Update identity
# 1. pyproject.toml     -> name, version, description
# 2. server.py          -> FastMCP("Your MCP Name")
# 3. metadata/template.json -> package, dataset, provenance
# 4. .env.example       -> your database defaults
# 5. docker-compose.yml -> COMPOSE_PROJECT_NAME
```

## Run Locally with Docker Compose

```bash
# 1. Configure credentials
cp .env.example .env
# Edit .env — fill in MCP_DB_PASSWORD (or DATABASE_URL)

# 2. Build and start
docker compose up --build -d

# 3. Check logs
docker compose logs -f

# 4. Verify
curl -s http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# 5. Stop
docker compose down
```

## Run Locally without Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env && $EDITOR .env
python -m mcp_server
```

## Add a New Tool

1. Create `mcp_server/tools/my_tools.py`:

```python
import json
from fastmcp import FastMCP

def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def my_tool(param: str) -> str:
        """Describe what this tool does.

        Args:
            param: Description of the parameter.
        """
        result = {"data": f"processed {param}"}
        return json.dumps(result)
```

2. Restart the server.  The tool is auto-discovered — no registration code needed.

## Add a New Skill

1. Create `mcp_server/skills/my_workflow.md`:

```markdown
---
name: my-workflow
description: A guided workflow that orchestrates multiple tools.
version: 1.0.0
---

# My Workflow

## Step 1: Do Something
**Tool:** `my_tool`
**Parameters:** `{"param": "value"}`

## Step 2: Analyse Results
**Tool:** `descriptive_stats`
**Parameters:** `{"values": [<results from step 1>]}`
```

2. Restart the server.  The skill appears as an MCP prompt.

## Generate Metadata Manifest

```bash
bash scripts/generate_manifest.sh
# Output: metadata/manifest.json
```

## Deploy Behind Caddy at /\<mcp-name\>/

1. Copy `Caddyfile.snippet` into your Caddy config.
2. Replace `example.com` with your domain.
3. Replace `/example/` with `/<your-mcp-name>/`.
4. Generate a password hash: `caddy hash-password --plaintext 'your-pass'`
5. Update the `basicauth` block.
6. Reload: `systemctl reload caddy`

Your MCP is now at `https://example.com/<your-mcp-name>/mcp`

## Run Smoke Tests

```bash
# Against local server
bash scripts/smoke_test.sh

# Against Docker container
bash scripts/smoke_test.sh http://localhost:8001/mcp

# Against production (with auth)
bash scripts/smoke_test.sh https://user:pass@example.com/my-mcp/mcp
```
