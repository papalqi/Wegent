#!/bin/bash
# Sync project Codex prompts to the user's Codex home directory.
#
# Copies all files under "<repo>/.codex/prompts/" into "<CODEX_HOME>/prompts/"
# (or "$HOME/.codex/prompts" if CODEX_HOME is not set).
#
# Usage:
#   ./scripts/sync-codex-prompts.sh
#   ./scripts/sync-codex-prompts.sh --repo-root /path/to/repo
#   ./scripts/sync-codex-prompts.sh --codex-home /path/to/.codex

set -euo pipefail

usage() {
  cat <<'EOF'
Sync project Codex prompts to the user's Codex home directory.

Copies "<repo>/.codex/prompts/" -> "<CODEX_HOME>/prompts/" (default: "~/.codex/prompts").

Usage:
  ./scripts/sync-codex-prompts.sh [--repo-root PATH] [--codex-home PATH]

Options:
  --repo-root PATH   Repo root directory (default: parent of this script's directory)
  --codex-home PATH  Codex home directory (default: $CODEX_HOME, then "~/.codex")
  -h, --help         Show this help
EOF
}

repo_root=""
codex_home=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root)
      repo_root="${2:-}"
      shift 2
      ;;
    --codex-home)
      codex_home="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
if [[ -z "${repo_root}" ]]; then
  repo_root="$(cd "${script_dir}/.." && pwd -P)"
else
  repo_root="$(cd "${repo_root}" && pwd -P)"
fi

source_prompts_dir="${repo_root}/.codex/prompts"
if [[ ! -d "${source_prompts_dir}" ]]; then
  echo "Source prompts directory not found: ${source_prompts_dir}" >&2
  exit 1
fi

if [[ -z "${codex_home}" ]]; then
  if [[ -n "${CODEX_HOME:-}" ]]; then
    codex_home="${CODEX_HOME}"
  else
    codex_home="${HOME}/.codex"
  fi
fi

mkdir -p "${codex_home}"
codex_home="$(cd "${codex_home}" && pwd -P)"

dest_prompts_dir="${codex_home}/prompts"
mkdir -p "${dest_prompts_dir}"

file_count="$(find "${source_prompts_dir}" -type f | wc -l | tr -d '[:space:]')"
if [[ "${file_count}" == "0" ]]; then
  echo "No prompt files found under: ${source_prompts_dir}" >&2
  exit 0
fi

if command -v rsync >/dev/null 2>&1; then
  rsync -a "${source_prompts_dir}/" "${dest_prompts_dir}/"
else
  while IFS= read -r -d '' file; do
    relative="${file#${source_prompts_dir}/}"
    mkdir -p "${dest_prompts_dir}/$(dirname "${relative}")"
    cp -a "${file}" "${dest_prompts_dir}/${relative}"
  done < <(find "${source_prompts_dir}" -type f -print0)
fi

echo "Synced ${file_count} prompt file(s) to: ${dest_prompts_dir}"
