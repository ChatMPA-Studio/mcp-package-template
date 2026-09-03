"""Entry point for stdio transport (e.g. Claude Desktop).

Claude Desktop launches this script directly; no HTTP server needs to be
running.  For the HTTP / Docker deployment use ``python -m mcp_server`` instead.
"""
import os
import sys

# Make the package importable even when launched from another directory.
sys.path.insert(0, os.path.dirname(__file__))

# Load .env from the project directory.
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from mcp_server.server import mcp

mcp.run(transport="stdio")
