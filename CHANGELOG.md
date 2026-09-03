# Changelog

All notable changes to this template are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); this project
uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `run_stdio.py` — stdio transport entry point for Claude Desktop (HTTP stays
  `python -m mcp_server`). Convergent across erddap-db-mcp and conapesca-db-mcp.
- `.dockerignore` — keeps secrets, caches, tests and docs out of the build
  context. Present in all three production MCPs; was missing here.
- Database **TLS/SSL** support — `DB_SSL` / `DB_SSL_CA` env vars wired through
  `config/settings.py` and `db.py` (OFF by default; encrypts, and verifies the
  server cert when a CA bundle is supplied). Backported from ltem-db-mcp, which
  needed it once its RDS instance was reachable over the public internet.
- `.claude-plugin/` distribution scaffold (`plugin.json`, `marketplace.json`,
  `scripts/sync_skills.sh`) — installs an MCP as a Claude Code plugin that
  re-syncs its skills to `~/.claude/skills` on every session. Genericized from
  conapesca-db-mcp; **customize the `CHANGEME` markers before use**.
- `.mcp.json` — HTTP MCP client descriptor for remote connections
  (`CHANGEME` host + auth-header placeholder).
- `.github/workflows/deploy.yml` + `scripts/deploy.sh` — SSH-triggered deploy
  that rebuilds the image, restarts the container, and verifies the MCP
  `initialize` handshake. Genericized from conapesca-db-mcp.
- `CHANGELOG.md` (this file).

### Changed
- `pyproject.toml`: pin `fastmcp>=2.0.0,<3.0.0`. fastmcp 3.x became a
  meta-package and changed the HTTP/SSE transport surface; the pin keeps
  streamable-HTTP + SSE working behind the chatMPA gateway. Documented as an
  explicit fix in conapesca-db-mcp.

### Notes
- Deliberately **not** adopted from the production repos, because the template's
  current approach is equal or better: modular tool auto-discovery
  (`tools/discovery.py`), the dual-layout skills loader, the multi-scheme
  `DATABASE_URL` parser, and the multi-backend `db.py`. Single-repo drift
  (hatchling, Python 3.11 floor, pandas/scipy stack, per-DB version checks,
  top-level `tools/` layout) was left out to keep the template generic.
