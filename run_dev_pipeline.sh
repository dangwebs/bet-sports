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

# 1. Train
echo -e "\n${BLUE}🧠 Step 1: Training Model (Days: 550)...${NC}"
backend/.venv/bin/python backend/scripts/orchestrator_cli.py train --days=550

# 2. Predict
echo -e "\n${BLUE}🔮 Step 2: Generating Predictions (Parallel)...${NC}"
# Top Tier Leagues
backend/.venv/bin/python backend/scripts/orchestrator_cli.py predict --leagues=E0,SP1,D1,I1,F1,P1

# 3. Top Picks
echo -e "\n${BLUE}🏆 Step 3: Generating Top Validation Picks...${NC}"
backend/.venv/bin/python backend/scripts/orchestrator_cli.py top-picks

echo -e "\n${GREEN}✅ Pipeline Completed Successfully!${NC}"
echo "=================================================="
