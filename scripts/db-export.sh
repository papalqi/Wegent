#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

load_env_file() {
  local file="$1"
  if [ ! -f "$file" ]; then
    return 0
  fi

  while IFS= read -r line || [ -n "$line" ]; do
    if [[ "$line" =~ ^[[:space:]]*# ]] || [[ "$line" =~ ^[[:space:]]*$ ]]; then
      continue
    fi
    if [[ "$line" != *"="* ]]; then
      continue
    fi

    local key="${line%%=*}"
    local value="${line#*=}"

    key="$(echo "$key" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    value="$(echo "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"

    if [ -z "$key" ]; then
      continue
    fi

    if [[ "$value" =~ ^\".*\"$ ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "$value" =~ ^\'.*\'$ ]]; then
      value="${value:1:${#value}-2}"
    fi

    if [ -z "${!key+x}" ]; then
      export "${key}=${value}"
    fi
  done <"$file"
}

load_env_file "${WEGENT_ENV_DEFAULTS_FILE:-${ROOT_DIR}/.env.defaults}"
load_env_file "${WEGENT_ENV_FILE:-${ROOT_DIR}/.env}"
load_env_file "${WEGENT_ENV_LOCAL_FILE:-${ROOT_DIR}/.env.local}"
load_env_file "${WEGENT_BACKEND_ENV_FILE:-${ROOT_DIR}/backend/.env}"

if [ -z "${DATABASE_URL:-}" ]; then
  mysql_host="${WEGENT_MYSQL_HOST:-127.0.0.1}"
  mysql_port="${WEGENT_MYSQL_PORT:-3306}"
  mysql_user="${WEGENT_MYSQL_USER:-root}"
  mysql_password="${WEGENT_MYSQL_PASSWORD:-123456}"
  mysql_database="${WEGENT_MYSQL_DATABASE:-task_manager}"
  export DATABASE_URL="mysql+pymysql://${mysql_user}:${mysql_password}@${mysql_host}:${mysql_port}/${mysql_database}"
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found in PATH; please install uv first." >&2
  exit 1
fi

exec bash -c "cd '${ROOT_DIR}/backend' && uv run python -m app.scripts.db_transfer export \"$@\"" -- "$@"

