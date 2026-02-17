#!/usr/bin/env bash
# =============================================================================
# generate_manifest.sh — Generate metadata/manifest.json
#
# Usage:
#   bash scripts/generate_manifest.sh           # writes manifest.json
#   bash scripts/generate_manifest.sh --stdout   # prints to stdout
# =============================================================================

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

GREEN='\033[0;32m'
NC='\033[0m'

# Activate venv if available
if [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

echo -e "${GREEN}[MANIFEST]${NC} Generating manifest..."

python -m mcp_server.metadata.manifest "$@"

echo -e "${GREEN}[MANIFEST]${NC} Done."
