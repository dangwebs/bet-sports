#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Local Dev MLOps Pipeline...${NC}"
echo "=================================================="

# Ensure we are in the project root
if [ ! -d "backend" ]; then
    echo -e "${RED}❌ Error: Please run this script from the project root (BJJ-BetSports/)${NC}"
    exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker is required to run the portable local pipeline${NC}"
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker Compose v2 is required${NC}"
    exit 1
fi

# Use all host CPUs by default unless user overrides N_JOBS
HOST_CPUS=$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)
export N_JOBS="${N_JOBS:-$HOST_CPUS}"
export TRAIN_DAYS="${TRAIN_DAYS:-550}"
export PREDICT_LEAGUES="${PREDICT_LEAGUES:-E0,SP1,D1,I1,F1,P1,B1,UCL}"

echo -e "${BLUE}🧠 Host resources detected: ${N_JOBS} CPU threads${NC}"
echo -e "${BLUE}📅 Training window: ${TRAIN_DAYS} days${NC}"
echo -e "${BLUE}⚽ Leagues: ${PREDICT_LEAGUES}${NC}"

echo -e "\n${BLUE}🐳 Step 1: Starting MongoDB dependency...${NC}"
docker compose -f docker-compose.dev.yml up -d mongodb

echo -e "\n${BLUE}🚀 Step 2: Running portable MLOps pipeline in Docker...${NC}"
docker compose -f docker-compose.dev.yml --profile mlops run --rm mlops-pipeline

echo -e "\n${GREEN}✅ Pipeline Completed Successfully!${NC}"
echo "=================================================="
