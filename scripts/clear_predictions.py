import os
import shutil
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv("backend/.env")

# Clear File Cache
cache_dir = "backend/.cache_data"
if os.path.exists(cache_dir):
    print(f"Removing cache dir: {cache_dir}")
    shutil.rmtree(cache_dir)
if os.path.exists(".cache_data"):
    print("Removing .cache_data")
    shutil.rmtree(".cache_data")

# Clear DB
db_url = os.getenv("DATABASE_URL")
if db_url:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        print("Clearing training_results for SP1...")
        conn.execute(text("DELETE FROM training_results WHERE key LIKE '%SP1%'"))
        print("Clearing match_predictions for SP1...")
        conn.execute(text("DELETE FROM match_predictions WHERE league_id = 'SP1'"))
        conn.commit()
    print("DB Cleared.")
else:
    print("No DATABASE_URL found.")
