#!/usr/bin/env bash
# =============================================================================
# smoke_test.sh — Verify the MCP server is running and responding correctly
#
# Usage:
#   bash scripts/smoke_test.sh                    # default: localhost:8000/mcp
#   bash scripts/smoke_test.sh http://host:port/path
#   MCP_SMOKE_KEY=<key> bash scripts/smoke_test.sh https://…/mcp   # with AUTH_ENABLED
#
# What it tests (only things every MCP from this template has):
#   1. Initialize handshake (JSON-RPC 2.0)
#   2. tools/list returns tools
#   3. Tool call: health_check (reports the data source's status)
#   4. Resource fetch: mcp://hello
#   5. Prompt listing (skills)
#
# The key is read from the MCP_SMOKE_KEY environment variable, never from an
# argument (arguments end up in shell history).
#
# Prerequisites:
#   - curl installed
#   - MCP server running
# =============================================================================

set -euo pipefail

# Default base URL
BASE_URL="${1:-http://localhost:8000/mcp}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

AUTH_HEADER=()
if [ -n "${MCP_SMOKE_KEY:-}" ]; then
    AUTH_HEADER=(-H "Authorization: Bearer ${MCP_SMOKE_KEY}")
fi

check() {
    local name="$1"
    local response="$2"
    local check_pattern="$3"

    if echo "$response" | grep -q "$check_pattern"; then
        echo -e "  ${GREEN}PASS${NC}  $name"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}FAIL${NC}  $name"
        echo -e "        Response: $(echo "$response" | head -c 200)"
        FAIL=$((FAIL + 1))
    fi
}

rpc_call() {
    local body="$1"
    curl -sf --compressed -X POST "$BASE_URL" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        ${AUTH_HEADER[@]+"${AUTH_HEADER[@]}"} \
        -d "$body" 2>/dev/null || echo '{"error":"connection_failed"}'
}

echo ""
echo "=== MCP Smoke Test ==="
echo "Target: $BASE_URL"
[ -n "${MCP_SMOKE_KEY:-}" ] && echo "Auth:   Bearer key from MCP_SMOKE_KEY"
echo ""

# ---------------------------------------------------------------------------
# 1. Initialize
# ---------------------------------------------------------------------------
echo "--- Initialize ---"
INIT=$(rpc_call '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "smoke-test", "version": "1.0"}
    }
}')
check "JSON-RPC initialize" "$INIT" '"jsonrpc"'

# ---------------------------------------------------------------------------
# 2. Tools listing
# ---------------------------------------------------------------------------
echo "--- Tools ---"
TOOLS=$(rpc_call '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
}')
check "tools/list includes health_check" "$TOOLS" '"health_check"'

# ---------------------------------------------------------------------------
# 3. Tool: health_check
# ---------------------------------------------------------------------------
echo "--- Tool: health_check ---"
HEALTH=$(rpc_call '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
        "name": "health_check",
        "arguments": {}
    }
}')
check "health_check answers" "$HEALTH" 'status'
if echo "$HEALTH" | grep -q 'status\\\?": \\\?"ok'; then
    echo -e "        data source: ${GREEN}ok${NC}"
else
    echo -e "        ${YELLOW}data source not ok — read the health_check response above or the logs${NC}"
    echo -e "        $(echo "$HEALTH" | head -c 300)"
fi

# ---------------------------------------------------------------------------
# 4. Resource: mcp://hello
# ---------------------------------------------------------------------------
echo "--- Resource: hello ---"
HELLO=$(rpc_call '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "resources/read",
    "params": {"uri": "mcp://hello"}
}')
check "hello resource" "$HELLO" 'Hello'

# ---------------------------------------------------------------------------
# 5. Prompts listing (skills)
# ---------------------------------------------------------------------------
echo "--- Prompts (skills) ---"
PROMPTS=$(rpc_call '{
    "jsonrpc": "2.0",
    "id": 5,
    "method": "prompts/list",
    "params": {}
}')
check "prompts/list returns data" "$PROMPTS" '"prompts"'

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
TOTAL=$((PASS + FAIL))
echo "=== Results: ${PASS}/${TOTAL} passed ==="
if [ $FAIL -gt 0 ]; then
    echo -e "${RED}${FAIL} test(s) failed.${NC}"
    exit 1
else
    echo -e "${GREEN}All tests passed.${NC}"
    exit 0
fi
