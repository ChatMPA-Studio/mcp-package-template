# API Examples

All MCP communication uses JSON-RPC 2.0 over HTTP.  These examples use `curl` for clarity.

## Base URL

- **Local (no Docker):** `http://localhost:8000/mcp`
- **Docker Compose:** `http://localhost:8001/mcp`
- **Production:** `https://<host>/<path>/mcp` (with a Bearer key if `AUTH_ENABLED`)

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

## With an API key (Production)

With `AUTH_ENABLED=true` every request needs a Bearer key that includes this
server's scope. Read it from an environment variable rather than typing it into
the command (commands end up in shell history):

```bash
curl -s --compressed https://<host>/<path>/mcp \
  -H "Authorization: Bearer $MCP_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'
```

## Response Format

The server answers with plain JSON (`json_response=True`), not an SSE stream,
compressed with gzip when the client sends `Accept-Encoding: gzip` (`--compressed`
in curl). Clients must still send `Accept: application/json, text/event-stream`
(the MCP spec requires accepting both). Every tool returns its result as a JSON
string in `result.content[0].text`:

```json
{"data": [ ], "meta": {"returned": 100, "truncated": true, "next_offset": 100}}
```

With the API source (option B), `meta` also says where and when the data was
retrieved: `source`, `retrieved_at`, `query`.
