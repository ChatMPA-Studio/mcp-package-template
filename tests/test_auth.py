"""Tests for mcp_server/auth.py — the per-investigator API key verifier.

Exercises ApiKeyVerifier.verify_token directly rather than through an HTTP app:
rejecting a missing/malformed Authorization header is FastMCP's job (its
transport middleware runs before verify_token is ever called), so what is left
to test here is the DynamoDB lookup and its caching.

Mocks mcp_server.auth.get_dynamodb_table (patched at the call site) — no
database connection or AWS credentials needed. Adapted from ltem-db-mcp.
"""

import asyncio
import hashlib
import time
from unittest.mock import MagicMock, patch

import pytest

from mcp_server import auth as auth_module
from mcp_server import config
from mcp_server.auth import ApiKeyVerifier, build_auth

VALID_KEY = "test-key-abc123"
VALID_HASH = hashlib.sha256(VALID_KEY.encode()).hexdigest()
SCOPE = "example"
OTHER_SCOPE = "another-server"


@pytest.fixture(autouse=True)
def required_scope(monkeypatch):
    monkeypatch.setattr(config, "AUTH_REQUIRED_SCOPE", SCOPE)


@pytest.fixture
def verifier(required_scope) -> ApiKeyVerifier:
    return build_auth()


@pytest.fixture(autouse=True)
def clear_cache():
    """The in-memory hash cache is a module-level dict — tests share it unless
    cleared, and several tests below reuse VALID_HASH with different records."""
    auth_module._cache.clear()
    yield
    auth_module._cache.clear()


def _mock_table(item: dict | None = None) -> MagicMock:
    table = MagicMock()
    table.get_item.return_value = {"Item": item} if item else {}
    return table


def _record(scopes=(SCOPE,), revoked_at=None) -> dict:
    return {"investigator_id": "researcher-42", "scopes": list(scopes), "revoked_at": revoked_at}


class TestValidKey:
    async def test_valid_key_with_required_scope_is_accepted(self, verifier):
        record = _record(scopes=[SCOPE, OTHER_SCOPE])
        with patch("mcp_server.auth.get_dynamodb_table", return_value=_mock_table(record)):
            token = await verifier.verify_token(VALID_KEY)
        assert token is not None
        assert token.client_id == "researcher-42"
        assert token.scopes == [SCOPE, OTHER_SCOPE]

    async def test_lookup_is_by_hash_never_the_raw_key(self, verifier):
        table = _mock_table(_record())
        with patch("mcp_server.auth.get_dynamodb_table", return_value=table):
            await verifier.verify_token(VALID_KEY)
        table.get_item.assert_called_once_with(Key={"key_hash": VALID_HASH})

    async def test_second_call_within_ttl_does_not_hit_dynamodb_again(self, verifier):
        table = _mock_table(_record())
        with patch("mcp_server.auth.get_dynamodb_table", return_value=table):
            await verifier.verify_token(VALID_KEY)
            await verifier.verify_token(VALID_KEY)
        assert table.get_item.call_count == 1


class TestDoesNotBlockEventLoop:
    async def test_slow_dynamodb_miss_does_not_freeze_other_requests(self, verifier):
        """boto3 is synchronous; if get_item ran on the event loop thread, a slow
        DynamoDB would stall every concurrent request, not just this one."""
        table = MagicMock()
        table.get_item.side_effect = lambda **_: time.sleep(0.5) or {}

        async def other_request() -> float:
            start = time.monotonic()
            await asyncio.sleep(0.01)
            return time.monotonic() - start

        with patch("mcp_server.auth.get_dynamodb_table", return_value=table):
            _, elapsed = await asyncio.gather(verifier.verify_token("slow-key"), other_request())
        assert elapsed < 0.2


class TestCacheSizeCap:
    """Once AUTH_CACHE_MAX_ENTRIES is reached, each new lookup evicts the oldest
    write, so a flood of random keys can't grow the cache forever."""

    async def test_cache_never_exceeds_max_entries(self, verifier, monkeypatch):
        monkeypatch.setattr(config, "AUTH_CACHE_MAX_ENTRIES", 2)
        with patch("mcp_server.auth.get_dynamodb_table", return_value=_mock_table(None)):
            for i in range(5):
                await verifier.verify_token(f"random-key-{i}")
        assert len(auth_module._cache) == 2

    async def test_oldest_entry_is_evicted_first(self, verifier, monkeypatch):
        monkeypatch.setattr(config, "AUTH_CACHE_MAX_ENTRIES", 2)
        table = _mock_table(_record())
        with patch("mcp_server.auth.get_dynamodb_table", return_value=table):
            await verifier.verify_token(VALID_KEY)
            await verifier.verify_token("second-key")
            await verifier.verify_token("third-key")  # evicts VALID_KEY
            assert VALID_HASH not in auth_module._cache
            await verifier.verify_token(VALID_KEY)
        assert table.get_item.call_count == 4

    async def test_refreshed_entry_moves_to_the_back(self, verifier, monkeypatch):
        """An expired entry that gets re-fetched is a new write, so it must not
        be the next one evicted."""
        monkeypatch.setattr(config, "AUTH_CACHE_MAX_ENTRIES", 2)
        with patch("mcp_server.auth.get_dynamodb_table", return_value=_mock_table(None)):
            await verifier.verify_token(VALID_KEY)
            await verifier.verify_token("second-key")
            record, _ = auth_module._cache[VALID_HASH]
            auth_module._cache[VALID_HASH] = (record, 0.0)  # force expiry
            await verifier.verify_token(VALID_KEY)  # re-fetch → back of the line
            await verifier.verify_token("third-key")  # evicts second-key
        assert VALID_HASH in auth_module._cache
        assert hashlib.sha256(b"second-key").hexdigest() not in auth_module._cache


class TestRejected:
    """verify_token returns None for anything it won't accept; FastMCP turns
    that into a 401."""

    async def test_unknown_key_is_rejected(self, verifier):
        with patch("mcp_server.auth.get_dynamodb_table", return_value=_mock_table(None)):
            assert await verifier.verify_token("wrong-key") is None

    async def test_second_lookup_of_unknown_key_does_not_hit_dynamodb_again(self, verifier):
        """Misses are cached too — a client retrying a typo'd key shouldn't get
        a GetItem on every single request."""
        table = _mock_table(None)
        with patch("mcp_server.auth.get_dynamodb_table", return_value=table):
            await verifier.verify_token("wrong-key")
            await verifier.verify_token("wrong-key")
        assert table.get_item.call_count == 1

    async def test_revoked_key_is_rejected(self, verifier):
        record = _record(revoked_at="2026-01-01T00:00:00Z")
        with patch("mcp_server.auth.get_dynamodb_table", return_value=_mock_table(record)):
            assert await verifier.verify_token(VALID_KEY) is None

    async def test_key_without_required_scope_is_rejected(self, verifier):
        record = _record(scopes=[OTHER_SCOPE])
        with patch("mcp_server.auth.get_dynamodb_table", return_value=_mock_table(record)):
            assert await verifier.verify_token(VALID_KEY) is None


class TestWiring:
    def test_required_scope_is_declared_to_fastmcp(self, verifier):
        """FastMCP re-checks scopes itself; the verifier has to advertise the
        requirement for that second gate to do anything."""
        assert SCOPE in verifier.required_scopes


class TestConfigValidation:
    def test_auth_enabled_without_table_region_scope_is_reported(self, monkeypatch):
        monkeypatch.setattr(config, "AUTH_ENABLED", True)
        monkeypatch.setattr(config, "AUTH_DYNAMODB_TABLE", "")
        monkeypatch.setattr(config, "AUTH_AWS_REGION", "")
        monkeypatch.setattr(config, "AUTH_REQUIRED_SCOPE", "")
        problems = " ".join(config.missing_required())
        for name in ("AUTH_DYNAMODB_TABLE", "AUTH_AWS_REGION", "AUTH_REQUIRED_SCOPE"):
            assert name in problems

    def test_auth_disabled_requires_nothing(self, monkeypatch):
        monkeypatch.setattr(config, "AUTH_ENABLED", False)
        monkeypatch.setattr(config, "AUTH_DYNAMODB_TABLE", "")
        assert not any("AUTH_" in p for p in config.missing_required())
