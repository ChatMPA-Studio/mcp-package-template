# Tutorial 07: Release Versioning

## Goal

Establish a versioning and release process for your MCP server.

## Versioning Strategy

Follow [Semantic Versioning](https://semver.org/) (SemVer):

```
MAJOR.MINOR.PATCH
  |     |     |
  |     |     +-- Bug fixes, documentation updates
  |     +-------- New tools, skills, or resources (backward-compatible)
  +-------------- Breaking changes to tool signatures or config format
```

### What Counts as a Breaking Change?

- Removing a tool or changing its name
- Changing a tool's parameter names or types
- Removing a resource URI
- Changing `.env` variable names
- Changing the metadata manifest structure

### What Is Backward-Compatible?

- Adding new tools or skills
- Adding optional parameters to existing tools
- Adding new resources
- Fixing bugs in tool logic
- Documentation updates

## Release Process

### 1. Prepare the Release

```bash
# 1. Update version numbers
# pyproject.toml:
#   version = "1.2.0"
#
# metadata/template.json:
#   "package": { "version": "1.2.0" }

# 2. Regenerate manifest
bash scripts/generate_manifest.sh

# 3. Run all tests
bash scripts/smoke_test.sh

# 4. Validate line endings
bash scripts/validate_line_endings.sh
```

### 2. Commit and Tag

```bash
git add -A
git commit -m "Release v1.2.0: add weather analysis tools"

# Create annotated tag
git tag -a v1.2.0 -m "Release v1.2.0

Changes:
- Added temperature trend analysis tool
- Added precipitation summary tool
- Fixed calculator division by zero handling
"

# Push
git push origin main
git push origin v1.2.0
```

### 3. Deploy

```bash
ssh root@your-server
cd /opt/mcps/my-mcp/repo
git pull origin main
docker compose down
docker compose up --build -d
bash scripts/smoke_test.sh http://localhost:8001/mcp
```

### 4. Verify

```bash
# Check the version via metadata resource
curl -u user:pass https://your-domain.com/weather/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"resources/read","params":{"uri":"mcp://metadata/package"}}' \
  | python -m json.tool | grep version
```

## Version Checklist

Before every release:

- [ ] `pyproject.toml` version updated
- [ ] `metadata/template.json` version updated
- [ ] `manifest.json` regenerated
- [ ] Smoke tests pass locally
- [ ] Line endings validated
- [ ] Git commit with descriptive message
- [ ] Git tag created (annotated)
- [ ] Deployed to production
- [ ] Production smoke tests pass

## Changelog

Maintain a `CHANGELOG.md` (optional but recommended):

```markdown
# Changelog

## [1.2.0] - 2026-03-15
### Added
- Temperature trend analysis tool
- Precipitation summary tool

### Fixed
- Calculator division by zero returns Infinity instead of error

## [1.1.0] - 2026-02-01
### Added
- Weather report skill
- Station metadata resource

## [1.0.0] - 2026-01-15
### Initial Release
- Core tools: echo, server_time, calculator
- Statistics tools: descriptive_stats, percentile, correlation
- Docker deployment with Caddy reverse proxy
```
