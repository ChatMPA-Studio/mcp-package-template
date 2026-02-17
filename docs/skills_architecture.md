# Skills Architecture

## What Skills Are

Skills are markdown-driven guided workflows that orchestrate MCP tools.  They are:
- **Agent-agnostic** — any AI assistant can follow them (Claude, ChatGPT, custom agents).
- **Composable** — they reference tools by name, not by implementation.
- **Discoverable** — registered as MCP prompts, visible to remote clients.

## How Skills Work

```
1. Client requests prompts/list  -->  Server returns skill names + descriptions
2. Client requests prompts/get   -->  Server returns full skill markdown
3. Client follows the workflow   -->  Calls tools in sequence, interprets results
```

The key insight: the skill body is a **prompt** sent to the AI assistant.  The assistant reads the step-by-step instructions and calls the specified tools.

## Skill File Format

### Flat Layout

```
mcp_server/skills/
    my_workflow.md
    another_workflow.md
```

### Nested Layout (with references)

```
mcp_server/skills/
    my_workflow/
        SKILL.md              # Main skill definition
        references/
            methodology.md    # Appended to the prompt body
            taxonomy.md       # Appended to the prompt body
```

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

1. Create the markdown file in `mcp_server/skills/`.
2. Add YAML frontmatter with `name` and `description`.
3. Write step-by-step instructions referencing existing tools.
4. Restart the server.
5. Verify: `curl ... -d '{"method":"prompts/list"}'`

## Design Guidelines

1. **Orchestrate, don't duplicate** — Skills call tools; they don't re-implement tool logic.
2. **Be explicit** — Name the exact tool, specify exact parameters.
3. **Provide interpretation** — Tell the assistant how to read results.
4. **Define success** — What does a "complete" run look like?
5. **Reference materials** — Put supplementary context in `references/` — the loader appends it automatically.

## Registry

The `registry.py` module provides programmatic access to skill metadata:

```python
from mcp_server.skills.registry import list_skills

for skill in list_skills():
    print(f"{skill['name']}: {skill['description']}")
```

This is useful for documentation generation, admin interfaces, or manifest building.
