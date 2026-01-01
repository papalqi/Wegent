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

# Default ports
FRONTEND_PORT="${WEGENT_FRONTEND_PORT:-3000}"
BACKEND_PORT="${WEGENT_BACKEND_PORT:-8000}"
EXECUTOR_MANAGER_PORT="${WEGENT_EXECUTOR_MANAGER_PORT:-8001}"
MYSQL_PORT="${WEGENT_MYSQL_PORT:-3306}"
REDIS_PORT="${WEGENT_REDIS_PORT:-6379}"
ELASTICSEARCH_PORT="${WEGENT_ELASTICSEARCH_PORT:-9200}"

# Optional components
ENABLE_RAG="${WEGENT_ENABLE_RAG:-false}"

# Runtime workspace for executor containers (host path)
EXECUTOR_WORKSPACE="${WEGENT_EXECUTOR_WORKSPACE:-${HOME}/wecode-bot}"

BACKEND_PGID=""
FRONTEND_PGID=""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

usage() {
  cat <<EOF
Usage: ./start.sh [OPTIONS]

Options:
  --frontend-port PORT           Frontend port (default: ${FRONTEND_PORT})
  --backend-port PORT            Backend port (default: ${BACKEND_PORT})
  --executor-manager-port PORT   Executor Manager port (default: ${EXECUTOR_MANAGER_PORT})
  --rag                          Start Elasticsearch (RAG profile) (default: ${ENABLE_RAG})
  --no-rag                       Do not start Elasticsearch
  -h, --help                     Show help

Environment variables (optional):
  WEGENT_FRONTEND_PORT, WEGENT_BACKEND_PORT, WEGENT_EXECUTOR_MANAGER_PORT
  WEGENT_MYSQL_PORT, WEGENT_REDIS_PORT, WEGENT_ELASTICSEARCH_PORT (must match docker-compose.yml port mapping)
  WEGENT_ENABLE_RAG, WEGENT_EXECUTOR_WORKSPACE
EOF
}

die() {
  echo -e "${RED}Error: $*${NC}" >&2
  exit 1
}

have() { command -v "$1" >/dev/null 2>&1; }

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
  elif have ss; then
    pids="$(
      ss -lptn "sport = :${port}" 2>/dev/null \
        | awk 'match($0, /pid=([0-9]+)/, a) {print a[1]}' \
        | sort -u \
        | tr '\n' ' '
    )"
  else
    return 0
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
    if curl -fsS "$url" >/dev/null 2>&1; then
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

  mkdir -p "$EXECUTOR_WORKSPACE"

  echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
  echo -e "${BLUE}║          Wegent Hybrid Local Startup Script            ║${NC}"
  echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "${GREEN}Ports:${NC}"
  echo -e "  Frontend:        http://localhost:${FRONTEND_PORT}"
  echo -e "  Backend:         http://localhost:${BACKEND_PORT}"
  echo -e "  ExecutorManager: http://localhost:${EXECUTOR_MANAGER_PORT}"
  echo -e "  MySQL:           localhost:${MYSQL_PORT}"
  echo -e "  Redis:           localhost:${REDIS_PORT}"
  if [ "$ENABLE_RAG" = "true" ]; then
    echo -e "  Elasticsearch:   http://localhost:${ELASTICSEARCH_PORT}"
  fi
  echo ""

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

  local network_gateway=""
  network_gateway="$(docker network inspect wegent-network --format '{{(index .IPAM.Config 0).Gateway}}' 2>/dev/null || true)"
  if [ -z "$network_gateway" ]; then
    die "Failed to detect gateway IP for docker network 'wegent-network'."
  fi

  docker run -d \
    --name wegent-executor-manager \
    --network wegent-network \
    --network-alias executor_manager \
    --add-host host.docker.internal:host-gateway \
    -p "${EXECUTOR_MANAGER_PORT}:8001" \
    -e TZ=Asia/Shanghai \
    -e TASK_API_DOMAIN="http://${network_gateway}:${BACKEND_PORT}" \
    -e EXECUTOR_MANAGER_PORT="8001" \
    -e MAX_CONCURRENT_TASKS=30 \
    -e PORT=8001 \
    -e CALLBACK_HOST="http://executor_manager:8001" \
    -e CALLBACK_PORT="8001" \
    -e NETWORK=wegent-network \
    -e DOCKER_HOST_ADDR="host.docker.internal" \
    -e EXECUTOR_IMAGE="ghcr.io/wecode-ai/wegent-executor:1.0.28" \
    -e EXECUTOR_PORT_RANGE_MIN=10001 \
    -e EXECUTOR_PORT_RANGE_MAX=10100 \
    -e EXECUTOR_WORKSPACE="${EXECUTOR_WORKSPACE}" \
    -e EXECUTOR_WORKSPCE="${EXECUTOR_WORKSPACE}" \
    -v /var/run/docker.sock:/var/run/docker.sock \
    ghcr.io/wecode-ai/wegent-executor-manager:1.0.25 >/dev/null

  if ! wait_for_http "http://127.0.0.1:${EXECUTOR_MANAGER_PORT}/health" 60; then
    die "Executor Manager did not become healthy on port ${EXECUTOR_MANAGER_PORT}."
  fi
  echo -e "${GREEN}✓ Executor Manager is healthy${NC}"
  echo ""

  echo -e "${BLUE}[4/6] Starting Backend (host, uv)...${NC}"
  ensure_uv

  (cd "${ROOT_DIR}/backend" && uv sync)

  local backend_pythonpath=""
  backend_pythonpath="${ROOT_DIR}:${PYTHONPATH:-}"

  env \
    PYTHONPATH="${backend_pythonpath}" \
    ENVIRONMENT="development" \
    DB_AUTO_MIGRATE="True" \
    DATABASE_URL="mysql+pymysql://root:123456@127.0.0.1:${MYSQL_PORT}/task_manager" \
    REDIS_URL="redis://127.0.0.1:${REDIS_PORT}/0" \
    EXECUTOR_MANAGER_URL="http://127.0.0.1:${EXECUTOR_MANAGER_PORT}" \
    EXECUTOR_CANCEL_TASK_URL="http://127.0.0.1:${EXECUTOR_MANAGER_PORT}/executor-manager/tasks/cancel" \
    EXECUTOR_DELETE_TASK_URL="http://127.0.0.1:${EXECUTOR_MANAGER_PORT}/executor-manager/executor/delete" \
    FRONTEND_URL="http://127.0.0.1:${FRONTEND_PORT}" \
    setsid bash -c "cd '${ROOT_DIR}/backend' && exec uv run uvicorn app.main:app --host 0.0.0.0 --port '${BACKEND_PORT}'" &

  BACKEND_PGID="$!"
  echo -e "${GREEN}✓ Backend started (PGID=${BACKEND_PGID})${NC}"

  if ! wait_for_http "http://127.0.0.1:${BACKEND_PORT}/api/health" 120; then
    die "Backend did not become healthy on port ${BACKEND_PORT}."
  fi
  echo -e "${GREEN}✓ Backend is healthy${NC}"
  echo ""

  echo -e "${BLUE}[5/6] Building Frontend (npm run build)...${NC}"
  local node_major=""
  node_major="$(node --version | sed 's/^v//' | cut -d. -f1)"
  if [ "${node_major}" -lt 18 ]; then
    die "Node.js 18+ is required (found v${node_major})."
  fi

  (
    cd "${ROOT_DIR}/frontend"
    if [ ! -d node_modules ]; then
      npm install
    fi
    npm run build
  )
  echo -e "${GREEN}✓ Frontend build completed${NC}"
  echo ""

  echo -e "${BLUE}[6/6] Starting Frontend (host, npm start)...${NC}"
  env \
    NODE_ENV="production" \
    RUNTIME_INTERNAL_API_URL="http://127.0.0.1:${BACKEND_PORT}" \
    RUNTIME_SOCKET_DIRECT_URL="http://localhost:${BACKEND_PORT}" \
    setsid bash -c "cd '${ROOT_DIR}/frontend' && exec npm start -- -p '${FRONTEND_PORT}'" &

  FRONTEND_PGID="$!"
  echo -e "${GREEN}✓ Frontend started (PGID=${FRONTEND_PGID})${NC}"

  if ! wait_for_http "http://127.0.0.1:${FRONTEND_PORT}" 120; then
    die "Frontend did not become ready on port ${FRONTEND_PORT}."
  fi

  echo ""
  echo -e "${GREEN}All services are up.${NC}"
  echo -e "${GREEN}- Frontend: http://localhost:${FRONTEND_PORT}${NC}"
  echo -e "${GREEN}- Backend:  http://localhost:${BACKEND_PORT}/api/docs${NC}"
  echo -e "${GREEN}- Executor: http://localhost:${EXECUTOR_MANAGER_PORT}/health${NC}"
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

