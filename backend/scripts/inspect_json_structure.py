
import os
import sys
import asyncio
import asyncpg
import json

# Configurar path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv("DATABASE_URL")

async def inspect():
    if not DATABASE_URL:
        print("DATABASE_URL not set")
        return

    try:
        conn = await asyncpg.connect(DATABASE_URL)
        # Fetch one row
        row = await conn.fetchrow("SELECT data FROM match_predictions LIMIT 1")
        
        if row:
            data_str = row['data']
            # asyncpg might return it as string or dict depending on codec. 
            # If it's json type in DB, asyncpg usually returns string unless specific codec is set, 
            # but for jsonb it returns native python objects.
            # Let's check type.
            print(f"Type of data: {type(data_str)}")
            
            data = data_str
            if isinstance(data_str, str):
                data = json.loads(data_str)
                
            print("Top level keys:", list(data.keys()))
            
            if 'suggested_picks' in data:
                print(f"Found 'suggested_picks' with {len(data['suggested_picks'])} items.")
                if len(data['suggested_picks']) > 0:
                    print("Sample pick:", data['suggested_picks'][0])
            else:
                print("'suggested_picks' NOT found in data.")
                
        else:
            print("No rows in match_predictions.")
            
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(inspect())
