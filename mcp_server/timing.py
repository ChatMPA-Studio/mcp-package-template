"""One log line per tool call: total time, time spent in the data source,
source calls, rows read, and response size.

Exists so a slow call in production can be split without guessing. A large
total with a small source_ms is time spent in Python or serialization; a large
``bytes`` is time spent on the wire (in ltem-db-mcp, most of a 76 s call was
the download of a 15 MB response, not the query).

The data source records into ``source_stats`` (see ``record_source_call``):
db.py does it per query; an API client would do it per HTTP request.
"""

import logging
import time
from contextvars import ContextVar

import mcp.types as mt
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools import ToolResult

logger = logging.getLogger(__name__)

# Data-source time spent by the current tool call. It holds a dict that is
# mutated, not rebound: sync tools run in a worker thread on a copy of the
# context, so a rebind there would never reach the middleware, but the dict is
# shared.
source_stats: ContextVar[dict | None] = ContextVar("source_stats", default=None)


def record_source_call(started: float, rows: int) -> None:
    """Add one data-source call (query or HTTP request) to the current tool call.

    ``started`` is a ``time.perf_counter()`` value taken before the call. A no-op
    outside a tool call (e.g. at startup).
    """
    stats = source_stats.get()
    if stats is not None:
        stats["calls"] += 1
        stats["rows"] += rows
        stats["seconds"] += time.perf_counter() - started


class ToolTimingMiddleware(Middleware):
    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        stats = {"calls": 0, "rows": 0, "seconds": 0.0}
        token = source_stats.set(stats)
        started = time.perf_counter()
        status, size = "error", 0
        try:
            result = await call_next(context)
            status = "error" if result.is_error else "ok"
            # Uncompressed size of the result text; gzip shrinks it on the wire.
            size = sum(len(getattr(block, "text", "")) for block in result.content)
            return result
        finally:
            source_stats.reset(token)
            logger.info(
                "tool=%s status=%s total_ms=%.0f source_ms=%.0f calls=%d rows=%d bytes=%d",
                context.message.name, status, (time.perf_counter() - started) * 1000,
                stats["seconds"] * 1000, stats["calls"], stats["rows"], size,
            )
