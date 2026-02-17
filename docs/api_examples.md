# API Examples

All MCP communication uses JSON-RPC 2.0 over HTTP.  These examples use `curl` for clarity.

## Base URL

- **Local (no Docker):** `http://localhost:8000/mcp`
- **Docker Compose:** `http://localhost:8001/mcp`
- **Production:** `https://your-domain.com/my-mcp/mcp` (with Basic Auth)

## Initialize Handshake

Every MCP session starts with an initialize call:

```bash
curl -s http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {
        "name": "my-client",
        "version": "1.0"
      }
    }
  }'
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {},
      "resources": {},
      "prompts": {}
    },
    "serverInfo": {
      "name": "My MCP Server",
      "version": "1.0.0"
    }
  }
}
```

## List Available Tools

```bash
curl -s http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
  }'
```

## Call a Tool

### Echo Tool

```bash
curl -s http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "echo",
      "arguments": {
        "message": "hello world"
      }
    }
  }'
```

### Calculator Tool

```bash
curl -s http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "calculator",
      "arguments": {
        "operation": "multiply",
        "a": 7,
        "b": 6
      }
    }
  }'
```

### Descriptive Statistics Tool

```bash
curl -s http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 5,
    "method": "tools/call",
    "params": {
      "name": "descriptive_stats",
      "arguments": {
        "values": [10.5, 20.3, 15.7, 18.2, 12.1, 22.8, 14.6]
      }
    }
  }'
```

## Read a Resource

```bash
curl -s http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 6,
    "method": "resources/read",
    "params": {
      "uri": "mcp://hello"
    }
  }'
```

## List Resources

```bash
curl -s http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 7,
    "method": "resources/list",
    "params": {}
  }'
```

## List Prompts (Skills)

```bash
curl -s http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 8,
    "method": "prompts/list",
    "params": {}
  }'
```

## Get a Prompt (Skill Body)

```bash
curl -s http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 9,
    "method": "prompts/get",
    "params": {
      "name": "example-health-check"
    }
  }'
```

## Health Check Tool

```bash
curl -s http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 10,
    "method": "tools/call",
    "params": {
      "name": "health_check",
      "arguments": {}
    }
  }'
```

## With Basic Auth (Production)

```bash
curl -s -u mcp_user:your-password \
  https://your-domain.com/my-mcp/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'
```

## SSE Transport

For streaming responses, set the Accept header:

```bash
curl -N http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "echo",
      "arguments": {"message": "streaming test"}
    }
  }'
```
