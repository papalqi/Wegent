#!/usr/bin/env bash
set -euo pipefail

# Host-only dev runner:
# - Restarts backend + frontend on the host
# - Does NOT start/stop any Docker containers
# - Safe for iterative development (hot reload in --dev mode)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

have() { command -v "$1" >/dev/null 2>&1; }

die() {
  echo "Error: $*" >&2
  exit 1
}

usage() {
  cat <<EOF
Usage: ./scripts/dev-host.sh [--dev|--prod] [--backend-port PORT] [--frontend-port PORT]

This script restarts Backend + Frontend on the host and keeps Docker services untouched.

Modes:
  --dev   Start with hot reload (backend --reload, frontend next dev) [default]
  --prod  Build frontend and start production servers (backend no reload, frontend next start)

Systemd:
  If wegent.service is running, this script will take over by stopping it with SIGKILL
  (to avoid triggering start.sh cleanup that would stop Docker containers). Disable this
  behavior with --no-systemd-takeover.

Environment:
  Reads (lowest precedence first): .env.defaults, .env, .env.local
  Respects already-exported variables (does not override).
EOF
}

# Load env files without overriding existing env vars.
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

MODE="dev"
BACKEND_PORT="${WEGENT_BACKEND_PORT:-8000}"
FRONTEND_PORT="${WEGENT_FRONTEND_PORT:-3000}"
FRONTEND_HOST="${WEGENT_FRONTEND_HOST:-0.0.0.0}"
EXECUTOR_MANAGER_PORT="${WEGENT_EXECUTOR_MANAGER_PORT:-8001}"
MYSQL_PORT="${WEGENT_MYSQL_PORT:-3306}"
REDIS_PORT="${WEGENT_REDIS_PORT:-6379}"

RUN_DIR="${ROOT_DIR}/logs/dev-host"
BACKEND_LOG="${RUN_DIR}/backend.log"
FRONTEND_LOG="${RUN_DIR}/frontend.log"
BACKEND_PID_FILE="${RUN_DIR}/backend.pid"
FRONTEND_PID_FILE="${RUN_DIR}/frontend.pid"

BACKEND_PGID=""
FRONTEND_PGID=""
CLEANUP_ARMED="false"
SYSTEMD_TAKEOVER="true"
TOOK_OVER_SYSTEMD="false"
ORIGINAL_SYSTEMD_RESTART=""

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

pid_is_docker_proxy() {
  local pid="$1"
  local comm=""
  comm="$(ps -p "$pid" -o comm= 2>/dev/null | awk '{print $1}' || true)"
  [ "$comm" = "docker-proxy" ]
}

kill_listen_port() {
  local port="$1"
  local pids=""

  if have lsof; then
    pids="$(lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true)"
  fi
  if [ -z "$pids" ] && have ss; then
    pids="$(
      ss -lptn "sport = :${port}" 2>/dev/null \
        | awk 'match($0, /pid=([0-9]+)/, a) {print a[1]}' \
        | sort -u \
        | tr '\n' ' '
    )"
  fi

  if [ -z "$pids" ]; then
    return 0
  fi

  for pid in $pids; do
    if pid_is_docker_proxy "$pid"; then
      die "Port ${port} is published by docker-proxy (a Docker container). Refusing to kill it. Stop the container or change port."
    fi
  done

  echo "Killing process(es) listening on port ${port}: ${pids}"
  # shellcheck disable=SC2086
  kill -TERM ${pids} >/dev/null 2>&1 || true
  sleep 1
  # shellcheck disable=SC2086
  kill -KILL ${pids} >/dev/null 2>&1 || true
}

stop_from_pidfile() {
  local pid_file="$1"
  if [ ! -f "$pid_file" ]; then
    return 0
  fi
  local pgid=""
  pgid="$(cat "$pid_file" 2>/dev/null || true)"
  if [[ "$pgid" =~ ^[0-9]+$ ]]; then
    kill_process_group "$pgid"
  fi
  rm -f "$pid_file" >/dev/null 2>&1 || true
}

wait_for_http() {
  local url="$1"
  local timeout_sec="$2"
  local start_ts
  start_ts="$(date +%s)"

  while true; do
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
  echo "Stopping host services..."
  kill_process_group "$FRONTEND_PGID"
  kill_process_group "$BACKEND_PGID"
  stop_from_pidfile "$FRONTEND_PID_FILE"
  stop_from_pidfile "$BACKEND_PID_FILE"

  if [ "$TOOK_OVER_SYSTEMD" = "true" ] && have systemctl; then
    if [ -n "$ORIGINAL_SYSTEMD_RESTART" ]; then
      systemctl set-property wegent.service "Restart=${ORIGINAL_SYSTEMD_RESTART}" >/dev/null 2>&1 || true
    else
      systemctl set-property wegent.service Restart=on-failure >/dev/null 2>&1 || true
    fi
    systemctl reset-failed wegent.service >/dev/null 2>&1 || true
  fi

  exit "$exit_code"
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

ensure_no_systemd_runner() {
  if ! have systemctl; then
    return 0
  fi
  if ! systemctl is-active --quiet wegent.service; then
    return 0
  fi

  if [ "$SYSTEMD_TAKEOVER" != "true" ]; then
    die "wegent.service is running. Stop it first, or re-run without --no-systemd-takeover."
  fi

  echo "Detected wegent.service running; taking over host ports without touching Docker..."
  ORIGINAL_SYSTEMD_RESTART="$(systemctl show -p Restart --value wegent.service 2>/dev/null || true)"
  if [ -z "$ORIGINAL_SYSTEMD_RESTART" ]; then
    ORIGINAL_SYSTEMD_RESTART="on-failure"
  fi

  # Prevent auto-restart while we develop.
  systemctl set-property wegent.service Restart=no >/dev/null 2>&1 || true

  # Kill the service cgroup without running start.sh cleanup (SIGKILL bypasses traps).
  systemctl kill -s SIGKILL wegent.service >/dev/null 2>&1 || true

  local i
  for i in {1..20}; do
    if ! systemctl is-active --quiet wegent.service; then
      break
    fi
    sleep 0.5
  done

  systemctl reset-failed wegent.service >/dev/null 2>&1 || true
  TOOK_OVER_SYSTEMD="true"
}

main() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dev)
        MODE="dev"
        shift
        ;;
      --prod)
        MODE="prod"
        shift
        ;;
      --no-systemd-takeover)
        SYSTEMD_TAKEOVER="false"
        shift
        ;;
      --backend-port)
        BACKEND_PORT="$2"
        shift 2
        ;;
      --frontend-port)
        FRONTEND_PORT="$2"
        shift 2
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

  ensure_no_systemd_runner

  mkdir -p "$RUN_DIR"
  : >"$BACKEND_LOG"
  : >"$FRONTEND_LOG"

  CLEANUP_ARMED="true"

  echo "[1/3] Stopping existing host services (backend/frontend)..."
  stop_from_pidfile "$FRONTEND_PID_FILE"
  stop_from_pidfile "$BACKEND_PID_FILE"
  kill_listen_port "$FRONTEND_PORT"
  kill_listen_port "$BACKEND_PORT"
  echo "✓ Host ports are free"
  echo ""

  : "${DATABASE_URL:=mysql+pymysql://root:123456@127.0.0.1:${MYSQL_PORT}/task_manager}"
  : "${REDIS_URL:=redis://127.0.0.1:${REDIS_PORT}/0}"
  : "${EXECUTOR_MANAGER_URL:=http://127.0.0.1:${EXECUTOR_MANAGER_PORT}}"
  : "${EXECUTOR_CANCEL_TASK_URL:=http://127.0.0.1:${EXECUTOR_MANAGER_PORT}/executor-manager/tasks/cancel}"
  : "${EXECUTOR_DELETE_TASK_URL:=http://127.0.0.1:${EXECUTOR_MANAGER_PORT}/executor-manager/executor/delete}"

  echo "[2/3] Starting Backend (host, uvicorn${MODE:+, ${MODE}})..."
  (cd "${ROOT_DIR}/backend" && uv sync)

  local backend_args=(app.main:app --host 0.0.0.0 --port "${BACKEND_PORT}")
  if [ "$MODE" = "dev" ]; then
    backend_args+=(--reload)
  fi

  env \
    PYTHONPATH="${ROOT_DIR}:${PYTHONPATH:-}" \
    ENVIRONMENT="development" \
    DB_AUTO_MIGRATE="True" \
    DATABASE_URL="${DATABASE_URL}" \
    REDIS_URL="${REDIS_URL}" \
    EXECUTOR_MANAGER_URL="${EXECUTOR_MANAGER_URL}" \
    EXECUTOR_CANCEL_TASK_URL="${EXECUTOR_CANCEL_TASK_URL}" \
    EXECUTOR_DELETE_TASK_URL="${EXECUTOR_DELETE_TASK_URL}" \
    FRONTEND_URL="http://127.0.0.1:${FRONTEND_PORT}" \
    sh -c "cd '${ROOT_DIR}/backend' && exec uv run uvicorn ${backend_args[*]}" >>"$BACKEND_LOG" 2>&1 &

  BACKEND_PGID="$!"
  echo "$BACKEND_PGID" >"$BACKEND_PID_FILE"
  echo "✓ Backend started (PGID=${BACKEND_PGID})"
  echo "  Backend log: ${BACKEND_LOG}"

  if ! wait_for_http "http://127.0.0.1:${BACKEND_PORT}/api/health" 120; then
    die "Backend did not become ready on port ${BACKEND_PORT}. Check ${BACKEND_LOG}"
  fi
  echo "✓ Backend is healthy"
  echo ""

  echo "[3/3] Starting Frontend (host, next ${MODE})..."
  (
    cd "${ROOT_DIR}/frontend"
    if [ ! -d node_modules ]; then
      npm install
    fi
    if [ "$MODE" = "prod" ]; then
      npm run build
    fi
  )

  if [ "$MODE" = "dev" ]; then
    env \
      NODE_ENV="development" \
      PORT="${FRONTEND_PORT}" \
      RUNTIME_INTERNAL_API_URL="http://127.0.0.1:${BACKEND_PORT}" \
      RUNTIME_SOCKET_DIRECT_URL="http://127.0.0.1:${BACKEND_PORT}" \
      sh -c "cd '${ROOT_DIR}/frontend' && exec npm run dev -- -p '${FRONTEND_PORT}' -H '${FRONTEND_HOST}'" >>"$FRONTEND_LOG" 2>&1 &
  else
    env \
      NODE_ENV="production" \
      RUNTIME_INTERNAL_API_URL="http://127.0.0.1:${BACKEND_PORT}" \
      RUNTIME_SOCKET_DIRECT_URL="http://127.0.0.1:${BACKEND_PORT}" \
      sh -c "cd '${ROOT_DIR}/frontend' && exec npm start -- -p '${FRONTEND_PORT}' -H '${FRONTEND_HOST}'" >>"$FRONTEND_LOG" 2>&1 &
  fi

  FRONTEND_PGID="$!"
  echo "$FRONTEND_PGID" >"$FRONTEND_PID_FILE"
  echo "✓ Frontend started (PGID=${FRONTEND_PGID})"
  echo "  Frontend log: ${FRONTEND_LOG}"

  if ! wait_for_http "http://127.0.0.1:${FRONTEND_PORT}" 120; then
    die "Frontend did not become ready on port ${FRONTEND_PORT}. Check ${FRONTEND_LOG}"
  fi
  echo "✓ Frontend is ready"

  echo ""
  echo "All host services are up (Docker untouched)."
  echo "- Frontend: http://127.0.0.1:${FRONTEND_PORT}"
  echo "- Backend:  http://127.0.0.1:${BACKEND_PORT}/api/docs"
  echo ""
  echo "Press Ctrl+C to stop backend/frontend (will NOT stop Docker)."

  wait -n "$BACKEND_PGID" "$FRONTEND_PGID"
  die "A host service exited unexpectedly. Check ${BACKEND_LOG} / ${FRONTEND_LOG}"
}

main "$@"
