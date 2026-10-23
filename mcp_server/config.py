"""Centralized configuration — read, validate, and expose environment variables.

All configuration is loaded once at import time. Nothing here exits the
process: importing the package must work without credentials (tests, and
data sources that don't need them). ``check_required()`` is what enforces the
variables the selected data source needs; ``python -m mcp_server`` calls it at
startup, so a container with a missing variable stops immediately with a
clear message instead of failing on the first request.

Data source
-----------
``MCP_DATA_SOURCE`` selects where the tools get their data:

* ``db``  — a project database (MySQL), via ``mcp_server/db.py`` and
  ``mcp_server/security.py``. Credentials: ``DATABASE_URL`` (takes precedence)
  or the individual ``MCP_DB_*`` variables.

Never put real values in this file or in ``.env.example``: they go in a local
``.env`` (git-ignored) or in the deployment's environment.
"""

import logging
import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv

# Load .env from project root (parent of mcp_server/)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# Server settings
# ---------------------------------------------------------------------------

PORT: int = int(os.getenv("PORT", "8000"))
MCP_BASE_PATH: str = os.getenv("MCP_BASE_PATH", "/mcp")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

# ---------------------------------------------------------------------------
# Data source
# ---------------------------------------------------------------------------

DATA_SOURCES = ("db",)
MCP_DATA_SOURCE: str = os.getenv("MCP_DATA_SOURCE", "db").strip().lower()

# ---------------------------------------------------------------------------
# Database settings (MCP_DATA_SOURCE=db)
# ---------------------------------------------------------------------------
# DATABASE_URL takes precedence over the individual MCP_DB_* variables.

_DEFAULT_PORTS = {"mysql": 3306, "postgresql": 5432, "sqlite": 0}
_SCHEME_MAP = {
    "mysql": "mysql",
    "mysql+pymysql": "mysql",
    "postgresql": "postgresql",
    "postgres": "postgresql",
    "postgresql+psycopg2": "postgresql",
    "sqlite": "sqlite",
}


def _parse_database_url(url: str) -> dict:
    """Parse a DATABASE_URL into individual components.

    Supports ``mysql://user:pass@host:port/dbname`` (and the postgresql / sqlite
    schemes, for which db.py must be extended). User and password are
    percent-decoded: urlparse leaves them encoded, so a password with an
    ``@`` or ``#`` written as ``%40`` / ``%23`` would otherwise fail to log in.
    """
    parsed = urlparse(url)
    scheme = _SCHEME_MAP.get(parsed.scheme, parsed.scheme)
    return {
        "backend": scheme,
        "host": parsed.hostname or "localhost",
        "port": parsed.port or _DEFAULT_PORTS.get(scheme, 3306),
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "name": parsed.path.lstrip("/"),
    }


DATABASE_URL: str | None = os.getenv("DATABASE_URL") or None

if DATABASE_URL:
    _db = _parse_database_url(DATABASE_URL)
    DB_BACKEND: str = _db["backend"]
    DB_HOST: str = _db["host"]
    DB_PORT: int = _db["port"]
    DB_USER: str = _db["user"]
    DB_PASSWORD: str = _db["password"]
    DB_NAME: str = _db["name"]
else:
    DB_BACKEND = os.getenv("MCP_DB_BACKEND", "mysql")
    DB_HOST = os.getenv("MCP_DB_HOST", "")
    DB_PORT = int(os.getenv("MCP_DB_PORT", str(_DEFAULT_PORTS.get(DB_BACKEND, 3306))))
    DB_USER = os.getenv("MCP_DB_USER", "")
    DB_PASSWORD = os.getenv("MCP_DB_PASSWORD", "")
    DB_NAME = os.getenv("MCP_DB_NAME", "")

# TLS (optional, off by default). With a CA bundle the server certificate is
# verified; without one the connection is encrypted but unverified. Strongly
# recommended once the database is reachable over the public internet. Amazon
# RDS bundle: https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
DB_SSL: bool = _flag("DB_SSL")
DB_SSL_CA: str | None = os.getenv("DB_SSL_CA") or None

# Connection pool. Each tool call borrows a connection instead of opening its
# own (TCP + auth handshake per call). DB_POOL_MAX is the hard cap on open
# connections; requests beyond it wait instead of failing (see db.py).
DB_POOL_MIN: int = int(os.getenv("DB_POOL_MIN", "1"))
DB_POOL_MAX: int = int(os.getenv("DB_POOL_MAX", "10"))
# Defaults to DB_POOL_MAX: with a smaller cache, connections opened during a
# burst beyond it are closed when returned, and the next burst reopens them.
DB_POOL_MAX_CACHED: int = int(os.getenv("DB_POOL_MAX_CACHED", str(DB_POOL_MAX)))


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def missing_required() -> list[str]:
    """Return the problems that would stop the selected data source from working."""
    problems: list[str] = []
    if MCP_DATA_SOURCE not in DATA_SOURCES:
        problems.append(
            f"MCP_DATA_SOURCE={MCP_DATA_SOURCE!r} is not supported; use one of {', '.join(DATA_SOURCES)}"
        )
    if MCP_DATA_SOURCE == "db":
        if DATABASE_URL:
            if not (DB_USER and DB_NAME):
                problems.append("DATABASE_URL must include a user and a database name")
        else:
            for name, value in (("MCP_DB_HOST", DB_HOST), ("MCP_DB_USER", DB_USER),
                                ("MCP_DB_PASSWORD", DB_PASSWORD), ("MCP_DB_NAME", DB_NAME)):
                if not value:
                    problems.append(f"{name} is not set (or set DATABASE_URL)")
    return problems


def check_required() -> None:
    """Exit with a clear message if the selected data source is misconfigured."""
    problems = missing_required()
    if problems:
        raise SystemExit(
            "FATAL: configuration incomplete:\n  - "
            + "\n  - ".join(problems)
            + "\nCopy .env.example to .env and fill it in (never commit .env)."
        )


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging() -> None:
    """Configure root logger based on LOG_LEVEL."""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def print_startup_summary() -> None:
    """Log a safe configuration summary (no passwords)."""
    logger = logging.getLogger("mcp_server.config")
    logger.info("=== MCP Server Configuration ===")
    logger.info("  Port:        %s", PORT)
    logger.info("  Base Path:   %s", MCP_BASE_PATH)
    logger.info("  Log Level:   %s", LOG_LEVEL)
    logger.info("  Data source: %s", MCP_DATA_SOURCE)
    if MCP_DATA_SOURCE == "db":
        logger.info("  DB Backend:  %s", DB_BACKEND)
        logger.info("  DB Host:     %s", DB_HOST)
        logger.info("  DB Port:     %s", DB_PORT)
        logger.info("  DB User:     %s", DB_USER)
        logger.info("  DB Name:     %s", DB_NAME)
        logger.info("  DB Password: %s", "****" if DB_PASSWORD else "NOT SET")
        logger.info("  DB SSL:      %s", "on" if DB_SSL else "off")
        logger.info("  DB Pool:     min=%s max_cached=%s max=%s",
                    DB_POOL_MIN, DB_POOL_MAX_CACHED, DB_POOL_MAX)
        logger.info("  DB Config:   %s", "DATABASE_URL" if DATABASE_URL else "MCP_DB_* env vars")
    logger.info("================================")
