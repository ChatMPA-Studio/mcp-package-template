# Skills Directory

Analytical skills for this MCP server. Each skill is a guided workflow
that orchestrates MCP tools to answer specific research questions about
your domain.

This layout, and the auto-discovery mechanism behind it
(`mcp_server/prompts.py`), was carried over from
[conapesca-db-mcp](https://github.com/ChatMPA-Studio/conapesca-db-mcp)
after it proved itself in production — see `docs/skills_architecture.md`
for the full design rationale.

## Structure

```
skills/
├── README.md
├── registry.py                              # Developer catalog (not loaded at runtime)
├── contracts/                               # JSON Schema per skill
│   ├── example_health_check.schema.json
│   ├── data_exploration.schema.json
│   └── statistical_analysis.schema.json
├── example-health-check/
│   └── SKILL.md
├── data-exploration/
│   └── SKILL.md
└── statistical-analysis/
    └── SKILL.md
```

## Invocation

Skills are auto-registered as MCP prompts at server startup
(`mcp_server/prompts.py` scans `skills/*/SKILL.md`). There are two ways
a researcher can use them, and neither requires knowing how the server
is built:

| Method | Command | Requires |
|--------|---------|---------|
| MCP Prompt (live) | `/mcp__<server-name>__<skill-name>` | Server connected in Claude Code config. Availability depends on client support — verify with a raw `prompts/list` call if it doesn't show up. |
| Local install | `/<skill-name>` | `bash scripts/install_skills.sh`, or the bundled `.claude-plugin` (auto-syncs every session — see `docs/tutorials/08_package_as_plugin.md`) |

## Adding a New Skill

1. Create `skills/your-skill-name/SKILL.md` with YAML frontmatter (`name`, `description`, `version`, `inputs`, `outputs`).
2. Add a contract in `skills/contracts/your_skill_name.schema.json`.
3. Register it in `skills/registry.py` (optional, but keeps the catalog useful for docs/tooling).
4. Restart the server — it appears automatically as an MCP prompt.
5. No redistribution step needed for researchers using the `.claude-plugin` — the `SessionStart` hook re-syncs on their next session automatically.
