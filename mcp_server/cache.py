"""Optional cache of API responses — in memory, per process, with expiry.

Off by default (``MCP_CACHE_TTL_SECONDS=0``). Turn it on when the API is slow,
rate-limited or charges per request, and its data does not change within the
TTL. Keys are built from the request path and parameters, never from the API
key.

Limits of this implementation, on purpose: each replica keeps its own cache
and it is lost on restart. When that is not enough (large responses, many
replicas, data downloaded in advance), keep the same ``get``/``set`` interface
and back it with shared storage: erddap-db-mcp stores its cache as files in S3
with an index and expiry (TTL) in DynamoDB, and claims the key before writing
so two replicas never write the same entry.
"""

import json
import time
from collections import OrderedDict
from typing import Any

from mcp_server import config


def make_key(path: str, params: dict | None) -> str:
    """Stable cache key for a request: path + sorted parameters."""
    return path + "?" + json.dumps(params or {}, sort_keys=True, default=str)


class TTLCache:
    """Small in-memory cache: entries expire after ``ttl`` seconds; at most
    ``max_entries`` are kept (oldest write evicted first)."""

    def __init__(self, ttl: float, max_entries: int):
        self.ttl = ttl
        self.max_entries = max_entries
        self._data: OrderedDict[str, tuple[Any, float]] = OrderedDict()

    @property
    def enabled(self) -> bool:
        return self.ttl > 0

    def get(self, key: str) -> Any | None:
        if not self.enabled:
            return None
        hit = self._data.get(key)
        if hit is None:
            return None
        value, expires_at = hit
        if expires_at <= time.monotonic():
            del self._data[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        if not self.enabled:
            return
        self._data[key] = (value, time.monotonic() + self.ttl)
        self._data.move_to_end(key)
        while len(self._data) > self.max_entries:
            self._data.popitem(last=False)

    def clear(self) -> None:
        self._data.clear()


cache = TTLCache(config.MCP_CACHE_TTL_SECONDS, config.MCP_CACHE_MAX_ENTRIES)
