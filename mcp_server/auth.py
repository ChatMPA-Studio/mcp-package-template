"""Per-investigator API key auth, enforced by FastMCP's own auth layer.

Off by default (``AUTH_ENABLED=false``). When on, it is wired through FastMCP's
``auth=`` hook as a ``TokenVerifier`` subclass, so *every* HTTP request must
carry ``Authorization: Bearer <key>`` — including a platform's internal calls.
FastMCP's transport middleware rejects a missing or malformed header before
this module is reached.

Keys are opaque, not JWTs (hence not ``JWTVerifier``). An admin panel elsewhere
generates a random key, shows it once, and stores only its SHA-256 hash in a
DynamoDB table shared by the platform's MCP servers. One item per key::

    {key_hash, investigator_id, scopes: [...], created_at, revoked_at}

This module only reads that table (GetItem), never writes it. It never sees or
stores a raw key — only the hash, in memory, for AUTH_CACHE_TTL_SECONDS.

Scope enforcement is declarative: ``required_scopes`` on the base class makes
FastMCP reject tokens lacking ``AUTH_REQUIRED_SCOPE`` (one scope per MCP
server, e.g. the name of its data source). Rejections reach the client as a
standard OAuth 401 (``WWW-Authenticate: Bearer ...``), so the specific reason
(unknown / revoked / missing scope) stays in the logs, not in the response.

Configuration (all required when AUTH_ENABLED=true): AUTH_DYNAMODB_TABLE,
AUTH_AWS_REGION, AUTH_REQUIRED_SCOPE. AWS credentials come from the runtime
(e.g. the ECS task role), never from this repo.
"""

import asyncio
import hashlib
import logging
import threading
import time
from collections import OrderedDict
from typing import Any

from fastmcp.server.auth import AccessToken, TokenVerifier

from mcp_server import config

logger = logging.getLogger(__name__)

# hash -> (record or None if not found, expires_at monotonic timestamp).
# Caching misses too, not just hits: a client retrying an invalid/typo'd key
# shouldn't cause a DynamoDB GetItem on every single request.
# Ordered by write time and capped at AUTH_CACHE_MAX_ENTRIES: once full, the
# oldest write is evicted. Every entry gets the same TTL, so the oldest write is
# also the one closest to expiring anyway. Without the cap, a stream of random
# keys would leave one miss entry behind each, forever.
_cache: OrderedDict[str, tuple[dict[str, Any] | None, float]] = OrderedDict()

# One boto3 Table per worker thread. _fetch runs in asyncio's thread pool, and
# boto3 resources (and its default session) aren't thread-safe to share, so
# each thread builds its own on first use and reuses it after that.
_thread_local = threading.local()


def get_dynamodb_table():
    """Isolated on purpose: tests patch this name, not boto3 itself, to swap in
    a fake table without touching AWS or real credentials."""
    table = getattr(_thread_local, "table", None)
    if table is None:
        import boto3

        table = (
            boto3.session.Session()
            .resource("dynamodb", region_name=config.AUTH_AWS_REGION)
            .Table(config.AUTH_DYNAMODB_TABLE)
        )
        _thread_local.table = table
    return table


def _fetch(key_hash: str) -> dict[str, Any] | None:
    """Blocking boto3 call — only ever run via asyncio.to_thread."""
    response = get_dynamodb_table().get_item(Key={"key_hash": key_hash})
    return response.get("Item")


async def _lookup(key_hash: str) -> dict[str, Any] | None:
    # Only the DynamoDB round trip leaves the event loop thread; every read and
    # write of _cache stays on it, so the cache needs no lock.
    cached = _cache.get(key_hash)
    if cached is not None and cached[1] > time.monotonic():
        return cached[0]

    record = await asyncio.to_thread(_fetch, key_hash)
    _cache[key_hash] = (record, time.monotonic() + config.AUTH_CACHE_TTL_SECONDS)
    # Assigning to an existing key keeps its old position; a refresh is a new
    # write, so it goes to the back of the eviction line.
    _cache.move_to_end(key_hash)
    if len(_cache) > config.AUTH_CACHE_MAX_ENTRIES:
        _cache.popitem(last=False)
    return record


def _reject(reason: str) -> None:
    """FastMCP turns a None return into a 401; the reason is logged here
    because the OAuth error response doesn't carry one."""
    logger.warning("auth_rejected", extra={"reason": reason})
    return None


class ApiKeyVerifier(TokenVerifier):
    """Validates an opaque bearer key against its SHA-256 hash in DynamoDB."""

    async def verify_token(self, token: str) -> AccessToken | None:
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        record = await _lookup(key_hash)

        if record is None:
            return _reject("key_not_found")
        if record.get("revoked_at"):
            return _reject("key_revoked")

        scopes = list(record.get("scopes", []))
        if config.AUTH_REQUIRED_SCOPE not in scopes:
            return _reject("missing_scope")

        return AccessToken(
            token=token,
            client_id=str(record.get("investigator_id", "")),
            scopes=scopes,
        )


def build_auth() -> ApiKeyVerifier:
    """Constructed only when AUTH_ENABLED — see mcp_server/server.py."""
    return ApiKeyVerifier(required_scopes=[config.AUTH_REQUIRED_SCOPE])
