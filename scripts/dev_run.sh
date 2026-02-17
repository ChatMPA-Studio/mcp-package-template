#!/usr/bin/env bash
# =============================================================================
# dev_run.sh — Run the MCP server locally for development
#
# Usage:
#   bash scripts/dev_run.sh
#
# Prerequisites:
#   - Python 3.10+ with venv
#   - A valid .env file (copy from .env.example)
# =============================================================================

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[DEV]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }

# ---------------------------------------------------------------------------
# Step 1: Check .env
# ---------------------------------------------------------------------------
if [ ! -f ".env" ]; then
    fail ".env file not found. Run: cp .env.example .env && edit .env"
fi
log ".env found"

# ---------------------------------------------------------------------------
# Step 2: Create / activate virtual environment
# ---------------------------------------------------------------------------
if [ ! -d ".venv" ]; then
    log "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate
# shellcheck disable=SC1091
source .venv/bin/activate
log "Virtual environment activated: $(python3 --version)"

# ---------------------------------------------------------------------------
# Step 3: Install dependencies
# ---------------------------------------------------------------------------
log "Installing package (editable mode)..."
pip install -q -e ".[dev]"
log "Dependencies installed"

# ---------------------------------------------------------------------------
# Step 4: Run the server
# ---------------------------------------------------------------------------
PORT=$(grep -E '^PORT=' .env 2>/dev/null | cut -d= -f2 || echo "8000")
MCP_PATH=$(grep -E '^MCP_BASE_PATH=' .env 2>/dev/null | cut -d= -f2 || echo "/mcp")

log "Starting MCP server on http://localhost:${PORT}${MCP_PATH}"
log "Press Ctrl+C to stop"
echo ""

python -m mcp_server
