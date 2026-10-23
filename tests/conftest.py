"""Shared pytest fixtures.

The tests in this directory need no database, API, network or AWS
credentials: data sources and the auth table are replaced by fakes. That is
what lets them run in CI and on a fresh clone.

Test-only defaults are set *before* importing the package, because
mcp_server.config reads the environment at import time. Values already set in
the environment (or in a local .env) win.
"""

import os
import sys
from pathlib import Path

import pytest

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("MCP_DATA_SOURCE", "db")
os.environ.setdefault("AUTH_REQUIRED_SCOPE", "example")


@pytest.fixture(scope="session")
def mcp_server():
    """Return the initialized MCP server instance with all tools registered."""
    from mcp_server.server import mcp
    return mcp
