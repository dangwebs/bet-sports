#!/bin/bash
# =============================================================================
# Setup script para desarrollo con paridad a producción
# =============================================================================
set -e

echo "🚀 Configurando ambiente de desarrollo (Paridad con Producción)"
echo ""

# 1. Verificar Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado."
    echo "   Instálalo desde: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "✅ Docker detectado"

# 2. Iniciar PostgreSQL
echo ""
echo "📦 Iniciando PostgreSQL con Docker..."
docker compose -f docker-compose.dev.yml up -d

# 3. Esperar a que PostgreSQL esté listo
echo ""
echo "⏳ Esperando que PostgreSQL esté listo..."
sleep 5

# Verificar que el contenedor está corriendo
if docker ps | grep -q "bjj-postgres-dev"; then
    echo "✅ PostgreSQL corriendo en localhost:5432"
else
    echo "❌ Error: PostgreSQL no inició correctamente"
    docker logs bjj-postgres-dev
    exit 1
fi

# 4. Mostrar configuración necesaria
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 Siguiente paso: Configura tu backend/.env con:"
echo ""
echo "   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bjj_betsports"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎉 ¡Ambiente de desarrollo listo!"
echo ""
echo "Comandos útiles:"
echo "  • Ver logs:    docker logs -f bjj-postgres-dev"
echo "  • Detener:     docker compose -f docker-compose.dev.yml down"
echo "  • Reiniciar:   docker compose -f docker-compose.dev.yml restart"
