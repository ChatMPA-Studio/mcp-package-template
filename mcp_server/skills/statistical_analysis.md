---
name: statistical-analysis
description: Guided workflow for running descriptive and comparative statistical analysis using the built-in statistics tools.
version: 1.0.0
inputs: two numeric series (x and y) for comparison, or one series for descriptive stats
outputs: statistical summary with interpretation
---

# Statistical Analysis Skill

## Purpose

Guide an AI assistant through a basic statistical analysis workflow
using the MCP's statistics tools.  The skill orchestrates tools in the
correct analytical sequence.

## Workflow

### Step 1: Descriptive Statistics

Compute summary statistics for each variable of interest.

**Tool:** `descriptive_stats`
**Parameters:** `{"values": [<your data>]}`
**Interpret:** Check mean vs median (skewness), std_dev (spread), range.

### Step 2: Percentile Analysis

Identify distribution shape and potential outliers.

**Tool:** `percentile`
**Parameters:** `{"values": [<your data>], "p": 25}` (repeat for 50, 75, 95)
**Interpret:** IQR = P75 - P25.  Values beyond P25 - 1.5*IQR or P75 + 1.5*IQR
are potential outliers.

### Step 3: Correlation Analysis (if two variables)

Test for linear relationship between two series.

**Tool:** `correlation`
**Parameters:** `{"x": [<series1>], "y": [<series2>]}`
**Interpret:**
| |r| range   | Interpretation        |
|-------------|------------------------|
| 0.7 - 1.0   | Strong correlation     |
| 0.4 - 0.7   | Moderate correlation   |
| 0.0 - 0.4   | Weak correlation       |

### Step 4: Synthesise Results

Combine findings into a coherent summary:
- Key statistics for each variable
- Distribution characteristics (symmetric, skewed, outliers)
- Relationship strength (if applicable)
- Caveats and limitations (sample size, assumptions)

## Success Criteria

- Descriptive stats computed for all variables
- At least 3 percentiles calculated per variable
- Correlation computed if two variables provided
- Written interpretation with caveats
