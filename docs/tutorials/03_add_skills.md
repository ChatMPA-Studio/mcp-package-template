# Tutorial 03: Add Skills

## Goal

Create a guided workflow skill that orchestrates multiple tools.

## Prerequisites

- Completed [Tutorial 02](02_add_tools.md)
- At least one working tool

## Steps

### 1. Create a Skill File

Create `skills/weather-report/SKILL.md`:

```markdown
---
name: weather-report
description: Generate a daily weather summary for a station by combining observation data with statistical analysis.
version: 1.0.0
inputs: station_id (integer)
outputs: formatted weather report with statistics
---

# Weather Report Skill

## Purpose

Generate a comprehensive weather summary for a specific station.

## Workflow

### Step 1: Get Station Info

**Tool:** `get_stations`
**Parameters:** None (or filter by region if known)
**Goal:** Find the target station and confirm it exists.

### Step 2: Retrieve Recent Observations

**Tool:** `get_daily_observations`
**Parameters:** `{"station_id": <from step 1>, "limit": 30}`
**Goal:** Get the last 30 days of data.

### Step 3: Compute Temperature Statistics

**Tool:** `descriptive_stats`
**Parameters:** `{"values": [<temperature_max values from step 2>]}`
**Interpret:** Mean = average high temperature; std_dev = day-to-day variability.

### Step 4: Compute Precipitation Statistics

**Tool:** `descriptive_stats`
**Parameters:** `{"values": [<precipitation values from step 2>]}`
**Interpret:** Sum = total precipitation; count of non-zero days = rainy days.

### Step 5: Synthesise Report

Combine findings into a report:
- Station name and location
- Date range covered
- Temperature: mean, min, max, trend
- Precipitation: total, rainy days, dry days
- Notable extremes

## Success Criteria

- All 4 tool calls completed
- Report includes temperature and precipitation statistics
- Date range clearly stated
```

### 2. Add a Contract and Register It

Add the input schema at `skills/contracts/weather_report.schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Weather Report Inputs",
  "type": "object",
  "properties": {
    "station_id": {"type": "integer", "description": "Target station ID. Required."}
  },
  "required": ["station_id"],
  "additionalProperties": false
}
```

Then add an entry in `skills/registry.py` (optional, but keeps the catalog useful).

### 2b. Add Reference Material (Optional)

For skills that need supplementary context:

```
skills/
    weather-report/
        SKILL.md           # The skill definition above
        references/
            climate_norms.md  # Automatically appended to the prompt
```

### 3. Restart and Verify

```bash
python -m mcp_server
```

Check prompts list:

```bash
curl -s http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"prompts/list","params":{}}' | python -m json.tool
```

### 4. Retrieve the Skill

```bash
curl -s http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"prompts/get","params":{"name":"weather-report"}}' | python -m json.tool
```

## Skill Design Guidelines

1. **Orchestrate tools** — Reference existing tools by name; don't duplicate logic.
2. **Be explicit** — Specify exact tool names and parameter formats.
3. **Guide interpretation** — Tell the AI assistant how to read results.
4. **Define success** — What constitutes a complete run.
5. **Use references** — Put supporting documentation in `references/`.

## Next Steps

- [Tutorial 04: Add Metadata](04_add_metadata.md)
