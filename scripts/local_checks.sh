#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Delegating to scripts/quality_gate.sh (source of truth)"
exec "$SCRIPT_DIR/quality_gate.sh" all
