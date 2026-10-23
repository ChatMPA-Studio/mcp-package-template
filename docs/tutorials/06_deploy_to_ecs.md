# Tutorial 06: Deploy to Amazon ECS

> The default deployment: stateless replicas on Amazon ECS behind a load
> balancer, with per-key auth in the server itself (`.github/workflows/deploy-ecs.yml`).
> For a single server with Docker Compose, deployed over SSH, see
> [Deploy with Caddy Subpath Routing](06_deploy_with_caddy_subpath.md) and
> `.github/workflows/deploy-ssh.yml`.

## Goal

Deploy your MCP so that every push to the `release` branch builds a new image
and rolls it out to an ECS service.

## Prerequisites

- The image builds and runs locally ([Tutorial 05](05_dockerize_and_run.md)).
- From the platform's operators (infrastructure lives outside this repo, usually Terraform):
  - an ECR repository, an ECS cluster, and a service plus an ACTIVE task definition family both named after your server (e.g. `mcp-<source>`), with a container of the same name;
  - a load balancer route to `MCP_BASE_PATH` on that service;
  - an IAM role GitHub can assume via OIDC for this repository;
  - the auth key table and a scope for your server.

## Steps

### 1. Set the repository variables

Settings → Secrets and variables → Actions → **Variables** (not secrets — none of these is a credential):

| Variable | Example shape |
|---|---|
| `AWS_REGION` | `us-west-2` |
| `AWS_ROLE_ARN` | `arn:aws:iam::<ACCOUNT_ID>:role/<ROLE>` |
| `ECR_REPOSITORY` | `<env>-app-repo` |
| `ECS_CLUSTER` | `<env>-ecs-cluster` |
| `ECS_SERVICE` | `mcp-<source>` |

Put the real values only in GitHub's settings, never in a file of the repository.
While `AWS_ROLE_ARN` is empty, the workflow is skipped.

### 2. Configure the task definition

With the operators, set the container's environment from `.env.example` for your source:

- `MCP_DATA_SOURCE`, and its section (`MCP_DB_*` or `MCP_API_*`);
- `AUTH_ENABLED=true`, `AUTH_DYNAMODB_TABLE`, `AUTH_AWS_REGION`, `AUTH_REQUIRED_SCOPE`;
- secrets (`MCP_DB_PASSWORD`, `MCP_API_KEY`) as references to AWS Secrets Manager or SSM Parameter Store, not plain values.

The task role (not keys in the environment) gives the container read access to the key table.

### 3. Create the release branch

```bash
git switch -c release main
git push -u origin release        # first deployment
```

From now on, `main` receives your work and `release` receives `main` (see [deployment_workflow.md](../deployment_workflow.md)).

### 4. Watch it deploy

Repository → *Actions* → *Deploy MCP to Amazon ECS*: build → push to ECR → new task definition revision → service update → wait for stability.

### 5. Verify

```bash
MCP_SMOKE_KEY=<key with your scope> bash scripts/smoke_test.sh https://<host>/<path>/mcp
```

`health_check` must report `"status": "ok"` for your data source.

## Connecting an AI Client

Claude Code (`.mcp.json` in a project folder; the key comes from an environment variable, never written in the file):

```json
{
  "my-source-mcp": {
    "type": "http",
    "url": "https://<host>/<path>/mcp",
    "headers": { "Authorization": "${MY_SOURCE_MCP_AUTH_HEADER}" }
  }
}
```

with `MY_SOURCE_MCP_AUTH_HEADER="Bearer <key>"` in the environment.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Workflow skipped | `AWS_ROLE_ARN` variable not set |
| `describe-task-definition` fails | No ACTIVE task definition with family `ECS_SERVICE` yet (infrastructure step) |
| Service never stable, tasks stop at once | Missing environment variable: the container log shows `FATAL: configuration incomplete` and which |
| 401 for every request | Key unknown, revoked, or without your server's scope (`auth_rejected` in the logs says which) |
| Sporadic 502 | Load balancer idle timeout longer than uvicorn's keep-alive (template uses 65 s) |

## Next Steps

- [Tutorial 07: Release Versioning](07_release_versioning.md)
