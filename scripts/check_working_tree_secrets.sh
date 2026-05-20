#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v gitleaks >/dev/null 2>&1; then
  echo "error: gitleaks is required for the working-tree secret scan" >&2
  exit 127
fi

cd "$ROOT"
gitleaks dir --redact --verbose --config .gitleaks.toml .
