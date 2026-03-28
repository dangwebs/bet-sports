#!/usr/bin/env bash
set -euo pipefail

TRAIN_DAYS="${TRAIN_DAYS:-550}"
N_JOBS="${N_JOBS:-2}"
PREDICT_LEAGUES="${PREDICT_LEAGUES:-E0,SP1,D1,I1,F1,P1,B1,UCL}"
TOP_PICKS_LIMIT="${TOP_PICKS_LIMIT:-50}"

echo "🚀 Iniciando pipeline MLOps local dentro de contenedor"
echo "📦 TRAIN_DAYS=${TRAIN_DAYS} | N_JOBS=${N_JOBS}"
echo "🎯 PREDICT_LEAGUES=${PREDICT_LEAGUES}"

python scripts/orchestrator_cli.py cleanup
python scripts/orchestrator_cli.py train --days "${TRAIN_DAYS}" --n-jobs "${N_JOBS}" --leagues "${PREDICT_LEAGUES}"
python scripts/orchestrator_cli.py predict --leagues "${PREDICT_LEAGUES}" --parallel
python scripts/orchestrator_cli.py top-picks --limit "${TOP_PICKS_LIMIT}" --leagues "${PREDICT_LEAGUES}"

echo "✅ Pipeline MLOps local completado"
