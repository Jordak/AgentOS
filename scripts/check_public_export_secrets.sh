#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -n "${AGENTOS_PUBLICATION_CANDIDATE:-}" || -n "${AGENTOS_PUBLIC_EXPORT:-}" ]]; then
  EXPORT_DIR="${AGENTOS_PUBLICATION_CANDIDATE:-${AGENTOS_PUBLIC_EXPORT:-}}"
  FORCE_EXPORT=1
else
  EXPORT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/agentos-export-XXXXXX")"
  rmdir "$EXPORT_DIR"
  FORCE_EXPORT=0
fi

python3 "$ROOT/os/verification/scripts/validate_agentos.py" --publication-precheck
if [[ "$FORCE_EXPORT" == "1" ]]; then
  python3 "$ROOT/scripts/export_public_agentos.py" --staged --output "$EXPORT_DIR" --force
else
  python3 "$ROOT/scripts/export_public_agentos.py" --staged --output "$EXPORT_DIR"
fi

if ! command -v gitleaks >/dev/null 2>&1; then
  echo "error: gitleaks is required for the publication candidate secret scan" >&2
  exit 127
fi

gitleaks dir --redact --verbose --config "$EXPORT_DIR/.gitleaks-publication.toml" "$EXPORT_DIR"

if [[ "${AGENTOS_TRUFFLEHOG_SCAN:-0}" == "1" ]]; then
  if ! command -v trufflehog >/dev/null 2>&1; then
    echo "error: trufflehog was requested but is not installed" >&2
    exit 127
  fi
  trufflehog filesystem --results=verified,unknown --fail --no-update "$EXPORT_DIR"
fi
