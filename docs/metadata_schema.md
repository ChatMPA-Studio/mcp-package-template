# Metadata Schema Documentation

## Overview

The metadata system provides structured, machine-readable descriptions of the MCP server, its dataset, tools, and data provenance.  It follows DCAT (Data Catalog Vocabulary) conventions where applicable.

## Schema Files

Located in `mcp_server/metadata/schema/`:

| Schema | Purpose |
|--------|---------|
| `package.schema.json` | Package identity: name, version, maintainer, runtime |
| `dataset.schema.json` | Dataset description: coverage, publisher, access terms |
| `provenance.schema.json` | Data lineage: sources, processing steps, quality |
| `tool.schema.json` | Tool documentation: parameters, returns, examples |

## Template File

`metadata/template.json` is the base metadata for your project.  Edit it to describe your package, dataset, and data sources.  The manifest generator reads this file and augments it with live introspection data (tool counts, skill lists).

## Manifest Generation

```bash
# Generate metadata/manifest.json
python -m mcp_server.metadata.manifest

# Print to stdout instead
python -m mcp_server.metadata.manifest --stdout

# Via script
bash scripts/generate_manifest.sh
```

The generator:
1. Reads `metadata/template.json`
2. Counts tool modules in `mcp_server/tools/`
3. Lists skills in `mcp_server/skills/`
4. Stamps a generation timestamp
5. Writes `metadata/manifest.json`

## MCP Resource Access

The manifest is exposed via MCP resources:

| Resource URI | Content |
|-------------|---------|
| `mcp://metadata/manifest` | Full manifest JSON |
| `mcp://metadata/package` | Package section only |
| `mcp://metadata/dataset` | Dataset section only |

## Customisation Guide

### 1. Edit `metadata/template.json`

Fill in all sections:

```json
{
  "package": {
    "name": "my-data-mcp",
    "version": "1.0.0",
    "description": "...",
    "maintainer": { "name": "...", "email": "..." }
  },
  "dataset": {
    "title": "My Dataset",
    "description": "...",
    "keywords": ["..."],
    "spatial_coverage": { ... },
    "temporal_coverage": { ... }
  },
  "provenance": {
    "source_systems": [{ "name": "...", "type": "MySQL" }],
    "processing": { "steps": ["Step 1", "Step 2"] }
  }
}
```

### 2. Run the Generator

```bash
bash scripts/generate_manifest.sh
```

### 3. Commit the Manifest

```bash
git add metadata/manifest.json
git commit -m "Update metadata manifest"
```

## Schema Validation

The schemas use JSON Schema draft 2020-12.  You can validate your template against them:

```bash
# Using Python jsonschema
pip install jsonschema
python -c "
import json, jsonschema
schema = json.load(open('mcp_server/metadata/schema/package.schema.json'))
data = json.load(open('metadata/template.json'))
jsonschema.validate(data['package'], schema)
print('Valid!')
"
```
