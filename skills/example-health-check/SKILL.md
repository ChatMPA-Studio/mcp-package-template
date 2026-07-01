---
name: example-health-check
description: Verify MCP server health by calling basic tools and validating responses.
version: 1.0.0
inputs: none
outputs: structured JSON health report
---

# Health Check Skill

## Purpose

Verify MCP server health by calling basic tools and checking responses.

**Use cases:**
- Server startup validation
- Deployment verification
- Automated monitoring
- Smoke testing

## Workflow

### Step 1: Echo Test

**Tool:** `echo`
**Parameters:** `{"message": "health-check"}`
**Expected:** Returns the message with a timestamp.

### Step 2: Server Time

**Tool:** `server_time`
**Parameters:** None
**Expected:** Returns current UTC time and unix timestamp.

### Step 3: Calculator Smoke Test

**Tool:** `calculator`
**Parameters:** `{"operation": "add", "a": 2, "b": 3}`
**Expected:** Returns `{"result": 5.0}`

## Success Criteria

- All tools return valid JSON
- No exceptions raised
- Response time < 5 seconds total
- Echo returns the same message sent

## Output

```json
{
  "status": "healthy",
  "checks": {
    "echo": {"status": "pass"},
    "server_time": {"status": "pass"},
    "calculator": {"status": "pass"}
  }
}
```
