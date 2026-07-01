# Tutorial 08: Package as a Claude Code Plugin

## Goal

Give researchers a one-command way to connect to your MCP server *and*
get its skills auto-installed locally — no manual `install_skills.sh`
run, no knowledge of MCP internals required.

## Background

Skills registered via `mcp_server/prompts.py` are visible to any MCP
client as prompts, agent-agnostically. But not every client surfaces
MCP prompts as ready-to-use commands, and even when they do, that's a
live network call every time — not something that survives being
bundled into a distributable package. The `.claude-plugin/` directory
in this template solves the Claude Code side of that problem:

- `.claude-plugin/plugin.json` bundles the MCP server connection
  (`mcpServers`) together with a `SessionStart` hook.
- `.claude-plugin/scripts/sync_skills.sh` is that hook's target — a
  portable (curl + python3 only, no `gh` CLI) script that pulls
  `skills/*/SKILL.md` from this repo's GitHub API and writes them to
  `~/.claude/skills/`, every session, automatically.

This is why `.claude-plugin/scripts/sync_skills.sh` duplicates
`scripts/install_skills.sh` rather than depending on it: once a
plugin is installed, only the files under `.claude-plugin/` are
guaranteed to be present on the researcher's machine — not the rest
of the repo.

## Steps

### 1. Fill in the plugin manifest

Edit `.claude-plugin/plugin.json` and replace the placeholders:

| Placeholder | Value |
|---|---|
| `{{package_name}}` | Your project's short name, e.g. `"my-fisheries-mcp"` |
| `{{version}}` | Match `pyproject.toml`'s version |
| `{{description}}` | One-line description |
| `{{MCP_SERVER_URL}}` | Your deployed server's URL, e.g. `"http://your-droplet-ip/your-mcp/"` |
| `{{MCP_AUTH_HEADER}}` | e.g. `"Basic <base64-creds>"` — whatever your Caddy/reverse-proxy auth expects |

### 2. Fill in the sync script

Edit `.claude-plugin/scripts/sync_skills.sh` and replace:

| Placeholder | Value |
|---|---|
| `{{GITHUB_ORG}}` | Your GitHub org, e.g. `"ChatMPA-Studio"` |
| `{{GITHUB_REPO}}` | This repo's name |
| `{{GITHUB_REF}}` | A pinned tag (e.g. `"v1.2.0"`) for reproducible installs, or `"main"`/`"master"` to always track latest |

Make it executable:

```bash
chmod +x .claude-plugin/scripts/sync_skills.sh
```

### 3. Test locally

From a Claude Code session, install the plugin from a local path to verify it works before publishing:

```bash
claude plugin install /path/to/your-mcp-repo
```

Start a new session and confirm:
- The MCP server shows up connected (`claude mcp list`)
- `~/.claude/skills/` now contains your skill directories
- The sync script's one-line summary appears in session start output

### 4. Register in a marketplace

A plugin needs a marketplace to be installable by name (rather than by
local path or full git URL every time). If your organization has a
shared marketplace repo, add an entry to its `marketplace.json`:

```json
{
  "name": "your-mcp-repo",
  "source": {
    "source": "github",
    "repo": "your-org/your-mcp-repo",
    "ref": "v1.2.0"
  },
  "version": "1.2.0"
}
```

Researchers then install with:

```bash
claude plugin marketplace add your-org/your-marketplace
claude plugin install your-mcp-repo@your-marketplace
```

Both commands work non-interactively, so they can be scripted into a
larger onboarding/installer flow rather than requiring a researcher to
run them by hand.

### 5. Keep it updated

Every new skill added to `skills/` becomes available to already-onboarded
researchers automatically on their next session — no redistribution
needed, as long as `GITHUB_REF` in `sync_skills.sh` tracks a branch
rather than a fixed tag. If you pin to a tag for reproducibility,
bumping that tag (and re-tagging the marketplace entry) is the only
step required to ship new skills to everyone.

## Next Steps

- [Tutorial 07: Release Versioning](07_release_versioning.md) — for how to tag releases the plugin/marketplace can pin to.
