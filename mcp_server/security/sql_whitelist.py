"""SQL whitelist validation — restrict queries to approved tables only.

This module is database-agnostic.  It validates that:
  1. Queries are read-only (SELECT / SHOW / DESCRIBE only).
  2. Only whitelisted table names appear in FROM / JOIN clauses.
  3. Destructive keywords (INSERT, DROP, etc.) are blocked.

Customization
-------------
* Add tables with ``add_allowed_table("my_table")`` or edit ``ALLOWED_TABLES``
  directly in this file.
* The whitelist is case-insensitive; table names are compared in upper case.
"""

import re

# ---------------------------------------------------------------------------
# Whitelist — add your table names here
# ---------------------------------------------------------------------------

ALLOWED_TABLES: set[str] = {
    # Example: "my_observations",
    # Example: "my_species_lookup",
}

# SQL keywords that indicate write / destructive operations
_DENIED_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "ALTER", "DROP", "CREATE",
    "TRUNCATE", "REPLACE", "GRANT", "REVOKE", "CALL", "LOAD",
    "OUTFILE", "INTO", "SET", "LOCK", "UNLOCK",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_allowed_table(name: str) -> None:
    """Register an additional table in the whitelist at runtime."""
    ALLOWED_TABLES.add(name)


def validate_sql(sql: str) -> None:
    """Validate that *sql* is a safe, read-only statement.

    Raises ``ValueError`` if the query is blocked.
    """
    if not sql or not sql.strip():
        raise ValueError("Empty SQL query")

    normalized = sql.strip().upper()

    # Must start with SELECT, SHOW, or DESCRIBE
    if not re.match(r"^(SELECT|SHOW|DESCRIBE|DESC)\b", normalized):
        raise ValueError("Only SELECT, SHOW, and DESCRIBE statements are allowed")

    # Check for denied keywords (word-boundary matching to avoid false positives)
    for keyword in _DENIED_KEYWORDS:
        if keyword == "INTO":
            # Allow "INTO" inside subqueries / table names; deny SELECT … INTO
            if re.search(r"\bSELECT\b.*\bINTO\b", normalized):
                raise ValueError(f"SQL contains denied keyword: {keyword}")
            continue
        if re.search(rf"\b{keyword}\b", normalized):
            raise ValueError(f"SQL contains denied keyword: {keyword}")

    # Validate table references (skip if whitelist is empty — open mode)
    if ALLOWED_TABLES:
        _validate_table_references(normalized)


def sanitize_table_name(name: str) -> str:
    """Return *name* if it is in the whitelist; raise ``ValueError`` otherwise."""
    if not ALLOWED_TABLES:
        return name  # open mode — no whitelist configured
    if name not in ALLOWED_TABLES:
        raise ValueError(
            f"Table '{name}' is not in the whitelist. "
            f"Allowed: {', '.join(sorted(ALLOWED_TABLES))}"
        )
    return name


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_table_references(normalized_sql: str) -> None:
    """Ensure only whitelisted tables appear in FROM / JOIN clauses."""
    table_pattern = r"(?:FROM|JOIN)\s+`?(\w+)`?"
    referenced = re.findall(table_pattern, normalized_sql)

    allowed_upper = {t.upper() for t in ALLOWED_TABLES}
    # Allow information-schema tables for DESCRIBE / SHOW equivalents
    allowed_upper |= {"INFORMATION_SCHEMA", "COLUMNS", "TABLES"}

    for table in referenced:
        if table.upper() not in allowed_upper:
            raise ValueError(
                f"Table '{table}' is not in the whitelist. "
                f"Allowed: {', '.join(sorted(ALLOWED_TABLES))}"
            )
