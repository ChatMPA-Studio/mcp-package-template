"""MCP Server — FastMCP entry point.

Creates the MCP server instance, registers resources, core tools,
auto-discovers tool modules from mcp_server/tools/, and registers
skills from the top-level skills/ directory as MCP prompts.
"""

import json
import logging
from pathlib import Path

from fastmcp import FastMCP

from mcp_server.db import test_connection
from mcp_server.tools.discovery import discover_tools
from mcp_server.prompts import discover_prompts

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Create the MCP server instance
# ---------------------------------------------------------------------------
# CUSTOMIZE: Change "My MCP Server" to your project's name.

mcp = FastMCP("My MCP Server")

# ---------------------------------------------------------------------------
# MCP Resources (static + dynamic)
# ---------------------------------------------------------------------------

@mcp.resource("mcp://hello")
def hello_resource() -> str:
    """A minimal 'hello world' resource to verify the server is alive."""
    return json.dumps({
        "message": "Hello from the MCP server!",
        "hint": "Replace this resource with something useful for your domain.",
    })


@mcp.resource("mcp://metadata/manifest")
def metadata_manifest_resource() -> str:
    """Full metadata manifest (auto-generated from template.json)."""
    manifest_path = Path(__file__).resolve().parent.parent / "metadata" / "manifest.json"
    if manifest_path.exists():
        return manifest_path.read_text(encoding="utf-8")
    return json.dumps({
        "error": "Manifest not found. Run: python -m mcp_server.metadata.manifest",
    })


@mcp.resource("mcp://metadata/package")
def metadata_package_resource() -> str:
    """Package metadata: name, version, description, license, runtime."""
    manifest_path = Path(__file__).resolve().parent.parent / "metadata" / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return json.dumps(manifest.get("package", {}), indent=2)
    return json.dumps({"error": "Manifest not found"})


@mcp.resource("mcp://metadata/dataset")
def metadata_dataset_resource() -> str:
    """Dataset metadata: title, description, coverage, publisher (DCAT-like)."""
    manifest_path = Path(__file__).resolve().parent.parent / "metadata" / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return json.dumps(manifest.get("dataset", {}), indent=2)
    return json.dumps({"error": "Manifest not found"})


# ---------------------------------------------------------------------------
# Core tools (health check)
# ---------------------------------------------------------------------------

@mcp.tool()
def health_check() -> str:
    """Verify database connectivity and return server info."""
    try:
        info = test_connection()
        return json.dumps({"status": "ok", **info})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ---------------------------------------------------------------------------
# Auto-discover tools and skills
# ---------------------------------------------------------------------------

discover_tools(mcp)
discover_prompts(mcp)
