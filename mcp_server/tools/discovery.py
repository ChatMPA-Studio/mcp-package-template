"""Tool auto-discovery — import every module in this package and call register(mcp).

How it works
------------
1. Iterates over all Python modules in ``mcp_server/tools/``.
2. Skips modules whose names start with ``_`` (private / helpers).
3. For each module that exposes a ``register(mcp)`` function, calls it —
   which registers the module's tools with the FastMCP server instance.
4. Modules without ``register()`` are silently skipped.

Adding a new tool module
------------------------
1. Create ``mcp_server/tools/my_tools.py``.
2. Define a ``register(mcp: FastMCP) -> None`` function.
3. Inside it, use ``@mcp.tool()`` to register individual tools.
4. Restart the server — the module will be picked up automatically.
"""

import importlib
import logging
import pkgutil

from fastmcp import FastMCP

logger = logging.getLogger(__name__)


def discover_tools(mcp: FastMCP) -> None:
    """Import every module in ``mcp_server.tools`` and call its ``register(mcp)``."""
    import mcp_server.tools as tools_pkg

    count = 0
    for _importer, module_name, _is_pkg in pkgutil.iter_modules(tools_pkg.__path__):
        if module_name.startswith("_") or module_name == "discovery":
            continue
        try:
            mod = importlib.import_module(f"mcp_server.tools.{module_name}")
            if hasattr(mod, "register"):
                mod.register(mcp)
                count += 1
                logger.info("Registered tools from mcp_server.tools.%s", module_name)
            else:
                logger.debug(
                    "Skipped mcp_server.tools.%s (no register function)", module_name
                )
        except Exception:
            logger.exception("Failed to load mcp_server.tools.%s", module_name)

    logger.info("Tool discovery complete: %d modules registered", count)
