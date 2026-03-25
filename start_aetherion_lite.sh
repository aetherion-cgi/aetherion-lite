#!/bin/bash

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR_CANDIDATES=(
  "$ROOT/.venv"
  "$ROOT/.venv311"
)

VENV_DIR=""
for candidate in "${VENV_DIR_CANDIDATES[@]}"; do
  if [ -d "$candidate" ] && [ -f "$candidate/bin/activate" ]; then
    VENV_DIR="$candidate"
    break
  fi
done

VENV=""
VENV_PYTHON=""
VENV_PIP=""
if [ -n "$VENV_DIR" ]; then
  VENV="$VENV_DIR/bin/activate"
  VENV_PYTHON="$VENV_DIR/bin/python"
  VENV_PIP="$VENV_DIR/bin/pip"
fi

LOG_DIR="$ROOT/.logs"
mkdir -p "$LOG_DIR"

CEOA_DIR_CANDIDATES=(
  "$ROOT/ceoa"
  "$ROOT/ceoa/backend"
  "$ROOT/ceoa/ceoa-fixed/backend"
)

BUE_DIR_CANDIDATES=(
  "$ROOT/bue"
  "$ROOT/bue/bue-ultimate"
  "$ROOT/bue/bue-ultimate/bue"
)

ILE_DIR_CANDIDATES=(
  "$ROOT/ile"
  "$ROOT/ile/ILE_Complete_Implementation"
)

BROKER_DIR_CANDIDATES=(
  "$ROOT/function-broker"
)

UIE_DIR_CANDIDATES=(
  "$ROOT/uie"
  "$ROOT/uie/universal-intelligence-engine/uie/api"
  "$ROOT/uie/universal-intelligence-engine"
)

log() {
  echo "$1"
}

fail() {
  echo "❌ $1" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

find_python() {
  if command -v python3.11 >/dev/null 2>&1; then
    echo "python3.11"
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    echo "python"
    return 0
  fi
  return 1
}

find_service_dir() {
  local marker="$1"
  shift
  local candidate
  for candidate in "$@"; do
    if [ -e "$candidate/$marker" ]; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

find_bue_dir() {
  local candidate
  for candidate in "$@"; do
    if [ -e "$candidate/bue/api/rest.py" ] || [ -e "$candidate/bue/api/rest/__init__.py" ]; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

kill_port() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    kill -9 $(lsof -ti:"$port") 2>/dev/null || true
  fi
}

wait_for_health() {
  local name="$1"
  local url="$2"
  local logfile="$3"
  local attempts="${4:-20}"
  local sleep_seconds="${5:-1}"

  for ((i=1; i<=attempts; i++)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      log "✅ $name is healthy"
      return 0
    fi
    sleep "$sleep_seconds"
  done

  echo ""
  echo "----- $name log tail ($logfile) -----" >&2
  if [ -f "$logfile" ]; then
    tail -n 50 "$logfile" >&2 || true
  else
    echo "(log file not found)" >&2
  fi
  echo "-------------------------------------" >&2
  fail "$name did not become healthy at $url"
}

start_service() {
  local name="$1"
  local workdir="$2"
  local command="$3"
  local logfile="$4"

  [ -d "$workdir" ] || fail "$name directory not found: $workdir"

  log "$name"
  (
    cd "$workdir"
    source "$VENV"
    eval "$command"
  ) >"$logfile" 2>&1 &
}

require_command curl
PYTHON_CMD="$(find_python)" || fail "Missing required command: python3.11, python3, or python"

if [ -z "$VENV" ]; then
  fail "No local virtual environment found. Run ./install_lite.sh first to create one under .venv or .venv311"
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  log "⚠️ This Lite bundle is currently optimized for macOS local use."
fi

if [[ "$(uname -m)" == "arm64" ]]; then
  log "🍎 Apple Silicon detected"
fi
log "🐍 Using virtual environment: $VENV_DIR"

CEOA_DIR="$(find_service_dir "main.py" "${CEOA_DIR_CANDIDATES[@]}")" || fail "Unable to locate CEOA entrypoint (main.py). Checked: ${CEOA_DIR_CANDIDATES[*]}"
BUE_DIR="$(find_bue_dir "${BUE_DIR_CANDIDATES[@]}")" || fail "Unable to locate BUE entrypoint (bue/api/rest.py or bue/api/rest/__init__.py). Checked: ${BUE_DIR_CANDIDATES[*]}"
ILE_DIR="$(find_service_dir "ile_system/api/main.py" "${ILE_DIR_CANDIDATES[@]}")" || fail "Unable to locate ILE entrypoint (ile_system/api/main.py). Checked: ${ILE_DIR_CANDIDATES[*]}"
BROKER_DIR="$(find_service_dir "broker/api/main.py" "${BROKER_DIR_CANDIDATES[@]}")" || fail "Unable to locate Function Broker entrypoint (broker/api/main.py). Checked: ${BROKER_DIR_CANDIDATES[*]}"
UIE_DIR="$(find_service_dir "uie/api/gateway.py" "${UIE_DIR_CANDIDATES[@]}")" || fail "Unable to locate UIE entrypoint (uie/api/gateway.py). Checked: ${UIE_DIR_CANDIDATES[*]}"

log "📁 CEOA dir:   $CEOA_DIR"
log "📁 BUE dir:    $BUE_DIR"
log "📁 ILE dir:    $ILE_DIR"
log "📁 Broker dir: $BROKER_DIR"
log "📁 UIE dir:    $UIE_DIR"

[ -d "$CEOA_DIR" ] || fail "Missing CEOA directory: $CEOA_DIR"
[ -d "$BUE_DIR" ] || fail "Missing BUE directory: $BUE_DIR"
[ -d "$ILE_DIR" ] || fail "Missing ILE directory: $ILE_DIR"
[ -d "$BROKER_DIR" ] || fail "Missing Function Broker directory: $BROKER_DIR"
[ -d "$UIE_DIR" ] || fail "Missing UIE directory: $UIE_DIR"

log "🚨 Cleaning existing Lite services..."
kill_port 8000
kill_port 8081
kill_port 9000
kill_port 7100
kill_port 7400

sleep 1

log "🚀 Starting Aetherion Lite..."

# === CEOA (7100) ===
start_service \
  "⚡ Starting CEOA..." \
  "$CEOA_DIR" \
  "export PYTHONPATH=\"$CEOA_DIR\" && export CEOA_LOCAL_MODE=true && python -m uvicorn main:app --host 127.0.0.1 --port 7100" \
  "$LOG_DIR/ceoa.log"

# === BUE (9000) ===
start_service \
  "💼 Starting BUE..." \
  "$BUE_DIR" \
  "export PYTHONPATH=\"$BUE_DIR\" && python -m uvicorn bue.api.rest:app --host 127.0.0.1 --port 9000" \
  "$LOG_DIR/bue.log"

# === ILE (7400) ===
start_service \
  "🧠 Starting ILE..." \
  "$ILE_DIR" \
  "export PYTHONPATH=\"$ILE_DIR\" && export ILE_LOCAL_MODE=true && python -m uvicorn ile_system.api.main:app --host 127.0.0.1 --port 7400" \
  "$LOG_DIR/ile.log"

# === FUNCTION BROKER (8081) ===
start_service \
  "🔗 Starting Function Broker..." \
  "$BROKER_DIR" \
  "export PYTHONPATH=\"$BROKER_DIR\" && python -m uvicorn broker.api.main:app --host 127.0.0.1 --port 8081" \
  "$LOG_DIR/broker.log"

# === UIE (8000) ===
start_service \
  "🌐 Starting UIE..." \
  "$UIE_DIR" \
  "export PYTHONPATH=\"$UIE_DIR\" && python -m uvicorn uie.api.gateway:app --host 127.0.0.1 --port 8000" \
  "$LOG_DIR/uie.log"

wait_for_health "CEOA" "http://127.0.0.1:7100/health" "$LOG_DIR/ceoa.log"
wait_for_health "BUE" "http://127.0.0.1:9000/health" "$LOG_DIR/bue.log"
wait_for_health "ILE" "http://127.0.0.1:7400/health" "$LOG_DIR/ile.log"
wait_for_health "Function Broker" "http://127.0.0.1:8081/health" "$LOG_DIR/broker.log"
wait_for_health "UIE" "http://127.0.0.1:8000/health" "$LOG_DIR/uie.log"

log ""
log "✅ AETHERION LITE ONLINE"
log "-----------------------------------"
log "UIE:    http://127.0.0.1:8000"
log "Broker: http://127.0.0.1:8081"
log "BUE:    http://127.0.0.1:9000"
log "CEOA:   http://127.0.0.1:7100"
log "ILE:    http://127.0.0.1:7400"
log "-----------------------------------"
log ""
log "Logs:   $LOG_DIR"
log "Downloaded from GitHub? Run from the repo root like this:"
log "  chmod +x ./install_lite.sh ./start_aetherion_lite.sh"
log "  ./install_lite.sh"
log "  ./start_aetherion_lite.sh"