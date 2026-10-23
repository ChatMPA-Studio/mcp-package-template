"""External API data source — the only door to the API (MCP_DATA_SOURCE=api).

No tool makes HTTP requests on its own: they all go through ``get_json`` or
``fetch_pages`` here, so every request gets the same rules. The pattern comes
from erddap-db-mcp (tools/erddap_client.py, tools/sync.py, tools/data_access.py),
without anything specific to satellite data.

Rules applied to every request
------------------------------
* **Timeout** always (MCP_API_TIMEOUT_SECONDS).
* **Retries** only for network errors, 429 and 5xx, waiting 1, 2, 4... seconds
  (MCP_API_MAX_RETRIES); a ``Retry-After`` header is honored up to
  MCP_API_MAX_RETRY_AFTER_SECONDS. Other 4xx are never retried: the same
  request would fail the same way.
* **Pacing**: at most one request every MCP_API_MIN_INTERVAL_SECONDS (the API's
  rate limit), per process.
* **Errors translated** to ``ApiError`` with a message that says what was
  asked and what to do — never a raw stack trace or HTML page.
* **Credentials**: MCP_API_KEY goes in a header (or in MCP_API_KEY_PARAM); it is
  never logged and never appears in ``describe_query`` / ``meta.query``.
* **Timing**: each request is recorded for the per-call log
  (mcp_server/timing.py).
* **Cache** (optional, mcp_server/cache.py): successful responses only.

Responses
---------
Tools return ``{"data": [...], "meta": {...}}``. ``provenance()`` builds the
part of ``meta`` that says where the data came from and when — with an API the
same query can return different data tomorrow, so a reference case needs it
(``data_snapshot``).
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import httpx

from mcp_server import config
from mcp_server.cache import cache, make_key
from mcp_server.timing import record_source_call

logger = logging.getLogger(__name__)

RETRY_STATUS = {429, 500, 502, 503, 504}
MASK = "****"


class ApiError(Exception):
    """A request to the API failed in a way the tool should report as-is."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


# ---------------------------------------------------------------------------
# Client (one per process). Tests replace the transport with set_transport().
# ---------------------------------------------------------------------------

_client: httpx.AsyncClient | None = None
_transport: httpx.AsyncBaseTransport | None = None
_pace_lock: asyncio.Lock | None = None
_last_request_at = 0.0
_sleep = asyncio.sleep  # patched in tests so retries don't really wait


def set_transport(transport: httpx.AsyncBaseTransport | None) -> None:
    """Route requests through ``transport`` (e.g. ``httpx.MockTransport``). Tests only."""
    global _client, _transport
    _transport = transport
    _client = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        headers = {"Accept": "application/json"}
        if config.MCP_API_KEY and not config.MCP_API_KEY_PARAM:
            value = config.MCP_API_KEY
            if config.MCP_API_KEY_HEADER.lower() == "authorization":
                value = f"Bearer {value}"
            headers[config.MCP_API_KEY_HEADER] = value
        _client = httpx.AsyncClient(
            headers=headers,
            timeout=config.MCP_API_TIMEOUT_SECONDS,
            transport=_transport,
            follow_redirects=True,
        )
    return _client


async def aclose() -> None:
    """Close the HTTP client (on shutdown)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def _url(path: str) -> str:
    return urljoin(config.MCP_API_BASE_URL + "/", path.lstrip("/"))


def describe_query(path: str, params: dict | None = None) -> dict:
    """The request as it can be shown to a client: endpoint and parameters, key masked."""
    shown = dict(params or {})
    if config.MCP_API_KEY_PARAM and config.MCP_API_KEY_PARAM in shown:
        shown[config.MCP_API_KEY_PARAM] = MASK
    return {"endpoint": _url(path), "params": shown}


def _scrub(text: str) -> str:
    """Remove the API key from any text that may reach a log or a client."""
    return text.replace(config.MCP_API_KEY, MASK) if config.MCP_API_KEY else text


async def _pace() -> None:
    """Keep at least MCP_API_MIN_INTERVAL_SECONDS between requests."""
    global _last_request_at, _pace_lock
    if config.MCP_API_MIN_INTERVAL_SECONDS <= 0:
        return
    if _pace_lock is None:
        _pace_lock = asyncio.Lock()
    async with _pace_lock:
        wait = _last_request_at + config.MCP_API_MIN_INTERVAL_SECONDS - time.monotonic()
        if wait > 0:
            await _sleep(wait)
        _last_request_at = time.monotonic()


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    try:
        return min(float(value), config.MCP_API_MAX_RETRY_AFTER_SECONDS) if value else None
    except ValueError:
        return None  # an HTTP-date; fall back to the normal backoff


def _error_for(response: httpx.Response, path: str) -> ApiError:
    status = response.status_code
    body = _scrub(response.text[:300].strip())
    if status in (401, 403):
        msg = (f"The API rejected the request to {path} ({status}). Check MCP_API_KEY "
               "and that the key has access to this endpoint.")
    elif status == 404:
        msg = (f"Not found at {path} (404): the endpoint does not exist or there is no "
               "record for these parameters.")
    elif status == 429:
        msg = f"The API is rate-limiting requests to {path} (429) and retries ran out. Try again later."
    elif status >= 500:
        msg = f"The API failed at {path} ({status}) and retries ran out. The service may be down."
    else:
        msg = f"The API refused the request to {path} ({status})."
    if body:
        msg += f" API said: {body}"
    return ApiError(msg, status)


async def get_json(path: str, params: dict | None = None, *, use_cache: bool = True) -> Any:
    """GET ``path`` (relative to MCP_API_BASE_URL) and return the decoded JSON.

    Applies timeout, pacing, retries, error translation, timing and the
    optional cache. Raises ``ApiError``.
    """
    key = make_key(path, params)
    if use_cache:
        cached = cache.get(key)
        if cached is not None:
            return cached

    request_params = dict(params or {})
    if config.MCP_API_KEY and config.MCP_API_KEY_PARAM:
        request_params[config.MCP_API_KEY_PARAM] = config.MCP_API_KEY

    attempts = 1 + max(0, config.MCP_API_MAX_RETRIES)
    last_error: Exception | None = None
    for attempt in range(attempts):
        await _pace()
        started = time.perf_counter()
        response = None
        try:
            response = await _get_client().get(_url(path), params=request_params)
        except httpx.HTTPError as e:  # network error, timeout
            last_error = e
            wait = None
        finally:
            record_source_call(started, 0)

        if response is not None:
            if response.status_code < 400:
                try:
                    data = response.json()
                except ValueError:
                    raise ApiError(f"The API answered {path} with something that is not JSON.",
                                   response.status_code)
                if use_cache:
                    cache.set(key, data)
                return data
            if response.status_code not in RETRY_STATUS:
                raise _error_for(response, path)
            last_error = _error_for(response, path)
            wait = _retry_after(response)

        if attempt < attempts - 1:
            wait = 2 ** attempt if wait is None else wait
            logger.warning("API request to %s failed (attempt %d/%d): %s — retrying in %.1fs",
                           path, attempt + 1, attempts, _scrub(str(last_error)), wait)
            await _sleep(wait)

    if isinstance(last_error, ApiError):
        raise last_error
    raise ApiError(f"Could not reach the API at {path} after {attempts} attempts: "
                   f"{_scrub(str(last_error))}")


async def fetch_pages(
    path: str,
    params: dict | None = None,
    *,
    results_key: str,
    total_key: str | None = None,
    offset_param: str = "offset",
    limit_param: str = "limit",
    page_size: int = 300,
    offset: int = 0,
    max_rows: int | None = None,
) -> tuple[list[dict], dict]:
    """Collect rows from an offset/limit paginated endpoint.

    Requests pages of ``page_size`` starting at ``offset`` until the API has no
    more rows or ``max_rows`` (default MCP_API_MAX_ROWS) are collected. Returns
    ``(rows, page_meta)``, where ``page_meta`` has ``offset``, ``returned``,
    ``total`` (if the API reports it), ``truncated`` and ``next_offset`` — the
    offset to pass to get the next part, or ``None`` when nothing is left.

    Adapt the keyword arguments to the API (e.g. GBIF-style APIs use
    ``offset``/``limit`` and report ``count``; others use ``page``/``per_page``:
    then write a small variant of this function rather than bending it).
    """
    max_rows = config.MCP_API_MAX_ROWS if max_rows is None else max_rows
    rows: list[dict] = []
    total = None
    position = offset
    exhausted = False

    while len(rows) < max_rows:
        size = min(page_size, max_rows - len(rows))
        body = await get_json(path, {**(params or {}), offset_param: position, limit_param: size})
        page_rows = body.get(results_key, []) if isinstance(body, dict) else []
        if total_key and isinstance(body, dict) and body.get(total_key) is not None:
            total = int(body[total_key])
        rows.extend(page_rows)
        position += len(page_rows)
        if len(page_rows) < size or (total is not None and position >= total):
            exhausted = True
            break

    truncated = not exhausted
    return rows, {
        "offset": offset,
        "returned": len(rows),
        "total": total,
        "truncated": truncated,
        "next_offset": position if truncated else None,
    }


def json_response(rows: list, meta: dict) -> str:
    """Serialize a tool result as ``{"data": rows, "meta": meta}``."""
    return json.dumps({"data": rows, "meta": meta}, ensure_ascii=False, default=str)


def provenance(path: str, params: dict | None, *, source: str = "api",
               version: str | None = None) -> dict:
    """Where and when the data came from, for ``meta``. ``version`` is the
    source's own data version or release, if the API reports one."""
    meta = {
        "source": source,
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "query": describe_query(path, params),
    }
    if version:
        meta["source_version"] = version
    return meta


async def health() -> dict:
    """Check that the API answers (GET MCP_API_HEALTH_PATH, default the base URL)."""
    path = config.MCP_API_HEALTH_PATH or ""
    params = {config.MCP_API_KEY_PARAM: config.MCP_API_KEY} if config.MCP_API_KEY and config.MCP_API_KEY_PARAM else None
    started = time.perf_counter()
    try:
        # One plain request, no retries: health_check must answer fast. Any
        # answer below 400 counts (the page need not be JSON).
        response = await _get_client().get(_url(path), params=params)
    except httpx.HTTPError as e:
        return {"status": "error", "endpoint": _url(path), "error": _scrub(f"API not reachable: {e}")}
    latency = round((time.perf_counter() - started) * 1000)
    if response.status_code >= 400:
        return {"status": "error", "endpoint": _url(path), "latency_ms": latency,
                "error": str(_error_for(response, path or "/"))}
    return {"status": "ok", "endpoint": _url(path), "latency_ms": latency}
