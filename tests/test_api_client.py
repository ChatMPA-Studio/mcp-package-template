"""Tests for the external API source: mcp_server/api_client.py, params.py,
cache.py and the example tool. The API is simulated with httpx.MockTransport —
no network, no real API, no key. Retries don't really wait (_sleep is patched).
"""

import asyncio
import json

import httpx
import pytest
from fastmcp import FastMCP

pytestmark = pytest.mark.api
api_client = pytest.importorskip("mcp_server.api_client", reason="API source removed from this MCP")

from mcp_server import config, params, source  # noqa: E402
from mcp_server.cache import TTLCache, cache  # noqa: E402
from mcp_server.timing import source_stats  # noqa: E402

BASE = "https://api.example.org/v1"
SECRET = "s3cr3t-key-value"


@pytest.fixture(autouse=True)
def api_mode(monkeypatch):
    monkeypatch.setattr(config, "MCP_DATA_SOURCE", "api")
    monkeypatch.setattr(config, "MCP_API_BASE_URL", BASE)
    monkeypatch.setattr(config, "MCP_API_KEY", "")
    monkeypatch.setattr(config, "MCP_API_KEY_PARAM", "")
    monkeypatch.setattr(config, "MCP_API_KEY_HEADER", "Authorization")
    monkeypatch.setattr(config, "MCP_API_MAX_RETRIES", 3)
    monkeypatch.setattr(config, "MCP_API_MIN_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(config, "MCP_API_MAX_ROWS", 5000)
    monkeypatch.setattr(cache, "ttl", 0)
    cache.clear()
    waits: list[float] = []

    async def fake_sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr(api_client, "_sleep", fake_sleep)
    yield waits
    api_client.set_transport(None)


def serve(handler):
    """Route the client through ``handler(request) -> httpx.Response``; return the request log."""
    seen: list[httpx.Request] = []

    def wrapped(request):
        seen.append(request)
        return handler(request)

    api_client.set_transport(httpx.MockTransport(wrapped))
    return seen


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# get_json: retries, errors, credentials
# ---------------------------------------------------------------------------

class TestGetJson:
    def test_returns_decoded_json(self):
        serve(lambda r: httpx.Response(200, json={"ok": True}))
        assert run(api_client.get_json("/ping")) == {"ok": True}

    def test_path_is_joined_to_base_url(self):
        seen = serve(lambda r: httpx.Response(200, json={}))
        run(api_client.get_json("/records", {"q": "x"}))
        assert str(seen[0].url) == f"{BASE}/records?q=x"

    def test_retries_5xx_with_growing_waits_then_succeeds(self, api_mode):
        answers = iter([httpx.Response(503), httpx.Response(502), httpx.Response(200, json=[1])])
        seen = serve(lambda r: next(answers))
        assert run(api_client.get_json("/x")) == [1]
        assert len(seen) == 3
        assert api_mode == [1, 2]

    def test_never_retries_other_4xx(self):
        seen = serve(lambda r: httpx.Response(400, text="bad year"))
        with pytest.raises(api_client.ApiError) as exc:
            run(api_client.get_json("/x"))
        assert len(seen) == 1
        assert exc.value.status == 400
        assert "bad year" in str(exc.value)

    def test_honors_retry_after_on_429(self, api_mode):
        answers = iter([httpx.Response(429, headers={"Retry-After": "3"}), httpx.Response(200, json={})])
        serve(lambda r: next(answers))
        run(api_client.get_json("/x"))
        assert api_mode == [3.0]

    def test_retry_after_is_capped(self, api_mode, monkeypatch):
        monkeypatch.setattr(config, "MCP_API_MAX_RETRY_AFTER_SECONDS", 10)
        answers = iter([httpx.Response(429, headers={"Retry-After": "3600"}), httpx.Response(200, json={})])
        serve(lambda r: next(answers))
        run(api_client.get_json("/x"))
        assert api_mode == [10]

    def test_gives_up_after_retries_with_a_clear_message(self):
        seen = serve(lambda r: httpx.Response(500))
        with pytest.raises(api_client.ApiError) as exc:
            run(api_client.get_json("/x"))
        assert len(seen) == 1 + config.MCP_API_MAX_RETRIES
        assert exc.value.status == 500
        assert "retries ran out" in str(exc.value)

    def test_network_errors_are_retried(self):
        calls = {"n": 0}

        def handler(request):
            calls["n"] += 1
            if calls["n"] == 1:
                raise httpx.ConnectError("connection refused", request=request)
            return httpx.Response(200, json={"ok": 1})

        serve(handler)
        assert run(api_client.get_json("/x")) == {"ok": 1}

    def test_non_json_answer_is_an_api_error(self):
        serve(lambda r: httpx.Response(200, text="<html>maintenance</html>"))
        with pytest.raises(api_client.ApiError, match="not JSON"):
            run(api_client.get_json("/x"))

    def test_key_goes_in_bearer_header(self, monkeypatch):
        monkeypatch.setattr(config, "MCP_API_KEY", SECRET)
        seen = serve(lambda r: httpx.Response(200, json={}))
        run(api_client.get_json("/x"))
        assert seen[0].headers["Authorization"] == f"Bearer {SECRET}"
        assert SECRET not in str(seen[0].url)

    def test_key_in_query_param_is_masked_everywhere(self, monkeypatch):
        monkeypatch.setattr(config, "MCP_API_KEY", SECRET)
        monkeypatch.setattr(config, "MCP_API_KEY_PARAM", "token")
        seen = serve(lambda r: httpx.Response(403, text=f"invalid token {SECRET}"))
        with pytest.raises(api_client.ApiError) as exc:
            run(api_client.get_json("/x", {"q": "a"}))
        assert seen[0].url.params["token"] == SECRET          # sent to the API...
        assert SECRET not in str(exc.value)                   # ...never shown
        shown = api_client.describe_query("/x", {"q": "a", "token": SECRET})
        assert SECRET not in json.dumps(shown)

    def test_each_request_is_recorded_for_timing(self):
        serve(lambda r: httpx.Response(200, json={}))
        stats = {"calls": 0, "rows": 0, "seconds": 0.0}

        async def call():
            token = source_stats.set(stats)
            try:
                await api_client.get_json("/x")
            finally:
                source_stats.reset(token)

        run(call())
        assert stats["calls"] == 1


# ---------------------------------------------------------------------------
# Pacing and cache
# ---------------------------------------------------------------------------

class TestPacingAndCache:
    def test_min_interval_spaces_requests(self, api_mode, monkeypatch):
        monkeypatch.setattr(config, "MCP_API_MIN_INTERVAL_SECONDS", 5)
        monkeypatch.setattr(api_client, "_last_request_at", 0.0)
        serve(lambda r: httpx.Response(200, json={}))

        async def two():
            await api_client.get_json("/a")
            await api_client.get_json("/b")

        run(two())
        assert api_mode and api_mode[-1] > 4  # the second request waited

    def test_cache_off_by_default(self):
        seen = serve(lambda r: httpx.Response(200, json={"v": 1}))
        run(api_client.get_json("/x", {"a": 1}))
        run(api_client.get_json("/x", {"a": 1}))
        assert len(seen) == 2

    def test_cache_on_serves_repeated_requests(self, monkeypatch):
        monkeypatch.setattr(cache, "ttl", 60)
        seen = serve(lambda r: httpx.Response(200, json={"v": 1}))
        run(api_client.get_json("/x", {"a": 1}))
        run(api_client.get_json("/x", {"a": 1}))
        run(api_client.get_json("/x", {"a": 2}))
        assert len(seen) == 2

    def test_errors_are_not_cached(self, monkeypatch):
        monkeypatch.setattr(cache, "ttl", 60)
        answers = iter([httpx.Response(404), httpx.Response(200, json={"v": 1})])
        serve(lambda r: next(answers))
        with pytest.raises(api_client.ApiError):
            run(api_client.get_json("/x"))
        assert run(api_client.get_json("/x")) == {"v": 1}

    def test_ttl_cache_evicts_oldest(self):
        c = TTLCache(ttl=60, max_entries=2)
        c.set("a", 1); c.set("b", 2); c.set("c", 3)
        assert c.get("a") is None and c.get("c") == 3


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

def paged_api(total: int):
    """A fake offset/limit API with ``total`` records."""
    def handler(request):
        offset = int(request.url.params["offset"])
        limit = int(request.url.params["limit"])
        rows = [{"id": i} for i in range(offset, min(offset + limit, total))]
        return httpx.Response(200, json={"results": rows, "count": total})
    return handler


class TestFetchPages:
    def test_collects_every_page(self):
        seen = serve(paged_api(7))
        rows, meta = run(api_client.fetch_pages("/r", results_key="results", total_key="count", page_size=3))
        assert [r["id"] for r in rows] == list(range(7))
        assert meta == {"offset": 0, "returned": 7, "total": 7, "truncated": False, "next_offset": None}
        assert len(seen) == 3

    def test_stops_at_max_rows_and_says_where_to_continue(self):
        serve(paged_api(12))
        rows, meta = run(api_client.fetch_pages("/r", results_key="results", total_key="count",
                                                page_size=3, max_rows=5))
        assert len(rows) == 5
        assert meta["truncated"] is True and meta["next_offset"] == 5

    def test_continues_from_next_offset(self):
        serve(paged_api(12))
        rows, meta = run(api_client.fetch_pages("/r", results_key="results", total_key="count",
                                                page_size=3, offset=5, max_rows=10))
        assert rows[0]["id"] == 5 and len(rows) == 7
        assert meta["truncated"] is False

    def test_works_without_a_total(self):
        def handler(request):
            offset = int(request.url.params["offset"])
            return httpx.Response(200, json={"results": [{"id": i} for i in range(offset, min(offset + 2, 3))]})
        serve(handler)
        rows, meta = run(api_client.fetch_pages("/r", results_key="results", page_size=2))
        assert len(rows) == 3 and meta["total"] is None and meta["truncated"] is False


# ---------------------------------------------------------------------------
# Parameter validation
# ---------------------------------------------------------------------------

class TestParams:
    def test_choice(self):
        assert params.choice("fleet", "MENORES", {"MAYORES", "MENORES"}) == "MENORES"
        with pytest.raises(ValueError, match="Allowed"):
            params.choice("fleet", "OTRA", {"MAYORES", "MENORES"})

    def test_year_range(self):
        assert params.year_range(2010, 2020, earliest=1900) == (2010, 2020)
        with pytest.raises(ValueError, match="year_from"):
            params.year_range(2020, 2010)
        with pytest.raises(ValueError, match="maximum is 5"):
            params.year_range(2000, 2010, max_span=5)
        with pytest.raises(ValueError, match="year_to"):
            params.year_range(None, 3000)

    def test_page_defaults_and_caps(self, monkeypatch):
        monkeypatch.setattr(config, "MCP_API_MAX_ROWS", 100)
        assert params.page(None, None) == (100, 0)
        with pytest.raises(ValueError, match="limit"):
            params.page(500, 0)
        with pytest.raises(ValueError, match="offset"):
            params.page(10, -1)

    def test_text(self):
        assert params.text("species", "  Lutjanus peru ") == "Lutjanus peru"
        with pytest.raises(ValueError, match="required"):
            params.text("species", " ", required=True)


# ---------------------------------------------------------------------------
# Example tool and health
# ---------------------------------------------------------------------------

def example_server() -> FastMCP:
    from tools import api_example
    m = FastMCP("test")
    api_example.register(m)
    return m


def call(m: FastMCP, name: str, **args):
    return asyncio.run(m.call_tool(name, args))


class TestExampleTool:
    def test_returns_data_with_provenance_and_pagination(self, monkeypatch):
        monkeypatch.setattr(config, "MCP_API_KEY", SECRET)
        seen = serve(paged_api(4))
        result = call(example_server(), "search_records", species="Lutjanus peru", year_from=2015, year_to=2020)
        body = json.loads(result.content[0].text)
        assert len(body["data"]) == 4
        meta = body["meta"]
        assert meta["source"] == "api" and meta["retrieved_at"]
        assert meta["query"]["params"] == {"q": "Lutjanus peru", "year_from": 2015, "year_to": 2020}
        assert meta["truncated"] is False
        assert SECRET not in result.content[0].text
        assert seen[0].url.params["q"] == "Lutjanus peru"  # standard name translated

    def test_invalid_parameters_never_reach_the_api(self):
        seen = serve(paged_api(4))
        with pytest.raises(Exception, match="year_from"):
            call(example_server(), "search_records", species="X", year_from=2020, year_to=2010)
        assert seen == []

    def test_not_registered_for_the_db_source(self, monkeypatch):
        monkeypatch.setattr(config, "MCP_DATA_SOURCE", "db")
        names = {t.name for t in asyncio.run(example_server().list_tools())}
        assert "search_records" not in names


class TestHealth:
    def test_ok_when_the_api_answers(self):
        serve(lambda r: httpx.Response(200, text="<html>up</html>"))
        report = run(source.health())
        assert report["status"] == "ok" and report["source"] == "api"

    def test_error_when_the_api_is_down(self):
        serve(lambda r: httpx.Response(503))
        report = run(source.health())
        assert report["status"] == "error" and "503" in report["error"]

    def test_missing_base_url_is_reported(self, monkeypatch):
        monkeypatch.setattr(config, "MCP_API_BASE_URL", "")
        report = run(source.health())
        assert report["status"] == "error"
        assert any("MCP_API_BASE_URL" in p for p in report["problems"])
