# Creating a new MCP server from this template

This guide takes you from a copy of the template to a server ready to deploy.
It replaces copying an existing production MCP (e.g. `ltem-db-mcp/TEMPLATE.md`):
the template already has their structure, auth, transport and deployment.

## 0. Choose the data source

| Your data is… | Use | Keep | Delete |
|---|---|---|---|
| In a database of your own project (MySQL) | **A — `db`** | `mcp_server/db.py`, `security.py`, `schema.py` | `mcp_server/api_client.py`, `params.py`, `cache.py`, `tools/api_example.py`, `tests/test_api_client.py` |
| Behind an external HTTP API (a public service, a partner's API) | **B — `api`** | `mcp_server/api_client.py`, `params.py`, `cache.py` (optional) | `mcp_server/db.py`, `security.py`, `schema.py` |
| Somewhere else (files, PDFs, a bucket) | Neither as-is | Start from B: keep its rules (one door to the source, validation, limits, provenance) and replace `api_client.py` with a reader for your source | as for B |

The skill side does not change: a skill receives the table a tool returns, whatever the source.

## 1. Copy and name it

```bash
cp -r mcp-package-template/ my-source-mcp/
cd my-source-mcp/
rm -rf .git && git init          # a new repository, not a fork of the template
```

| File | Change |
|---|---|
| `pyproject.toml` | `name`, `version` (start at `0.1.0`), `description` |
| `mcp_server/server.py` | `TemplateMCP("My MCP Server")` → your server name |
| `metadata/template.json` | Package, dataset and provenance metadata (license, citation, coverage) |
| `docker-compose.yml` / `.env` | `COMPOSE_PROJECT_NAME` |
| `README.md` | Rewrite for your source: what it serves, its tools, its license and citation |

## 2. Keep only one source

Delete the other source's files (table above), then remove its traces:

- `mcp_server/source.py` — delete the other source's branch in `health()` and `warmup()`.
- `mcp_server/server.py` — with B, delete `_register_db_schema_tools()` and its call.
- `mcp_server/config.py` — delete the other source's section and its checks in `missing_required()`; set the default of `MCP_DATA_SOURCE` to your source.
- `.env.example` — delete the other source's section.
- `pyproject.toml` — with B, drop `pymysql` and `DBUtils`; with A, `httpx` can stay (tests use it).
- `tools/` — delete `api_example.py` (A) or replace it with your tools (B). `example_tools.py` and `statistics_tools.py` are examples that use no data: delete them when you have real tools.

Run `pytest`: it must still pass before you write anything new.

## 3A. Configure a database source

1. **Read-only user.** Ask for (or create) a database user with `SELECT` only. Never use an admin user, even locally.
2. **Whitelist.** List the tables the tools may read in `ALLOWED_TABLES` (`mcp_server/security.py`). An empty list blocks every query: that is on purpose.
3. **Credentials** in `.env` only (`MCP_DB_*` or `DATABASE_URL`). `.env` is git-ignored; never commit it.
4. **Size.** Keep `DEFAULT_MAX_ROWS` for responses. For queries whose rows a tool aggregates in Python, pass `max_rows=AGGREGATION_MAX_ROWS` explicitly, so the cap never silently changes an answer.

## 3B. Configure an API source

Read the API's documentation first and write down, in the README:

1. **Base URL and authentication.** `MCP_API_BASE_URL`; `MCP_API_KEY` only if it needs one (header by default; `MCP_API_KEY_PARAM` if it wants it in the URL).
2. **Limits.** Requests per minute → `MCP_API_MIN_INTERVAL_SECONDS`; page size and maximum offset → `fetch_pages(page_size=…)` and `MCP_API_MAX_ROWS`; typical latency → `MCP_API_TIMEOUT_SECONDS`.
3. **Pagination style.** `fetch_pages` handles `offset`/`limit` (and the names of the results and total keys). For `page`/`per_page` or cursor pagination, write a small variant next to it.
4. **Change over time.** Can the same query return different data tomorrow? (Almost always yes.) Report the source's version or release in `provenance(version=…)` if the API exposes one; if it offers citable downloads (a DOI), say how to obtain one for reference cases.
5. **License and citation.** Whether the data's license allows your use, and how to cite it. Put both in the README and in `metadata/template.json`.
6. **Cache.** Turn it on (`MCP_CACHE_TTL_SECONDS`) only if responses are slow, rate-limited or paid, and the data does not change within the TTL.

## 4. Write the tools

Create `tools/<topic>.py` with a `register(mcp)` function; the server finds it on its own. See [docs/tutorials/02_add_tools.md](docs/tutorials/02_add_tools.md) and, for B, [09_api_data_source.md](docs/tutorials/09_api_data_source.md).

Rules for every tool:

- **One door to the data.** A: `execute_select()` with `%s` parameters, never values formatted into SQL. B: `api_client.get_json()` / `fetch_pages()`, never `httpx` directly.
- **Validate first.** B: `params.*` for every parameter, before any request.
- **Standard parameter names** for new tools: generic English names, the same across tools and skills, no `_filter` suffix, ranges as `_from` / `_to` (`species`, `state`, `year_from`, `year_to`, …). Translate them to the source's own names inside the tool.
- **Output columns keep the source's names**; do not rename them.
- **Return** a JSON string: `{"data": [...], "meta": {...}}`. With B, `meta` includes `api_client.provenance(...)`.
- **Never cut silently.** If a response is capped, `meta.truncated = true` and `meta.next_offset` say where to continue.
- **The docstring is what the model reads** to decide whether to use the tool. Say what it returns, at what level (one row per year, per site, per record), units, columns, and whether it can be truncated. Put the important part first: long descriptions may be cut when published.
- **No secrets and no sensitive data** in code, docstrings, examples, tests or logs.

## 5. Test locally

```bash
pytest                         # no database, API or AWS needed
python -m mcp_server           # stops with a clear message if .env is incomplete
```

Then call `health_check` (it says which source is active and what is missing), and connect an MCP client, e.g. Claude Code with a `.mcp.json`:

```json
{ "my-source-mcp": { "type": "http", "url": "http://localhost:8000/mcp" } }
```

Add tests for your tools with fakes: a mocked `execute_select` (A) or `httpx.MockTransport` through `api_client.set_transport()` (B), as in `tests/test_api_client.py`.

## 6. Deploy

See [DEPLOYMENT.md](DEPLOYMENT.md). In short: branches `main` → `release`; a push to `release` runs `.github/workflows/deploy-ecs.yml`, which needs the repository variables `AWS_REGION`, `AWS_ROLE_ARN`, `ECR_REPOSITORY`, `ECS_CLUSTER`, `ECS_SERVICE` (and infrastructure created outside this repo). Runtime secrets go in the ECS task definition, never in the repository. Agree on these values, the auth scope (`AUTH_REQUIRED_SCOPE`) and the redeploy process with whoever operates the platform.

Alternative, a single server with Docker Compose: set the repository variable `DEPLOY_TARGET=ssh` and the secrets `DEPLOY_HOST`, `DEPLOY_SSH_KEY`, `DEPLOY_PATH`; a push to `release` then runs `.github/workflows/deploy-ssh.yml` (see DEPLOYMENT.md, "Alternative: single server over SSH").

To give researchers the server's skills in Claude Code, fill in `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` and `.mcp.json` (name, URL): [docs/tutorials/08_package_as_plugin.md](docs/tutorials/08_package_as_plugin.md).

## Checklist before the first deployment

- [ ] One data source kept; the other's files and code paths deleted; `pytest` passes.
- [ ] Server, package and metadata renamed; README rewritten for the source.
- [ ] A: read-only DB user; `ALLOWED_TABLES` lists only what the tools need.
- [ ] B: limits, pagination, change over time, license and citation documented; `params.*` on every parameter.
- [ ] Every tool returns `{"data", "meta"}`, reports truncation, uses standard parameter names and keeps the source's column names.
- [ ] Docstrings say what, at what level, units and columns.
- [ ] `health_check` answers `ok` locally against the real source.
- [ ] `.env` not committed; no keys, passwords, hosts, account IDs, ARNs or table names of real infrastructure anywhere in the repository (search the diff before every push).
- [ ] Deployment variables and auth scope agreed with the platform's operators; `AUTH_ENABLED=true` in deployed environments.
