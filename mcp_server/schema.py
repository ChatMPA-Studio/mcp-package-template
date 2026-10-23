"""Schema discovery and caching — database data source only (MCP_DATA_SOURCE=db).

Backs the schema tools registered in mcp_server/server.py (list_tables,
describe_table, schema_snapshot). Only whitelisted tables are described.
"""

from mcp_server.db import execute_raw, execute_select
from mcp_server.security import ALLOWED_TABLES, sanitize_table_name

# In-memory cache (populated once per process)
_schema_cache: dict | None = None


def discover_tables() -> list[str]:
    """Return the table names in the database."""
    rows = execute_raw("SHOW TABLES")
    # SHOW TABLES returns rows with a single key like 'Tables_in_<dbname>'
    return [list(row.values())[0] for row in rows]


def describe_table(table: str) -> list[dict]:
    """Return column descriptions for a whitelisted table.

    Returns a list of dicts with Field, Type, Null, Key, Default, Extra.
    """
    safe_table = sanitize_table_name(table)
    return execute_raw(f"SHOW COLUMNS FROM `{safe_table}`")


def get_row_count(table: str) -> int:
    """Return the row count of a whitelisted table."""
    safe_table = sanitize_table_name(table)
    rows = execute_select(f"SELECT COUNT(*) AS cnt FROM `{safe_table}`", max_rows=1)
    return rows[0]["cnt"] if rows else 0


def build_schema_snapshot() -> dict:
    """Build a schema snapshot of the whitelisted tables: columns, types, row counts.

    Cached in memory for the process lifetime (see invalidate_cache).
    """
    global _schema_cache
    if _schema_cache is not None:
        return _schema_cache

    snapshot: dict = {"tables": {}}
    for table in sorted(ALLOWED_TABLES):
        try:
            columns = describe_table(table)
            snapshot["tables"][table] = {
                "columns": [
                    {
                        "name": col["Field"],
                        "type": col["Type"],
                        "nullable": col["Null"] == "YES",
                        "key": col.get("Key", ""),
                    }
                    for col in columns
                ],
                "row_count": get_row_count(table),
            }
        except Exception as e:
            snapshot["tables"][table] = {"error": str(e)}

    _schema_cache = snapshot
    return snapshot


def invalidate_cache() -> None:
    """Clear the schema cache to force re-discovery."""
    global _schema_cache
    _schema_cache = None
