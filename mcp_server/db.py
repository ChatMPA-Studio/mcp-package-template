"""Database data source — pooled connections and validated query execution.

Used when ``MCP_DATA_SOURCE=db``. Supports MySQL (PyMySQL) out of the box; to
add PostgreSQL or SQLite, install the driver and extend ``_build_pool()``.

All queries pass through the security layer (``mcp_server/security.py``:
table whitelist + LIMIT enforcement) before reaching the database.
"""

import logging
import threading
import time

import pymysql
import pymysql.cursors
from dbutils.pooled_db import PooledDB

from mcp_server import config
from mcp_server.security import validate_sql, enforce_limit, DEFAULT_TIMEOUT, DEFAULT_MAX_ROWS
from mcp_server.timing import record_source_call

logger = logging.getLogger(__name__)

_pool: PooledDB | None = None
_pool_lock = threading.Lock()

def _build_pool() -> PooledDB:
    """Build the process-wide connection pool from config settings."""
    if config.DB_BACKEND != "mysql":
        raise RuntimeError(
            f"Unsupported DB_BACKEND '{config.DB_BACKEND}'. "
            "Extend db.py:_build_pool() for your database driver."
        )

    conn_kwargs = dict(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        read_timeout=DEFAULT_TIMEOUT,
        write_timeout=DEFAULT_TIMEOUT,
        connect_timeout=10,
        charset="utf8mb4",
        # Every query here is a read. Without autocommit each SELECT opens a
        # transaction that has to be rolled back when the connection goes back
        # to the pool; with it there is none, and reset=False below skips that
        # ROLLBACK round trip.
        autocommit=True,
    )

    # Optional TLS (off by default). With a CA bundle the server cert is
    # verified; without one, the connection is encrypted but unverified.
    if config.DB_SSL:
        conn_kwargs["ssl"] = (
            {"ca": config.DB_SSL_CA} if config.DB_SSL_CA else {"check_hostname": False}
        )

    return PooledDB(
        creator=pymysql,
        mincached=config.DB_POOL_MIN,
        maxcached=config.DB_POOL_MAX_CACHED,
        maxconnections=config.DB_POOL_MAX,
        blocking=True,
        # MySQL (and managed services such as RDS) drops idle connections after
        # a while; ping=1 checks liveness on every checkout and transparently
        # reconnects instead of handing out a dead connection.
        ping=1,
        reset=False,
        setsession=[
            # enforce_limit() appends LIMIT to queries that have none. With
            # ORDER BY + LIMIT, MySQL's optimizer prefers an index already in
            # ORDER BY order, hoping to stop early, even when DISTINCT/GROUP BY
            # means it can't (in ltem-db-mcp one query scanned 449K rows instead
            # of 74K: 421 ms -> 103 ms with this off, same rows). Re-applied by
            # DBUtils on every reconnect. Requires MySQL 8.0.21+; remove it for
            # older servers.
            "SET SESSION optimizer_switch='prefer_ordering_index=off'",
        ],
        **conn_kwargs,
    )


def _get_pool() -> PooledDB:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = _build_pool()
    return _pool


def warm_pool() -> None:
    """Open the pool's first connections at startup instead of on the first request.

    Best effort: if the database is unreachable at startup the server still
    starts, and the pool is built on the first query.
    """
    try:
        _get_pool()
    except Exception:
        logger.warning("Could not open the database pool at startup; retrying on first query", exc_info=True)


def get_connection() -> pymysql.connections.Connection:
    """Borrow a connection from the process-wide pool.

    Behaves like a plain pymysql connection to callers: closing it (as
    execute_select/execute_raw do) returns it to the pool instead of tearing
    down the TCP session. Blocks (does not raise) if all DB_POOL_MAX
    connections are checked out — the caller waits for one to free up.
    """
    return _get_pool().connection()


def execute_select(
    sql: str,
    params: tuple | list | dict | None = None,
    max_rows: int = DEFAULT_MAX_ROWS,
) -> list[dict]:
    """Execute a validated SELECT query and return rows as dicts.

    Parameters
    ----------
    sql : str
        SQL SELECT statement (parameterised placeholders allowed).
    params : tuple | list | dict | None
        Query parameters for parameterised queries. Never format user input
        into ``sql`` directly.
    max_rows : int
        Maximum rows to return (auto-injected LIMIT). For intermediate rows
        that a tool aggregates in Python, use ``security.AGGREGATION_MAX_ROWS``.

    Raises
    ------
    ValueError
        If the SQL fails security validation.
    """
    validate_sql(sql)
    sql = enforce_limit(sql, max_rows)

    started = time.perf_counter()
    rows: list[dict] = []
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return rows
    finally:
        conn.close()
        record_source_call(started, len(rows))


def execute_raw(sql: str) -> list[dict]:
    """Execute a SHOW or DESCRIBE statement (no LIMIT injection).

    Used for schema discovery only. Still validates SQL safety.
    """
    validate_sql(sql)

    started = time.perf_counter()
    rows: list[dict] = []
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            return rows
    finally:
        conn.close()
        record_source_call(started, len(rows))


def test_connection() -> dict:
    """Test database connectivity and return server info."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT VERSION() AS version")
            version = cursor.fetchone()
            cursor.execute("SELECT DATABASE() AS db_name")
            db_info = cursor.fetchone()
            cursor.execute("SELECT CURRENT_USER() AS `db_user`")
            user_info = cursor.fetchone()
            return {
                "status": "connected",
                "version": version["version"] if version else None,
                "database": db_info["db_name"] if db_info else None,
                "user": user_info["db_user"] if user_info else None,
            }
    finally:
        conn.close()
