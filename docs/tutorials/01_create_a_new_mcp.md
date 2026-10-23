# Tutorial 01: Create a New MCP from the Template

## Goal

Copy the template, give it your identity, keep one data source, and see it
answer locally. The full reference is [TEMPLATE.md](../../TEMPLATE.md); this
tutorial walks through it with an example: a weather database (option A). For
an API, make the choices of option B in steps 3–4 and continue with
[Tutorial 09](09_api_data_source.md).

## Steps

### 1. Copy the template

```bash
cp -r mcp-package-template/ weather-mcp/
cd weather-mcp/
rm -rf .git && git init
```

### 2. Update the identity

| File | Change |
|---|---|
| `pyproject.toml` | `name = "weather-mcp"`, `version = "0.1.0"`, `description` |
| `mcp_server/server.py` | `TemplateMCP("My MCP Server", …)` → `TemplateMCP("Weather Observations", …)` |
| `metadata/template.json` | package, dataset (coverage, license, citation), provenance |
| `docker-compose.yml` / `.env` | `COMPOSE_PROJECT_NAME=weather-mcp` |

### 3. Keep one data source

Option A (database): delete the API files and their traces.

```bash
rm mcp_server/api_client.py mcp_server/params.py mcp_server/cache.py
rm tools/api_example.py tests/test_api_client.py
```

Then, as in [TEMPLATE.md](../../TEMPLATE.md) step 2: remove the `api` branch from `mcp_server/source.py`, the API section and checks from `mcp_server/config.py` and `.env.example`.

```bash
pytest          # must still pass
```

### 4. Configure the connection

```bash
cp .env.example .env
```

```bash
MCP_DATA_SOURCE=db
MCP_DB_HOST=<your-database-host>
MCP_DB_PORT=3306
MCP_DB_USER=<read-only user>
MCP_DB_PASSWORD=<password>
MCP_DB_NAME=<database>
```

`.env` is git-ignored: never commit it. Use a user that can only `SELECT`.

### 5. Whitelist your tables

`mcp_server/security.py`:

```python
ALLOWED_TABLES: set[str] = {"weather_stations", "daily_observations"}
```

### 6. Install and run

```bash
python -m venv .venv
source .venv/bin/activate      # .venv\Scripts\activate on Windows
pip install -e ".[dev]"
python -m mcp_server
```

If something is missing in `.env`, the server stops and lists it.

### 7. Verify

```bash
bash scripts/smoke_test.sh
```

`health_check` must answer `"status": "ok"` with the database version, name and user. `list_tables`, `describe_table` and `schema_snapshot` show what the server can read.

### 8. Commit

```bash
git add -A
git status        # .env must NOT appear
git commit -m "Initial weather MCP from template"
```

## What You Changed

| File | Change |
|---|---|
| `pyproject.toml`, `metadata/template.json` | Identity and metadata |
| `mcp_server/server.py` | Server name |
| `mcp_server/source.py`, `config.py`, `.env.example` | Only the database source remains |
| `mcp_server/security.py` | Allowed tables |
| `.env` (not committed) | Connection |

## Next Steps

- [Tutorial 02: Add Tools](02_add_tools.md)
