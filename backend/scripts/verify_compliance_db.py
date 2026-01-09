
import sys
import os
import json
from collections import defaultdict
from dotenv import load_dotenv

# Load env variables explicitly
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(env_path)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.infrastructure.repositories.persistence_repository import PersistenceRepository

def verify_compliance():
    repo = PersistenceRepository()
    # Ensure DB tables exist (just in case)
    # repo.create_tables() 
    
    leagues = ['SP1', 'E0', 'D1', 'I1', 'F1', 'P1', 'B1']
    
    league_stats = defaultdict(lambda: {"matches": 0, "ia_confirmed": 0, "ml_confirmed": 0, "errors": [], "min_markets": set()})
    
    print("\n🔍 Verifying Compliance (League by League)...")
    
    for league in leagues:
        predictions = repo.get_league_predictions(league)
        # predictions is a list of 'data' dicts (JSON content)
        
        league_stats[league]["matches"] = len(predictions)
        
        for i, data in enumerate(predictions):
            # Inspect structure of first item
            if i == 0 and league == "SP1":
                print(f"DEBUG: Keys in data: {list(data.keys())}")
                if "match" in data:
                     print(f"DEBUG: Match Keys: {list(data['match'].keys())}")
                     match_date = data["match"].get("match_date", "Unknown")
                else:
                     match_date = data.get("match_date", "Unknown")
            else:
                 if "match" in data:
                     match_date = data["match"].get("match_date", "Unknown")
                 else:
                     match_date = data.get("match_date", "Unknown")

            # Match ID inside data? Usually yes.
            match_id = data.get("id", "Unknown") 
            picks = []
            if "prediction" in data:
                picks = data["prediction"].get("suggested_picks", [])
            else:
                picks = data.get("suggested_picks", [])
            
            ia_conf_count = sum(1 for p in picks if p.get("is_ia_confirmed"))
            ml_conf_count = sum(1 for p in picks if p.get("is_ml_confirmed"))
            
            league_stats[league]["ia_confirmed"] += ia_conf_count
            league_stats[league]["ml_confirmed"] += ml_conf_count
            
            # Count Market Types
            for p in picks:
                m_type = p.get("market_type")
                if m_type:
                    league_stats[league]["min_markets"].add(m_type)

            if league == "SP1" and ia_conf_count == 0:
                 league_stats[league]["errors"].append(f"Info: Match {match_date} has picks but no IA Lock.")
            
            # Rule 1: Max 1 IA Confirmed per match
            if ia_conf_count > 1:
                league_stats[league]["errors"].append(f"Match {match_id}: Found {ia_conf_count} IA Confirmed picks! (Max 1 allowed)")

    print("\n📊 Compliance Report by League:\n")
    print(f"{'League':<10} | {'Matches':<8} | {'IA Locks':<8} | {'ML High':<8} | {'New Mkts':<10} | {'Status':<10}")
    print("-" * 80)
    
    new_markets_set = {
        "double_chance_1x", "double_chance_x2", "double_chance_12",
        "draw_no_bet_1", "draw_no_bet_2",
        "btts_yes", "btts_no",
        "correct_score",
        "team_goals_over", "team_goals_under",
        "home_corners_over", "away_corners_over",
        "corners_1x2_1", "corners_1x2_2"
    }
    
    for league, stats in sorted(league_stats.items()):
        # Check if new markets are present
        found_new = stats["min_markets"].intersection(new_markets_set)
        has_new = len(found_new) > 0
        status = "✅ PASS" if not stats["errors"] else "❌ FAIL"
        
        # Color coding for terminal if supported, else symbols
        print(f"{league:<10} | {stats['matches']:<8} | {stats['ia_confirmed']:<8} | {stats['ml_confirmed']:<8} | {len(found_new):<10} | {status}")
        
        if found_new:
             print(f"  ✨ Verification: Found {len(found_new)} new market types: {list(found_new)[:5]}...")
        else:
             print(f"  ⚠️ Warning: No new market types found in DB for this league.")
        
        for err in stats["errors"]:
            print(f"  🚨 {err}")

if __name__ == "__main__":
    verify_compliance()
