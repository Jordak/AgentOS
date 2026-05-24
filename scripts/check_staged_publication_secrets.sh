#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SNAPSHOT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/agentos-staged-publication-XXXXXX")"
trap 'rm -rf "$SNAPSHOT_DIR"' EXIT

TREE="$(git -C "$ROOT" write-tree)"
git -C "$ROOT" archive --format=tar "$TREE" | tar -xf - -C "$SNAPSHOT_DIR"

python3 "$ROOT/os/verification/scripts/validate_agentos.py" --root "$ROOT" --public-export "$SNAPSHOT_DIR"

if ! command -v gitleaks >/dev/null 2>&1; then
  echo "error: gitleaks is required for the staged publication secret scan" >&2
  exit 127
fi

gitleaks dir --redact --verbose --config "$SNAPSHOT_DIR/.gitleaks-publication.toml" "$SNAPSHOT_DIR"
