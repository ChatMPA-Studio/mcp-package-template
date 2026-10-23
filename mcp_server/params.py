"""Validation of tool parameters before calling an external API.

The API-source counterpart of mcp_server/security.py: there is no SQL to
check, so what protects the API (and the answer) is checking every parameter
*before* the request — allowed values, ranges, and how much is asked for.
From erddap-db-mcp's security.py (VALID_*, validate_date_range, MAX_DATE_SPAN).

Every helper raises ``ValueError`` with a message that names the parameter and
says what is accepted; tools let it propagate, so the client sees it.

Parameter names follow ChatMPA's standard vocabulary for new tools: generic
English names, no ``_filter`` suffix, ranges as ``_from`` / ``_to``
(e.g. ``species``, ``year_from``, ``year_to``).
"""

from datetime import date
from typing import Iterable

from mcp_server import config


def choice(name: str, value: str | None, allowed: Iterable[str], *, required: bool = False) -> str | None:
    """Value must be one of ``allowed`` (case-sensitive)."""
    if value is None or value == "":
        if required:
            raise ValueError(f"{name} is required. Allowed: {', '.join(sorted(allowed))}")
        return None
    allowed = set(allowed)
    if value not in allowed:
        raise ValueError(f"Invalid {name} {value!r}. Allowed: {', '.join(sorted(allowed))}")
    return value


def text(name: str, value: str | None, *, max_length: int = 200, required: bool = False) -> str | None:
    """Free text (e.g. a scientific name): trimmed, non-empty if required, bounded."""
    if value is None or not str(value).strip():
        if required:
            raise ValueError(f"{name} is required")
        return None
    value = str(value).strip()
    if len(value) > max_length:
        raise ValueError(f"{name} is too long ({len(value)} characters; maximum {max_length})")
    return value


def int_range(name: str, value: int | None, *, minimum: int | None = None,
              maximum: int | None = None, required: bool = False) -> int | None:
    """Integer within [minimum, maximum]."""
    if value is None:
        if required:
            raise ValueError(f"{name} is required")
        return None
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum} (got {value})")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be <= {maximum} (got {value})")
    return value


def year_range(year_from: int | None, year_to: int | None, *, earliest: int | None = None,
               max_span: int | None = None) -> tuple[int | None, int | None]:
    """``year_from`` <= ``year_to``, not before ``earliest``, not after the current
    year, and at most ``max_span`` years long."""
    latest = date.today().year
    int_range("year_from", year_from, minimum=earliest, maximum=latest)
    int_range("year_to", year_to, minimum=earliest, maximum=latest)
    if year_from is not None and year_to is not None:
        if year_from > year_to:
            raise ValueError(f"year_from ({year_from}) must be <= year_to ({year_to})")
        if max_span is not None and year_to - year_from + 1 > max_span:
            raise ValueError(
                f"The range {year_from}-{year_to} spans {year_to - year_from + 1} years; "
                f"the maximum is {max_span}. Narrow it or split the request."
            )
    return year_from, year_to


def page(limit: int | None, offset: int | None) -> tuple[int, int]:
    """Rows per response and starting row. ``limit`` defaults to, and is capped
    at, MCP_API_MAX_ROWS; ``offset`` is the ``meta.next_offset`` of a previous
    truncated response."""
    limit = config.MCP_API_MAX_ROWS if limit is None else limit
    int_range("limit", limit, minimum=1, maximum=config.MCP_API_MAX_ROWS)
    offset = 0 if offset is None else offset
    int_range("offset", offset, minimum=0)
    return limit, offset
