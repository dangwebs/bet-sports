#!/bin/bash
# =============================================================================
# Setup script para desarrollo rápido y portable (Cualquier Máquina)
# =============================================================================
set -e

echo "🚀 Configurando ambiente de desarrollo BJJ-BetSports (Modo Portable)"
echo ""

# 1. Verificar Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado."
    echo "   Instálalo desde: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "✅ Docker detectado"

# 2. Iniciar Stack Portable (MongoDB + Backend + Frontend)
echo ""
echo "📦 Iniciando Stack Portable con Docker Compose..."
docker compose -f docker-compose.dev.yml up -d

# 3. Esperar a que los servicios base estén listos
echo ""
echo "⏳ Esperando que MongoDB esté listo..."
sleep 5

# Verificar que el contenedor de MongoDB está corriendo
if docker ps | grep -q "bjj-mongo-dev"; then
    echo "✅ MongoDB (Portable) corriendo en localhost:27017"
else
    echo "❌ Error: El contenedor de base de datos no inició correctamente"
    docker logs bjj-mongo-dev
    exit 1
fi

# 4. Mostrar configuración necesaria
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 Siguiente paso: Configura tu backend/.env con:"
echo ""
echo "   MONGO_URI=mongodb://admin:adminpassword@localhost:27017/"
echo "   MONGO_DB_NAME=bjj_betsports"
echo ""
echo "   (O simplemente copia el .env.example)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎉 ¡Ambiente de desarrollo listo!"
echo ""
echo "Servicios:"
echo "  • Frontend: http://localhost:5173"
echo "  • Backend:  http://localhost:8000"
echo ""
echo "Comandos útiles:"
echo "  • Ver logs:    docker compose -f docker-compose.dev.yml logs -f"
echo "  • Detener:     docker compose -f docker-compose.dev.yml down"
echo "  • Rebuild:     bash scripts/docker-rebuild-portable.sh"
