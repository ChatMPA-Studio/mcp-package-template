"""Manifest generator — build manifest.json from template.json + live introspection.

Usage:
    python -m mcp_server.metadata.manifest          # writes metadata/manifest.json
    python -m mcp_server.metadata.manifest --stdout  # prints to stdout

The generator:
  1. Reads ``metadata/template.json`` as the base manifest.
  2. Introspects registered tools and skills to update endpoint counts.
  3. Stamps a generation timestamp.
  4. Writes the result to ``metadata/manifest.json``.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE_PATH = PROJECT_ROOT / "metadata" / "template.json"
OUTPUT_PATH = PROJECT_ROOT / "metadata" / "manifest.json"


def _count_tools() -> tuple[int, list[str]]:
    """Introspect tool modules and return (count, category_names)."""
    tools_dir = PROJECT_ROOT / "mcp_server" / "tools"
    categories: list[str] = []
    count = 0

    if tools_dir.is_dir():
        for py_file in sorted(tools_dir.glob("*.py")):
            name = py_file.stem
            if name.startswith("_") or name == "discovery":
                continue
            # Convert filename to category label
            label = name.replace("_", " ").title()
            categories.append(label)
            count += 1  # approximate — one module = one category

    return count, categories


def _count_skills() -> tuple[int, list[str]]:
    """List skill names from the skills directory."""
    skills_dir = PROJECT_ROOT / "mcp_server" / "skills"
    names: list[str] = []

    if skills_dir.is_dir():
        # Nested layout
        for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
            names.append(skill_file.parent.name)
        # Flat layout
        for skill_file in sorted(skills_dir.glob("*.md")):
            if not skill_file.stem.startswith("_"):
                names.append(skill_file.stem)

    return len(names), names


def generate_manifest() -> dict:
    """Build the full manifest dict."""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Template not found at {TEMPLATE_PATH}. "
            "Create metadata/template.json first."
        )

    manifest = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))

    # Update endpoint counts from live introspection
    tool_count, tool_categories = _count_tools()
    skill_count, skill_names = _count_skills()

    endpoints = manifest.setdefault("endpoints", {})
    endpoints.setdefault("tools", {})["categories"] = tool_categories
    endpoints.setdefault("skills", {})["count"] = skill_count
    endpoints["skills"]["available"] = skill_names

    # Stamp generation time
    manifest["generated"] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "generator": "mcp_server.metadata.manifest",
        "version": "1.0.0",
    }

    return manifest


def write_manifest(to_stdout: bool = False) -> None:
    """Generate and write the manifest."""
    manifest = generate_manifest()
    output = json.dumps(manifest, indent=2, ensure_ascii=False)

    if to_stdout:
        print(output)
    else:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(output + "\n", encoding="utf-8")
        print(f"Manifest written to {OUTPUT_PATH}")


# Allow running as: python -m mcp_server.metadata.manifest
if __name__ == "__main__":
    to_stdout = "--stdout" in sys.argv
    write_manifest(to_stdout=to_stdout)
