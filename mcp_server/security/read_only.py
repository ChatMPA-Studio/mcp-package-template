"""Read-only enforcement — inject LIMIT caps and timeout defaults.

Works for any SQL dialect that supports ``LIMIT n`` (MySQL, PostgreSQL,
SQLite).  For SQL Server or Oracle, override ``enforce_limit`` with the
appropriate ``TOP`` / ``FETCH FIRST`` syntax.
"""

import re

DEFAULT_MAX_ROWS: int = 5000
DEFAULT_TIMEOUT: int = 20  # seconds


def enforce_limit(sql: str, max_rows: int = DEFAULT_MAX_ROWS) -> str:
    """Inject or cap a LIMIT clause to prevent oversized result sets.

    * If a LIMIT already exists and exceeds *max_rows*, it is replaced.
    * If no LIMIT is present on a SELECT statement, one is appended.
    * SHOW / DESCRIBE statements are returned unchanged.
    """
    normalized = sql.strip().upper()

    # Check if LIMIT already exists
    limit_match = re.search(r"\bLIMIT\s+(\d+)", normalized)
    if limit_match:
        existing = int(limit_match.group(1))
        if existing > max_rows:
            sql = re.sub(
                r"\bLIMIT\s+\d+",
                f"LIMIT {max_rows}",
                sql,
                flags=re.IGNORECASE,
            )
        return sql

    # No LIMIT found — add one for SELECT statements only
    if re.match(r"^\s*(SELECT)\b", normalized):
        sql = sql.rstrip().rstrip(";")
        sql = f"{sql} LIMIT {max_rows}"

    return sql
