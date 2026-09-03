# Changelog

## [1.2.0] — 2026-09-03

Syncs configuration + deployment fixes that converged across the production
MCPs built from this template — erddap-db-mcp, ltem-db-mcp, conapesca-db-mcp.
Only multi-repo / generic-safe changes were taken; single-repo drift
(hatchling, Python 3.11 floor, data-science stack, per-DB version checks,
top-level `tools/` layout) was intentionally left out.

### Added

- `run_stdio.py` — stdio transport entry point for Claude Desktop. HTTP stays
  `python -m mcp_server`. Convergent across erddap-db-mcp and conapesca-db-mcp.
- `.dockerignore` — keeps secrets, caches, tests, docs and CI out of the build
  context. Present in all three production MCPs; was missing here.
- Database **TLS/SSL** support — `DB_SSL` / `DB_SSL_CA` wired through
  `mcp_server/config/settings.py` and `mcp_server/db.py` (OFF by default;
  encrypts, and verifies the server cert when a CA bundle is supplied).
  Backported from ltem-db-mcp, which needed it once its RDS instance was
  reachable over the public internet. Documented in `.env.example`.
- `.github/workflows/deploy.yml` — SSH-triggered deploy that invokes the
  existing `scripts/deploy.sh`. Requires `DEPLOY_HOST` / `DEPLOY_SSH_KEY` /
  `DEPLOY_PATH` repo secrets.

### Changed

- `pyproject.toml`: pin `fastmcp>=2.0.0,<3.0.0`. fastmcp 3.x became a
  meta-package and changed the HTTP/SSE transport surface; the pin keeps
  streamable-HTTP + SSE working behind the chatMPA gateway. Documented as an
  explicit fix in conapesca-db-mcp.

## [1.1.0] — 2026-07-01

Ports forward the skills/distribution work done in
[conapesca-db-mcp](https://github.com/ChatMPA-Studio/conapesca-db-mcp) v0.2.0
(2026-06-29), which was built from this template but diverged from it in
production. This release folds those improvements back in, generalized to
be domain/database-agnostic, and adds a new distribution layer on top.

### Changed

- **Skills relocated**: `mcp_server/skills/*.md` (flat, subpackage of
  `mcp_server`) → top-level `skills/<name>/SKILL.md` (nested only, sibling
  of `mcp_server/`). Flat-layout skills are no longer supported — every
  skill now gets its own directory, matching its contract and references.
- **`mcp_server/skills/loader.py` → `mcp_server/prompts.py`**: same
  auto-discovery mechanism, simplified, now reads from the top-level
  `skills/` directory instead of `mcp_server/skills/`.
- **`mcp_server/skills/registry.py` → `skills/registry.py`**: moved
  alongside the skill definitions it catalogs; no longer imports from
  `mcp_server`.
- The three example skills were moved and renamed to match: `example_skill.md`
  → `skills/example-health-check/SKILL.md`, `data_exploration.md` →
  `skills/data-exploration/SKILL.md`, `statistical_analysis.md` →
  `skills/statistical-analysis/SKILL.md`.

### Added

- `skills/contracts/*.schema.json` — JSON Schema input contract per skill
  (new concept, not previously in the template).
- `skills/README.md` — documents the skills directory structure and the
  two ways a researcher can invoke a skill (live MCP prompt vs. local
  install).
- `scripts/install_skills.sh` — one-shot skill installer. Ported from
  conapesca-db-mcp, but rewritten to depend only on `curl` + `python3`
  (the original required the `gh` CLI, which is not guaranteed to be
  present on a researcher's machine).
- `scripts/deploy.sh` — backup → pull → rebuild → health-check deployment
  workflow, ported from conapesca-db-mcp and generalized.
- **`.claude-plugin/`** — new. Bundles the MCP server connection
  (`mcpServers`) with a `SessionStart` hook
  (`.claude-plugin/scripts/sync_skills.sh`) that re-syncs skills into
  `~/.claude/skills/` automatically every session, so new skills added to
  a deployed MCP reach already-onboarded researchers with zero manual
  steps. See `docs/tutorials/08_package_as_plugin.md`.
- `docs/tutorials/08_package_as_plugin.md` — new tutorial covering plugin
  packaging and marketplace registration.

### Known tradeoff

`.claude-plugin/scripts/sync_skills.sh` duplicates the fetch logic in
`scripts/install_skills.sh` rather than depending on it, since only
`.claude-plugin/`'s contents are guaranteed present after a plugin
install (not the whole repo). Keep both in sync when changing one.

## [1.0.0] — 2026-02-17

Initial release.
