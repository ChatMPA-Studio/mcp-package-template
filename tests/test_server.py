"""The server starts and answers without a data source or credentials.

A fresh clone (or CI) has no database and no .env: the server must still load,
list its tools, and say clearly — through health_check — what is missing,
instead of crashing at import time.
"""

import asyncio
import json
import logging

import pytest

from mcp_server import config, source
from mcp_server.server import mcp


def _call(name: str, **args) -> dict:
    result = asyncio.run(mcp.call_tool(name, args))
    return json.loads(result.content[0].text)


@pytest.fixture
def no_db_credentials(monkeypatch):
    monkeypatch.setattr(config, "MCP_DATA_SOURCE", "db")
    monkeypatch.setattr(config, "DATABASE_URL", None)
    for name in ("DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"):
        monkeypatch.setattr(config, name, "")


def test_server_lists_core_and_example_tools():
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert {"health_check", "echo", "server_time"} <= names


def test_db_source_registers_schema_tools():
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert {"list_tables", "describe_table", "schema_snapshot"} <= names


def test_health_check_reports_missing_configuration(no_db_credentials):
    report = _call("health_check")
    assert report["status"] == "error"
    assert report["source"] == "db"
    assert any("MCP_DB_HOST" in p for p in report["problems"])


def test_health_check_never_raises_on_connection_errors(monkeypatch):
    monkeypatch.setattr(config, "missing_required", lambda: [])

    def boom():
        raise RuntimeError("cannot reach database")

    monkeypatch.setattr("mcp_server.db.test_connection", boom)
    report = source.health()
    assert report == {"status": "error", "source": "db", "error": "cannot reach database"}


def test_unknown_data_source_is_reported(monkeypatch):
    monkeypatch.setattr(config, "MCP_DATA_SOURCE", "spreadsheet")
    assert any("MCP_DATA_SOURCE" in p for p in config.missing_required())


def test_startup_check_exits_with_a_clear_message(no_db_credentials):
    with pytest.raises(SystemExit) as exc:
        config.check_required()
    assert "MCP_DB_HOST" in str(exc.value)
    assert ".env.example" in str(exc.value)


def test_each_tool_call_is_logged_with_timing(caplog):
    with caplog.at_level(logging.INFO, logger="mcp_server.timing"):
        _call("echo", message="hola")
    line = next(r.getMessage() for r in caplog.records if r.name == "mcp_server.timing")
    assert "tool=echo status=ok" in line
    assert "source_ms=" in line and "bytes=" in line
