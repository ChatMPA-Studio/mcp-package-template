# Skills Architecture

## What Skills Are

Skills are markdown-driven guided workflows that orchestrate MCP tools.  They are:
- **Agent-agnostic** — any AI assistant can follow them (Claude, ChatGPT, custom agents), because the mechanism is standard MCP, not a Claude-specific format.
- **Composable** — they reference tools by name, not by implementation.
- **Discoverable** — registered as MCP prompts, visible to remote clients.

## How Skills Work

```
1. Client requests prompts/list  -->  Server returns skill names + descriptions
2. Client requests prompts/get   -->  Server returns full skill markdown
3. Client follows the workflow   -->  Calls tools in sequence, interprets results
```

The key insight: the skill body is a **prompt** sent to the AI assistant.  The assistant reads the step-by-step instructions and calls the specified tools.

This part — the MCP server, its tools, and its prompts — is portable across any MCP-aware client. What's Claude Code-specific is purely the *distribution convenience layer* built on top of it: see `docs/tutorials/08_package_as_plugin.md` for how `.claude-plugin/` auto-installs these skills as local Claude Code commands, so a researcher doesn't need their client to support live MCP prompts at all.

## Skill File Format

Skills live in a **top-level `skills/` directory** (a sibling of `mcp_server/`, not a subpackage of it) — this keeps skill content (markdown, not Python) separate from the server implementation, and makes it directly fetchable via the GitHub Contents API (see `scripts/install_skills.sh`).

```
skills/
├── README.md
├── registry.py              # Developer catalog — not loaded at runtime
├── contracts/                # JSON Schema per skill
│   └── your_skill.schema.json
└── your-skill-name/
    ├── SKILL.md              # Main skill definition
    └── references/           # Optional — appended to the prompt body
        └── methodology.md
```

Only the nested `skills/<name>/SKILL.md` layout is supported (no flat single-file skills) — this keeps every skill's contract, references, and definition co-located under one directory.

### YAML Frontmatter

```yaml
---
name: my-workflow
description: One-line summary for the prompts/list response.
version: 1.0.0
inputs: optional description of expected inputs
outputs: optional description of expected outputs
---
```

### Body Structure

```markdown
# Workflow Title

## Purpose
What this workflow accomplishes.

## Workflow

### Step 1: Name
**Tool:** `tool_name`
**Parameters:** `{"param": "value"}`
**Interpret:** How to read the results.

### Step 2: Name
**Tool:** `another_tool`
**Parameters:** `{"param": "<output from step 1>"}`

## Success Criteria
- What constitutes a complete run.
- Expected output format.
```

## Adding a New Skill

1. Create `skills/your-skill-name/SKILL.md` with YAML frontmatter (`name`, `description`, `version`, `inputs`, `outputs`).
2. Add a contract in `skills/contracts/your_skill_name.schema.json` — the JSON Schema for the skill's inputs.
3. Register it in `skills/registry.py` (optional; keeps the catalog useful for docs/tooling — `mcp_server/prompts.py` discovers skills directly from disk and doesn't read this file).
4. Restart the server.
5. Verify: `curl ... -d '{"method":"prompts/list"}'`

No redistribution step is needed beyond that — researchers using the `.claude-plugin` get the new skill automatically on their next session.

## Design Guidelines

1. **Orchestrate, don't duplicate** — Skills call tools; they don't re-implement tool logic.
2. **Be explicit** — Name the exact tool, specify exact parameters.
3. **Provide interpretation** — Tell the assistant how to read results.
4. **Define success** — What does a "complete" run look like?
5. **Reference materials** — Put supplementary context in `references/` — the loader appends it automatically.

## Invocation Methods

| Method | Command | Requires |
|--------|---------|---------|
| MCP Prompt (live) | `/mcp__<server-name>__<skill-name>` | Server connected in client config. Support for surfacing MCP prompts as commands varies by client — verify with a raw `prompts/list` call if it doesn't appear. |
| Local install | `/<skill-name>` | `bash scripts/install_skills.sh`, or a `.claude-plugin` install (auto-syncs every session) |

## Registry

The `registry.py` module provides programmatic access to skill metadata:

```python
from skills.registry import list_skills

for skill in list_skills():
    print(f"{skill['name']}: {skill['description']}")
```

This is useful for documentation generation, admin interfaces, or manifest building. It is a developer convenience only — it is not read by `mcp_server/prompts.py` at runtime.
