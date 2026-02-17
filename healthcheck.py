"""Docker health check — verify the MCP HTTP server is accepting connections."""

import os
import socket
import sys

port = int(os.environ.get("PORT", "8000"))
try:
    s = socket.create_connection(("localhost", port), timeout=3)
    s.close()
except Exception:
    sys.exit(1)
