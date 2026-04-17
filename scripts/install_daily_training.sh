#!/usr/bin/env bash
# =============================================================================
# install_daily_training.sh — Install/uninstall the daily training LaunchAgent
#
# Usage:
#   ./scripts/install_daily_training.sh            # Install
#   ./scripts/install_daily_training.sh --uninstall # Uninstall
#   ./scripts/install_daily_training.sh --status    # Check status
# =============================================================================
set -euo pipefail

LABEL="com.bjj-betsports.daily-training"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_TEMPLATE="${PROJECT_DIR}/scripts/launchd/${LABEL}.plist"
PLIST_DEST="${HOME}/Library/LaunchAgents/${LABEL}.plist"
LOG_DIR="${HOME}/Library/Logs/bjj-betsports"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------------
if [ "${1:-}" = "--uninstall" ]; then
  echo -e "${BLUE}🗑️  Uninstalling daily training LaunchAgent...${NC}"

  if launchctl list "${LABEL}" >/dev/null 2>&1; then
    launchctl unload "${PLIST_DEST}" 2>/dev/null || true
    echo -e "${GREEN}✅ LaunchAgent unloaded${NC}"
  fi

  if [ -f "${PLIST_DEST}" ]; then
    rm -f "${PLIST_DEST}"
    echo -e "${GREEN}✅ Plist removed from ${PLIST_DEST}${NC}"
  else
    echo -e "${YELLOW}⚠️  Plist not found (already removed?)${NC}"
  fi

  echo -e "${GREEN}🏁 Uninstall complete${NC}"
  exit 0
fi

# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------
if [ "${1:-}" = "--status" ]; then
  echo -e "${BLUE}📊 Daily Training LaunchAgent Status${NC}"
  echo "──────────────────────────────────────"

  if [ -f "${PLIST_DEST}" ]; then
    echo -e "Plist installed: ${GREEN}✅ Yes${NC}"
  else
    echo -e "Plist installed: ${RED}❌ No${NC}"
    exit 1
  fi

  if launchctl list "${LABEL}" >/dev/null 2>&1; then
    echo -e "LaunchAgent loaded: ${GREEN}✅ Yes${NC}"
    # Show last exit status
    status=$(launchctl list "${LABEL}" 2>/dev/null | grep -o '"LastExitStatus" = [0-9]*' | grep -o '[0-9]*' || echo "unknown")
    echo -e "Last exit status: ${status}"
  else
    echo -e "LaunchAgent loaded: ${RED}❌ No${NC}"
  fi

  # Show last log
  latest_log=$(ls -t "${LOG_DIR}"/training_*.log 2>/dev/null | head -1 || true)
  if [ -n "${latest_log}" ]; then
    echo -e "\nLatest log: ${latest_log}"
    echo "Last 5 lines:"
    tail -5 "${latest_log}"
  else
    echo -e "\n${YELLOW}No training logs found yet${NC}"
  fi

  exit 0
fi

# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------
echo -e "${BLUE}🔧 Installing BJJ-BetSports Daily Training LaunchAgent${NC}"
echo "════════════════════════════════════════════════════════"

# Verify template exists
if [ ! -f "${PLIST_TEMPLATE}" ]; then
  echo -e "${RED}❌ FATAL: Plist template not found at ${PLIST_TEMPLATE}${NC}"
  exit 1
fi

# Create log directory
mkdir -p "${LOG_DIR}"

# Make training script executable
chmod +x "${PROJECT_DIR}/scripts/daily_training.sh"
echo -e "${GREEN}✅ Training script marked as executable${NC}"

# Unload existing agent if present
if launchctl list "${LABEL}" >/dev/null 2>&1; then
  echo -e "${YELLOW}⚠️  Existing agent found, unloading first...${NC}"
  launchctl unload "${PLIST_DEST}" 2>/dev/null || true
fi

# Generate plist with correct paths
mkdir -p "$(dirname "${PLIST_DEST}")"
sed -e "s|__PROJECT_DIR__|${PROJECT_DIR}|g" \
    -e "s|__HOME__|${HOME}|g" \
    "${PLIST_TEMPLATE}" > "${PLIST_DEST}"
echo -e "${GREEN}✅ Plist installed to ${PLIST_DEST}${NC}"

# Load the agent
launchctl load "${PLIST_DEST}"
echo -e "${GREEN}✅ LaunchAgent loaded${NC}"

# Verify
if launchctl list "${LABEL}" >/dev/null 2>&1; then
  echo -e "\n${GREEN}🎉 Installation successful!${NC}"
else
  echo -e "\n${RED}❌ LaunchAgent failed to load. Check: launchctl list | grep bjj${NC}"
  exit 1
fi

echo ""
echo -e "${BLUE}📋 Summary:${NC}"
echo "  Schedule:    Every day at 06:00 (local time)"
echo "  Script:      ${PROJECT_DIR}/scripts/daily_training.sh"
echo "  Logs:        ${LOG_DIR}/"
echo "  Plist:       ${PLIST_DEST}"
echo ""
echo -e "${BLUE}📌 Useful commands:${NC}"
echo "  Check status:    ./scripts/install_daily_training.sh --status"
echo "  Manual run:      ./scripts/daily_training.sh"
echo "  Uninstall:       ./scripts/install_daily_training.sh --uninstall"
echo "  View logs:       tail -f ~/Library/Logs/bjj-betsports/training_\$(date +%Y-%m-%d).log"
