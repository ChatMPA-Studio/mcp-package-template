# Tutorial 01: Create a New MCP from the Template

## Goal

Copy the template, customise identity, and get a running MCP server.

## Steps

### 1. Copy the Template

```bash
cp -r mcp-package-template/ my-weather-mcp/
cd my-weather-mcp/
git init
```

### 2. Update Package Identity

Edit `pyproject.toml`:

```toml
[project]
name = "my-weather-mcp"
version = "1.0.0"
description = "MCP server for weather observation data"
```

### 3. Update Server Name

Edit `mcp_server/server.py`, line 25:

```python
mcp = FastMCP("Weather Data Server")
```

### 4. Configure Database Connection

```bash
cp .env.example .env
```

Edit `.env`:
```env
MCP_DB_HOST=your-database-host.com
MCP_DB_PORT=3306
MCP_DB_USER=weather_readonly
MCP_DB_PASSWORD=your-secure-password
MCP_DB_NAME=weather_observations
```

### 5. Add Your Tables to the Whitelist

Edit `mcp_server/security/sql_whitelist.py`:

```python
ALLOWED_TABLES: set[str] = {
    "weather_stations",
    "daily_observations",
    "monthly_summaries",
}
```

### 6. Update Metadata

Edit `metadata/template.json` — fill in your package, dataset, and provenance sections.

### 7. Install and Run

```bash
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
# .venv\Scripts\activate     # Windows

pip install -e ".[dev]"
python -m mcp_server
```

### 8. Verify

```bash
curl -s http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

You should see a JSON-RPC response with `"result"` containing server capabilities.

### 9. Commit

```bash
git add -A
git commit -m "Initial MCP from template: weather observation data"
```

## What You Changed

| File | Change |
|------|--------|
| `pyproject.toml` | Package name, version, description |
| `mcp_server/server.py` | FastMCP server name |
| `.env` | Database credentials |
| `mcp_server/security/sql_whitelist.py` | Allowed table names |
| `metadata/template.json` | Project metadata |

## Next Steps

- [Tutorial 02: Add Tools](02_add_tools.md)
- [Tutorial 03: Add Skills](03_add_skills.md)
