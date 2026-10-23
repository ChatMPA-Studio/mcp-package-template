"""MCP Server — FastMCP entry point.

Creates the MCP server instance (with optional API-key auth and per-call
timing), registers resources and core tools, auto-discovers tool modules from
tools/, and registers skills from skills/ as MCP prompts.

The server never talks to the data source directly: it goes through
mcp_server/source.py, so the source can be swapped or removed (see
MCP_DATA_SOURCE in mcp_server/config.py).
"""

import importlib
import json
import logging
import pkgutil
from pathlib import Path

from fastmcp import FastMCP

from mcp_server import config, source
from mcp_server.prompts import discover_prompts
from mcp_server.timing import ToolTimingMiddleware

logger = logging.getLogger(__name__)

MANIFEST_PATH = Path(__file__).resolve().parent.parent / "metadata" / "manifest.json"

# ---------------------------------------------------------------------------
# Create the MCP server instance
# ---------------------------------------------------------------------------


class TemplateMCP(FastMCP):
    """FastMCP whose tools default to output_schema=None.

    Every tool returns its result already serialized as a JSON string. For a
    ``-> str`` tool FastMCP's default is an output schema that wraps that
    string, so each response carried the payload twice: in content[0].text and
    again in structuredContent.result, doubling what goes over the wire.
    Without the schema only content[0].text is sent, which is what clients read
    when there is no structuredContent (ChatMPA's orchestrator falls back to
    json.loads() of it). Set here rather than on each decorator so tools added
    later get it too. From ltem-db-mcp.
    """

    def tool(self, *args, **kwargs):
        kwargs.setdefault("output_schema", None)
        return super().tool(*args, **kwargs)


def _build_auth():
    if not config.AUTH_ENABLED:
        return None
    from mcp_server.auth import build_auth
    return build_auth()


# CUSTOMIZE: Change "My MCP Server" to your project's name.
# With AUTH_ENABLED, FastMCP's auth layer requires a valid bearer key on every
# HTTP request — there is no unauthenticated path left (see mcp_server/auth.py).
mcp = TemplateMCP(
    "My MCP Server",
    auth=_build_auth(),
    middleware=[ToolTimingMiddleware()],
)

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


def _manifest() -> dict | None:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return None


@mcp.resource("mcp://metadata/manifest")
def metadata_manifest_resource() -> str:
    """Full metadata manifest (auto-generated from template.json)."""
    manifest = _manifest()
    if manifest is not None:
        return json.dumps(manifest, indent=2)
    return json.dumps({"error": "Manifest not found. Run: python scripts/generate_metadata_manifest.py"})


@mcp.resource("mcp://metadata/package")
def metadata_package_resource() -> str:
    """Package metadata: name, version, description, license, runtime."""
    manifest = _manifest()
    if manifest is not None:
        return json.dumps(manifest.get("package", {}), indent=2)
    return json.dumps({"error": "Manifest not found"})


@mcp.resource("mcp://metadata/dataset")
def metadata_dataset_resource() -> str:
    """Dataset metadata: title, description, coverage, publisher (DCAT-like)."""
    manifest = _manifest()
    if manifest is not None:
        return json.dumps(manifest.get("dataset", {}), indent=2)
    return json.dumps({"error": "Manifest not found"})


# ---------------------------------------------------------------------------
# Core tools
# ---------------------------------------------------------------------------

@mcp.tool(tags={"internal"})
def health_check() -> str:
    """Check that the server's data source answers and return its info.

    Technical diagnostic tool. Reports the selected data source, and what is
    missing from its configuration if it is not set up.
    """
    return json.dumps(source.health())


def _register_db_schema_tools() -> None:
    """Schema-discovery tools — only meaningful for the database source."""
    from mcp_server.schema import build_schema_snapshot, describe_table, discover_tables

    @mcp.tool(tags={"internal"})
    def list_tables() -> str:
        """List the tables in the database. Technical schema-exploration tool."""
        try:
            tables = discover_tables()
            return json.dumps({"tables": tables, "count": len(tables)})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(name="describe_table", tags={"internal"})
    def describe_table_tool(table: str) -> str:
        """Describe the columns and data types of a whitelisted table.

        Args:
            table: Table name, as listed in mcp_server/security.py ALLOWED_TABLES.
        """
        try:
            columns = describe_table(table)
            return json.dumps({"table": table, "columns": columns, "column_count": len(columns)})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(tags={"internal"})
    def schema_snapshot() -> str:
        """Full snapshot of the whitelisted tables: columns, types and row counts."""
        try:
            return json.dumps(build_schema_snapshot(), indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})


if config.MCP_DATA_SOURCE == "db":
    _register_db_schema_tools()

# ---------------------------------------------------------------------------
# Auto-discover tool modules from tools/ and skills from skills/
# ---------------------------------------------------------------------------


def _discover_tools() -> None:
    """Import every module in the tools/ package and call its register(mcp).

    To add tools: create ``tools/my_tools.py`` with a ``register(mcp)`` function
    that defines them with ``@mcp.tool()``. Modules whose name starts with ``_``
    are skipped. No other registration is needed.
    """
    import tools as tools_pkg

    count = 0
    for _importer, module_name, _is_pkg in pkgutil.iter_modules(tools_pkg.__path__):
        if module_name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"tools.{module_name}")
            if hasattr(mod, "register"):
                mod.register(mcp)
                count += 1
                logger.info("Registered tools from tools.%s", module_name)
            else:
                logger.debug("Skipped tools.%s (no register function)", module_name)
        except Exception:
            logger.exception("Failed to load tools.%s", module_name)
    logger.info("Tool discovery complete: %d modules registered", count)


_discover_tools()
discover_prompts(mcp)
