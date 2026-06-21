#!/usr/bin/env bash
set -euo pipefail

# Conservative stale-instruction audit for AgentOS Core/Personal Overlay routing.
# The audit is read-only. It reports suspicious path or instruction references
# and exits nonzero when findings are present.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOME_DIR="$(python3 -c 'import os; print(os.path.expanduser(chr(126)))')"

SCOPES=(
  "$ROOT/os"
  "$ROOT/personal/os"
  "$HOME_DIR/.agents/skills"
  "$HOME_DIR/.codex/automations"
)

existing_scopes=()
for scope in "${SCOPES[@]}"; do
  if [ -e "$scope" ]; then
    existing_scopes+=("$scope")
  fi
done

if [ "${#existing_scopes[@]}" -eq 0 ]; then
  echo "No audit scopes exist."
  exit 0
fi

findings=0

report_matches() {
  local category="$1"
  local pattern="$2"
  shift 2
  local tmp
  tmp="$(mktemp)"

  if rg -n --hidden --glob '!**/.git/**' --glob '!**/.DS_Store' -e "$pattern" "$@" >"$tmp"; then
    while IFS= read -r line; do
      if [[ "$line" == *"scripts/agent-push"* ]]; then
        continue
      fi
      printf '%s: %s\n' "$category" "$line"
      findings=$((findings + 1))
    done <"$tmp"
  fi

  rm -f "$tmp"
}

report_path_matches() {
  local category="$1"
  local pattern="$2"
  local scope="$3"
  local tmp
  tmp="$(mktemp)"

  find "$scope" -path '*/.git' -prune -o -print >"$tmp"
  while IFS= read -r path; do
    if [[ "$path" =~ $pattern ]]; then
      printf '%s: %s\n' "$category" "$path"
      findings=$((findings + 1))
    fi
  done <"$tmp"

  rm -f "$tmp"
}

# Core should not contain live generated-output, history, queue, or report paths.
report_path_matches \
  "core-generated-output-path" \
  '(^|/)(reports?|briefs?|histories|run-logs|outputs?|queues?)(/|$)|(^|/)(BRIEF_HISTORY|HISTORY|RUN_HISTORY|QUEUE)\.(md|html|json|jsonl|txt)$' \
  "$ROOT/os"

# Personal Overlay is allowed to contain live state, but references that route it
# back into Core are stale and should be reviewed.
report_matches \
  "personal-routes-live-state-to-core" \
  '(^|[^[:alnum:]_./-])os/(agents|automations)/[^[:space:]`]*((reports?|briefs?|histories|run-logs|outputs?|queues?)/|/(BRIEF_HISTORY|HISTORY|RUN_HISTORY|QUEUE)\.(md|html|json|jsonl|txt))' \
  "$ROOT/personal/os"

# Raw Git push/persistence instructions should be replaced by scripts/agent-push
# for AgentOS public repository pushes. This intentionally flags historical
# automation memories so humans can migrate or retire them.
report_matches \
  "raw-git-persistence-instruction" \
  '(^|[^[:alnum:]_./-])(git[[:space:]]+push|pushed to `?origin/(main|master)`?|push(ed)? to `?origin/(main|master)`?)' \
  --glob '!os/verification/scripts/agentos_validator/**' \
  "${existing_scopes[@]}"

# Installed skills and automations that adapt private live agents should not
# route private reports, briefs, histories, queues, or outputs into Core.
installed_scopes=()
for scope in "$HOME_DIR/.agents/skills" "$HOME_DIR/.codex/automations"; do
  if [ -e "$scope" ]; then
    installed_scopes+=("$scope")
  fi
done

if [ "${#installed_scopes[@]}" -gt 0 ]; then
  report_matches \
    "installed-private-agent-routes-to-core" \
    '(^|[^[:alnum:]_./-])os/(agents|automations)/[^[:space:]`]*((reports?|briefs?|histories|run-logs|outputs?|queues?)/|/(BRIEF_HISTORY|HISTORY|RUN_HISTORY|QUEUE)\.(md|html|json|jsonl|txt))' \
    "${installed_scopes[@]}"
fi

if [ "$findings" -gt 0 ]; then
  echo
  echo "AgentOS stale-instruction audit found $findings finding(s)."
  exit 1
fi

echo "AgentOS stale-instruction audit passed."
