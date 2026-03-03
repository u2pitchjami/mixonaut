#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

usage() {
    echo "Usage:"
    echo "  ./dev_scripts/patch.sh check"
    echo "  ./dev_scripts/patch.sh compile"
    echo "  ./dev_scripts/patch.sh upgrade <package>"
    echo "  ./dev_scripts/patch.sh upgrade-all"
    exit 1
}

COMMAND="${1:-}"

if [ -z "$COMMAND" ]; then
    usage
fi

check_outdated() {
    echo "🔎 Checking outdated packages..."
    if [ -d ".venv" ]; then
        # shellcheck disable=SC1091
        source .venv/bin/activate
        pip list --outdated
    else
        echo "❌ .venv not found. Run rebuild_env.sh first."
        exit 1
    fi
}

compile_all() {
    echo "🛠 Compiling runtime (hash strict)..."
    pip-compile \
        --generate-hashes \
        --allow-unsafe \
        --output-file requirements.txt \
        requirements.in

    echo "🛠 Compiling dev (no hash)..."
    pip-compile \
        --output-file requirements-dev.txt \
        requirements-dev.in
}

upgrade_package() {
    PACKAGE="$1"
    echo "⬆ Upgrading package: $PACKAGE"

    pip-compile \
        --generate-hashes \
        --allow-unsafe \
        --upgrade-package "$PACKAGE" \
        --output-file requirements.txt \
        requirements.in

    pip-compile \
        --upgrade-package "$PACKAGE" \
        --output-file requirements-dev.txt \
        requirements-dev.in
}

upgrade_all() {
    echo "⚠️  Upgrade ALL dependencies?"
    read -rp "Continue? (y/N): " CONFIRM

    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi

    pip-compile \
        --generate-hashes \
        --allow-unsafe \
        --upgrade \
        --output-file requirements.txt \
        requirements.in

    pip-compile \
        --upgrade \
        --output-file requirements-dev.txt \
        requirements-dev.in
}

run_audit() {
    echo "🔐 Running security audit (runtime only)..."
    pip-audit -r requirements.txt || true
}

case "$COMMAND" in
    check)
        check_outdated
        ;;
    compile)
        compile_all
        ;;
    upgrade)
        [ -z "${2:-}" ] && usage
        upgrade_package "$2"
        ;;
    upgrade-all)
        upgrade_all
        ;;
    *)
        usage
        ;;
esac

if [[ "$COMMAND" != "check" ]]; then
    run_audit
    echo "📋 Git diff:"
    git --no-pager diff requirements*.txt || true
    echo "✅ Patch process complete."
fi
