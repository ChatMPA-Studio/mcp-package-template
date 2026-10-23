"""Run the MCP Server as an HTTP service.

Usage:
    python -m mcp_server

Environment variables (see .env.example for the full list):
    PORT             HTTP port to bind (default: 8000)
    MCP_BASE_PATH    Endpoint path (default: /mcp)
    LOG_LEVEL        Logging verbosity (default: INFO)
    MCP_DATA_SOURCE  Where tools get their data (default: db)
    AUTH_ENABLED     Require Authorization: Bearer <key> on every request
                     (default: false — see mcp_server/auth.py)

Startup checks the configuration the selected data source needs and exits with
a clear message if something is missing, so a misconfigured container stops at
once instead of failing on its first request.
"""

import uvicorn
from starlette.middleware import Middleware
from starlette.middleware.gzip import GZipMiddleware

from mcp_server import source
from mcp_server.config import (
    MCP_BASE_PATH,
    PORT,
    check_required,
    print_startup_summary,
    setup_logging,
)
from mcp_server.server import mcp


def build_app():
    """The ASGI app, built apart from serving it so tests can drive it in-process."""
    # stateless_http=True: no session state kept between requests, required so
    # N replicas behind a load balancer can each answer any request
    # interchangeably. Auth is attached to the FastMCP instance itself
    # (mcp_server/server.py), not as Starlette middleware, so its transport
    # enforces it on every request.
    return mcp.http_app(
        path=MCP_BASE_PATH,
        stateless_http=True,
        # Answer with plain JSON instead of an SSE stream: Starlette's
        # GZipMiddleware never compresses text/event-stream, and no tool streams
        # progress mid-call, so SSE buys nothing here. MCP clients must accept
        # both (the spec requires it).
        json_response=True,
        # Results are JSON text that compresses 10-25x (in ltem-db-mcp, 7.7 MB to
        # 0.6 MB). Level 6 instead of Starlette's default 9: on that response 9
        # saves 8% more bytes but takes 5x the CPU. Clients that don't send
        # Accept-Encoding: gzip get it uncompressed.
        middleware=[Middleware(GZipMiddleware, minimum_size=1024, compresslevel=6)],
    )


if __name__ == "__main__":
    setup_logging()
    check_required()
    print_startup_summary()
    source.warmup()
    # Keep idle connections open longer than the load balancer's idle timeout
    # (60 s on an AWS ALB unless configured otherwise; uvicorn's default is 5 s),
    # so it never reuses a connection uvicorn already closed — that surfaces as
    # a sporadic 502.
    uvicorn.run(build_app(), host="0.0.0.0", port=PORT, timeout_keep_alive=65)
