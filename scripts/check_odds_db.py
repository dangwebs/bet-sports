import os
import json
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv("backend/.env")

db_url = os.getenv("DATABASE_URL")
if db_url:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        print("Checking odds in match_predictions...")
        result = conn.execute(text("SELECT match_id, data FROM match_predictions WHERE league_id = 'SP1' LIMIT 5"))
        
        for row in result:
            mid = row[0]
            data = row[1] # JSON
            if isinstance(data, str):
                data = json.loads(data)
                
            match_data = data.get("match", {})
            h_odds = match_data.get("home_odds")
            a_odds = match_data.get("away_odds")
            d_odds = match_data.get("draw_odds")
            
            print(f"Match {mid}: Home={h_odds}, Draw={d_odds}, Away={a_odds}")
            
            # Check picks
            prediction = data.get("prediction", {})
            picks = prediction.get("suggested_picks", [])
            for p in picks:
                label = p.get("market_label")
                odds = p.get("odds", 0) # odds might not be top level in DTO if implied? 
                # Actually SuggestedPickDTO doesn't have 'odds' field per se, 
                # but RiskManager logs 'Odds: 0.0'. 
                # Let's check if 'metadata' or 'logic' has it.
                # Actually SuggestedPick entity has odds. DTO might not show it explicitly if not mapped?
                # Wait, SuggestedPickDTO in use_cases.py:
                # does NOT have 'odds' field! (See lines 634 in use_cases.py snippet above)
                pass 
                
else:
    print("No DATABASE_URL found.")
