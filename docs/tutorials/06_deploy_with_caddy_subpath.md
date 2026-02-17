# Tutorial 06: Deploy with Caddy Subpath Routing

## Goal

Deploy the MCP server behind Caddy with TLS, Basic Auth, and subpath routing.

## Prerequisites

- MCP running in Docker on a VPS
- Caddy installed on the VPS
- A domain name pointing to the VPS

## Steps

### 1. Generate a Password Hash

```bash
caddy hash-password --plaintext 'your-secure-password'
# Output: $2a$14$aBcDeFgHiJkLmNoPqRsTuV...
```

### 2. Configure Caddy

Edit `/etc/caddy/Caddyfile`:

```caddy
your-domain.com {

    # Weather MCP at /weather/
    route /weather/* {
        basicauth {
            mcp_user $2a$14$YOUR_HASH_HERE
        }
        uri strip_prefix /weather
        reverse_proxy localhost:8001
    }
}
```

### 3. Reload Caddy

```bash
# Validate config first
caddy validate --config /etc/caddy/Caddyfile

# Reload
systemctl reload caddy
```

### 4. Test

```bash
# Should return MCP server response
curl -u mcp_user:your-secure-password \
  https://your-domain.com/weather/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

## Subpath Constraints

| Constraint | Detail |
|-----------|--------|
| Trailing slash | Route must end with `/*` (e.g., `/weather/*`) |
| `strip_prefix` | Removes the subpath before forwarding — the container sees `/mcp`, not `/weather/mcp` |
| Header forwarding | Caddy sets `X-Forwarded-For`, `X-Forwarded-Proto` automatically |
| TLS | Caddy obtains and renews certificates automatically via ACME |

## Multiple MCPs

Each MCP gets its own route block and `HOST_PORT`:

```caddy
your-domain.com {
    route /weather/* {
        basicauth { weather_user $HASH1 }
        uri strip_prefix /weather
        reverse_proxy localhost:8001
    }

    route /ecology/* {
        basicauth { ecology_user $HASH2 }
        uri strip_prefix /ecology
        reverse_proxy localhost:8002
    }

    route /sensors/* {
        basicauth { sensor_user $HASH3 }
        uri strip_prefix /sensors
        reverse_proxy localhost:8003
    }
}
```

## Connecting an AI Client

Configure your MCP client with:

- **URL:** `https://your-domain.com/weather/mcp`
- **Auth:** Basic Auth (username + password)
- **Transport:** HTTP/SSE

Example Claude Code MCP config:

```json
{
  "mcpServers": {
    "weather": {
      "type": "sse",
      "url": "https://your-domain.com/weather/mcp",
      "headers": {
        "Authorization": "Basic base64(user:password)"
      }
    }
  }
}
```

## Next Steps

- [Tutorial 07: Release Versioning](07_release_versioning.md)
