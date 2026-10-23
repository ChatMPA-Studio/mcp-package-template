"""Tool modules — auto-discovered by mcp_server/server.py.

Each module here that defines ``register(mcp)`` has it called at startup;
inside it, define tools with ``@mcp.tool()``. Modules whose name starts with
``_`` are skipped (use them for shared helpers).
"""
