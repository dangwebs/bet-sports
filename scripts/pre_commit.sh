#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

CANDIDATES=(
    "$ROOT_DIR/backend/.venv/bin/pre-commit"
    "$ROOT_DIR/.venv/bin/pre-commit"
    "$ROOT_DIR/backend/venv/bin/pre-commit"
    "$ROOT_DIR/venv/bin/pre-commit"
)

for candidate in "${CANDIDATES[@]}"; do
    if [[ -x "$candidate" ]]; then
        cd "$ROOT_DIR"
        exec "$candidate" "$@"
    fi
done

echo "❌ pre-commit no encontrado en un entorno virtual conocido." >&2
echo "   Revisa backend/.venv o instala pre-commit en una venv soportada." >&2
exit 1