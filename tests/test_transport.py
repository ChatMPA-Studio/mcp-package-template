"""Tests for what the HTTP app puts on the wire (mcp_server/__main__.py and
TemplateMCP in mcp_server/server.py). Adapted from ltem-db-mcp.

Each guards one of the reasons a 7.7 MB result once cost 15 MB on the wire in
ltem-db-mcp: a second copy of the payload in structuredContent, an SSE body gzip
won't touch, and no compression. Drives the app in-process with Starlette's
TestClient and only calls tools/list — no data source needed.
"""

import asyncio

import pytest
from starlette.testclient import TestClient

from mcp_server.__main__ import build_app
from mcp_server.config import MCP_BASE_PATH
from mcp_server.server import mcp

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}
LIST_TOOLS = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}


@pytest.fixture(scope="module")
def client():
    with TestClient(build_app(), base_url="http://localhost") as c:
        yield c


def test_no_tool_has_an_output_schema():
    # With an output schema FastMCP sends each result twice (content[0].text and
    # structuredContent), so a tool registered without TemplateMCP.tool()'s
    # default would quietly double its response size again.
    tools = asyncio.run(mcp.list_tools())
    assert tools
    assert [t.name for t in tools if t.output_schema is not None] == []


def test_responses_are_plain_json_not_sse(client):
    resp = client.post(MCP_BASE_PATH, headers=HEADERS, json=LIST_TOOLS)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json()["result"]["tools"]


def test_gzipped_when_the_client_accepts_it(client):
    resp = client.post(MCP_BASE_PATH, headers={**HEADERS, "Accept-Encoding": "gzip"}, json=LIST_TOOLS)
    assert resp.headers.get("content-encoding") == "gzip"
    # httpx decompresses transparently, as any MCP client's HTTP layer does
    assert resp.json()["result"]["tools"]


def test_uncompressed_when_the_client_does_not_ask(client):
    resp = client.post(MCP_BASE_PATH, headers={**HEADERS, "Accept-Encoding": "identity"}, json=LIST_TOOLS)
    assert "content-encoding" not in resp.headers
    assert resp.json()["result"]["tools"]
