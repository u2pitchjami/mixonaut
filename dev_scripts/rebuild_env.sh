#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PY_VERSION="$(tr -d ' \t\r\n' < .python-version)"
PY_BIN="python${PY_VERSION}"
VENV_PATH=".venv"

if ! command -v "$PY_BIN" >/dev/null 2>&1; then
    echo "❌ $PY_BIN not found."
    exit 1
fi

echo "🐍 Using $PY_BIN"
echo "🧱 Rebuilding virtual environment..."

rm -rf "$VENV_PATH"
"$PY_BIN" -m venv "$VENV_PATH"

# shellcheck disable=SC1091
source "$VENV_PATH/bin/activate"

python -m pip install -U pip

if [ -f "requirements.txt" ]; then
    python -m pip install -r requirements.txt
fi

if [ -f "requirements-dev.txt" ]; then
    python -m pip install -r requirements-dev.txt
fi

if [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
    echo "📦 Installing project in editable mode..."
    python -m pip install -e .
fi

echo "✅ Environment ready."
