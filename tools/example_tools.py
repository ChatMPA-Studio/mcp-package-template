"""Example tool module — demonstrates the tool registration pattern.

This module provides simple, stateless tools to illustrate how to build
MCP tools.  Replace or extend these with your own domain-specific tools.

Each tool:
  - Returns a JSON string (FastMCP convention).
  - Is stateless — no side effects, no shared state between calls.
  - Is composable — designed to be chained by skills or client orchestration.
"""

import json
import math
from datetime import datetime, timezone

from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register example tools with the MCP server."""

    @mcp.tool()
    def echo(message: str) -> str:
        """Echo a message back — useful for connectivity testing.

        Args:
            message: The message to echo back.
        """
        return json.dumps({
            "echo": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    @mcp.tool()
    def server_time() -> str:
        """Return the current server time in ISO-8601 UTC format."""
        now = datetime.now(timezone.utc)
        return json.dumps({
            "utc": now.isoformat(),
            "unix": int(now.timestamp()),
        })

    @mcp.tool()
    def calculator(operation: str, a: float, b: float) -> str:
        """Perform a basic arithmetic operation.

        Args:
            operation: One of 'add', 'subtract', 'multiply', 'divide', 'power'.
            a: First operand.
            b: Second operand.
        """
        ops = {
            "add": lambda x, y: x + y,
            "subtract": lambda x, y: x - y,
            "multiply": lambda x, y: x * y,
            "divide": lambda x, y: x / y if y != 0 else float("inf"),
            "power": lambda x, y: x ** y,
        }
        if operation not in ops:
            return json.dumps({
                "error": f"Unknown operation '{operation}'. Use: {', '.join(ops)}",
            })
        result = ops[operation](a, b)
        return json.dumps({
            "operation": operation,
            "a": a,
            "b": b,
            "result": result,
        })
