# MCP Package Template

A production-ready template for building [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) servers that expose a **project database** or an **external API** to AI assistants and platforms.

**Runtime:** Python 3.10+, [FastMCP](https://github.com/jlowin/fastmcp) 4.0.5, uvicorn
**Transport:** streamable HTTP (stateless, JSON responses, gzip) or stdio (local development)
**Structure:** the same as the MCP servers in production built from it (`ltem-db-mcp`, `conapesca-db-mcp`, `erddap-db-mcp`)

## One template, two data sources

Everything is shared except the layer that reaches the data. You pick one data source with `MCP_DATA_SOURCE` and delete the other's files:

| | Option A — `db` (project database) | Option B — `api` (external API) |
|---|---|---|
| Files | `mcp_server/db.py`, `security.py`, `schema.py` | `mcp_server/api_client.py`, `params.py`, `cache.py` |
| How tools get data | Validated, parameterised SQL (`execute_select`) | HTTP through one client (`get_json`, `fetch_pages`) |
| What is validated | Read-only SQL, whitelisted tables, automatic LIMIT | Every parameter before the request (values, ranges, size) |
| Limits | Row cap per query | Row cap + the API's own limits: rate, pages, timeouts |
| Extra | Connection pool, schema tools | Retries, pagination, optional cache, provenance in every response |
| Came from | `ltem-db-mcp` | `erddap-db-mcp` (minus the satellite-specific parts) |

Shared by both: FastMCP server with tool and skill auto-discovery, optional API-key auth, per-call timing logs, metadata schemas, Docker image, and a parameterised deployment to Amazon ECS.

## What This Template Provides

| Component | Description |
|-----------|-------------|
| **FastMCP server** | `mcp_server/server.py`: auto-discovers tools in `tools/` and skills in `skills/`; tools never return their payload twice |
| **Data sources** | `MCP_DATA_SOURCE=db` or `api`, behind `mcp_server/source.py` (`health`, `warmup`) |
| **Configuration** | `mcp_server/config.py`: everything from environment variables; `check_required()` stops startup with a clear message if something is missing |
| **Auth (optional)** | `mcp_server/auth.py`: `Authorization: Bearer <key>` validated against a DynamoDB table of key hashes, one scope per server |
| **Timing** | `mcp_server/timing.py`: one log line per tool call (total time, time in the data source, rows, bytes) |
| **Skill prompts** | `skills/<name>/SKILL.md` registered as MCP prompts (guided workflows) |
| **Metadata schemas** | DCAT-inspired JSON schemas for package, dataset, provenance and tools (`metadata/`) |
| **Docker packaging** | Multi-stage Dockerfile + docker-compose with health checks, non-root user |
| **Deployment** | `.github/workflows/deploy-ecs.yml` (default): push to `release` → image in ECR → ECS service; all identifiers from repository variables. Alternative for a single server: `deploy-ssh.yml` + `scripts/deploy.sh` behind Caddy |
| **Local stdio** | `run_stdio.py`: the same server over stdio for Claude Desktop / Claude Code, no HTTP |
| **Plugin distribution** | `.claude-plugin/` + `.mcp.json` + `scripts/install_skills.sh`: ship the server's skills to researchers as a Claude Code plugin |
| **Tests** | `tests/`: run without a database, an API, network or AWS |

## Quick Start

```bash
# 1. Copy the template
cp -r mcp-package-template/ my-new-mcp/
cd my-new-mcp/

# 2. Configure (choose MCP_DATA_SOURCE=db or api and fill in its section)
cp .env.example .env

# 3. Install
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 4. Test (no database or API needed)
pytest

# 5. Run locally
python -m mcp_server

# 6. Docker
docker compose up --build -d
```

Then follow **[TEMPLATE.md](TEMPLATE.md)**: what to change, what to delete, and the checklist before the first deployment.

## Architecture

```
Client (Claude, an orchestrator, …)
    |  JSON-RPC 2.0 over HTTP   (Authorization: Bearer <key> if AUTH_ENABLED)
    v
[Load balancer]                 e.g. AWS ALB; TLS terminates here
    v
[Container]  python -m mcp_server  (uvicorn, stateless HTTP, gzip)
    |
[MCP Server]  auth -> timing -> tool
    |                     |
    |        source = db: validated SQL -> [Database, read-only user]
    |        source = api: one HTTP client -> [External API]
    v
JSON: {"data": [...], "meta": {...}}
```

## Project Structure

```
my-new-mcp/
|-- mcp_server/
|   |-- server.py          # FastMCP entry point: resources, core tools, discovery
|   |-- __main__.py        # HTTP runner (uvicorn): python -m mcp_server
|   |-- config.py          # Environment variables + check_required()
|   |-- source.py          # The active data source: health(), warmup()
|   |-- auth.py            # Optional API-key auth (Bearer, DynamoDB)
|   |-- timing.py          # Per-call timing log
|   |-- prompts.py         # Registers skills/ as MCP prompts
|   |-- db.py              # Option A: pooled connections, execute_select
|   |-- security.py        # Option A: SQL whitelist + LIMIT
|   |-- schema.py          # Option A: schema discovery
|   |-- api_client.py      # Option B: the only door to the API
|   |-- params.py          # Option B: parameter validation
|   |-- cache.py           # Option B: optional response cache
|-- tools/                 # YOUR TOOLS — any module with register(mcp)
|   |-- example_tools.py   # Examples without data (echo, server_time, …)
|   |-- statistics_tools.py
|   |-- api_example.py     # Option B example (search_records)
|-- skills/                # Guided workflows: <name>/SKILL.md; contracts/ (input schemas); registry.py
|-- metadata/              # template.json + JSON schemas
|-- resources/             # Static reference documents
|-- tests/                 # Run with pytest; no external services
|-- scripts/               # Dev runner, smoke tests, manifest generator
|-- docs/                  # Specification and tutorials
|-- .github/workflows/     # deploy-ecs.yml (default), deploy-ssh.yml (single server)
|-- .claude-plugin/        # Claude Code plugin manifest + marketplace
|-- Dockerfile · docker-compose.yml · healthcheck.py · Caddyfile.snippet
|-- run_stdio.py · .mcp.json
|-- pyproject.toml · .env.example · .gitignore · .dockerignore
|-- TEMPLATE.md            # How to create a new MCP from this template
|-- CHANGELOG.md
```

## Documentation

- **[TEMPLATE.md](TEMPLATE.md)** — Create a new MCP: choose the data source, what to change, checklist
- [Template Specification](docs/mcp_template_spec.md) — Contracts and non-negotiable rules
- [Quick Launch Guide](quick_launch.md) — One-page onboarding
- [Deployment Guide](DEPLOYMENT.md) — Local Docker, Amazon ECS (default) and a single server over SSH
- [Tutorials](docs/tutorials/) — Step-by-step guides (tools, skills, metadata, Docker, ECS or Caddy, releases, plugin, API source)
- [API Examples](docs/api_examples.md) — curl JSON-RPC examples
- [Troubleshooting](docs/troubleshooting.md) — Common pitfalls and fixes
- [CHANGELOG](CHANGELOG.md) — What changed in each version

## License

MIT — see [LICENSE](LICENSE).
