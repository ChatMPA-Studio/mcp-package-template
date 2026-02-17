#!/usr/bin/env bash
# =============================================================================
# validate_line_endings.sh — Detect Windows CRLF line endings
#
# Windows CRLF (\r\n) line endings break shell scripts on Linux.
# Run this before deploying to catch problems early.
#
# Usage:
#   bash scripts/validate_line_endings.sh
#
# Exit codes:
#   0 — all files have Unix (LF) line endings
#   1 — CRLF detected in one or more files
# =============================================================================

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

CRLF_FILES=()

# Check shell scripts
while IFS= read -r -d '' file; do
    if grep -Prl '\r$' "$file" > /dev/null 2>&1; then
        CRLF_FILES+=("$file")
    fi
done < <(find . -type f \( -name "*.sh" -o -name "*.py" -o -name "*.yml" -o -name "*.yaml" -o -name "Dockerfile" -o -name "*.toml" \) -not -path './.venv/*' -not -path './.git/*' -print0)

if [ ${#CRLF_FILES[@]} -eq 0 ]; then
    echo -e "${GREEN}[OK]${NC} All checked files have Unix (LF) line endings."
    exit 0
fi

echo -e "${RED}[FAIL]${NC} CRLF line endings detected in ${#CRLF_FILES[@]} file(s):"
echo ""
for f in "${CRLF_FILES[@]}"; do
    echo -e "  ${YELLOW}$f${NC}"
done

echo ""
echo "Fix with:"
echo "  # Single file:"
echo "  sed -i 's/\\r\$//' path/to/file"
echo ""
echo "  # All affected files:"
echo "  find . -type f \\( -name '*.sh' -o -name '*.py' \\) -exec sed -i 's/\\r\$//' {} +"
echo ""
echo "  # Or configure git to auto-convert:"
echo "  git config core.autocrlf input"

exit 1
