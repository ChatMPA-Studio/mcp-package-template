# MCP Template Specification

## Design Principles

1. **Domain-agnostic** — The template contains no domain-specific logic.  All domain knowledge lives in tool modules, skill definitions, and metadata.
2. **Convention over configuration** — Drop a file in the right directory and it works.  No registration boilerplate.
3. **Security by default** — Read-only enforcement, SQL whitelist, non-root Docker user, localhost-only port binding.
4. **Composable tools** — Tools are small, stateless functions.  Skills orchestrate tools into workflows.
5. **Portable metadata** — JSON schemas follow DCAT conventions for interoperability.

## Module Contracts

### Tool Module Contract

Every file in `mcp_server/tools/` that is not `__init__.py` or `discovery.py` is a candidate tool module.

**Required:**
```python
def register(mcp: FastMCP) -> None:
    """Register tools with the MCP server."""
    @mcp.tool()
    def my_tool(param: str) -> str:
        """Tool docstring becomes the MCP tool description.

        Args:
            param: Parameter docstring becomes the parameter description.
        """
        return json.dumps({"result": "value"})
```

**Rules:**
- Return type must be `str` (JSON-encoded).
- Tools must be stateless — no module-level mutable state.
- Use `mcp_server.db.execute_select()` for database queries (passes through security layer).
- Do not import other tool modules — tools are independent.

### Skill Definition Contract

Every `.md` file in `mcp_server/skills/` (flat) or `mcp_server/skills/<name>/SKILL.md` (nested) is a candidate skill.

**Required YAML frontmatter:**
```yaml
---
name: skill-name
description: One-line description of the skill's purpose.
---
```

**Optional frontmatter:**
```yaml
version: 1.0.0
inputs: description of expected inputs
outputs: description of expected outputs
```

**Body format:**
- Markdown with step-by-step workflow.
- Each step references a tool by name with expected parameters.
- Skills orchestrate tools — they do not duplicate tool logic.

### Config Contract

Environment variables follow the pattern:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MCP_DB_HOST` | Yes (if no DATABASE_URL) | localhost | Database hostname |
| `MCP_DB_PORT` | No | 3306 | Database port |
| `MCP_DB_USER` | No | mcp_readonly | Database username |
| `MCP_DB_PASSWORD` | Yes (if no DATABASE_URL) | — | Database password |
| `MCP_DB_NAME` | No | mydb | Database name |
| `MCP_DB_BACKEND` | No | mysql | Database type |
| `DATABASE_URL` | No | — | Full connection URL (overrides above) |
| `PORT` | No | 8000 | HTTP server port |
| `MCP_BASE_PATH` | No | /mcp | HTTP endpoint path |
| `LOG_LEVEL` | No | INFO | Logging verbosity |
| `HOST_PORT` | No | 8001 | Docker host port mapping |

### Security Contract

- `validate_sql(sql)` — raises `ValueError` if the query is not safe.
- `enforce_limit(sql, max_rows)` — returns modified SQL with capped LIMIT.
- `sanitize_table_name(name)` — raises `ValueError` if table is not whitelisted.
- If `ALLOWED_TABLES` is empty, table validation is skipped (open mode).

## Versioning

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** — Breaking changes to tool signatures, resource URIs, or config format
- **MINOR** — New tools, skills, or resources (backward-compatible)
- **PATCH** — Bug fixes, documentation updates

Update version in:
1. `pyproject.toml` → `version`
2. `metadata/template.json` → `package.version`
3. Git tag: `git tag v1.2.0 && git push origin v1.2.0`
