"""EXAMPLE tool for the external API source (MCP_DATA_SOURCE=api).

Replace it with your API's tools. It shows the pattern every API tool follows:

1. Validate every parameter first (mcp_server/params.py).
2. Translate the standard parameter names to the API's own names.
3. Request through mcp_server/api_client.py only (never httpx directly).
4. Return ``{"data": [...], "meta": {...}}`` with provenance and pagination,
   so a truncated answer says so (``truncated``, ``next_offset``).

The endpoint assumed here is generic: ``GET {MCP_API_BASE_URL}/records`` with
``q``, ``year_from``, ``year_to``, ``offset`` and ``limit``, answering
``{"results": [...], "count": <total>}``. Adapt the path, the parameter
translation (API_PARAMS) and the keys (results/count) to the real API.

The docstring of each tool is what the model reads to decide whether to use it:
say what it returns, at what level (one row per record, per year...), the
units, the columns, and that it may be truncated.
"""

from mcp_server import api_client, config, params

# Standard parameter name -> the API's own parameter name.
API_PARAMS = {"species": "q", "year_from": "year_from", "year_to": "year_to"}
ENDPOINT = "/records"


def register(mcp) -> None:
    if config.MCP_DATA_SOURCE != "api":
        return

    @mcp.tool()
    async def search_records(
        species: str,
        year_from: int | None = None,
        year_to: int | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> str:
        """EXAMPLE — search records of a species in the external API.

        Returns one row per record, with the API's own column names, plus
        ``meta``: where and when the data was retrieved (source, retrieved_at,
        query) and pagination (total, returned, truncated, next_offset). If
        ``meta.truncated`` is true, call again with ``offset = meta.next_offset``
        to get the next part.

        Args:
            species: scientific name, e.g. "Lutjanus peru" (no common names)
            year_from: first year (inclusive), optional
            year_to: last year (inclusive), optional
            limit: maximum rows in this response (default and maximum: the server's MCP_API_MAX_ROWS)
            offset: first row to return; use meta.next_offset of a previous response
        """
        species = params.text("species", species, required=True)
        year_from, year_to = params.year_range(year_from, year_to, earliest=1900, max_span=100)
        limit, offset = params.page(limit, offset)

        standard = {"species": species, "year_from": year_from, "year_to": year_to}
        query = {API_PARAMS[k]: v for k, v in standard.items() if v is not None}

        rows, page_meta = await api_client.fetch_pages(
            ENDPOINT, query,
            results_key="results", total_key="count",
            offset=offset, max_rows=limit,
        )
        return api_client.json_response(rows, {
            **api_client.provenance(ENDPOINT, query),
            **page_meta,
        })
