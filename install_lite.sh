#!/bin/bash

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$ROOT/.venv"

log() {
  echo "$1"
}

fail() {
  echo "❌ $1" >&2
  exit 1
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

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

PYTHON_CMD="$(find_python)" || fail "Missing required command: python3.11, python3, or python"
require_command curl

if [[ "$(uname -s)" != "Darwin" ]]; then
  log "⚠️ This Lite installer is currently optimized for macOS."
fi

if [[ "$(uname -m)" == "arm64" ]]; then
  log "🍎 Apple Silicon detected"
fi

log "📦 Creating local virtual environment..."
"$PYTHON_CMD" -m venv "$VENV_DIR"

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip setuptools wheel

log "📚 Installing core runtime dependencies..."
python -m pip install \
  "fastapi==0.103.2" \
  "pydantic==1.10.24" \
  "starlette<0.28" \
  "uvicorn[standard]" \
  "httpx" \
  "PyYAML" \
  "asyncpg" \
  "neo4j" \
  "redis" \
  "numpy" \
  "scikit-learn" \
  "scipy" \
  "pytest" \
  "pytest-asyncio" \
  "pytest-cov" \
  "black" \
  "flake8" \
  "isort" \
  "mypy" \
  "joblib" \
  "psutil" \
  "loguru" \
  "redis-om" \
  "threadpoolctl" \
  "psutil" \
  "loguru" \
  "python-dotenv" \
  "pandas" 


log ""
log "✅ AETHERION LITE INSTALL COMPLETE"
log "-----------------------------------"
log "Virtual environment: $VENV_DIR"
log ""
log "Next steps:"
log "  chmod +x ./start_aetherion_lite.sh"
log "  ./start_aetherion_lite.sh"