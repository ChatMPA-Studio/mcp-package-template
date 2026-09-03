#!/usr/bin/env bash
# =============================================================================
# sync_skills.sh — SessionStart hook: re-sync this MCP's skills every session.
#
# Runs on a researcher's machine (not this repo's dev environment), so it uses
# only curl + python3 — no `gh` CLI, no git clone.  It fetches every skill
# directory (SKILL.md + references/) from GitHub and installs it under
# ~/.claude/skills so Claude Code picks them up automatically.
#
# CUSTOMIZE the three GITHUB_* values below when you author your plugin, plus
# SKILLS_REPO_PATH if your SKILL.md directories don't live at repo-root skills/.
# This layout expects:  <SKILLS_REPO_PATH>/<skill-name>/SKILL.md
#
# Runs silently on success; prints a one-line summary either way so it's
# visible in SessionStart hook logs without being noisy.
# =============================================================================

set -euo pipefail

GITHUB_ORG="ChatMPA-Studio"
GITHUB_REPO="CHANGEME"       # <-- your MCP repo name
GITHUB_REF="main"
SKILLS_REPO_PATH="skills"    # <-- path in the repo that holds <skill>/SKILL.md

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

_list_dirs() {
    _curl "$1" | python3 -c 'import json,sys; [print(e["name"]) for e in json.load(sys.stdin) if e.get("type") == "dir"]'
}

_fetch_file() {
    _curl "$1" | python3 -c 'import json,sys,base64; d=json.load(sys.stdin); sys.stdout.buffer.write(base64.b64decode(d["content"]))' > "$2"
}

_is_skipped() {
    local needle="$1"
    for d in "${SKIP_DIRS[@]}"; do
        [[ "$d" == "$needle" ]] && return 0
    done
    return 1
}

mkdir -p "${SKILLS_DIR}"
synced=0

skill_names="$(_list_dirs "${API}/${SKILLS_REPO_PATH}?ref=${GITHUB_REF}" 2>/dev/null || true)"
if [[ -z "$skill_names" ]]; then
    echo "[${GITHUB_REPO}] skill sync skipped (server unreachable or ${SKILLS_REPO_PATH}/ not found)"
    exit 0
fi

while read -r skill; do
    [[ -z "$skill" ]] && continue
    _is_skipped "$skill" && continue
    mkdir -p "${SKILLS_DIR}/${skill}"
    _fetch_file "${API}/${SKILLS_REPO_PATH}/${skill}/SKILL.md?ref=${GITHUB_REF}" "${SKILLS_DIR}/${skill}/SKILL.md" || continue

    ref_names="$(_list_names "${API}/${SKILLS_REPO_PATH}/${skill}/references?ref=${GITHUB_REF}" 2>/dev/null || true)"
    if [[ -n "$ref_names" ]]; then
        mkdir -p "${SKILLS_DIR}/${skill}/references"
        while read -r ref; do
            [[ -z "$ref" ]] && continue
            _fetch_file "${API}/${SKILLS_REPO_PATH}/${skill}/references/${ref}?ref=${GITHUB_REF}" "${SKILLS_DIR}/${skill}/references/${ref}"
        done <<< "$ref_names"
    fi
    synced=$((synced + 1))
done <<< "$skill_names"

echo "[${GITHUB_REPO}] synced ${synced} skill(s) to ${SKILLS_DIR}"
