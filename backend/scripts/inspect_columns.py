
import os
import sys
import asyncio
import asyncpg

# Configurar path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv("DATABASE_URL")

async def inspect():
    if not DATABASE_URL:
        print("DATABASE_URL not set")
        return

    try:
        conn = await asyncpg.connect(DATABASE_URL)
        rows = await conn.fetch("""
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            ORDER BY table_name, column_name
        """)
        
        print(f"{'Table':<30} | {'Column':<30} | {'Type':<20}")
        print("-" * 85)
        for row in rows:
            print(f"{row['table_name']:<30} | {row['column_name']:<30} | {row['data_type']:<20}")
            
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(inspect())
