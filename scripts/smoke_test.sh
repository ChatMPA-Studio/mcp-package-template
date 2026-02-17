#!/usr/bin/env bash
# =============================================================================
# smoke_test.sh — Verify the MCP server is running and responding correctly
#
# Usage:
#   bash scripts/smoke_test.sh                    # default: localhost:8000/mcp
#   bash scripts/smoke_test.sh http://host:port/path
#
# What it tests:
#   1. Initialize handshake (JSON-RPC 2.0)
#   2. Tool call: echo
#   3. Tool call: server_time
#   4. Tool call: calculator
#   5. Resource fetch: mcp://hello
#   6. Prompt listing (skills)
#
# Prerequisites:
#   - curl and jq installed
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
    curl -sf -X POST "$BASE_URL" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d "$body" 2>/dev/null || echo '{"error":"connection_failed"}'
}

echo ""
echo "=== MCP Smoke Test ==="
echo "Target: $BASE_URL"
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
# 2. Tool: echo
# ---------------------------------------------------------------------------
echo "--- Tool: echo ---"
ECHO=$(rpc_call '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "echo",
        "arguments": {"message": "smoke-test"}
    }
}')
check "echo tool returns message" "$ECHO" 'smoke-test'

# ---------------------------------------------------------------------------
# 3. Tool: server_time
# ---------------------------------------------------------------------------
echo "--- Tool: server_time ---"
TIME=$(rpc_call '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
        "name": "server_time",
        "arguments": {}
    }
}')
check "server_time returns UTC" "$TIME" 'utc'

# ---------------------------------------------------------------------------
# 4. Tool: calculator
# ---------------------------------------------------------------------------
echo "--- Tool: calculator ---"
CALC=$(rpc_call '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
        "name": "calculator",
        "arguments": {"operation": "add", "a": 2, "b": 3}
    }
}')
check "calculator 2+3" "$CALC" '"result"'

# ---------------------------------------------------------------------------
# 5. Resource: mcp://hello
# ---------------------------------------------------------------------------
echo "--- Resource: hello ---"
HELLO=$(rpc_call '{
    "jsonrpc": "2.0",
    "id": 5,
    "method": "resources/read",
    "params": {"uri": "mcp://hello"}
}')
check "hello resource" "$HELLO" 'Hello'

# ---------------------------------------------------------------------------
# 6. Prompts listing (skills)
# ---------------------------------------------------------------------------
echo "--- Prompts (skills) ---"
PROMPTS=$(rpc_call '{
    "jsonrpc": "2.0",
    "id": 6,
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
