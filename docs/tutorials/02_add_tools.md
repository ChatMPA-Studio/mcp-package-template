# Tutorial 02: Add Tools

## Goal

Create a new tool module that queries your database and returns structured results.

## Prerequisites

- Completed [Tutorial 01](01_create_a_new_mcp.md)
- Database connection working (`python -m mcp_server` starts without errors)

## Steps

### 1. Create a Tool Module

Create `mcp_server/tools/weather_tools.py`:

```python
"""Weather observation tools."""

import json
from fastmcp import FastMCP
from mcp_server.db import execute_select


def register(mcp: FastMCP) -> None:
    """Register weather tools with the MCP server."""

    @mcp.tool()
    def get_stations(region: str | None = None) -> str:
        """List weather stations, optionally filtered by region.

        Args:
            region: Filter by geographic region.
        """
        if region:
            rows = execute_select(
                "SELECT station_id, name, latitude, longitude "
                "FROM weather_stations WHERE region = %s ORDER BY name",
                params=(region,),
            )
        else:
            rows = execute_select(
                "SELECT station_id, name, latitude, longitude "
                "FROM weather_stations ORDER BY name"
            )
        return json.dumps({
            "data": rows,
            "meta": {"count": len(rows), "region": region},
        })

    @mcp.tool()
    def get_daily_observations(
        station_id: int,
        year: int | None = None,
        limit: int = 100,
    ) -> str:
        """Retrieve daily weather observations for a station.

        Args:
            station_id: Weather station ID.
            year: Filter by year.
            limit: Maximum rows (default 100, max 5000).
        """
        limit = min(limit, 5000)
        sql = (
            "SELECT date, temperature_min, temperature_max, "
            "precipitation, wind_speed "
            "FROM daily_observations WHERE station_id = %s"
        )
        params = [station_id]

        if year:
            sql += " AND YEAR(date) = %s"
            params.append(year)

        sql += " ORDER BY date DESC"
        rows = execute_select(sql, params=tuple(params), max_rows=limit)
        return json.dumps({
            "data": rows,
            "meta": {"station_id": station_id, "year": year, "count": len(rows)},
        })
```

### 2. Restart the Server

```bash
python -m mcp_server
```

Check the logs — you should see:
```
Registered tools from mcp_server.tools.weather_tools
```

### 3. Test Your Tool

```bash
curl -s http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "get_stations",
      "arguments": {}
    }
  }'
```

### 4. Verify in Tools List

```bash
curl -s http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python -m json.tool
```

Your new tools should appear alongside the example tools.

## Tool Design Rules

1. **Return JSON strings** — Always `json.dumps({...})`.
2. **Stateless** — No mutable module-level state.
3. **Use `execute_select()`** — It validates SQL and enforces limits.
4. **Parameterise queries** — Use `%s` placeholders, never f-strings for SQL.
5. **Document parameters** — Docstrings become MCP parameter descriptions.

## Removing Example Tools

Once you have your own tools, delete `example_tools.py` and `statistics_tools.py`:

```bash
rm mcp_server/tools/example_tools.py
rm mcp_server/tools/statistics_tools.py
```

The discovery engine ignores missing files — no other changes needed.

## Next Steps

- [Tutorial 03: Add Skills](03_add_skills.md)
