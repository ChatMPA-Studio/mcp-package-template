"""Skill registry — programmatic access to available skills and their metadata.

This module provides a function to list all discovered skills with their
input/output contracts, intended for documentation generation or runtime
introspection.  The loader (``loader.py``) handles MCP registration;
this module is a convenience overlay.

Usage::

    from mcp_server.skills.registry import list_skills
    for skill in list_skills():
        print(skill["name"], skill["description"])
"""

import logging
from pathlib import Path

from mcp_server.skills.loader import _parse_frontmatter

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).resolve().parent


def list_skills() -> list[dict]:
    """Return metadata for every discovered skill.

    Each dict contains:
      - name: Skill identifier
      - description: Human-readable summary
      - file: Path to the skill definition
      - has_references: Whether supplementary reference files exist
      - inputs: List of expected input parameters (from frontmatter)
      - outputs: Expected output description (from frontmatter)
    """
    skills: list[dict] = []

    # Nested layout
    for skill_file in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        info = _extract_info(skill_file, skill_file.parent.name)
        if info:
            skills.append(info)

    # Flat layout
    for skill_file in sorted(SKILLS_DIR.glob("*.md")):
        if skill_file.stem.startswith("_"):
            continue
        info = _extract_info(skill_file, skill_file.stem)
        if info:
            skills.append(info)

    return skills


def _extract_info(skill_file: Path, fallback_id: str) -> dict | None:
    """Parse a skill file and return its metadata dict."""
    try:
        raw = skill_file.read_text(encoding="utf-8")
        meta, _body = _parse_frontmatter(raw)

        ref_dir = skill_file.parent / "references"
        return {
            "name": meta.get("name", fallback_id),
            "description": meta.get("description", ""),
            "version": meta.get("version", ""),
            "file": str(skill_file),
            "has_references": ref_dir.is_dir() and any(ref_dir.glob("*.md")),
            "inputs": meta.get("inputs", "none"),
            "outputs": meta.get("outputs", "structured JSON"),
        }
    except Exception:
        logger.exception("Failed to parse skill %s", skill_file)
        return None
