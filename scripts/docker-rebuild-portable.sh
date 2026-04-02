#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f "docker-compose.dev.yml" ]]; then
  echo "Error: ejecuta este script desde la raiz del repositorio."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: Docker no esta instalado o no esta disponible en PATH."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Error: Docker Compose v2 es obligatorio para este rebuild."
  exit 1
fi

docker compose -f docker-compose.dev.yml up -d --build --force-recreate "$@"