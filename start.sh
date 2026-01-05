#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Wegent local start script (hybrid mode):
# - Backend + Frontend run on host (no Docker)
# - Other components (MySQL/Redis/Executor Manager, optional Elasticsearch) run via Docker
# - If target ports/services are already running, they will be stopped and restarted
# - On exit, everything started by this script will be stopped

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load env files (lowest precedence first):
# - .env.defaults (tracked, safe defaults for deployment)
# - .env (local overrides, gitignored)
# - .env.local (local overrides, gitignored)
load_env_file() {
  local file="$1"
  if [ ! -f "$file" ]; then
    return 0
  fi

  while IFS= read -r line || [ -n "$line" ]; do
    # Ignore comments and empty lines.
    if [[ "$line" =~ ^[[:space:]]*# ]] || [[ "$line" =~ ^[[:space:]]*$ ]]; then
      continue
    fi
    # Only support KEY=VALUE lines.
    if [[ "$line" != *"="* ]]; then
      continue
    fi

    local key="${line%%=*}"
    local value="${line#*=}"

    # Trim surrounding whitespace.
    key="$(echo "$key" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    value="$(echo "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"

    if [ -z "$key" ]; then
      continue
    fi

    # Remove single/double quotes around the value, if present.
    if [[ "$value" =~ ^\".*\"$ ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "$value" =~ ^\'.*\'$ ]]; then
      value="${value:1:${#value}-2}"
    fi

    # Do not override variables already present in the process environment.
    if [ -z "${!key+x}" ]; then
      export "${key}=${value}"
    fi
  done <"$file"
}

load_env_file "${WEGENT_ENV_DEFAULTS_FILE:-${ROOT_DIR}/.env.defaults}"
load_env_file "${WEGENT_ENV_FILE:-${ROOT_DIR}/.env}"
load_env_file "${WEGENT_ENV_LOCAL_FILE:-${ROOT_DIR}/.env.local}"

# Default ports
FRONTEND_PORT="${WEGENT_FRONTEND_PORT:-3000}"
BACKEND_PORT="${WEGENT_BACKEND_PORT:-8000}"
EXECUTOR_MANAGER_PORT="${WEGENT_EXECUTOR_MANAGER_PORT:-8001}"
MYSQL_PORT="${WEGENT_MYSQL_PORT:-3306}"
REDIS_PORT="${WEGENT_REDIS_PORT:-6379}"
ELASTICSEARCH_PORT="${WEGENT_ELASTICSEARCH_PORT:-9200}"

# Optional components
ENABLE_RAG="${WEGENT_ENABLE_RAG:-false}"
FRONTEND_DEV_MODE="${WEGENT_FRONTEND_DEV_MODE:-false}"

# Public access configuration (for browsers on other machines).
# By default, the script keeps using localhost.
# Set WEGENT_PUBLIC_HOST=auto to auto-detect a non-loopback IPv4 address.
detect_default_ipv4() {
  local ip=""

  if command -v ip >/dev/null 2>&1; then
    ip="$(ip route get 1.1.1.1 2>/dev/null | awk '{for (i=1; i<=NF; i++) if ($i=="src") {print $(i+1); exit}}')"
  fi

  if [ -z "$ip" ] && command -v python3 >/dev/null 2>&1; then
    ip="$(python3 - <<'PY'
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    s.connect(("8.8.8.8", 80))
    print(s.getsockname()[0])
finally:
    s.close()
PY
)"
  fi
  if [ -z "$ip" ] && command -v python >/dev/null 2>&1; then
    ip="$(python - <<'PY'
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    s.connect(("8.8.8.8", 80))
    print(s.getsockname()[0])
finally:
    s.close()
PY
)"
  fi

  echo "${ip}"
}

PUBLIC_SCHEME="${WEGENT_PUBLIC_SCHEME:-http}"
PUBLIC_HOST="${WEGENT_PUBLIC_HOST:-localhost}"
if [ "${PUBLIC_HOST}" = "auto" ]; then
  PUBLIC_HOST="$(detect_default_ipv4)"
  if [ -z "${PUBLIC_HOST}" ]; then
    PUBLIC_HOST="localhost"
  fi
fi

PUBLIC_FRONTEND_URL="${PUBLIC_SCHEME}://${PUBLIC_HOST}:${FRONTEND_PORT}"
PUBLIC_BACKEND_URL="${PUBLIC_SCHEME}://${PUBLIC_HOST}:${BACKEND_PORT}"

# Allow overrides via existing env vars (useful for reverse proxies).
BACKEND_FRONTEND_URL="${FRONTEND_URL:-${PUBLIC_FRONTEND_URL}}"
SOCKET_DIRECT_URL="${RUNTIME_SOCKET_DIRECT_URL:-${PUBLIC_BACKEND_URL}}"

# Next.js bind host (affects whether other machines can access the frontend).
# Default to 0.0.0.0 to allow LAN/WAN access; override with WEGENT_FRONTEND_HOST=127.0.0.1 to restrict to local only.
FRONTEND_HOST="${WEGENT_FRONTEND_HOST:-0.0.0.0}"

# Runtime workspace for executor containers (host path)
EXECUTOR_WORKSPACE="${WEGENT_EXECUTOR_WORKSPACE:-${HOME}/wecode-bot}"

# Docker image overrides (useful for forks publishing to GHCR)
detect_image_prefix() {
  if [ -n "${WEGENT_IMAGE_PREFIX:-}" ]; then
    echo "${WEGENT_IMAGE_PREFIX}"
    return 0
  fi

  # Best-effort: infer GHCR owner from git origin remote.
  if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    local origin_url=""
    origin_url="$(git remote get-url origin 2>/dev/null || true)"
    if [ -n "${origin_url}" ]; then
      local owner=""
      owner="$(echo "${origin_url}" | sed -nE 's#^(git@github\.com:|https://github\.com/)([^/]+)/Wegent(\.git)?$#\\2#p')"
      if [ -n "${owner}" ]; then
        echo "ghcr.io/${owner}"
        return 0
      fi
    fi
  fi

  echo "ghcr.io/wecode-ai"
}

IMAGE_PREFIX="$(detect_image_prefix)"

EXECUTOR_MANAGER_IMAGE="${WEGENT_EXECUTOR_MANAGER_IMAGE:-${IMAGE_PREFIX}/wegent-executor-manager:${WEGENT_EXECUTOR_MANAGER_VERSION:-latest}}"
# Default to Codex-enabled tag to avoid per-release version bumps.
EXECUTOR_IMAGE="${WEGENT_EXECUTOR_IMAGE:-${IMAGE_PREFIX}/wegent-executor:${WEGENT_EXECUTOR_VERSION:-latest-codex}}"

BACKEND_PGID=""
FRONTEND_PGID=""
CLEANUP_ARMED="false"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

usage() {
  cat <<EOF
Usage: ./start.sh [OPTIONS]

This script reads env files automatically (lowest precedence first):
  - .env.defaults (tracked)
  - .env (gitignored)
  - .env.local (gitignored)

Options:
  --frontend-port PORT           Frontend port (default: ${FRONTEND_PORT})
  --backend-port PORT            Backend port (default: ${BACKEND_PORT})
  --executor-manager-port PORT   Executor Manager port (default: ${EXECUTOR_MANAGER_PORT})
  --rag                          Start Elasticsearch (RAG profile) (default: ${ENABLE_RAG})
  --no-rag                       Do not start Elasticsearch
  --dev                          Start frontend in development mode (skip build, use next dev)
  -h, --help                     Show help

Environment variables (optional):
  WEGENT_FRONTEND_PORT, WEGENT_BACKEND_PORT, WEGENT_EXECUTOR_MANAGER_PORT
  WEGENT_PUBLIC_HOST (default: localhost; use 'auto' to detect), WEGENT_PUBLIC_SCHEME (default: http)
  WEGENT_FRONTEND_HOST (default: 0.0.0.0; set to 127.0.0.1 to restrict to local only)
  WEGENT_MYSQL_PORT, WEGENT_REDIS_PORT, WEGENT_ELASTICSEARCH_PORT (must match docker-compose.yml port mapping)
  WEGENT_ENABLE_RAG, WEGENT_EXECUTOR_WORKSPACE, WEGENT_FRONTEND_DEV_MODE
  WEGENT_IMAGE_PREFIX, WEGENT_EXECUTOR_MANAGER_IMAGE, WEGENT_EXECUTOR_IMAGE
  WEGENT_EXECUTOR_MANAGER_VERSION, WEGENT_EXECUTOR_VERSION
  REDIS_PASSWORD (required for docker-compose.yml redis auth; auto-generated if missing)
EOF
}

die() {
  echo -e "${RED}Error: $*${NC}" >&2
  exit 1
}

have() { command -v "$1" >/dev/null 2>&1; }

ensure_redis_password() {
  if [ -n "${REDIS_PASSWORD:-}" ]; then
    return 0
  fi

  local generated=""
  if have python3; then
    generated="$(python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
)"
  elif have openssl; then
    generated="$(openssl rand -hex 32)"
  else
    generated="wegent-redis-$(date +%s)"
  fi

  export REDIS_PASSWORD="${generated}"

  local env_local_file="${WEGENT_ENV_LOCAL_FILE:-${ROOT_DIR}/.env.local}"
  if [ -f "${env_local_file}" ]; then
    if ! grep -qE '^REDIS_PASSWORD=' "${env_local_file}" 2>/dev/null; then
      echo "" >>"${env_local_file}"
      echo "REDIS_PASSWORD=${generated}" >>"${env_local_file}"
    fi
  else
    echo "REDIS_PASSWORD=${generated}" >>"${env_local_file}"
  fi

  echo -e "${YELLOW}REDIS_PASSWORD 未设置，已自动生成并写入 ${env_local_file}${NC}"
}

# macOS compatibility: setsid is not available by default
# Use setsid if available, otherwise fall back to nohup or direct background execution
# The command should already include output redirection (e.g., >>log 2>&1)
run_detached() {
  local cmd="$1"
  if have setsid; then
    setsid bash -c "$cmd" &
  elif have nohup; then
    # macOS fallback: use nohup (command should handle its own redirection)
    nohup bash -c "$cmd" &
  else
    # Last resort: direct background execution
    bash -c "$cmd" &
  fi
  echo $!
}

validate_port() {
  local port="$1"
  local name="$2"

  if ! [[ "$port" =~ ^[0-9]+$ ]]; then
    die "${name} must be a number, got: ${port}"
  fi
  if ((port < 1 || port > 65535)); then
    die "${name} must be between 1 and 65535, got: ${port}"
  fi
}

DOCKER_COMPOSE=()
detect_docker_compose() {
  if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE=(docker compose)
    return 0
  fi
  if have docker-compose; then
    DOCKER_COMPOSE=(docker-compose)
    return 0
  fi
  die "docker compose is not available (install Docker Compose plugin or docker-compose)."
}

ensure_uv() {
  if have uv; then
    return 0
  fi

  echo -e "${YELLOW}uv not found, installing...${NC}"
  have curl || die "curl is required to install uv."
  curl -LsSf https://astral.sh/uv/install.sh | sh

  if [ -f "${HOME}/.cargo/env" ]; then
    # shellcheck disable=SC1090
    source "${HOME}/.cargo/env"
  fi
  export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"

  have uv || die "uv installation failed. Please install uv manually: https://github.com/astral-sh/uv"
}

# Prefer python3; fall back to python; last resort: uv-managed python.
PYTHON_RUNNER=()
ensure_python_runner() {
  if [ "${#PYTHON_RUNNER[@]}" -ne 0 ]; then
    return 0
  fi

  if have python3; then
    PYTHON_RUNNER=(python3)
    return 0
  fi
  if have python; then
    PYTHON_RUNNER=(python)
    return 0
  fi

  ensure_uv
  PYTHON_RUNNER=(uv run python)
}
maybe_build_frontend_needed() {
  local flag_var="$1"
  local source_ts
  source_ts="$(max_mtime "${ROOT_DIR}/frontend")"
  local build_ts
  build_ts="$(max_mtime "${ROOT_DIR}/frontend/.next")"

  local need="false"
  if [ "$build_ts" -eq 0 ] || [ "$source_ts" -gt "$build_ts" ]; then
    need="true"
  fi

  printf -v "$flag_var" '%s' "$need"
}

# Ensure Next.js standalone runtime has all required static assets.
# When `output: 'standalone'` is enabled, the server may run from `.next/standalone/` and
# expects `public/` and `.next/static/` to be present alongside `server.js`.
sync_frontend_standalone_assets() {
  local frontend_dir="${ROOT_DIR}/frontend"
  local standalone_dir="${frontend_dir}/.next/standalone"

  if [ ! -f "${standalone_dir}/server.js" ]; then
    return 0
  fi

  echo -e "${BLUE}  Syncing standalone assets (public/, .next/static)...${NC}"

  rm -rf "${standalone_dir}/public" "${standalone_dir}/.next/static"
  mkdir -p "${standalone_dir}/.next"

  if [ -d "${frontend_dir}/public" ]; then
    cp -a "${frontend_dir}/public" "${standalone_dir}/"
  fi

  if [ -d "${frontend_dir}/.next/static" ]; then
    cp -a "${frontend_dir}/.next/static" "${standalone_dir}/.next/"
  fi
}

# Return max mtime (seconds) for given paths, pruning common cache dirs to keep checks fast.
max_mtime() {
  ensure_python_runner
  "${PYTHON_RUNNER[@]}" - "$@" <<'PY'
import os, sys

prune = {'.git', 'node_modules', '.next', '.turbo', '.pytest_cache', '__pycache__', '.mypy_cache', 'dist', 'build', 'coverage', '.venv'}
max_ts = 0

def walk(path):
    global max_ts
    if not os.path.exists(path):
        return
    if os.path.isfile(path):
        try:
            max_ts = max(max_ts, os.path.getmtime(path))
        except FileNotFoundError:
            pass
        return
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in prune]
        for f in files:
            fp = os.path.join(root, f)
            try:
                max_ts = max(max_ts, os.path.getmtime(fp))
            except FileNotFoundError:
                continue

for p in sys.argv[1:]:
    walk(p)

print(int(max_ts))
PY
}

# Get docker image created timestamp (seconds since epoch); returns 0 if image missing.
image_created_ts() {
  local image="$1"
  local created=""
  created="$(docker image inspect "$image" -f '{{.Created}}' 2>/dev/null || true)"
  if [ -z "$created" ]; then
    echo 0
    return
  fi
  ensure_python_runner
  "${PYTHON_RUNNER[@]}" - "$created" <<'PY'
import sys, datetime
val = sys.argv[1]
try:
    dt = datetime.datetime.fromisoformat(val.replace('Z', '+00:00'))
    print(int(dt.timestamp()))
except Exception:
    print(0)
PY
}

# Build image if source is newer (or image missing). Sets flag variable by name to "true"/"false".
maybe_build_image() {
  local image="$1"
  local dockerfile="$2"
  local label="$3"
  local flag_var="$4"
  shift 4
  local source_ts
  source_ts="$(max_mtime "$@")"
  local image_ts
  image_ts="$(image_created_ts "$image")"

  local built="false"
  if [ "$image_ts" -lt "$source_ts" ] || [ "$image_ts" -eq 0 ]; then
    echo -e "${YELLOW}  Building ${label} image from local source (tag: ${image})...${NC}"
    docker build -f "$dockerfile" -t "$image" "$ROOT_DIR"
    built="true"
  else
    echo -e "${GREEN}  ${label} image up-to-date (source mtime ≤ image).${NC}"
  fi

  printf -v "$flag_var" '%s' "$built"
}

kill_process_group() {
  local pgid="$1"
  if [ -z "$pgid" ]; then
    return 0
  fi
  if kill -0 "-${pgid}" >/dev/null 2>&1; then
    kill -TERM "-${pgid}" >/dev/null 2>&1 || true
    sleep 1
    kill -KILL "-${pgid}" >/dev/null 2>&1 || true
  fi
}

docker_rm_if_exists() {
  local name="$1"
  docker rm -f "$name" >/dev/null 2>&1 || true
}

docker_rm_by_host_port() {
  local port="$1"
  local ids=""

  ids="$(
    docker ps --format '{{.ID}}\t{{.Ports}}' \
      | awk -v p="${port}" 'index($0, ":"p"->") {print $1}' \
      | tr '\n' ' '
  )"

  if [ -n "$ids" ]; then
    echo -e "${YELLOW}Stopping Docker container(s) publishing port ${port}: ${ids}${NC}"
    # shellcheck disable=SC2086
    docker rm -f ${ids} >/dev/null 2>&1 || true
  fi
}

kill_listen_port() {
  local port="$1"
  local pids=""

  if have lsof; then
    pids="$(lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true)"
  fi
  # lsof may exist but return empty on some environments (e.g., IPv6-only listeners).
  # Fall back to ss if available.
  if [ -z "$pids" ] && have ss; then
    pids="$(
      ss -lptn "sport = :${port}" 2>/dev/null \
        | awk 'match($0, /pid=([0-9]+)/, a) {print a[1]}' \
        | sort -u \
        | tr '\n' ' '
    )"
  fi

  if [ -n "$pids" ]; then
    echo -e "${YELLOW}Killing process(es) listening on port ${port}: ${pids}${NC}"
    # shellcheck disable=SC2086
    kill -TERM ${pids} >/dev/null 2>&1 || true
    sleep 1
    # shellcheck disable=SC2086
    kill -KILL ${pids} >/dev/null 2>&1 || true
  fi
}

wait_for_container_healthy() {
  local name="$1"
  local timeout_sec="$2"
  local start_ts
  start_ts="$(date +%s)"

  while true; do
    local status=""
    status="$(docker inspect -f '{{.State.Health.Status}}' "$name" 2>/dev/null || true)"
    if [ "$status" = "healthy" ] || [ -z "$status" ]; then
      return 0
    fi
    if (( $(date +%s) - start_ts > timeout_sec )); then
      echo -e "${YELLOW}Warning: timeout waiting for ${name} to become healthy (last status: ${status}).${NC}"
      return 1
    fi
    sleep 2
  done
}

wait_for_http() {
  local url="$1"
  local timeout_sec="$2"
  local start_ts
  start_ts="$(date +%s)"

  while true; do
    # Ensure curl doesn't hang forever if the TCP connection is accepted but no response is returned.
    if curl -fsS --connect-timeout 2 --max-time 5 "$url" >/dev/null 2>&1; then
      return 0
    fi
    if (( $(date +%s) - start_ts > timeout_sec )); then
      return 1
    fi
    sleep 1
  done
}

cleanup() {
  local exit_code=$?

  trap - EXIT

  if [ "${CLEANUP_ARMED}" != "true" ]; then
    exit "$exit_code"
  fi

  echo ""
  echo -e "${BLUE}Shutting down...${NC}"

  kill_process_group "$FRONTEND_PGID"
  kill_process_group "$BACKEND_PGID"

  local executor_container_ids=""
  executor_container_ids="$(docker ps -aq --filter 'label=owner=executor_manager' 2>/dev/null || true)"
  if [ -n "$executor_container_ids" ]; then
    # shellcheck disable=SC2086
    docker rm -f $executor_container_ids >/dev/null 2>&1 || true
  fi

  docker_rm_if_exists "wegent-executor-manager"
  docker_rm_if_exists "wegent-backend"
  docker_rm_if_exists "wegent-frontend"
  docker_rm_if_exists "wegent-elasticsearch"
  docker_rm_if_exists "wegent-redis"
  docker_rm_if_exists "wegent-mysql"

  exit "$exit_code"
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

main() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --frontend-port)
        FRONTEND_PORT="$2"
        shift 2
        ;;
      --backend-port)
        BACKEND_PORT="$2"
        shift 2
        ;;
      --executor-manager-port)
        EXECUTOR_MANAGER_PORT="$2"
        shift 2
        ;;
      --rag)
        ENABLE_RAG="true"
        shift
        ;;
      --no-rag)
        ENABLE_RAG="false"
        shift
        ;;
      --dev)
        FRONTEND_DEV_MODE="true"
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "Unknown option: $1 (use --help)"
        ;;
    esac
  done

  validate_port "$FRONTEND_PORT" "Frontend port"
  validate_port "$BACKEND_PORT" "Backend port"
  validate_port "$EXECUTOR_MANAGER_PORT" "Executor Manager port"
  validate_port "$MYSQL_PORT" "MySQL port"
  validate_port "$REDIS_PORT" "Redis port"
  validate_port "$ELASTICSEARCH_PORT" "Elasticsearch port"

  if [ "$MYSQL_PORT" != "3306" ] || [ "$REDIS_PORT" != "6379" ] || [ "$ELASTICSEARCH_PORT" != "9200" ]; then
    die "Custom MySQL/Redis/Elasticsearch ports are not supported by this script unless you also update docker-compose.yml port mappings."
  fi

  have docker || die "docker is required."
  detect_docker_compose
  have node || die "node is required (Node.js 18+ recommended)."
  have npm || die "npm is required."
  have curl || die "curl is required."

  ensure_redis_password

  mkdir -p "$EXECUTOR_WORKSPACE"

  echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
  echo -e "${BLUE}║          Wegent Hybrid Local Startup Script            ║${NC}"
  echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "${GREEN}Ports:${NC}"
  echo -e "  Frontend:        ${PUBLIC_FRONTEND_URL}"
  echo -e "  Backend:         ${PUBLIC_BACKEND_URL}"
  echo -e "  ExecutorManager: http://${PUBLIC_HOST}:${EXECUTOR_MANAGER_PORT}"
  echo -e "  MySQL:           localhost:${MYSQL_PORT}"
  echo -e "  Redis:           localhost:${REDIS_PORT}"
  if [ "$ENABLE_RAG" = "true" ]; then
    echo -e "  Elasticsearch:   http://${PUBLIC_HOST}:${ELASTICSEARCH_PORT}"
  fi
  if [ "${PUBLIC_HOST}" = "localhost" ] || [ "${PUBLIC_HOST}" = "127.0.0.1" ] || [ "${PUBLIC_HOST}" = "::1" ]; then
    echo ""
    echo -e "${YELLOW}Tip: To allow access from other machines, run with:${NC}"
    echo -e "  ${BLUE}WEGENT_PUBLIC_HOST=auto ./start.sh${NC}"
  fi
  echo ""

  CLEANUP_ARMED="true"

  echo -e "${BLUE}[1/6] Stopping existing services on target ports...${NC}"

  docker_rm_if_exists "wegent-backend"
  docker_rm_if_exists "wegent-frontend"
  docker_rm_if_exists "wegent-executor-manager"
  docker_rm_if_exists "wegent-elasticsearch"
  docker_rm_if_exists "wegent-redis"
  docker_rm_if_exists "wegent-mysql"

  local executor_container_ids=""
  executor_container_ids="$(docker ps -aq --filter 'label=owner=executor_manager' 2>/dev/null || true)"
  if [ -n "$executor_container_ids" ]; then
    # shellcheck disable=SC2086
    docker rm -f $executor_container_ids >/dev/null 2>&1 || true
  fi

  docker_rm_by_host_port "$FRONTEND_PORT"
  docker_rm_by_host_port "$BACKEND_PORT"
  docker_rm_by_host_port "$EXECUTOR_MANAGER_PORT"
  docker_rm_by_host_port "$MYSQL_PORT"
  docker_rm_by_host_port "$REDIS_PORT"
  if [ "$ENABLE_RAG" = "true" ]; then
    docker_rm_by_host_port "$ELASTICSEARCH_PORT"
  fi

  kill_listen_port "$FRONTEND_PORT"
  kill_listen_port "$BACKEND_PORT"
  kill_listen_port "$EXECUTOR_MANAGER_PORT"
  kill_listen_port "$MYSQL_PORT"
  kill_listen_port "$REDIS_PORT"
  if [ "$ENABLE_RAG" = "true" ]; then
    kill_listen_port "$ELASTICSEARCH_PORT"
  fi
  echo -e "${GREEN}✓ Ports are free${NC}"
  echo ""

  echo -e "${BLUE}[2/6] Starting Docker services (mysql/redis)...${NC}"
  if [ "$ENABLE_RAG" = "true" ]; then
    echo -e "${BLUE}Starting Elasticsearch (RAG profile)...${NC}"
    (cd "$ROOT_DIR" && "${DOCKER_COMPOSE[@]}" --profile rag up -d mysql redis elasticsearch)
  else
    (cd "$ROOT_DIR" && "${DOCKER_COMPOSE[@]}" up -d mysql redis)
  fi

  wait_for_container_healthy "wegent-mysql" 180 || true
  wait_for_container_healthy "wegent-redis" 60 || true
  if [ "$ENABLE_RAG" = "true" ]; then
    wait_for_container_healthy "wegent-elasticsearch" 240 || true
  fi
  echo -e "${GREEN}✓ Docker services started${NC}"
  echo ""

  echo -e "${BLUE}[3/6] Starting Executor Manager (Docker)...${NC}"

  echo -e "  Checking local executor images freshness..."
  local built_executor_manager_image="false"
  local built_executor_image="false"
  maybe_build_image "${EXECUTOR_MANAGER_IMAGE}" "${ROOT_DIR}/docker/executor_manager/Dockerfile" "Executor Manager" "built_executor_manager_image" "${ROOT_DIR}/executor_manager" "${ROOT_DIR}/shared" "${ROOT_DIR}/docker/executor_manager/Dockerfile"
  maybe_build_image "${EXECUTOR_IMAGE}" "${ROOT_DIR}/docker/executor/Dockerfile" "Executor" "built_executor_image" "${ROOT_DIR}/executor" "${ROOT_DIR}/shared" "${ROOT_DIR}/docker/executor/Dockerfile"

  local network_gateway=""
  network_gateway="$(docker network inspect wegent-network --format '{{(index .IPAM.Config 0).Gateway}}' 2>/dev/null || true)"
  if [ -z "$network_gateway" ]; then
    die "Failed to detect gateway IP for docker network 'wegent-network'."
  fi

  # Check if image exists locally to avoid unnecessary pulls
  local image_exists=false
  if docker image inspect "${EXECUTOR_MANAGER_IMAGE}" >/dev/null 2>&1; then
    image_exists=true
    echo -e "${GREEN}  Using existing local image: ${EXECUTOR_MANAGER_IMAGE}${NC}"
  fi

  # If using floating tags (latest*), always pull before starting to avoid stale images.
  local pull_flag=()
  if [[ "${EXECUTOR_MANAGER_IMAGE}" == *":latest"* ]] && [ "$built_executor_manager_image" = "false" ]; then
    pull_flag=(--pull=always)
    if [ "$image_exists" = false ]; then
      echo -e "${YELLOW}  Pulling ${EXECUTOR_MANAGER_IMAGE}...${NC}"
    fi
  elif [ "$image_exists" = false ] && [ "$built_executor_manager_image" = "false" ]; then
    echo -e "${YELLOW}  Image not found locally, pulling ${EXECUTOR_MANAGER_IMAGE}...${NC}"
    echo -e "${YELLOW}  (This may take a while for first-time download)${NC}"
  fi
  if [ "$built_executor_manager_image" = "false" ]; then
    # Avoid overriding freshly built image with a pull.
    if [[ "${EXECUTOR_IMAGE}" == *":latest"* ]] && [ "$built_executor_image" = "false" ]; then
      if ! docker image inspect "${EXECUTOR_IMAGE}" >/dev/null 2>&1; then
        echo -e "${YELLOW}  Pulling ${EXECUTOR_IMAGE}...${NC}"
      fi
      docker pull "${EXECUTOR_IMAGE}" >/dev/null 2>&1 || true
    fi
  fi

  # Build docker run command with optional pull flag
  local docker_cmd=(
    docker run -d
  )
  if [ ${#pull_flag[@]} -gt 0 ]; then
    docker_cmd+=("${pull_flag[@]}")
  fi
  docker_cmd+=(
        --name wegent-executor-manager
        --network wegent-network
        --network-alias executor_manager
        --add-host host.docker.internal:host-gateway
        -p "${EXECUTOR_MANAGER_PORT}:8001"
        -e TZ=Asia/Shanghai
        -e TASK_API_DOMAIN="http://${network_gateway}:${BACKEND_PORT}"
        -e EXECUTOR_MANAGER_PORT="8001"
        -e MAX_CONCURRENT_TASKS=30
        -e PORT=8001
        -e CALLBACK_HOST="http://executor_manager:8001"
        -e CALLBACK_PORT="8001"
        -e NETWORK=wegent-network
        -e DOCKER_HOST_ADDR="host.docker.internal"
        -e EXECUTOR_IMAGE="${EXECUTOR_IMAGE}"
        -e EXECUTOR_PORT_RANGE_MIN=10001
        -e EXECUTOR_PORT_RANGE_MAX=10100
        -e EXECUTOR_WORKSPACE="${EXECUTOR_WORKSPACE}"
        -e EXECUTOR_WORKSPCE="${EXECUTOR_WORKSPACE}"
        -v /var/run/docker.sock:/var/run/docker.sock
    "${EXECUTOR_MANAGER_IMAGE}"
  )
  "${docker_cmd[@]}" >/dev/null

  # Executor Manager performs a one-time executor binary extraction which can take ~2 minutes
  # on first run (docker pull + copy). Extend health wait to avoid false negatives.
  if ! wait_for_http "http://127.0.0.1:${EXECUTOR_MANAGER_PORT}/health" 200; then
    die "Executor Manager did not become healthy on port ${EXECUTOR_MANAGER_PORT}."
  fi
  echo -e "${GREEN}✓ Executor Manager is healthy${NC}"
  echo ""

  echo -e "${BLUE}[4/6] Starting Backend (host, uv)...${NC}"
  ensure_uv

  (cd "${ROOT_DIR}/backend" && uv sync)

  local backend_pythonpath=""
  backend_pythonpath="${ROOT_DIR}:${PYTHONPATH:-}"

  local backend_log=""
  backend_log="${ROOT_DIR}/backend/uvicorn.log"
  : >"$backend_log"

  env \
    PYTHONPATH="${backend_pythonpath}" \
    ENVIRONMENT="development" \
    DB_AUTO_MIGRATE="True" \
    DATABASE_URL="mysql+pymysql://root:123456@127.0.0.1:${MYSQL_PORT}/task_manager" \
    REDIS_URL="redis://127.0.0.1:${REDIS_PORT}/0" \
    EXECUTOR_MANAGER_URL="http://127.0.0.1:${EXECUTOR_MANAGER_PORT}" \
    EXECUTOR_CANCEL_TASK_URL="http://127.0.0.1:${EXECUTOR_MANAGER_PORT}/executor-manager/tasks/cancel" \
    EXECUTOR_DELETE_TASK_URL="http://127.0.0.1:${EXECUTOR_MANAGER_PORT}/executor-manager/executor/delete" \
    FRONTEND_URL="${BACKEND_FRONTEND_URL}" \
    sh -c "cd '${ROOT_DIR}/backend' && exec uv run uvicorn app.main:app --host 0.0.0.0 --port '${BACKEND_PORT}'" >>"$backend_log" 2>&1 &

  BACKEND_PGID="$!"
  echo -e "${GREEN}✓ Backend started (PGID=${BACKEND_PGID})${NC}"
  echo -e "${GREEN}  Backend log: ${backend_log}${NC}"

  if ! wait_for_http "http://127.0.0.1:${BACKEND_PORT}/api/health" 120; then
    die "Backend did not become healthy on port ${BACKEND_PORT}."
  fi
  echo -e "${GREEN}✓ Backend is healthy${NC}"
  echo ""

  local node_major=""
  node_major="$(node --version | sed 's/^v//' | cut -d. -f1)"
  if [ "${node_major}" -lt 18 ]; then
    die "Node.js 18+ is required (found v${node_major})."
  fi

  if [ "$FRONTEND_DEV_MODE" = "true" ]; then
    echo -e "${BLUE}[5/6] Starting Frontend in Development Mode (npm run dev)...${NC}"
    echo -e "${YELLOW}  Note: Development mode enables hot reload and incremental compilation${NC}"
    
    (
      cd "${ROOT_DIR}/frontend"
      if [ ! -d node_modules ]; then
        npm install
      fi
    )
    
    local frontend_log=""
    frontend_log="${ROOT_DIR}/frontend/next.log"
    : >"$frontend_log"

    env \
      NODE_ENV="development" \
      PORT="${FRONTEND_PORT}" \
      RUNTIME_INTERNAL_API_URL="http://127.0.0.1:${BACKEND_PORT}" \
      RUNTIME_SOCKET_DIRECT_URL="${SOCKET_DIRECT_URL}" \
      sh -c "cd '${ROOT_DIR}/frontend' && exec npm run dev -- -p '${FRONTEND_PORT}' -H '${FRONTEND_HOST}'" >>"$frontend_log" 2>&1 &

    FRONTEND_PGID="$!"
    echo -e "${GREEN}✓ Frontend started in dev mode (PGID=${FRONTEND_PGID})${NC}"
    echo -e "${GREEN}  Frontend log: ${frontend_log}${NC}"
  else
    local need_frontend_build="false"
    maybe_build_frontend_needed need_frontend_build

    if [ "$need_frontend_build" = "true" ]; then
      echo -e "${BLUE}[5/6] Building Frontend (npm run build)...${NC}"
    else
      echo -e "${BLUE}[5/6] Frontend build not needed (source unchanged)...${NC}"
    fi

    (
      cd "${ROOT_DIR}/frontend"
      if [ ! -d node_modules ]; then
        npm install
      fi
      if [ "$need_frontend_build" = "true" ]; then
        npm run build
      fi
    )
    if [ "$need_frontend_build" = "true" ]; then
      echo -e "${GREEN}✓ Frontend build completed${NC}"
      echo ""
    else
      echo -e "${GREEN}✓ Reusing existing frontend build output (.next)${NC}"
      echo ""
    fi

    sync_frontend_standalone_assets

    echo -e "${BLUE}[6/6] Starting Frontend (host, npm start)...${NC}"
    local frontend_log=""
    frontend_log="${ROOT_DIR}/frontend/next.log"
    : >"$frontend_log"

    env \
      NODE_ENV="production" \
      RUNTIME_INTERNAL_API_URL="http://127.0.0.1:${BACKEND_PORT}" \
      RUNTIME_SOCKET_DIRECT_URL="${SOCKET_DIRECT_URL}" \
      sh -c "cd '${ROOT_DIR}/frontend' && exec npm start -- -p '${FRONTEND_PORT}' -H '${FRONTEND_HOST}'" >>"$frontend_log" 2>&1 &

    FRONTEND_PGID="$!"
    echo -e "${GREEN}✓ Frontend started (PGID=${FRONTEND_PGID})${NC}"
    echo -e "${GREEN}  Frontend log: ${frontend_log}${NC}"
  fi

  if ! wait_for_http "http://127.0.0.1:${FRONTEND_PORT}" 120; then
    die "Frontend did not become ready on port ${FRONTEND_PORT}."
  fi

  echo ""
  echo -e "${GREEN}All services are up.${NC}"
  echo -e "${GREEN}- Frontend: ${PUBLIC_FRONTEND_URL}${NC}"
  echo -e "${GREEN}- Backend:  ${PUBLIC_BACKEND_URL}/api/docs${NC}"
  echo -e "${GREEN}- Executor: http://${PUBLIC_HOST}:${EXECUTOR_MANAGER_PORT}/health${NC}"
  echo ""
  echo -e "${YELLOW}Press Ctrl+C to stop everything.${NC}"

  if ((BASH_VERSINFO[0] > 4 || (BASH_VERSINFO[0] == 4 && BASH_VERSINFO[1] >= 3) )); then
    wait -n "$BACKEND_PGID" "$FRONTEND_PGID"
    die "A service exited unexpectedly. Check logs above."
  else
    wait "$BACKEND_PGID" "$FRONTEND_PGID"
  fi
}

main "$@"
