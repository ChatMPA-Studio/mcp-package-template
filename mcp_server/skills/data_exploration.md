---
name: data-exploration
description: Guided workflow for exploring an unfamiliar dataset — check connectivity, discover schema, compute summary statistics, and identify data quality issues.
version: 1.0.0
inputs: none (uses database connection from server config)
outputs: structured exploration report
---

# Data Exploration Skill

## Purpose

Walk through a systematic dataset exploration when connecting to a new
or unfamiliar database.  This skill orchestrates existing tools in the
correct order — it does not duplicate their logic.

## Workflow

### Step 1: Verify Connectivity

**Tool:** `health_check`
**Parameters:** None
**Goal:** Confirm the database is reachable and return version info.

### Step 2: Discover Schema

If the server exposes schema tools (list_tables, describe_table), call them:

**Tool:** `list_tables` (if available)
**Tool:** `describe_table` (if available, for each table)

### Step 3: Sample Data

Retrieve a small sample to understand the data shape:

**Tool:** A query/observation tool (e.g., `get_observations` with `limit=10`)

### Step 4: Compute Summary Statistics

Use the `descriptive_stats` tool on key numeric columns:

**Tool:** `descriptive_stats`
**Parameters:** `{"values": [<extracted column values>]}`

### Step 5: Document Findings

Summarise:
- Number of tables and columns
- Row counts
- Data types and ranges
- Missing data rates
- Key relationships identified

## Success Criteria

A complete exploration report includes:
- Database version and connectivity status
- Table and column inventory
- Sample data for each table
- Descriptive statistics for numeric fields
- Any data quality flags observed
