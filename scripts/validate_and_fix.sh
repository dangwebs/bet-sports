#!/usr/bin/env bash
# scripts/validate_and_fix.sh
# Script to auto-format, lint (auto-fix), and run tests before pushing.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRE_COMMIT_WRAPPER="$SCRIPT_DIR/pre_commit.sh"

# --- DETECCIÓN DE ENTORNO VIRTUAL ---
VENV_PATHS=(".venv" "venv" "backend/.venv" "backend/venv")
VENV_ACTIVATE=""

for path in "${VENV_PATHS[@]}"; do
    if [ -f "$path/bin/activate" ]; then
        VENV_ACTIVATE="$path/bin/activate"
        break
    fi
done

if [ -n "$VENV_ACTIVATE" ]; then
    echo "🐍 Activando entorno virtual desde $VENV_ACTIVATE..."
    source "$VENV_ACTIVATE"
fi
# ------------------------------------

echo "============================================="
echo "🛠️  Paso 1: Detectando y corrigiendo formato y linting (Auto-fix)..."
echo "============================================="

# Si existe el wrapper repo-local, lo usamos como fuente de verdad.
if [ -x "$PRE_COMMIT_WRAPPER" ]; then
    echo "Running pre-commit via repo wrapper..."
    "$PRE_COMMIT_WRAPPER" run --all-files || echo "⚠️  pre-commit modificó archivos. Por favor haz un commit con estos cambios."
elif command -v pre-commit &> /dev/null; then
    echo "Running pre-commit..."
    pre-commit run --all-files || echo "⚠️  pre-commit modificó archivos. Por favor haz un commit con estos cambios."
else
    echo "⚠️  pre-commit no encontrado, intentando herramientas individuales..."
    
    # Intenta usar black y ruff si están disponibles (backend)
    if [ -d "backend" ]; then
        cd backend
        echo "Corriendo Black..."
        python3 -m black src/ tests/ || echo "❌ Falló Black. Asegúrate de tenerlo instalado."
        echo "Corriendo Ruff (auto-fix)..."
        python3 -m ruff check --fix src/ tests/ || echo "⚠️  Ruff no encontrado o falló."
        
        echo "Corriendo Mypy (Types)..."
        python3 -m mypy src/ --ignore-missing-imports --follow-imports=skip || { echo "❌ Mypy detectó errores. Por favor corrígelos antes de subir."; exit 1; }
        cd ..
    fi

    # Intenta usar prettier y eslint (frontend)
    if [ -d "frontend" ]; then
        cd frontend
        if command -v npm &> /dev/null; then
            echo "Corriendo Lint del Frontend (fix)..."
            npm run lint -- --fix || echo "⚠️  Lint del frontend falló."
        fi
        cd ..
    fi
fi

echo ""
echo "============================================="
echo "🧪 Paso 2: Ejecutando suite de tests (Backend)..."
echo "============================================="
if [ -d "backend" ]; then
    cd backend
    export PYTHONPATH=.
    echo "Corriendo Pytest..."
    python3 -m pytest tests/ -q
    cd ..
else
    echo "Carpeta backend no encontrada, omitiendo tests de python."
fi

echo ""
echo "============================================="
echo "✅ Todo en orden. El código está listo para subirse (push)."
echo "============================================="
