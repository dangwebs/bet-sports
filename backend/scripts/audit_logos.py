#!/usr/bin/env python3
"""
Script de Auditoría de Logos de Equipos

Este script verifica la validez de las URLs de logos en team_logos.json
realizando peticiones HTTP HEAD para cada una.

Uso:
    python3 scripts/audit_logos.py

Salida:
    - Lista de equipos con logos rotos (404)
    - Lista de equipos con logos válidos (200)
    - Estadísticas de la auditoría
"""

import asyncio
import json
import os
import sys
from typing import Dict, List, Tuple

# Agregar path del proyecto
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    import httpx
except ImportError:
    print("❌ Error: httpx no instalado. Ejecuta: pip install httpx")
    sys.exit(1)


DATA_FILE = os.path.join(PROJECT_ROOT, "data", "team_logos.json")

# Timeout para cada request (segundos)
TIMEOUT = 10
# Máximo de requests concurrentes (para no abrumar servidores)
MAX_CONCURRENT = 20


async def check_url(
    client: httpx.AsyncClient, 
    team_name: str, 
    url: str
) -> Tuple[str, str, bool, int]:
    """
    Verifica si una URL está accesible.
    Retorna: (team_name, url, is_valid, status_code)
    """
    if not url:
        return team_name, url, False, 0
    
    try:
        response = await client.head(url, timeout=TIMEOUT, follow_redirects=True)
        is_valid = response.status_code == 200
        return team_name, url, is_valid, response.status_code
    except httpx.TimeoutException:
        return team_name, url, False, -1  # Timeout
    except Exception as e:
        return team_name, url, False, -2  # Error de conexión


async def audit_logos() -> Dict[str, List]:
    """
    Audita todas las URLs en team_logos.json.
    """
    print(f"📂 Leyendo archivo: {DATA_FILE}")
    
    if not os.path.exists(DATA_FILE):
        print(f"❌ Archivo no encontrado: {DATA_FILE}")
        return {"valid": [], "broken": [], "errors": []}
    
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        logos: Dict[str, str] = json.load(f)
    
    print(f"📊 Total de entradas en JSON: {len(logos)}")
    
    # Eliminar duplicados (mismo URL para diferentes variantes de nombre)
    unique_urls = {}
    for team, url in logos.items():
        if url and url not in unique_urls.values():
            unique_urls[team] = url
    
    print(f"🔗 URLs únicas a verificar: {len(unique_urls)}")
    print(f"⏳ Iniciando auditoría (máx {MAX_CONCURRENT} concurrent requests)...")
    print("-" * 60)
    
    valid_logos = []
    broken_logos = []
    error_logos = []
    
    # Semáforo para limitar concurrencia
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    
    async def bounded_check(client, team, url):
        async with semaphore:
            return await check_url(client, team, url)
    
    async with httpx.AsyncClient() as client:
        tasks = [
            bounded_check(client, team, url) 
            for team, url in unique_urls.items()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                error_logos.append(("Unknown", str(result)))
                continue
                
            team_name, url, is_valid, status_code = result
            
            if is_valid:
                valid_logos.append(team_name)
            elif status_code == 404:
                broken_logos.append((team_name, url))
            elif status_code == -1:
                error_logos.append((team_name, f"TIMEOUT: {url}"))
            else:
                error_logos.append((team_name, f"STATUS {status_code}: {url}"))
    
    return {
        "valid": valid_logos,
        "broken": broken_logos,
        "errors": error_logos
    }


def print_report(results: Dict[str, List]):
    """
    Imprime un reporte detallado de la auditoría.
    """
    print("\n" + "=" * 60)
    print("📋 REPORTE DE AUDITORÍA DE LOGOS")
    print("=" * 60)
    
    valid = results["valid"]
    broken = results["broken"]
    errors = results["errors"]
    
    total = len(valid) + len(broken) + len(errors)
    
    # Estadísticas
    print(f"\n📊 ESTADÍSTICAS:")
    print(f"   ✅ Logos válidos (200 OK): {len(valid)}")
    print(f"   ❌ Logos rotos (404):      {len(broken)}")
    print(f"   ⚠️  Errores de conexión:   {len(errors)}")
    print(f"   📈 Total verificados:      {total}")
    
    if broken:
        print("\n" + "-" * 60)
        print("❌ LOGOS ROTOS (404 Not Found):")
        print("-" * 60)
        for team, url in sorted(broken, key=lambda x: x[0]):
            print(f"\n   Team: '{team}'")
            print(f"   URL:  {url}")
        
        print("\n" + "-" * 60)
        print("💡 ACCIÓN REQUERIDA:")
        print("   Actualiza las URLs en 'data/team_logos.json' con valores válidos.")
        print("   Puedes buscar logos en:")
        print("   - https://a.espncdn.com/i/teamlogos/soccer/500/*.png")
        print("   - https://crests.football-data.org/*.png")
    
    if errors:
        print("\n" + "-" * 60)
        print("⚠️  ERRORES DE CONEXIÓN:")
        print("-" * 60)
        for team, error in errors:
            print(f"   {team}: {error}")
    
    print("\n" + "=" * 60)
    print("✅ Auditoría completada.")
    print("=" * 60)


def main():
    """
    Punto de entrada principal.
    """
    print("\n🔍 AUDIT LOGOS - Verificador de URLs de Logos")
    print("=" * 60)
    
    results = asyncio.run(audit_logos())
    print_report(results)
    
    # Exit code basado en si hay logos rotos
    if results["broken"]:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
