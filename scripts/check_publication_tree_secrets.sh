#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TREEISH="${1:-HEAD}"

if [[ "$#" -gt 1 ]]; then
  echo "usage: scripts/check_publication_tree_secrets.sh [treeish]" >&2
  exit 2
fi

if ! git -C "$ROOT" cat-file -e "${TREEISH}^{tree}" 2>/dev/null; then
  echo "error: treeish does not resolve to a Git tree: $TREEISH" >&2
  exit 2
fi

TREE="$(git -C "$ROOT" rev-parse --verify "${TREEISH}^{tree}")"
SNAPSHOT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/agentos-publication-tree-XXXXXX")"
trap 'rm -rf "$SNAPSHOT_DIR"' EXIT

git -C "$ROOT" archive --format=tar "$TREE" | tar -xf - -C "$SNAPSHOT_DIR"

python3 "$ROOT/os/verification/scripts/validate_agentos.py" --root "$ROOT" --public-export "$SNAPSHOT_DIR"

if ! command -v gitleaks >/dev/null 2>&1; then
  echo "error: gitleaks is required for the publication tree secret scan" >&2
  exit 127
fi

if [[ ! -f "$SNAPSHOT_DIR/.gitleaks-publication.toml" ]]; then
  echo "error: snapshot is missing .gitleaks-publication.toml" >&2
  exit 2
fi

gitleaks dir --redact --verbose --config "$SNAPSHOT_DIR/.gitleaks-publication.toml" "$SNAPSHOT_DIR"
