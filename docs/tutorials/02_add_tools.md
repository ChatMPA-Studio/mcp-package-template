# Tutorial 02: Add Tools

## Goal

Create a tool module that reads your data and returns structured results.
This tutorial uses the database source (option A). For an external API (option
B), the pattern is the same but the door to the data is different: see
[Tutorial 09](09_api_data_source.md).

## Prerequisites

- Completed [Tutorial 01](01_create_a_new_mcp.md) with `MCP_DATA_SOURCE=db`
- `health_check` answers `"status": "ok"` (`python -m mcp_server` and call it)

## Steps

### 1. Whitelist the tables

In `mcp_server/security.py`:

```python
ALLOWED_TABLES: set[str] = {"weather_stations", "daily_observations"}
```

An empty whitelist blocks every query: list only what the tools need.

### 2. Create a tool module

Create `tools/weather_tools.py` (any module in `tools/` with a `register(mcp)` function is picked up at startup):

```python
"""Weather observation tools."""

import json

from mcp_server.db import execute_select
from mcp_server.security import DEFAULT_MAX_ROWS


def register(mcp) -> None:
    """Register weather tools with the MCP server."""

    @mcp.tool()
    def get_stations(region: str | None = None) -> str:
        """List weather stations, one row per station: station_id, name,
        latitude, longitude (decimal degrees). Optionally filtered by region.

        Args:
            region: Region name exactly as stored, e.g. "Pacific". Omit for all.
        """
        sql = "SELECT station_id, name, latitude, longitude FROM weather_stations"
        params = []
        if region:
            sql += " WHERE region = %s"
            params.append(region)
        rows = execute_select(sql + " ORDER BY name", params=tuple(params))
        return json.dumps({"data": rows, "meta": {"region": region, "returned": len(rows)}},
                          default=str)

    @mcp.tool()
    def get_daily_observations(
        station_id: int,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> str:
        """Daily observations of one station, one row per day: date,
        temperature_min and temperature_max (°C), precipitation (mm), wind_speed
        (m/s). Newest first. Capped at 5000 rows: if meta.truncated is true,
        narrow the years.

        Args:
            station_id: Station ID from get_stations.
            year_from: First year (inclusive), optional.
            year_to: Last year (inclusive), optional.
        """
        sql = ("SELECT date, temperature_min, temperature_max, precipitation, wind_speed "
               "FROM daily_observations WHERE station_id = %s")
        params = [station_id]
        if year_from is not None:
            sql += " AND YEAR(date) >= %s"
            params.append(year_from)
        if year_to is not None:
            sql += " AND YEAR(date) <= %s"
            params.append(year_to)
        # Ask for one row more than the cap to know whether the result was cut.
        rows = execute_select(sql + " ORDER BY date DESC", params=tuple(params),
                              max_rows=DEFAULT_MAX_ROWS + 1)
        truncated = len(rows) > DEFAULT_MAX_ROWS
        rows = rows[:DEFAULT_MAX_ROWS]
        return json.dumps({
            "data": rows,
            "meta": {"station_id": station_id, "year_from": year_from, "year_to": year_to,
                     "returned": len(rows), "truncated": truncated},
        }, default=str)
```

### 3. Restart the server

```bash
python -m mcp_server
```

The logs show `Registered tools from tools.weather_tools`.

### 4. Test your tool

```bash
curl -s http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_stations","arguments":{}}}'
```

The logs show one timing line per call: `tool=get_stations status=ok total_ms=… source_ms=… rows=…`.

### 5. Add a test

Mock the data access so the test needs no database:

```python
from unittest.mock import patch
import asyncio, json
from mcp_server.server import mcp

def test_get_stations_filters_by_region():
    with patch("tools.weather_tools.execute_select", return_value=[{"station_id": 1}]) as q:
        result = asyncio.run(mcp.call_tool("get_stations", {"region": "Pacific"}))
    assert json.loads(result.content[0].text)["data"] == [{"station_id": 1}]
    assert q.call_args.kwargs["params"] == ("Pacific",)
```

## Tool Design Rules

1. **Return JSON strings** — `{"data": [...], "meta": {...}}`.
2. **Stateless** — no mutable module-level state.
3. **One door to the data** — `execute_select()` validates the SQL and caps the rows.
4. **Parameterise queries** — `%s` placeholders and `params=`; never format values into SQL.
5. **Standard parameter names** — generic English names, no `_filter` suffix, ranges as `_from` / `_to`; output columns keep the database's names.
6. **Never cut silently** — report `truncated` when a response is capped.
7. **The docstring is what the model reads** — what it returns, at what level, units and columns; the important part first.
8. **Intermediate rows** — if a tool aggregates many rows in Python, pass `max_rows=AGGREGATION_MAX_ROWS` (from `mcp_server.security`) so the cap never changes the answer.

## Removing Example Tools

Once you have your own tools, delete the examples:

```bash
rm tools/example_tools.py tools/statistics_tools.py
```

Nothing else needs to change; the tests do not depend on them.

## Next Steps

- [Tutorial 03: Add Skills](03_add_skills.md)
- [Tutorial 09: External API data source](09_api_data_source.md)
