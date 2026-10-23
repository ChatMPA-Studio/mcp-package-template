# Quick Launch Guide

## What This Template Is

A ready-to-copy MCP server: FastMCP over stateless HTTP, optional API-key auth,
per-call timing, Docker image and Amazon ECS deployment. It serves data from a
**project database** (option A, `db`) or an **external API** (option B, `api`);
a new MCP keeps one. Full guide: [TEMPLATE.md](TEMPLATE.md).

## Prerequisites

- Python 3.10+
- Docker (to build the image)
- For a database source: a read-only user. For an API source: its documentation.

## Copy to a New MCP

```bash
cp -r mcp-package-template/ my-source-mcp/
cd my-source-mcp/
rm -rf .git && git init

# Update identity
# 1. pyproject.toml          -> name, version, description
# 2. mcp_server/server.py    -> TemplateMCP("Your MCP Name", …)
# 3. metadata/template.json  -> package, dataset (license, citation), provenance
# 4. docker-compose.yml/.env -> COMPOSE_PROJECT_NAME

# Keep one data source (TEMPLATE.md, step 2)
#   A (db):  rm mcp_server/api_client.py mcp_server/params.py mcp_server/cache.py tools/api_example.py tests/test_api_client.py
#   B (api): rm mcp_server/db.py mcp_server/security.py mcp_server/schema.py
#   then remove the other source's branch in mcp_server/source.py and its section in config.py / .env.example
```

## Run Locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                          # no database, API or AWS needed

cp .env.example .env            # MCP_DATA_SOURCE + its section; never commit .env
python -m mcp_server            # stops with a clear message if .env is incomplete
bash scripts/smoke_test.sh      # health_check must report "ok"
```

With Docker Compose instead:

```bash
docker compose up --build -d
docker compose logs -f
bash scripts/smoke_test.sh http://127.0.0.1:8001/mcp
docker compose down
```

## Add a New Tool

1. Create `tools/my_tools.py`:

```python
import json
from mcp_server.db import execute_select      # option A; option B: from mcp_server import api_client, params

def register(mcp) -> None:
    @mcp.tool()
    def my_tool(species: str, year_from: int | None = None) -> str:
        """What it returns, at what level, units and columns."""
        rows = execute_select("SELECT … FROM my_table WHERE species = %s", params=(species,))
        return json.dumps({"data": rows, "meta": {"returned": len(rows)}}, default=str)
```

2. Restart the server: it is registered automatically.
3. Rules: [docs/tutorials/02_add_tools.md](docs/tutorials/02_add_tools.md) (database), [09_api_data_source.md](docs/tutorials/09_api_data_source.md) (API).

## Add a New Skill

1. Create `skills/my-workflow/SKILL.md`:

```markdown
---
name: my-workflow
description: One line saying when to use this workflow.
---

# My Workflow

## Step 1: Do Something
Call `my_tool` with …

## Step 2: Analyse Results
…
```

2. Restart the server: it is registered as an MCP prompt.

## Generate Metadata Manifest

```bash
python scripts/generate_metadata_manifest.py
# Output: metadata/manifest.json (git-ignored; generated)
```

## Deploy to Amazon ECS

1. Agree with the platform's operators on the infrastructure (ECR, cluster, service, load balancer route, IAM role) and the auth scope.
2. Set the repository variables `AWS_REGION`, `AWS_ROLE_ARN`, `ECR_REPOSITORY`, `ECS_CLUSTER`, `ECS_SERVICE`.
3. `git push origin release`.

Step by step: [docs/tutorials/06_deploy_to_ecs.md](docs/tutorials/06_deploy_to_ecs.md).

Single server instead of ECS: `DEPLOY_TARGET=ssh` + `deploy-ssh.yml` ([DEPLOYMENT.md](DEPLOYMENT.md)).

## Use It Locally from Claude (stdio)

`python run_stdio.py` runs the same server over stdio (reads `.env`). To ship the skills to researchers as a Claude Code plugin: [docs/tutorials/08_package_as_plugin.md](docs/tutorials/08_package_as_plugin.md).

## Run Smoke Tests

```bash
# Against local server
bash scripts/smoke_test.sh

# Against Docker container
bash scripts/smoke_test.sh http://127.0.0.1:8001/mcp

# Against production (with auth): the key from an environment variable
MCP_SMOKE_KEY=<key> bash scripts/smoke_test.sh https://<host>/<path>/mcp
```
