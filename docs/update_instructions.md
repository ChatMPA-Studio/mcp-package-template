# Update Instructions

## Updating Your MCP Server

### Minor Updates (Bug Fixes, New Tools)

```bash
cd /opt/mcps/my-mcp/repo

# Pull changes
git pull origin main

# Rebuild and restart
docker compose down
docker compose up --build -d

# Verify
bash scripts/smoke_test.sh http://localhost:8001/mcp
```

### Major Updates (Breaking Changes)

1. Read the changelog for breaking changes.
2. Back up `.env` and any custom files.
3. Pull and rebuild:
   ```bash
   git pull origin main
   docker compose down
   docker compose up --build -d
   ```
4. Run full smoke tests.
5. Test client connections.

## Updating from Template

If the upstream template has improvements you want:

```bash
# Add template as a remote (one-time)
git remote add template https://github.com/your-org/mcp-package-template.git

# Fetch template updates
git fetch template

# Merge selectively (review changes carefully)
git merge template/main --no-commit --allow-unrelated-histories

# Resolve conflicts — keep your domain-specific changes
git checkout --ours mcp_server/tools/    # keep your tools
git checkout --theirs mcp_server/config/ # take template config updates

# Review and commit
git diff --staged
git commit -m "Merge template updates"
```

## Updating Dependencies

### Python Dependencies

1. Edit `pyproject.toml` with new versions.
2. Rebuild: `docker compose up --build -d`
3. Test: `bash scripts/smoke_test.sh`

### Docker Base Image

1. Edit `Dockerfile` — change `python:3.12-slim` to desired version.
2. Rebuild: `docker compose up --build --no-cache -d`

### Caddy

```bash
apt update && apt upgrade caddy
systemctl reload caddy
```

## Version Tagging

Follow Semantic Versioning:

```bash
# Update version in pyproject.toml and metadata/template.json first
# Then tag:
git tag -a v1.2.0 -m "Release v1.2.0: add new analysis tools"
git push origin v1.2.0
```

### Version Checklist

When releasing a new version:

- [ ] Update `pyproject.toml` → `version`
- [ ] Update `metadata/template.json` → `package.version`
- [ ] Regenerate manifest: `bash scripts/generate_manifest.sh`
- [ ] Run smoke tests locally
- [ ] Commit all changes
- [ ] Create git tag
- [ ] Deploy to production
- [ ] Run smoke tests against production
