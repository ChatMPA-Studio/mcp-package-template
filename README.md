# MCP Package Template

A production-ready template for building [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) servers that expose databases, APIs, or any data source to AI assistants.

**Version:** 1.0.0
**Runtime:** Python 3.10+, [FastMCP 2.x](https://github.com/jlowin/fastmcp)
**Transport:** HTTP/SSE (Docker) or stdio (local development)

## What This Template Provides

| Component | Description |
|-----------|-------------|
| **FastMCP server** | Entry point with SSE transport, tool/skill auto-discovery |
| **Tool auto-discovery** | Drop a Python module in `mcp_server/tools/`, it registers automatically |
| **Skill system** | Markdown-driven guided workflows with YAML frontmatter |
| **Config module** | `.env`-based config with `DATABASE_URL` or component vars |
| **Security layer** | SQL whitelist + read-only enforcement (optional, for DB-backed MCPs) |
| **Metadata schemas** | DCAT-inspired JSON schemas for package, dataset, provenance, tools |
| **Docker packaging** | Multi-stage Dockerfile + docker-compose with health checks |
| **Reverse proxy** | Caddyfile snippet for subpath routing with Basic Auth |
| **Scripts** | Dev runner, smoke tests, manifest generator, CRLF validator |
| **Documentation** | Architecture docs, tutorials, deployment guide |

## Quick Start

```bash
# 1. Copy the template
cp -r mcp-package-template/ my-new-mcp/
cd my-new-mcp/

# 2. Configure
cp .env.example .env
# Edit .env — fill in your database credentials

# 3. Install
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 4. Run locally
python -m mcp_server

# 5. Test
bash scripts/smoke_test.sh

# 6. Docker
docker compose up --build -d
```

## Architecture

```
Client (Claude, ChatGPT, etc.)
    |  JSON-RPC 2.0 over HTTP
    v
[Caddy Reverse Proxy]  <-- Basic Auth + TLS
    |  http://127.0.0.1:HOST_PORT
    v
[Docker Container]
    |  FastMCP HTTP/SSE on PORT
    v
[MCP Server]
    |  SQL validation -> parameterised queries
    v
[Database]  <-- read-only user
```

## Project Structure

```
my-new-mcp/
|-- mcp_server/
|   |-- server.py           # FastMCP entry point
|   |-- __main__.py          # HTTP runner
|   |-- db.py                # Database connection layer
|   |-- config/
|   |   |-- settings.py      # Environment variable loading
|   |-- security/
|   |   |-- sql_whitelist.py # Table whitelist validation
|   |   |-- read_only.py     # LIMIT enforcement
|   |-- tools/
|   |   |-- discovery.py     # Auto-discovery engine
|   |   |-- example_tools.py # Example: echo, server_time, calculator
|   |   |-- statistics_tools.py  # Example: descriptive_stats, correlation
|   |-- skills/
|   |   |-- loader.py        # Skill auto-discovery + MCP prompt registration
|   |   |-- registry.py      # Programmatic skill listing
|   |   |-- *.md             # Skill definitions (YAML frontmatter + body)
|   |-- metadata/
|   |   |-- manifest.py      # Manifest generator
|   |   |-- schema/          # JSON schemas (package, dataset, provenance, tool)
|   |-- resources/
|       |-- README.md        # Resource documentation
|-- metadata/
|   |-- template.json        # Base metadata (edit for your project)
|-- scripts/
|   |-- dev_run.sh           # Local development runner
|   |-- smoke_test.sh        # Curl-based integration tests
|   |-- generate_manifest.sh # Manifest generation
|   |-- validate_line_endings.sh  # CRLF detection
|-- docs/                    # Architecture and tutorial documentation
|-- Dockerfile               # Multi-stage production build
|-- docker-compose.yml       # Container orchestration
|-- Caddyfile.snippet        # Reverse proxy configuration
|-- pyproject.toml           # Python packaging
|-- .env.example             # Environment variable template
```

## Customisation Checklist

When creating a new MCP from this template:

1. **`pyproject.toml`** — Change `name`, `version`, `description`, add your dependencies
2. **`mcp_server/server.py`** — Change `FastMCP("My MCP Server")` to your project name
3. **`mcp_server/config/settings.py`** — Adjust env var prefix if needed (`MCP_DB_*`)
4. **`mcp_server/security/sql_whitelist.py`** — Add your table names to `ALLOWED_TABLES`
5. **`metadata/template.json`** — Fill in your package, dataset, and provenance metadata
6. **`.env.example`** — Update with your database connection details
7. **`docker-compose.yml`** — Set `COMPOSE_PROJECT_NAME` to your project name
8. **`Caddyfile.snippet`** — Set your domain and subpath

## Documentation

- [Quick Launch Guide](quick_launch.md) — One-page onboarding
- [Deployment Guide](DEPLOYMENT.md) — Full deployment workflow
- [API Examples](docs/api_examples.md) — curl JSON-RPC examples
- [Tutorials](docs/tutorials/) — Step-by-step guides
- [Troubleshooting](docs/troubleshooting.md) — Common pitfalls and fixes

## License

MIT — see [LICENSE](LICENSE).
