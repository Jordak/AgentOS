#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FORCE=0

usage() {
  cat >&2 <<'USAGE'
usage: scripts/install_agentos_hooks.sh [--force]

Symlinks scripts/hooks/pre-commit and scripts/hooks/pre-push into the Git hooks
directory. The hooks resolve the active worktree at runtime. Existing
non-AgentOS hooks are left untouched unless --force is used.
USAGE
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --force)
      FORCE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

if ! git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  echo "error: AgentOS root is not a Git working tree: $ROOT" >&2
  exit 2
fi

HOOKS_DIR="$(git -C "$ROOT" rev-parse --git-path hooks)"
case "$HOOKS_DIR" in
  /*) ;;
  *) HOOKS_DIR="$ROOT/$HOOKS_DIR" ;;
esac
mkdir -p "$HOOKS_DIR"

for hook in pre-commit pre-push; do
  source="$ROOT/scripts/hooks/$hook"
  target="$HOOKS_DIR/$hook"
  if [[ ! -x "$source" ]]; then
    echo "error: hook source is missing or not executable: $source" >&2
    exit 2
  fi
  if [[ -e "$target" || -L "$target" ]]; then
    current="$(readlink "$target" || true)"
    if [[ "$current" != "$source" && "$FORCE" != "1" ]]; then
      echo "error: refusing to overwrite existing hook: $target" >&2
      echo "       rerun with --force to replace it with $source" >&2
      exit 2
    fi
  fi
  ln -sfn "$source" "$target"
  echo "Installed $hook -> $source"
done
