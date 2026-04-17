#!/usr/bin/env bash
# =============================================================================
# daily_training.sh — Automated daily ML training via Docker Compose
#
# Called by macOS launchd (LaunchAgent) every day at 06:00 COT.
# Logs output to ~/Library/Logs/bjj-betsports/
#
# Usage (manual):
#   ./scripts/daily_training.sh
#
# The script:
#   1. Verifies Docker is running (waits up to 2 minutes)
#   2. Ensures MongoDB is healthy
#   3. Runs the MLOps pipeline (train → predict → top-picks)
#   4. Logs everything with automatic log rotation (keeps 7 days)
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${HOME}/Library/Logs/bjj-betsports"
LOG_FILE="${LOG_DIR}/training_$(date +%Y-%m-%d).log"
MAX_LOG_DAYS=7
DOCKER_WAIT_SECONDS=120
DOCKER_CHECK_INTERVAL=5

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------
mkdir -p "${LOG_DIR}"

log() {
  local timestamp
  timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
  echo "[${timestamp}] $*" | tee -a "${LOG_FILE}"
}

rotate_logs() {
  find "${LOG_DIR}" -name "training_*.log" -mtime "+${MAX_LOG_DAYS}" -delete 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
rotate_logs

log "=========================================="
log "🚀 BJJ-BetSports Daily Training Started"
log "=========================================="
log "📂 Project: ${PROJECT_DIR}"

# Verify project directory
if [ ! -f "${PROJECT_DIR}/docker-compose.dev.yml" ]; then
  log "❌ FATAL: docker-compose.dev.yml not found in ${PROJECT_DIR}"
  exit 1
fi

cd "${PROJECT_DIR}"

# Wait for Docker daemon
log "🐳 Checking Docker daemon..."
elapsed=0
while ! docker info >/dev/null 2>&1; do
  if [ "${elapsed}" -ge "${DOCKER_WAIT_SECONDS}" ]; then
    log "❌ FATAL: Docker daemon not available after ${DOCKER_WAIT_SECONDS}s"
    exit 1
  fi
  log "⏳ Docker not ready, retrying in ${DOCKER_CHECK_INTERVAL}s... (${elapsed}/${DOCKER_WAIT_SECONDS}s)"
  sleep "${DOCKER_CHECK_INTERVAL}"
  elapsed=$((elapsed + DOCKER_CHECK_INTERVAL))
done
log "✅ Docker daemon is running"

# ---------------------------------------------------------------------------
# Execute pipeline
# ---------------------------------------------------------------------------
log "🐳 Step 1/3: Starting MongoDB..."
if ! docker compose -f docker-compose.dev.yml up -d mongodb 2>&1 | tee -a "${LOG_FILE}"; then
  log "❌ FATAL: Failed to start MongoDB"
  exit 1
fi

# Wait for MongoDB to be healthy
log "⏳ Waiting for MongoDB to be healthy..."
mongo_wait=0
mongo_max=60
while [ "${mongo_wait}" -lt "${mongo_max}" ]; do
  health=$(docker inspect --format='{{.State.Health.Status}}' bjj-mongo-dev 2>/dev/null || echo "unknown")
  if [ "${health}" = "healthy" ]; then
    break
  fi
  sleep 3
  mongo_wait=$((mongo_wait + 3))
done

if [ "${health}" != "healthy" ]; then
  log "❌ FATAL: MongoDB did not become healthy after ${mongo_max}s (status: ${health})"
  exit 1
fi
log "✅ MongoDB is healthy"

log "🚀 Step 2/3: Running MLOps pipeline..."
pipeline_start=$(date +%s)

if docker compose -f docker-compose.dev.yml --profile mlops run --rm mlops-pipeline 2>&1 | tee -a "${LOG_FILE}"; then
  pipeline_end=$(date +%s)
  duration=$(( pipeline_end - pipeline_start ))
  log "✅ Step 3/3: Pipeline completed successfully in ${duration}s"
else
  pipeline_end=$(date +%s)
  duration=$(( pipeline_end - pipeline_start ))
  log "❌ Pipeline FAILED after ${duration}s"
  exit 1
fi

log "=========================================="
log "🏁 Daily Training Finished"
log "=========================================="
