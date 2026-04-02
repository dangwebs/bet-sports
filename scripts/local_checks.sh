#!/usr/bin/env bash
set -uo pipefail

echo "=== RUN LOCAL CHECKS ==="
echo "USER: $(whoami)"
echo "PWD: $(pwd)"
echo "SHELL: $SHELL"
echo "PATH: $PATH"

which node || echo "NODE_NOT_FOUND"
node -v 2>/dev/null || true
which npm || echo "NPM_NOT_FOUND"
npm -v 2>/dev/null || true
which curl || echo "CURL_NOT_FOUND"
which brew || echo "BREW_NOT_FOUND"
which nvm || echo "NVM_NOT_FOUND"

# Try installing Node if missing
if ! command -v node >/dev/null 2>&1; then
  echo "Node not found — attempting installation..."
  if [ -n "${NVM_DIR:-}" ] && [ -s "$NVM_DIR/nvm.sh" ]; then
    echo "Sourcing existing NVM_DIR: $NVM_DIR"
    . "$NVM_DIR/nvm.sh"
    nvm install --lts || true
    nvm use --lts || true
  elif command -v nvm >/dev/null 2>&1; then
    echo "Using existing nvm"
    nvm install --lts || true
    nvm use --lts || true
  elif command -v brew >/dev/null 2>&1; then
    echo "Installing node via brew"
    brew install node || true
  elif command -v curl >/dev/null 2>&1 || command -v wget >/dev/null 2>&1; then
    echo "Installing nvm via install script"
    if command -v curl >/dev/null 2>&1; then
      curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash || true
    else
      wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash || true
    fi
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
    nvm install --lts || true
    nvm use --lts || true
  else
    echo "No installer available (brew/curl/wget). Cannot install Node automatically."
    exit 2
  fi
fi

echo "Post-install: node: $(command -v node || echo NONE)"
echo "node version: $(node -v 2>/dev/null || echo none)"
echo "npm version: $(npm -v 2>/dev/null || echo none)"

# Frontend steps
cd frontend || { echo "Cannot cd to frontend"; exit 3; }

echo "=== FRONTEND: npm ci ==="
npm ci --no-audit --no-fund
rc=$?
echo "npm ci exit code: $rc"


echo "=== FRONTEND: npm run build --if-present ==="
npm run build --if-present
rc=$?
echo "build exit code: $rc"


echo "=== FRONTEND: npm test --if-present ==="
npm test --if-present
rc=$?
echo "npm test exit code: $rc"

# Backend steps
cd .. || true
if [ -f .venv/bin/activate ]; then
  echo "Activating .venv"
  . .venv/bin/activate
fi

if command -v pytest >/dev/null 2>&1; then
  echo "Running pytest -q"
  pytest -q
  rc=$?
  echo "pytest exit code: $rc"
else
  echo "pytest not found in PATH; attempting to install backend requirements"
  if command -v python >/dev/null 2>&1; then
    python -m pip install -r backend/requirements.txt || true
    if command -v pytest >/dev/null 2>&1; then
      pytest -q || true
    else
      echo "pytest still not available after pip install"
    fi
  else
    echo "Python not available; skipping backend tests"
  fi
fi

echo "LOCAL CHECKS COMPLETE"
