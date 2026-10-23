# MCP Template Specification

## Design Principles

1. **Domain-agnostic** — The template contains no domain logic. Domain knowledge lives in tool modules, skill definitions and metadata.
2. **One template, two data sources** — Everything is shared except the layer that reaches the data: a project database (option A, `db`) or an external API (option B, `api`). A new MCP keeps one and deletes the other.
3. **Convention over configuration** — Drop a module in `tools/` or a skill in `skills/` and it is registered. No registration boilerplate.
4. **One door to the data** — Tools never open connections or make HTTP requests themselves: `db.execute_select()` (A) or `api_client.get_json()` / `fetch_pages()` (B).
5. **Security by default** — Read-only SQL and a closed table whitelist (A), parameter validation before every request (B), optional API-key auth, non-root container, credentials only in the environment.
6. **Never cut silently** — Every capped response says so (`meta.truncated`, `meta.next_offset`).
7. **Production parity** — The structure, transport and deployment are those of the MCP servers in production built from this template.

## Module Contracts

### Tool Module Contract

Every module in `tools/` whose name does not start with `_` is a candidate tool module. It is imported by `mcp_server/server.py` at startup.

**Required:**
```python
def register(mcp) -> None:
    """Register tools with the MCP server."""
    @mcp.tool()
    def my_tool(species: str, year_from: int | None = None) -> str:
        """What it returns, at what level, units and columns (the model reads this).

        Args:
            species: Scientific name, e.g. "Lutjanus peru".
            year_from: First year (inclusive), optional.
        """
        return json.dumps({"data": rows, "meta": meta})
```

**Rules:**
- Return a JSON string: `{"data": [...], "meta": {...}}`. Tools have no output schema (`TemplateMCP` sets `output_schema=None`), so each result travels once.
- Tools are stateless — no module-level mutable state (caches belong in `mcp_server/cache.py`).
- Data access only through the source's door (Design Principle 4). With A, parameters go in `params=` with `%s` placeholders, never formatted into SQL.
- With B, validate every parameter with `mcp_server/params.py` before any request, and include `api_client.provenance(...)` in `meta`.
- Parameter names follow the standard vocabulary for new tools: generic English names, the same across tools, no `_filter` suffix, ranges as `_from` / `_to`. Translate them to the source's names inside the tool. Output columns keep the source's names.
- If a response is capped: `meta.truncated = true` and `meta.next_offset`.
- A source-specific example tool registers itself only for its source (`if config.MCP_DATA_SOURCE != "api": return`).
- Do not import other tool modules — tools are independent; shared helpers go in modules named `_*.py`.

### Data Source Contract

`mcp_server/source.py` is the only module that knows which source is active.

| Function | Contract |
|---|---|
| `async health() -> dict` | Never raises. `{"status": "ok" or "error", "source": ..., ...}`; on a configuration problem, `"problems": [...]` from `config.missing_required()`. |
| `warmup() -> None` | Best effort at startup (opens the DB pool with A; nothing with B). Never raises. |

Each source records the time it spends per call with `timing.record_source_call(started, rows)`, so the per-call log line separates source time from the rest.

### Skill Definition Contract

`skills/<name>/SKILL.md` (top-level `skills/`, nested layout only) is registered as an MCP prompt by `mcp_server/prompts.py`. Files in `skills/<name>/references/*.md` are appended to the prompt. A JSON Schema of the skill's inputs goes in `skills/contracts/<name>.schema.json`, and `skills/registry.py` catalogs them for docs and tooling (it is not read at runtime). The same skills can be synced into a researcher's Claude Code by the plugin in `.claude-plugin/` (Tutorial 08).

**Required YAML frontmatter:**
```yaml
---
name: skill-name
description: One-line description of the skill's purpose.
---
```

**Optional frontmatter:** `version`, `inputs`, `outputs`.

These are guided workflows served by this MCP server (prompts). They are not the analysis skills of a separate skills service; those declare this server's tools as their data source.

### Config Contract

All configuration comes from environment variables (`.env` locally, the task definition in deployment). `config.py` never exits at import; `check_required()` validates what the selected source needs and is called by `python -m mcp_server` before it binds the port.

| Variable | Required | Default | Description |
|---|---|---|---|
| `MCP_DATA_SOURCE` | No | `db` | `db` or `api` |
| `PORT` / `MCP_BASE_PATH` / `LOG_LEVEL` | No | `8000` / `/mcp` / `INFO` | HTTP server |
| **A — db** | | | |
| `MCP_DB_HOST`, `MCP_DB_USER`, `MCP_DB_PASSWORD`, `MCP_DB_NAME` | Yes, unless `DATABASE_URL` | — | Connection (read-only user) |
| `MCP_DB_PORT` / `MCP_DB_BACKEND` | No | `3306` / `mysql` | |
| `DATABASE_URL` | No | — | Full URL, takes precedence; user and password percent-decoded |
| `DB_SSL` / `DB_SSL_CA` | No | off | TLS to the database |
| `DB_POOL_MIN` / `DB_POOL_MAX` / `DB_POOL_MAX_CACHED` | No | `1` / `10` / `DB_POOL_MAX` | Connection pool |
| **B — api** | | | |
| `MCP_API_BASE_URL` | Yes | — | `https://…` |
| `MCP_API_KEY` | No | — | Only if the API needs one |
| `MCP_API_KEY_HEADER` / `MCP_API_KEY_PARAM` | No | `Authorization` / — | Where the key goes (header, or query parameter) |
| `MCP_API_HEALTH_PATH` | No | base URL | What `health_check` requests |
| `MCP_API_TIMEOUT_SECONDS` | No | `15` | Per request |
| `MCP_API_MAX_RETRIES` / `MCP_API_MAX_RETRY_AFTER_SECONDS` | No | `3` / `30` | Retries for network errors, 429, 5xx |
| `MCP_API_MIN_INTERVAL_SECONDS` | No | `0` | The API's rate limit |
| `MCP_API_MAX_ROWS` | No | `5000` | Rows per response |
| `MCP_CACHE_TTL_SECONDS` / `MCP_CACHE_MAX_ENTRIES` | No | `0` (off) / `256` | Response cache |
| **Auth** | | | |
| `AUTH_ENABLED` | No | `false` | Require `Authorization: Bearer <key>` |
| `AUTH_DYNAMODB_TABLE`, `AUTH_AWS_REGION`, `AUTH_REQUIRED_SCOPE` | Yes if `AUTH_ENABLED` | — | Key table, its region, this server's scope |
| `AUTH_CACHE_TTL_SECONDS` / `AUTH_CACHE_MAX_ENTRIES` | No | `60` / `1000` | |
| `HOST_PORT` / `COMPOSE_PROJECT_NAME` | No | `8001` / `my-mcp` | docker-compose |

### Security Contract

**A — database (`mcp_server/security.py`):**
- `validate_sql(sql)` — raises `ValueError` unless the statement is SELECT/SHOW/DESCRIBE, has no write keyword, and names only whitelisted tables.
- `enforce_limit(sql, max_rows)` — appends or caps `LIMIT`.
- `sanitize_table_name(name)` — raises `ValueError` if the table is not whitelisted.
- An empty `ALLOWED_TABLES` blocks every query that names a table (closed by default).

**B — API (`mcp_server/params.py`, `api_client.py`):**
- `params.choice / text / int_range / year_range / page` — raise `ValueError` with the parameter name and what is accepted.
- `api_client` never retries a 4xx other than 429, and never puts the API key in logs, errors or `meta.query`.

**Both:**
- With `AUTH_ENABLED`, every HTTP request needs a valid key with the server's scope (`mcp_server/auth.py`); only the key's SHA-256 hash is looked up.
- No credential, key, host, account ID, ARN or real table name in the repository.

## Response Format

```json
{
  "data": [ { "...": "one row per record, source column names" } ],
  "meta": {
    "source": "api",
    "retrieved_at": "2026-10-23T16:47:00+00:00",
    "query": { "endpoint": "https://…/records", "params": { "q": "…" } },
    "offset": 0, "returned": 100, "total": 223,
    "truncated": true, "next_offset": 100
  }
}
```

`source`, `retrieved_at` and `query` are mandatory with B: with an API the same query can return different data later, so reference cases need them.

## Versioning

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** — Breaking changes to tool signatures, parameter names, output columns, resource URIs, or config format
- **MINOR** — New tools, skills, or resources (backward-compatible)
- **PATCH** — Bug fixes, documentation updates

Update version in:
1. `pyproject.toml` → `version`
2. `metadata/template.json` → `package.version`
3. Git tag: `git tag v1.2.0 && git push origin v1.2.0`
