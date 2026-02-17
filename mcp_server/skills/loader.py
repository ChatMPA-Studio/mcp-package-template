"""Skill loader — auto-discover skills and register them as MCP prompts.

Reads every ``mcp_server/skills/*.md`` file (or ``skills/<name>/SKILL.md``
in nested layout), parses its YAML frontmatter, and registers it as an
MCP prompt so any remote client can discover guided workflows.

If a skill directory contains a ``references/`` subdirectory, all ``.md``
files within it are appended to the prompt body as supplementary context.

Supported layouts
-----------------
Flat::

    mcp_server/skills/
        my_skill.md          # frontmatter + body

Nested::

    mcp_server/skills/
        my_skill/
            SKILL.md         # frontmatter + body
            references/
                extra.md     # appended to body
"""

import logging
import re
from pathlib import Path

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# YAML frontmatter parser (minimal — avoids pyyaml dependency)
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return ``(metadata_dict, body)`` from a skill markdown file."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text

    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta, text[m.end():]


# ---------------------------------------------------------------------------
# Reference file loader
# ---------------------------------------------------------------------------

def _load_references(skill_dir: Path) -> str:
    """Concatenate all ``.md`` files under ``skill_dir/references/``."""
    refs_dir = skill_dir / "references"
    if not refs_dir.is_dir():
        return ""

    parts: list[str] = []
    for ref_file in sorted(refs_dir.glob("*.md")):
        content = ref_file.read_text(encoding="utf-8")
        parts.append(f"\n\n---\n## Reference: {ref_file.stem}\n\n{content}")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def discover_prompts(mcp: FastMCP) -> None:
    """Find all skill definitions and register each as an MCP prompt."""
    if not SKILLS_DIR.is_dir():
        logger.warning("skills/ directory not found at %s", SKILLS_DIR)
        return

    count = 0

    # Nested layout: skills/<name>/SKILL.md
    for skill_file in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        if _register_skill_file(mcp, skill_file, skill_file.parent):
            count += 1

    # Flat layout: skills/*.md (excluding __init__.py, loader.py, registry.py)
    for skill_file in sorted(SKILLS_DIR.glob("*.md")):
        if skill_file.stem.startswith("_"):
            continue
        if _register_skill_file(mcp, skill_file, SKILLS_DIR):
            count += 1

    logger.info("Skill discovery complete: %d prompts registered", count)


def _register_skill_file(mcp: FastMCP, skill_file: Path, ref_base: Path) -> bool:
    """Parse and register a single skill file.  Returns True on success."""
    try:
        raw = skill_file.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(raw)

        skill_id = skill_file.parent.name if skill_file.name == "SKILL.md" else skill_file.stem
        name = meta.get("name", skill_id)
        description = meta.get("description", f"Guided workflow: {name}")

        refs = _load_references(ref_base)
        full_body = body.strip() + refs

        _register_prompt(mcp, name, description, full_body)
        logger.info("Registered prompt: %s", name)
        return True

    except Exception:
        logger.exception("Failed to register prompt from %s", skill_file)
        return False


def _register_prompt(mcp: FastMCP, name: str, description: str, body: str) -> None:
    """Register a single skill as an MCP prompt."""

    @mcp.prompt(name=name, description=description)
    def _prompt() -> str:
        return body

    _prompt.__name__ = f"prompt_{name.replace('-', '_')}"
    _prompt.__qualname__ = _prompt.__name__
