# Deployment Workflow

How a change travels from a working branch to the deployed server. Setup of the
infrastructure and the repository variables: [DEPLOYMENT.md](../DEPLOYMENT.md).
The branches are the same for both deployment methods: Amazon ECS (default) or a
single server over SSH (`DEPLOY_TARGET=ssh`); only the workflow that runs on a
push to `release` changes.

## Branches

| Branch | Role |
|---|---|
| `<you>/<topic>` | Your work. Commit freely; never deploy from it. |
| `main` | Integration. Receives working branches by pull request, after review. |
| `release` | What is deployed. Receives `main` by pull request (or fast-forward). A push here deploys. |

## Pre-Deployment Checklist

- [ ] `pytest` passes locally (no database, API or AWS needed).
- [ ] New tools: docstrings say what they return, at what level, units and columns; parameters use the standard names; responses report truncation.
- [ ] B (API): every parameter validated with `params.*`; provenance in `meta`.
- [ ] No secrets or real infrastructure identifiers in the diff (`git diff main...HEAD` and search for keys, passwords, hosts, account IDs, ARNs).
- [ ] Version bumped (`pyproject.toml`, `metadata/template.json`) if tools, parameters or outputs changed.
- [ ] The platform's operators know the change is coming (they redeploy and may need to update the client's tool list).

## Step-by-Step

### 1. Merge into `main`

Open a pull request from your branch to `main`; get it reviewed; merge.

### 2. Promote to `release`

```bash
git fetch origin
git switch release && git pull --ff-only
git merge --ff-only origin/main     # or open a PR main -> release
git push origin release             # starts .github/workflows/deploy-ecs.yml
```

### 3. Watch the deployment

In the repository's *Actions* tab, the *Deploy MCP to Amazon ECS* run builds the image, registers a new task definition revision and waits until the service is stable. If the run is *skipped*, `AWS_ROLE_ARN` is not set in the repository variables.

### 4. Verify

```bash
MCP_SMOKE_KEY=<a key with this server's scope> bash scripts/smoke_test.sh https://<host>/<path>/mcp
```

- `health_check` → `"status": "ok"` for the data source.
- `tools/list` includes the new or changed tools.
- The service logs show one `tool=… status=ok` line per call.

## Rollback

```bash
git switch release
git revert <bad-commit>        # keeps history; redeploys the previous code
git push origin release
```

Faster, without a build: point the ECS service at the previous task definition revision.

## Monitoring

- **Per-call log line** (`mcp_server.timing`): `tool`, `status`, `total_ms`, `source_ms`, `calls`, `rows`, `bytes`.
- **Auth rejections**: `auth_rejected` with `key_not_found`, `key_revoked` or `missing_scope`.
- **Source health**: the `health_check` tool.
- **Container health**: `healthcheck.py` (port accepting connections).
