"""Shared pytest fixtures.

The tests in this directory need no database, API, network or AWS
credentials: data sources and the auth table are replaced by fakes. That is
what lets them run in CI and on a fresh clone.

They also adapt to the data source the MCP kept (TEMPLATE.md, step 2): tests
for a source whose files were deleted are skipped, not failed.

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

HAS_DB = (PROJECT_ROOT / "mcp_server" / "db.py").exists()
HAS_API = (PROJECT_ROOT / "mcp_server" / "api_client.py").exists()

os.environ.setdefault("MCP_DATA_SOURCE", "db" if HAS_DB else "api")
os.environ.setdefault("AUTH_REQUIRED_SCOPE", "example")
if not HAS_DB:
    os.environ.setdefault("MCP_API_BASE_URL", "https://api.example.org")


def pytest_collection_modifyitems(config, items):
    """Skip tests marked for a data source whose files are not in this MCP."""
    for item in items:
        if item.get_closest_marker("db") and not HAS_DB:
            item.add_marker(pytest.mark.skip(reason="database source removed from this MCP"))
        if item.get_closest_marker("api") and not HAS_API:
            item.add_marker(pytest.mark.skip(reason="API source removed from this MCP"))


def pytest_configure(config):
    config.addinivalue_line("markers", "db: needs the database source files (mcp_server/db.py)")
    config.addinivalue_line("markers", "api: needs the API source files (mcp_server/api_client.py)")


@pytest.fixture(scope="session")
def mcp_server():
    """Return the initialized MCP server instance with all tools registered."""
    from mcp_server.server import mcp
    return mcp
