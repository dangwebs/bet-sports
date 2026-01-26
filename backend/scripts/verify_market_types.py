
import os
import sys
import asyncio
import json
import logging
from typing import Set, Any

# Configurar path para imports del backend
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)

# Configuración de Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from src.domain.entities.suggested_pick import MarketType
except ImportError as e:
    logger.error(f"No se pudo importar MarketType. Error: {e}")
    sys.exit(1)

try:
    import asyncpg
except ImportError:
    logger.error("La librería 'asyncpg' es necesaria. Instálala con: pip install asyncpg")
    sys.exit(1)

DATABASE_URL = os.getenv("DATABASE_URL")

async def get_db_connection():
    if not DATABASE_URL:
        logger.error("DATABASE_URL no está definida en variables de entorno.")
        sys.exit(1)
    return await asyncpg.connect(DATABASE_URL)

def extract_market_types_recursive(data: Any, found_types: Set[str]):
    """
    Busca recursivamente la clave 'market_type' en estructuras JSON arbitrarias.
    """
    if isinstance(data, dict):
        for k, v in data.items():
            if k == 'market_type' and isinstance(v, str):
                found_types.add(v)
            else:
                extract_market_types_recursive(v, found_types)
    elif isinstance(data, list):
        for item in data:
            extract_market_types_recursive(item, found_types)

async def verify_market_types():
    """
    Verifica que los tipos de mercado en la base de datos coincidan con el Enum MarketType.
    Escanea tablas con columnas JSON/JSONB.
    """
    logger.info("🔍 Iniciando auditoría forense de MarketTypes en DB...")
    
    # 1. Obtener valores válidos del código
    valid_market_types = {m.value for m in MarketType}
    logger.info(f"ℹ️  Enums válidos definidos en código: {len(valid_market_types)}")
    
    conn = await get_db_connection()
    
    try:
        # 2. Identificar tablas candidatas (buscando columnas JSON o JSONB)
        # Nota: asyncpg devuelve los nombres de tipos como string
        tables_query = """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns 
            WHERE data_type IN ('json', 'jsonb') AND table_schema = 'public';
        """
        columns = await conn.fetch(tables_query)
        
        if not columns:
            logger.warning("⚠️  No se encontraron columnas JSON/JSONB en la base de datos.")
            return

        found_discrepancies = False
        total_rows_inspected = 0
        
        for table_record in columns:
            table = table_record['table_name']
            col = table_record['column_name']
            dtype = table_record['data_type']
            
            # Filtramos tablas irrelevantes si es necesario (ej. auditoria interna de postgres)
            if table.startswith("pg_"): continue

            logger.info(f"🔎 Analizando {table}.{col} ({dtype})...")
            
            # Fetch data using a cursor to handle potentially large tables
            # For simplicity in this script, we fetch all (assuming reasonable size for dev/test)
            # or use LIMIT.
            
            query = f"SELECT {col} FROM {table}"
            try:
                rows = await conn.fetch(query)
            except Exception as e:
                logger.error(f"Error leyendo {table}.{col}: {e}")
                continue
                
            if not rows:
                logger.info(f"   (Tabla vacía)")
                continue
                
            db_types = set()
            count = 0
            
            for row in rows:
                val = row[col]
                if not val:
                    continue
                
                count += 1
                # Parse JSON string if necessary (asyncpg automatic decoding depends on setup, 
                # but standard JSON type often returns string)
                data = val
                if isinstance(val, str):
                    try:
                        data = json.loads(val)
                    except json.JSONDecodeError:
                        continue
                
                # Extract market types
                extract_market_types_recursive(data, db_types)
            
            total_rows_inspected += count
            
            if not db_types:
                logger.info(f"   (No se encontraron 'market_type' en {count} filas)")
                continue

            logger.info(f"   -> Encontrados {len(db_types)} tipos únicos en {count} filas.")

            # 4. Comparar
            invalid_types = db_types - valid_market_types
            
            if invalid_types:
                found_discrepancies = True
                logger.warning(f"❌ DISCREPANCIAS EN {table}.{col}:")
                for inv in invalid_types:
                    logger.warning(f"   - Valor obsoleto/inválido: '{inv}'")
                
                # Generar script de migración sugerido (Simplificado)
                print(f"\n--- 🛠️  SQL SUGERIDO PARA MIGRACIÓN ({table}) ---")
                for inv in invalid_types:
                    # Heurística de mapeo simple
                    suggestion = "UNKNOWN_MAPPING"
                    inv_upper = inv.upper()
                    
                    if "UNDER" in inv_upper and "2.5" in inv_upper: suggestion = "GOALS_UNDER_2_5"
                    elif "OVER" in inv_upper and "2.5" in inv_upper: suggestion = "GOALS_OVER_2_5"
                    elif "BTTS" in inv_upper and "YES" in inv_upper: suggestion = "BTTS_YES"
                    elif "BTTS" in inv_upper and "NO" in inv_upper: suggestion = "BTTS_NO"
                    elif "WIN" in inv_upper: suggestion = "RESULT_1X2"
                    
                    print(f"-- DISCREPANCY: '{inv}' -> SUGGESTION: '{suggestion}' (Requires manual JSON update query)")
                print("----------------------------------------------\n")
            else:
                 logger.info(f"   ✅ Todos los valores son válidos.")

        if total_rows_inspected == 0:
             logger.warning("⚠️  La base de datos parece estar vacía (0 filas con JSON inspeccionadas).")
        elif not found_discrepancies:
            logger.info("✅ Integridad verificada globalmente: Todos los MarketTypes encontrados son válidos.")

    except Exception as e:
        logger.error(f"Error crítico durante la verificación: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify_market_types())