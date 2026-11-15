#!/usr/bin/env bash
set -euo pipefail
APP_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

find_python() {
  for candidate in \
    "$APP_ROOT/.venv/bin/python" \
    "$APP_ROOT/.venv/Scripts/python.exe" \
    "$(command -v python3 2>/dev/null || true)" \
    "$(command -v python 2>/dev/null || true)" \
    "/c/Python314/python.exe" \
    "/c/Python313/python.exe" \
    "/c/Python312/python.exe"
  do
    if [ -n "$candidate" ] && [ -x "$candidate" ] && "$candidate" --version >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

PYTHON_BIN="$(find_python || true)"
if [ -z "$PYTHON_BIN" ]; then
  echo "Error: Python 3.12+ is required. Install Python or create .venv first." >&2
  exit 1
fi

exec "$PYTHON_BIN" "$APP_ROOT/scripts/run.py" "$@"
