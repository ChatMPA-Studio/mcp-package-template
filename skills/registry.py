"""Skills registry for this MCP server.

Catalogs available analytical skills with metadata, tool dependencies,
and input/output contracts. Developer reference only — not loaded at runtime.
The runtime registration path is mcp_server/prompts.py, which discovers
skills/*/SKILL.md directly and does not read this file.

CUSTOMIZE: Replace the three example entries with your own skills as you
add them under skills/<name>/SKILL.md.
"""

from typing import Dict, List, Optional

SKILLS_REGISTRY: Dict[str, Dict] = {
    "example-health-check": {
        "name": "Health Check",
        "description": "Verify MCP server health by calling basic tools and validating responses.",
        "version": "1.0.0",
        "inputs_schema": "skills/contracts/example_health_check.schema.json",
        "outputs_schema": "skills/contracts/example_health_check.schema.json",
        "estimated_duration": "5 seconds",
        "tools_required": ["echo", "server_time", "calculator"],
        "tags": ["health", "smoke-test"],
    },
    "data-exploration": {
        "name": "Data Exploration",
        "description": "Systematic exploration of an unfamiliar dataset: connectivity, schema, sample data, summary statistics.",
        "version": "1.0.0",
        "inputs_schema": "skills/contracts/data_exploration.schema.json",
        "outputs_schema": "skills/contracts/data_exploration.schema.json",
        "estimated_duration": "30 seconds",
        "tools_required": ["health_check", "descriptive_stats"],
        "tags": ["exploration", "schema", "onboarding"],
    },
    "statistical-analysis": {
        "name": "Statistical Analysis",
        "description": "Descriptive and comparative statistical analysis using the built-in statistics tools.",
        "version": "1.0.0",
        "inputs_schema": "skills/contracts/statistical_analysis.schema.json",
        "outputs_schema": "skills/contracts/statistical_analysis.schema.json",
        "estimated_duration": "15 seconds",
        "tools_required": ["descriptive_stats", "percentile", "correlation"],
        "tags": ["statistics", "correlation", "distribution"],
    },
}


def list_skills() -> List[Dict]:
    return [{"id": sid, **meta} for sid, meta in SKILLS_REGISTRY.items()]


def get_skill(skill_id: str) -> Optional[Dict]:
    return SKILLS_REGISTRY.get(skill_id)


def list_skills_by_tag(tag: str) -> List[Dict]:
    return [
        {"id": sid, **meta}
        for sid, meta in SKILLS_REGISTRY.items()
        if tag in meta.get("tags", [])
    ]


def get_skill_count() -> int:
    return len(SKILLS_REGISTRY)
