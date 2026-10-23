# Tutorial 09: External API Data Source

## Goal

Serve data from an external HTTP API (a public service or a partner's API)
instead of a project database: option B, `MCP_DATA_SOURCE=api`.

## When to use it

Use it when the data is not yours to host and the provider offers an API. Data in
your own database → option A ([Tutorial 02](02_add_tools.md)).

What changes compared with a database:

| | Database (A) | API (B) |
|---|---|---|
| Access | SQL through `execute_select` | HTTP through `api_client` |
| Validation | the SQL (read-only, whitelist) | every parameter, before the request |
| Limits | a row cap | a row cap **and** the API's: requests per minute, page size, timeouts |
| Speed | fast, stable | depends on the provider; may need a cache |
| Over time | changes only when you reload | can change any day — record when and how it was queried |
| Terms | yours | the provider's license and citation rules |

## Prerequisites

- Completed [Tutorial 01](01_create_a_new_mcp.md) choosing option B (database files deleted)
- The API's documentation at hand

## Steps

### 1. Read the API's documentation and write down

1. Base URL and whether it needs a key (and where: header or query string).
2. Rate limit (requests per second or minute).
3. Pagination: parameter names (`offset`/`limit`, `page`/`per_page`, a cursor), maximum page size, maximum offset.
4. The response: which key holds the rows, which the total.
5. Whether results change over time, and whether it offers versions or citable downloads (e.g. a DOI).
6. License and how to cite the data.

Put 2, 5 and 6 in the README: whoever uses your MCP needs them.

### 2. Configure

In `.env`:

```bash
MCP_DATA_SOURCE=api
MCP_API_BASE_URL=https://api.example.org/v1
# MCP_API_KEY=...                 # only if needed; secret, never committed
# MCP_API_KEY_PARAM=token         # only if the key goes in the URL
MCP_API_HEALTH_PATH=/status       # any cheap endpoint; default: the base URL
MCP_API_MIN_INTERVAL_SECONDS=0.2  # e.g. 5 requests per second
MCP_API_MAX_ROWS=5000
```

Start the server and call `health_check`: it must answer `"status": "ok"`.

### 3. Write a tool

Replace `tools/api_example.py` with your tools. The pattern:

```python
"""Occurrence tools."""

from mcp_server import api_client, config, params

ENDPOINT = "/occurrence/search"
# standard parameter name -> the API's own name
API_PARAMS = {"species": "scientificName", "year_from": "year_from", "year_to": "year_to"}


def register(mcp) -> None:
    if config.MCP_DATA_SOURCE != "api":
        return

    @mcp.tool()
    async def get_occurrences(species: str, year_from: int | None = None,
                              year_to: int | None = None, limit: int | None = None,
                              offset: int | None = None) -> str:
        """Occurrence records of a species, one row per record, with the API's
        column names. meta says where and when the data was retrieved and
        whether it was truncated (then call again with offset=meta.next_offset).

        Args:
            species: Scientific name, e.g. "Lutjanus peru" (no common names).
            year_from: First year (inclusive), optional.
            year_to: Last year (inclusive), optional.
            limit: Maximum rows in this response (default and maximum: MCP_API_MAX_ROWS).
            offset: First row; use meta.next_offset of a previous response.
        """
        # 1. validate everything before any request
        species = params.text("species", species, required=True)
        year_from, year_to = params.year_range(year_from, year_to, earliest=1900)
        limit, offset = params.page(limit, offset)

        # 2. standard names -> the API's names
        standard = {"species": species, "year_from": year_from, "year_to": year_to}
        query = {API_PARAMS[k]: v for k, v in standard.items() if v is not None}

        # 3. through the one door, collecting pages
        rows, page = await api_client.fetch_pages(
            ENDPOINT, query, results_key="results", total_key="count",
            page_size=300, offset=offset, max_rows=limit,
        )

        # 4. data + provenance + pagination
        return api_client.json_response(rows, {**api_client.provenance(ENDPOINT, query), **page})
```

If the API paginates with `page`/`per_page` or a cursor, write a small variant of `fetch_pages` next to it instead of forcing it; keep the same `truncated` / `next_offset` contract.

### 4. What `api_client` does for you

- Timeout on every request; at most one request every `MCP_API_MIN_INTERVAL_SECONDS`.
- Retries network errors, 429 and 5xx (waits 1, 2, 4 s; honors `Retry-After`); never other 4xx.
- Turns failures into `ApiError` messages that say what was asked and what to do.
- Never shows the key: not in logs, errors or `meta.query`.
- Records each request for the per-call timing log.
- Optional cache: set `MCP_CACHE_TTL_SECONDS` only if responses are slow, limited or paid and do not change within the TTL.

### 5. Test without the network

```python
import asyncio, json, httpx
from fastmcp import FastMCP
from mcp_server import api_client, config
from tools import occurrences

def test_get_occurrences(monkeypatch):
    monkeypatch.setattr(config, "MCP_DATA_SOURCE", "api")
    monkeypatch.setattr(config, "MCP_API_BASE_URL", "https://api.example.org/v1")
    api_client.set_transport(httpx.MockTransport(
        lambda r: httpx.Response(200, json={"results": [{"key": 1}], "count": 1})))
    m = FastMCP("test"); occurrences.register(m)
    body = json.loads(asyncio.run(m.call_tool("get_occurrences", {"species": "Lutjanus peru"})).content[0].text)
    assert body["data"] == [{"key": 1}] and body["meta"]["truncated"] is False
    api_client.set_transport(None)
```

See `tests/test_api_client.py` for retries, errors, pagination and the key.

### 6. Reference cases with an API

Because the same query can return different data later, a verified reference value must record `meta.retrieved_at`, `meta.query` and, if available, the source's version or a download DOI (`data_snapshot` in the reference case).

## Next Steps

- [Tutorial 05: Dockerize and Run](05_dockerize_and_run.md)
- [Tutorial 06: Deploy to Amazon ECS](06_deploy_to_ecs.md)
