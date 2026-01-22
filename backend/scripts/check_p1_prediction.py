
import sys
import os
import json
import logging

# Setup path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Load environment variables
from dotenv import load_dotenv
env_path = os.path.join(PROJECT_ROOT, '.env')
load_dotenv(env_path)

from src.api.dependencies import get_persistence_repository

logging.basicConfig(level=logging.ERROR)

def main():
    repo = get_persistence_repository()
    # Fetch P1 predictions (Liga Portugal)
    predictions = repo.get_league_predictions("P1")
    
    print(f"Found {len(predictions)} predictions for P1")
    
    found = False
    print("\n--- Matches involving Rio Ave or Benfica ---")
    for p in predictions:
        data = p.data if hasattr(p, 'data') else p
        
        match_data = data.get('match', {})
        home_obj = match_data.get('home_team', {})
        away_obj = match_data.get('away_team', {})
        
        home = home_obj.get('name', 'Unknown')
        away = away_obj.get('name', 'Unknown')
        match_date = match_data.get('match_date') or match_data.get('utcDate') or 'Unknown Date'
        
        # Check for Rio Ave or Benfica
        is_rio = "Rio Ave" in str(home) or "Rio Ave" in str(away)
        is_benfica = "Benfica" in str(home) or "Benfica" in str(away)
        
        if is_rio or is_benfica:
            print(f"Found match: {home} vs {away} ({match_date})")
            
            # If it's the target match, print details
            if is_rio and is_benfica:
                    print("\nMatch Found (Rio Ave vs Benfica)!")
                    prediction_data = data.get('prediction', {})
                    print("Prediction Summary:")
                    print(json.dumps(prediction_data, indent=2))
                    
                    top_picks = data.get('top_ml_picks', [])
                    if top_picks:
                        print("\nTop Picks:")
                        print(json.dumps(top_picks, indent=2))
                        
                    found = True
    
    if not found:
        print("\nMatch Rio Ave vs Benfica not found.")

if __name__ == "__main__":
    main()
