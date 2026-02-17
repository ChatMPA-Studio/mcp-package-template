"""Database connection and query execution — generic, backend-aware.

Supports MySQL (PyMySQL) out of the box.  To add PostgreSQL or SQLite,
install the corresponding driver and extend ``_get_connection()``.

All queries pass through the security layer (SQL whitelist + LIMIT
enforcement) before reaching the database.
"""

import json
from typing import Any

import pymysql
import pymysql.cursors

from mcp_server.config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_BACKEND
from mcp_server.security import validate_sql, enforce_limit, DEFAULT_TIMEOUT, DEFAULT_MAX_ROWS


def get_connection():
    """Create a new database connection using config settings.

    Currently supports MySQL via PyMySQL.  Extend this function to add
    PostgreSQL (psycopg2) or SQLite (stdlib sqlite3) support.
    """
    if DB_BACKEND in ("mysql", "mysql+pymysql"):
        return pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor,
            read_timeout=DEFAULT_TIMEOUT,
            write_timeout=DEFAULT_TIMEOUT,
            connect_timeout=10,
            charset="utf8mb4",
        )
    raise RuntimeError(
        f"Unsupported DB_BACKEND '{DB_BACKEND}'. "
        "Extend db.py:get_connection() for your database driver."
    )


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
        Query parameters for parameterised queries.
    max_rows : int
        Maximum rows to return (auto-injected LIMIT).

    Returns
    -------
    list[dict]
        Each row as a dictionary.

    Raises
    ------
    ValueError
        If the SQL fails security validation.
    RuntimeError
        If the database connection fails.
    """
    validate_sql(sql)
    sql = enforce_limit(sql, max_rows)

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        conn.close()


def execute_raw(sql: str) -> list[dict]:
    """Execute a SHOW or DESCRIBE statement (no LIMIT injection).

    Used for schema discovery only.  Still validates SQL safety.
    """
    validate_sql(sql)

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()
    finally:
        conn.close()


def test_connection() -> dict[str, Any]:
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
