# MCP Resources

Resources are read-only data endpoints that MCP clients can fetch.
Unlike tools (which perform computation), resources return static or
semi-static content — schemas, data dictionaries, configuration info.

## How Resources Work

Resources are registered in `mcp_server/server.py` using the `@mcp.resource()` decorator:

```python
@mcp.resource("mcp://my-resource")
def my_resource() -> str:
    return json.dumps({"key": "value"})
```

## Built-in Resources

| URI                       | Description                          |
|---------------------------|--------------------------------------|
| `mcp://hello`             | Hello world — connectivity check     |
| `mcp://metadata/manifest` | Full metadata manifest (JSON)        |
| `mcp://metadata/package`  | Package metadata subset              |
| `mcp://metadata/dataset`  | Dataset metadata subset              |

## Adding Custom Resources

1. Define a function in `server.py` (or a separate module).
2. Decorate it with `@mcp.resource("mcp://your-uri")`.
3. Return a JSON string.

### Example: Data Dictionary

```python
@mcp.resource("mcp://data-dictionary")
def data_dictionary() -> str:
    path = Path(__file__).parent / "resources" / "data_dictionary.md"
    return path.read_text(encoding="utf-8")
```

## Client Access

```bash
# Via JSON-RPC
curl http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "resources/read",
    "params": {"uri": "mcp://hello"}
  }'
```
