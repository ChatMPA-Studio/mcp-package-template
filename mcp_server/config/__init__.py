"""Configuration module — re-export settings for convenience."""

from mcp_server.config.settings import (
    PORT,
    MCP_BASE_PATH,
    LOG_LEVEL,
    DATABASE_URL,
    DB_HOST,
    DB_PORT,
    DB_USER,
    DB_PASSWORD,
    DB_NAME,
    DB_BACKEND,
    setup_logging,
    print_startup_summary,
)

__all__ = [
    "PORT",
    "MCP_BASE_PATH",
    "LOG_LEVEL",
    "DATABASE_URL",
    "DB_HOST",
    "DB_PORT",
    "DB_USER",
    "DB_PASSWORD",
    "DB_NAME",
    "DB_BACKEND",
    "setup_logging",
    "print_startup_summary",
]
