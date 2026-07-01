#!/usr/bin/env bash
# =============================================================================
# install_skills.sh — Install this MCP's skills into ~/.claude/skills/
#
# Portable: only requires `curl` + `python3` (no `gh` CLI dependency).
#
# Usage:
#   bash scripts/install_skills.sh            # install
#   bash scripts/install_skills.sh --uninstall
#
# Env overrides (useful for forks/private mirrors without editing this file):
#   GITHUB_ORG, GITHUB_REPO, GITHUB_REF, GH_TOKEN (needed only for private repos)
#
# After installation, skills are available as /<skill-name>.
# Without installation, skills are available via MCP as
#   /mcp__<server-name>__<skill-name>   (if your client surfaces MCP prompts —
#   verify with a raw prompts/list call if the command doesn't appear)
# =============================================================================

set -euo pipefail

# CUSTOMIZE: set these three for your project (or override via env vars above).
GITHUB_ORG="${GITHUB_ORG:-your-org}"
GITHUB_REPO="${GITHUB_REPO:-your-mcp-repo}"
GITHUB_REF="${GITHUB_REF:-main}"

SKILLS_DIR="${HOME}/.claude/skills"
SKIP_DIRS=("contracts" "example-workflow")
API="https://api.github.com/repos/${GITHUB_ORG}/${GITHUB_REPO}/contents"

_curl() {
    if [[ -n "${GH_TOKEN:-}" ]]; then
        curl -sf -H "Authorization: token ${GH_TOKEN}" "$@"
    else
        curl -sf "$@"
    fi
}

_list_names() {
    _curl "$1" | python3 -c 'import json,sys; [print(e["name"]) for e in json.load(sys.stdin)]'
}

_fetch_file() {
    # $1 = API contents URL for a file, $2 = local destination path
    _curl "$1" | python3 -c 'import json,sys,base64; d=json.load(sys.stdin); sys.stdout.buffer.write(base64.b64decode(d["content"]))' > "$2"
}

_is_skipped() {
    local needle="$1"
    for d in "${SKIP_DIRS[@]}"; do
        [[ "$d" == "$needle" ]] && return 0
    done
    return 1
}

uninstall=false
[[ "${1:-}" == "--uninstall" ]] && uninstall=true

if $uninstall; then
    echo "Uninstalling ${GITHUB_REPO} skills..."
    _list_names "${API}/skills?ref=${GITHUB_REF}" | while read -r skill; do
        _is_skipped "$skill" && continue
        rm -rf "${SKILLS_DIR}/${skill}"
        echo "Removed: ${skill}"
    done
    exit 0
fi

echo "Installing ${GITHUB_REPO} skills to ${SKILLS_DIR}..."
mkdir -p "${SKILLS_DIR}"

_list_names "${API}/skills?ref=${GITHUB_REF}" | while read -r skill; do
    _is_skipped "$skill" && continue
    mkdir -p "${SKILLS_DIR}/${skill}"

    _fetch_file "${API}/skills/${skill}/SKILL.md?ref=${GITHUB_REF}" "${SKILLS_DIR}/${skill}/SKILL.md"

    ref_names="$(_list_names "${API}/skills/${skill}/references?ref=${GITHUB_REF}" 2>/dev/null || true)"
    if [[ -n "$ref_names" ]]; then
        mkdir -p "${SKILLS_DIR}/${skill}/references"
        while read -r ref; do
            [[ -z "$ref" ]] && continue
            _fetch_file "${API}/skills/${skill}/references/${ref}?ref=${GITHUB_REF}" "${SKILLS_DIR}/${skill}/references/${ref}"
        done <<< "$ref_names"
    fi

    echo "Installed: ${skill}"
done

echo "Done. Restart Claude Code to load new skills."
echo "Skills are now available as /<skill-name>"
