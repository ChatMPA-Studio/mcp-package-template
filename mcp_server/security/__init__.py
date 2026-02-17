"""Security module — SQL safety guardrails for database-backed MCPs."""

from mcp_server.security.sql_whitelist import (
    ALLOWED_TABLES,
    validate_sql,
    sanitize_table_name,
    add_allowed_table,
)
from mcp_server.security.read_only import (
    enforce_limit,
    DEFAULT_MAX_ROWS,
    DEFAULT_TIMEOUT,
)

__all__ = [
    "ALLOWED_TABLES",
    "validate_sql",
    "sanitize_table_name",
    "add_allowed_table",
    "enforce_limit",
    "DEFAULT_MAX_ROWS",
    "DEFAULT_TIMEOUT",
]
