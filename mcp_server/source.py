"""The active data source — the only place that knows which one is selected.

``MCP_DATA_SOURCE`` (mcp_server/config.py) chooses it. The server and the
startup code talk to the source only through ``health()`` and ``warmup()``,
so a source can be removed from a new MCP without touching them:

* ``db``  — project database: mcp_server/db.py + mcp_server/security.py
            (+ mcp_server/schema.py for the schema-discovery tools).

Each source module is imported lazily, so the other source's dependencies and
credentials are never needed.
"""

import logging

from mcp_server import config

logger = logging.getLogger(__name__)


def health() -> dict:
    """Check that the data source answers. Never raises: returns a status dict."""
    problems = config.missing_required()
    if problems:
        return {"status": "error", "source": config.MCP_DATA_SOURCE,
                "error": "data source not configured", "problems": problems}
    try:
        if config.MCP_DATA_SOURCE == "db":
            from mcp_server.db import test_connection
            return {"status": "ok", "source": "db", **test_connection()}
    except Exception as e:
        return {"status": "error", "source": config.MCP_DATA_SOURCE, "error": str(e)}
    return {"status": "error", "source": config.MCP_DATA_SOURCE,
            "error": f"unknown data source {config.MCP_DATA_SOURCE!r}"}


def warmup() -> None:
    """Open connections / prepare clients at startup. Best effort, never raises."""
    if config.MCP_DATA_SOURCE == "db":
        from mcp_server.db import warm_pool
        warm_pool()
