# Tutorial 04: Add Metadata

## Goal

Fill in project metadata and generate a discoverable manifest.

## Steps

### 1. Edit the Template

Open `metadata/template.json` and fill in each section:

**Package section:**
```json
{
  "package": {
    "name": "my-weather-mcp",
    "version": "1.0.0",
    "description": "MCP server for weather observation data from 50 stations across the Pacific Northwest.",
    "maintainer": {
      "name": "Jane Scientist",
      "email": "jane@weather-lab.org",
      "organization": "Pacific Weather Lab"
    },
    "license": "MIT"
  }
}
```

**Dataset section:**
```json
{
  "dataset": {
    "title": "Pacific Northwest Weather Observations",
    "description": "Daily temperature, precipitation, and wind observations from 50 automated weather stations.",
    "keywords": ["weather", "temperature", "precipitation", "Pacific Northwest"],
    "spatial_coverage": {
      "description": "Pacific Northwest, USA",
      "bounding_box": {"north": 49.0, "south": 42.0, "east": -116.0, "west": -125.0}
    },
    "temporal_coverage": {
      "start": "2010-01-01",
      "end": "2025-12-31",
      "frequency": "daily"
    }
  }
}
```

**Provenance section:**
```json
{
  "provenance": {
    "source_systems": [
      {"name": "Weather Station Network", "type": "MySQL", "description": "Automated weather stations with hourly data aggregated to daily."}
    ],
    "processing": {
      "steps": [
        "Quality control: flag values outside physical bounds",
        "Gap filling: linear interpolation for gaps < 3 hours",
        "Daily aggregation: min/max/mean from hourly records"
      ]
    },
    "quality": {
      "completeness": 0.95,
      "accuracy": "Instruments calibrated annually per WMO standards"
    }
  }
}
```

### 2. Generate the Manifest

```bash
bash scripts/generate_manifest.sh
```

This creates `metadata/manifest.json` with your template data plus auto-detected tool and skill counts.

### 3. Verify via MCP Resource

```bash
curl -s http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"resources/read","params":{"uri":"mcp://metadata/package"}}' | python -m json.tool
```

### 4. Commit

```bash
git add metadata/manifest.json metadata/template.json
git commit -m "Add project metadata"
```

## Schema Validation

Validate your metadata against the JSON schemas:

```python
import json, jsonschema

schema = json.load(open("mcp_server/metadata/schema/package.schema.json"))
template = json.load(open("metadata/template.json"))
jsonschema.validate(template["package"], schema)
print("Package metadata is valid!")
```

## Next Steps

- [Tutorial 05: Dockerize and Run](05_dockerize_and_run.md)
