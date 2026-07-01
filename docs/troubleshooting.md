# Troubleshooting

## Common Pitfalls

### 1. Windows CRLF Line Endings Breaking Shell Scripts on Linux

**Symptom:** Shell scripts fail with `/bin/bash^M: bad interpreter` or `'\r': command not found`.

**Cause:** Windows uses `\r\n` line endings; Linux expects `\n` only.  Git on Windows may auto-convert files to CRLF.

**Fix:**
```bash
# Fix a single file
sed -i 's/\r$//' scripts/dev_run.sh

# Fix all shell scripts
find . -name "*.sh" -exec sed -i 's/\r$//' {} +

# Prevent future issues — configure git
git config core.autocrlf input
```

**Detection:**
```bash
bash scripts/validate_line_endings.sh
```

### 2. Multi-Stage Docker Builds and Transitive Dependencies

**Symptom:** Container crashes at startup with `ModuleNotFoundError: No module named 'packaging'` (or another transitive dependency).

**Cause:** In multi-stage Docker builds, `pip install --prefix=/install .` skips dependencies that already exist in the builder environment.  The runtime stage doesn't have those pre-installed packages.

**Fix:** Use `--force-reinstall` in the builder stage:
```dockerfile
RUN pip install --no-cache-dir --force-reinstall --prefix=/install .
```

This ensures all dependencies (including transitive ones) are installed into the prefix directory and copied to the runtime stage.

### 3. PowerShell vs Bash Environment Variable Syntax

**Symptom:** Environment variables don't expand correctly when running commands from PowerShell.

**Cause:** PowerShell uses `$env:VAR` syntax, not `$VAR`.  Shell scripts using `$VAR` don't work in PowerShell.

**Fix:** Use the correct syntax for your shell:

| Shell | Syntax |
|-------|--------|
| Bash/Zsh | `$VAR` or `${VAR}` |
| PowerShell | `$env:VAR` |
| CMD | `%VAR%` |

**Best practice:** Use `.env` files instead of inline env vars.  Docker Compose reads `.env` automatically.

### 4. Container Starts but Health Check Fails

**Symptom:** `docker inspect` shows `unhealthy` status.

**Diagnosis:**
```bash
# Check container logs
docker compose logs --tail=50

# Test connectivity manually
docker exec my-mcp python healthcheck.py

# Check if the port is listening
docker exec my-mcp python -c "
import socket
s = socket.create_connection(('localhost', 8000), timeout=3)
s.close()
print('OK')
"
```

**Common causes:**
- Database credentials wrong in `.env`
- Database server unreachable from container
- Port conflict (another service on same port)
- Missing environment variables

### 5. Database Connection Refused

**Symptom:** `Can't connect to MySQL server` or `Connection refused`.

**Diagnosis:**
```bash
# From inside the container
docker exec my-mcp python -c "
from mcp_server.db import test_connection
print(test_connection())
"

# Check DNS resolution
docker exec my-mcp python -c "
import socket
print(socket.gethostbyname('your-db-host'))
"
```

**Common causes:**
- Database host not reachable from Docker network
- Firewall blocking outbound connections
- Wrong port number
- Database user not granted access from container IP

### 6. Caddy Returns 502 Bad Gateway

**Symptom:** Browser or curl shows `502 Bad Gateway`.

**Diagnosis:**
```bash
# Is the container running?
docker ps | grep my-mcp

# Can you reach it locally?
curl http://localhost:8001/mcp

# Check Caddy logs
journalctl -u caddy --tail=20
```

**Common causes:**
- Container not running
- `HOST_PORT` in `.env` doesn't match Caddy's `reverse_proxy` port
- Container bound to wrong interface

### 7. Tools Not Auto-Discovered

**Symptom:** New tool module not appearing in `tools/list`.

**Diagnosis:**
```bash
# Check server logs for discovery errors
docker compose logs | grep -i "tools"
```

**Common causes:**
- Module missing `register(mcp)` function
- Import error in the module (check for typos, missing dependencies)
- Module name starts with `_` (skipped by convention)
- Module name is `discovery` (reserved)

### 8. Skills Not Appearing as Prompts

**Symptom:** Skill not in `prompts/list` response.

**Diagnosis:**
```bash
docker compose logs | grep -i "skill\|prompt"
```

**Common causes:**
- Missing YAML frontmatter (`---` delimiters)
- File not at `skills/<name>/SKILL.md` (top-level `skills/`, nested layout only)
- Invalid YAML syntax in frontmatter
- File extension not `.md`

## Debug Mode

Run with verbose logging:

```bash
# In .env
LOG_LEVEL=DEBUG

# Restart
docker compose restart

# Watch detailed logs
docker compose logs -f
```

## Getting Help

1. Check this troubleshooting guide
2. Review container logs: `docker compose logs --tail=100`
3. Run smoke tests: `bash scripts/smoke_test.sh`
4. Run line ending validator: `bash scripts/validate_line_endings.sh`
