# Deployment Guide

## Deployment Options

| Option | Use it for | How |
|---|---|---|
| Local, no Docker | Development | `python -m mcp_server` with a `.env` |
| Local, Docker Compose | Checking the image before deploying | `docker compose up --build -d` (port bound to `127.0.0.1` only) |
| **Amazon ECS (production, default)** | Serving a platform | Push to `release` → `.github/workflows/deploy-ecs.yml` |
| Single server over SSH (alternative) | One server with Docker Compose behind Caddy | Repository variable `DEPLOY_TARGET=ssh`; push to `release` → `.github/workflows/deploy-ssh.yml` → `scripts/deploy.sh` |

The container image is the same in every case: `python -m mcp_server` behind uvicorn, listening on `PORT` (default 8000) at `MCP_BASE_PATH` (default `/mcp`), stateless, so any number of replicas can run behind a load balancer.

## Local with Docker Compose

```bash
cp .env.example .env          # choose MCP_DATA_SOURCE and fill in its section
docker compose up --build -d
docker compose ps             # wait for "healthy"
docker compose logs -f
bash scripts/smoke_test.sh http://127.0.0.1:8001/mcp
docker compose down
```

If `.env` is incomplete the container stops at once, and `docker compose logs` shows which variables are missing (`check_required()`).

## Production on Amazon ECS

### How it works

```
git push origin release
   └─ GitHub Actions: deploy-ecs.yml
        1. assumes the IAM role in AWS_ROLE_ARN (OIDC, no stored AWS keys)
        2. builds the image and pushes it to ECR as <ECR_REPOSITORY>:<ECS_SERVICE>
        3. reads the ACTIVE task definition of family <ECS_SERVICE>
        4. registers a new revision with the new image
        5. updates the ECS service and waits until it is stable
```

### One-time setup (with the platform's operators)

1. **Infrastructure** (usually Terraform, in an infrastructure repository — not here): ECR repository, ECS cluster, a service named `<ECS_SERVICE>` with an ACTIVE task definition of the same family and a container of the same name (it can start with `desired_count: 0`), a load balancer target group pointing at `MCP_BASE_PATH`, and an IAM role that trusts this repository through GitHub OIDC.
2. **Runtime configuration in the task definition**: the variables of `.env.example` for the chosen source. Secrets (`MCP_DB_PASSWORD`, `MCP_API_KEY`) come from AWS Secrets Manager or SSM Parameter Store, never as plain values in the repository. AWS access for auth (DynamoDB) comes from the task role.
3. **Repository variables** (Settings → Secrets and variables → Actions → *Variables*): `AWS_REGION`, `AWS_ROLE_ARN`, `ECR_REPOSITORY`, `ECS_CLUSTER`, `ECS_SERVICE`. Until `AWS_ROLE_ARN` is set, the workflow skips the deployment.
4. **Auth**: `AUTH_ENABLED=true`, `AUTH_DYNAMODB_TABLE`, `AUTH_AWS_REGION` and `AUTH_REQUIRED_SCOPE` (this server's scope) in the task definition. Keys are issued by the platform's admin; this server only reads their hashes.
5. **Branches**: `main` (integration) and `release` (what is deployed). Only merge into `release` by pull request.

### Deploying a change

```bash
# change reviewed and merged into main
git switch release && git pull
git merge --ff-only main      # or open a PR main -> release
git push origin release       # starts the deployment
```

Follow it in the repository's *Actions* tab. Then check the deployed server: `health_check` must answer `"status": "ok"` and the tools list must include the new tools.

### Rollback

Revert on `release` and push: the workflow deploys the previous code as a new revision.

```bash
git switch release
git revert <bad-commit>
git push origin release
```

For an immediate rollback without a build, update the ECS service to the previous task definition revision (console or `aws ecs update-service --task-definition <family>:<revision>`).

## Alternative: single server over SSH

For an MCP that runs on one server with Docker Compose instead of ECS. Only one method deploys: with the repository variable `DEPLOY_TARGET=ssh`, `deploy-ecs.yml` is skipped and `deploy-ssh.yml` runs on every push to `release`.

1. On the server: clone the repository, create `.env` (never in git) and run `docker compose up --build -d` once.
2. Repository secrets: `DEPLOY_HOST`, `DEPLOY_SSH_KEY`, `DEPLOY_PATH` (the clone's absolute path). Repository variable: `DEPLOY_TARGET=ssh`.
3. A push to `release` runs `scripts/deploy.sh` on the server: backup, pull, rebuild, wait for the health check. It reads `CONTAINER_NAME` (default `my-mcp`), which must match `COMPOSE_PROJECT_NAME`.
4. Route a public path to the container with Caddy: [docs/tutorials/06_deploy_with_caddy_subpath.md](docs/tutorials/06_deploy_with_caddy_subpath.md) and `Caddyfile.snippet`.

Rollback: revert on `release` and push, as above.

## Monitoring

- **Logs** (CloudWatch, or `docker compose logs` locally). One line per tool call from `mcp_server.timing`:
  `tool=<name> status=ok total_ms=… source_ms=… calls=… rows=… bytes=…`.
  A large `total_ms` with a small `source_ms` is time in Python or serialization; a large `bytes` is time on the wire.
- **`health_check` tool** — active source, reachability, and what is missing from the configuration.
- **Container health check** — `healthcheck.py` checks that the port accepts connections.
- Rejected keys are logged as `auth_rejected` with the reason (`key_not_found`, `key_revoked`, `missing_scope`).

## Security Checklist

- [ ] `.env` is not committed (it is in `.gitignore`); no keys, passwords, hosts, account IDs, ARNs or real table names anywhere in the repository.
- [ ] A: the database user is read-only; `ALLOWED_TABLES` lists only what the tools need.
- [ ] B: the API key, if any, is a secret in the task definition; it never appears in logs or responses.
- [ ] `AUTH_ENABLED=true` in every deployed environment.
- [ ] TLS terminates at the load balancer; the container is not reachable directly from the internet.
- [ ] The container runs as the non-root `mcp` user (Dockerfile).
