"""SQL security — table whitelist and read-only limits for database-backed MCPs.

Used only with the database data source (``MCP_DATA_SOURCE=db``). It validates
that:

1. Queries are read-only (SELECT / SHOW / DESCRIBE only).
2. Destructive keywords (INSERT, DROP, etc.) are blocked.
3. Only whitelisted tables appear in FROM / JOIN clauses.

and caps result sizes with an automatic LIMIT.

Customization
-------------
* List your tables in ``ALLOWED_TABLES`` (or call ``add_allowed_table``).
* The whitelist is case-insensitive; table names are compared in upper case.
* An empty whitelist blocks every query that names a table: the template ships
  closed on purpose, so a new MCP cannot read a table nobody listed.
"""

import re

# ---------------------------------------------------------------------------
# Whitelist — add your table names here
# ---------------------------------------------------------------------------

# set(), not {}: an empty {} literal is a dict, and add_allowed_table() would fail.
ALLOWED_TABLES: set[str] = set(
    # Example: {"my_observations", "my_species_lookup"}
)

# SQL keywords that indicate write / destructive operations
DENIED_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "ALTER", "DROP", "CREATE",
    "TRUNCATE", "REPLACE", "GRANT", "REVOKE", "CALL", "LOAD",
    "OUTFILE", "INTO", "SET", "LOCK", "UNLOCK",
]

# ---------------------------------------------------------------------------
# Read-only limits
# ---------------------------------------------------------------------------

DEFAULT_MAX_ROWS: int = 5000
DEFAULT_TIMEOUT: int = 20  # seconds

# Ceiling for a query whose rows are an intermediate step, not the answer:
# a tool that pulls detailed rows only to reduce them to a few summary rows in
# Python. DEFAULT_MAX_ROWS is a response-size guard, and applying it to one of
# these silently drops rows the tool was going to aggregate — changing the
# answer with no error and no warning (in ltem-db-mcp a diversity index was
# computed from 2.6% of the surveys before this existed). Set it above the
# size of your largest table on purpose: reaching it means something is wrong,
# not that the data grew. Pass it explicitly: execute_select(sql, max_rows=...)
AGGREGATION_MAX_ROWS: int = 500_000

# ---------------------------------------------------------------------------
# Precompiled regex patterns
#
# validate_sql() and enforce_limit() run on every query. With pooled
# connections (db.py) the connection handshake no longer dominates latency,
# so compiling these once at import time is worth it.
# ---------------------------------------------------------------------------

_SELECT_SHOW_DESCRIBE_RE = re.compile(r"^(SELECT|SHOW|DESCRIBE|DESC)\b")
_SELECT_INTO_RE = re.compile(r"\bSELECT\b.*\bINTO\b")
_DENIED_KEYWORD_PATTERNS = [
    (keyword, re.compile(r"\b" + keyword + r"\b"))
    for keyword in DENIED_KEYWORDS
    if keyword != "INTO"  # INTO gets the SELECT...INTO-specific check above
]
_TABLE_REF_RE = re.compile(r"(?:FROM|JOIN)\s+`?(\w+)`?")
_LIMIT_RE = re.compile(r"\bLIMIT\s+(\d+)")
_LIMIT_SUB_RE = re.compile(r"\bLIMIT\s+\d+", flags=re.IGNORECASE)
_SELECT_START_RE = re.compile(r"^\s*(SELECT)\b")


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
    if not _SELECT_SHOW_DESCRIBE_RE.match(normalized):
        raise ValueError("Only SELECT, SHOW, and DESCRIBE statements are allowed")

    # SELECT ... INTO (e.g. INTO OUTFILE) is the one denied keyword that needs a
    # shape-specific check instead of a plain word-boundary search: "INTO" also
    # shows up harmlessly in table or column names.
    if _SELECT_INTO_RE.search(normalized):
        raise ValueError("SQL contains denied keyword: INTO")

    # The remaining denied keywords, as whole words (not substrings)
    for keyword, pattern in _DENIED_KEYWORD_PATTERNS:
        if pattern.search(normalized):
            raise ValueError(f"SQL contains denied keyword: {keyword}")

    _validate_table_references(normalized)


def sanitize_table_name(name: str) -> str:
    """Return *name* if it is in the whitelist; raise ``ValueError`` otherwise."""
    if name not in ALLOWED_TABLES:
        raise ValueError(
            f"Table '{name}' is not allowed. Allowed: {_allowed_list()}"
        )
    return name


def enforce_limit(sql: str, max_rows: int = DEFAULT_MAX_ROWS) -> str:
    """Inject or cap a LIMIT clause to prevent oversized result sets.

    * If a LIMIT already exists and exceeds *max_rows*, it is replaced.
    * If no LIMIT is present on a SELECT statement, one is appended.
    * SHOW / DESCRIBE statements are returned unchanged.

    Works for any SQL dialect that supports ``LIMIT n`` (MySQL, PostgreSQL,
    SQLite). For SQL Server or Oracle, adapt it to ``TOP`` / ``FETCH FIRST``.
    """
    normalized = sql.strip().upper()

    limit_match = _LIMIT_RE.search(normalized)
    if limit_match:
        if int(limit_match.group(1)) > max_rows:
            sql = _LIMIT_SUB_RE.sub(f"LIMIT {max_rows}", sql)
        return sql

    # No LIMIT found — add one for SELECT statements only
    if _SELECT_START_RE.match(normalized):
        sql = sql.rstrip().rstrip(";")
        sql = f"{sql} LIMIT {max_rows}"

    return sql


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _allowed_list() -> str:
    return ", ".join(sorted(ALLOWED_TABLES)) or "(none — add tables to ALLOWED_TABLES in mcp_server/security.py)"


def _validate_table_references(normalized_sql: str) -> None:
    """Ensure only whitelisted tables appear in FROM / JOIN clauses."""
    referenced = _TABLE_REF_RE.findall(normalized_sql)

    allowed_upper = {t.upper() for t in ALLOWED_TABLES}
    # Allow information-schema tables for DESCRIBE / SHOW equivalents
    allowed_upper |= {"INFORMATION_SCHEMA", "COLUMNS", "TABLES"}

    for table in referenced:
        if table.upper() not in allowed_upper:
            raise ValueError(
                f"Table '{table}' is not in the whitelist. Allowed: {_allowed_list()}"
            )
