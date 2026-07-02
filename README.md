# MCP Package Template

A production-ready template for building [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) servers that expose databases, APIs, or any data source to AI assistants.

**Version:** 1.1.0
**Runtime:** Python 3.10+, [FastMCP 2.x](https://github.com/jlowin/fastmcp)
**Transport:** HTTP/SSE (Docker) or stdio (local development)

## What This Template Provides

| Component | Description |
|-----------|-------------|
| **FastMCP server** | Entry point with SSE transport, tool/skill auto-discovery |
| **Tool auto-discovery** | Drop a Python module in `mcp_server/tools/`, it registers automatically |
| **Skill system** | Markdown-driven guided workflows in top-level `skills/`, auto-registered as MCP prompts, each with a JSON Schema input contract |
| **Config module** | `.env`-based config with `DATABASE_URL` or component vars |
| **Security layer** | SQL whitelist + read-only enforcement (optional, for DB-backed MCPs) |
| **Metadata schemas** | DCAT-inspired JSON schemas for package, dataset, provenance, tools |
| **Docker packaging** | Multi-stage Dockerfile + docker-compose with health checks |
| **Reverse proxy** | Caddyfile snippet for subpath routing with Basic Auth |
| **Claude Code plugin** | `.claude-plugin/` bundles the MCP connection + a `SessionStart` hook that auto-syncs skills locally every session |
| **Scripts** | Dev runner, smoke tests, manifest generator, CRLF validator, skill installer, deploy workflow |
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
|   |-- prompts.py           # Skill auto-discovery + MCP prompt registration (reads top-level skills/)
|   |-- config/
|   |   |-- settings.py      # Environment variable loading
|   |-- security/
|   |   |-- sql_whitelist.py # Table whitelist validation
|   |   |-- read_only.py     # LIMIT enforcement
|   |-- tools/
|   |   |-- discovery.py     # Auto-discovery engine
|   |   |-- example_tools.py # Example: echo, server_time, calculator
|   |   |-- statistics_tools.py  # Example: descriptive_stats, correlation
|   |-- metadata/
|   |   |-- manifest.py      # Manifest generator
|   |   |-- schema/          # JSON schemas (package, dataset, provenance, tool)
|   |-- resources/
|       |-- README.md        # Resource documentation
|-- skills/                  # Skill definitions (top-level, not under mcp_server/)
|   |-- README.md
|   |-- registry.py          # Programmatic skill listing (dev reference only)
|   |-- contracts/           # JSON Schema input contract per skill
|   |-- <skill-name>/
|       |-- SKILL.md         # YAML frontmatter + guided workflow body
|-- .mcp.json                # MCP server connection (HTTP endpoint + auth env var)
|-- .claude-plugin/          # Claude Code plugin: SessionStart hook + marketplace manifest
|   |-- plugin.json          # Plugin metadata + SessionStart hook (no credentials)
|   |-- marketplace.json     # Self-hosted marketplace so 'claude plugin marketplace add' works
|   |-- scripts/
|       |-- sync_skills.sh   # Hook target — pulls skills/ into ~/.claude/skills/ every session
|-- metadata/
|   |-- template.json        # Base metadata (edit for your project)
|-- scripts/
|   |-- dev_run.sh           # Local development runner
|   |-- smoke_test.sh        # Curl-based integration tests
|   |-- generate_manifest.sh # Manifest generation
|   |-- validate_line_endings.sh  # CRLF detection
|   |-- install_skills.sh    # Manual one-shot skill install (curl + python3, no gh CLI)
|   |-- deploy.sh            # Backup -> pull -> rebuild -> health-check deploy workflow
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
9. **`skills/`** — Replace the three example skills with your own domain workflows (see `docs/skills_architecture.md`)
10. **`scripts/install_skills.sh`** — Set `GITHUB_ORG` / `GITHUB_REPO` / `GITHUB_REF`
11. **`.mcp.json`** — Fill in `{{MCP_SERVER_URL}}`; set `{{ENV_AUTH_HEADER}}` to the env var name researchers will export (e.g. `MYPROJECT_AUTH_HEADER`). Never hardcode the token value — researchers set the env var in their shell profile.
12. **`.claude-plugin/plugin.json`**, **`.claude-plugin/marketplace.json`**, and **`.claude-plugin/scripts/sync_skills.sh`** — Fill in the `{{placeholders}}` (see `docs/tutorials/08_package_as_plugin.md`)

## Documentation

- [Quick Launch Guide](quick_launch.md) — One-page onboarding
- [Deployment Guide](DEPLOYMENT.md) — Full deployment workflow
- [API Examples](docs/api_examples.md) — curl JSON-RPC examples
- [Skills Architecture](docs/skills_architecture.md) — how skills are authored and discovered
- [Tutorials](docs/tutorials/) — Step-by-step guides, including [packaging as a Claude Code plugin](docs/tutorials/08_package_as_plugin.md)
- [Troubleshooting](docs/troubleshooting.md) — Common pitfalls and fixes

## License

MIT — see [LICENSE](LICENSE).
