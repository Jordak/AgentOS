#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'USAGE'
Usage:
  make_temp_file.sh [prefix] [extension]
  make_temp_file.sh [--prefix PREFIX] [--extension EXTENSION]

Creates a temporary file and prints its path.

Defaults:
  prefix:    tmp-
  extension: .tmp
  directory: ${TMPDIR:-/tmp}

Examples:
  make_temp_file.sh
  make_temp_file.sh api-cache- json
  make_temp_file.sh --prefix readme- --extension .md
USAGE
}

make_temp_file() {
    local prefix="${1:-tmp-}"
    local extension="${2:-.tmp}"
    local template_dir="${TMPDIR:-/tmp}"

    while [[ "$template_dir" != "/" && "$template_dir" == */ ]]; do
        template_dir="${template_dir%/}"
    done
    local template_path
    if [[ "$template_dir" == "/" ]]; then
        template_path="/${prefix}XXXXXXXXXX"
    else
        template_path="${template_dir}/${prefix}XXXXXXXXXX"
    fi

    if [[ "$prefix" == *"/"* ]]; then
        echo "Error: prefix must not contain '/'" >&2
        return 2
    fi

    if [[ -n "$extension" && "$extension" != .* ]]; then
        extension=".$extension"
    fi

    if command -v gmktemp >/dev/null 2>&1; then
        gmktemp "${template_path}${extension}"
    elif mktemp --version >/dev/null 2>&1 && mktemp --version 2>&1 | grep -q "GNU coreutils"; then
        mktemp "${template_path}${extension}"
    else
        local tmp_base
        tmp_base=$(mktemp "$template_path") || return 1
        if [[ -z "$extension" ]]; then
            echo "$tmp_base"
            return 0
        fi
        mv "$tmp_base" "${tmp_base}${extension}"
        echo "${tmp_base}${extension}"
    fi
}

prefix="tmp-"
extension=".tmp"
positional=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --prefix)
            if [[ $# -lt 2 ]]; then
                echo "Error: --prefix requires a value" >&2
                exit 2
            fi
            prefix="$2"
            shift 2
            ;;
        --extension|--ext)
            if [[ $# -lt 2 ]]; then
                echo "Error: --extension requires a value" >&2
                exit 2
            fi
            extension="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        --)
            shift
            while [[ $# -gt 0 ]]; do
                positional+=("$1")
                shift
            done
            ;;
        -*)
            echo "Error: unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
        *)
            positional+=("$1")
            shift
            ;;
    esac
done

if [[ ${#positional[@]} -gt 2 ]]; then
    echo "Error: expected at most 2 positional arguments" >&2
    usage >&2
    exit 2
fi

if [[ ${#positional[@]} -ge 1 ]]; then
    prefix="${positional[0]}"
fi

if [[ ${#positional[@]} -ge 2 ]]; then
    extension="${positional[1]}"
fi

make_temp_file "$prefix" "$extension"
