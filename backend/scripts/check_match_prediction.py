
import sys
import os
import json
import logging

# Setup path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Load environment variables from .env file FIRST
from dotenv import load_dotenv
env_path = os.path.join(PROJECT_ROOT, '.env')
load_dotenv(env_path)

from src.api.dependencies import get_persistence_repository

# Configure logging to stdout
logging.basicConfig(level=logging.INFO)

def main():
    try:
        repo = get_persistence_repository()
        # League SP1 is La Liga
        predictions = repo.get_league_predictions("SP1")
        
        print(f"Found {len(predictions)} predictions for SP1")
        
        # Searching for Betis vs Villarreal
        # We need to be flexible with names, checking substrings or exact matches found earlier
        target_teams = ["Betis", "Villarreal"]
        
        found = False
        
        found = False
        
        if predictions:
            print("\n--- Inspecting First Match Data Structure ---")
            first_p = predictions[0]
            first_data = first_p.data if hasattr(first_p, 'data') else first_p
            print(f"Type of data: {type(first_data)}")
            if isinstance(first_data, dict):
                print(f"Keys: {list(first_data.keys())}")
                # Print first 500 chars of string representation
                print(f"Content preview: {str(first_data)[:500]}")
        
        found = False
        print("\n--- Matches involving Betis or Villarreal ---")
        for p in predictions:
            data = p.data if hasattr(p, 'data') else p
            
            match_data = data.get('match', {})
            home_obj = match_data.get('home_team', {})
            away_obj = match_data.get('away_team', {})
            
            home = home_obj.get('name', 'Unknown')
            away = away_obj.get('name', 'Unknown')
            match_date = match_data.get('match_date') or match_data.get('utcDate') or 'Unknown Date'
            
            # Check for Betis or Villarreal loosely
            is_betis = "Betis" in str(home) or "Betis" in str(away)
            is_villa = "Villarreal" in str(home) or "Villarreal" in str(away)
            
            if is_betis or is_villa:
                print(f"Found match: {home} vs {away} ({match_date})")
                
                # If it's the target match, print details
                if is_betis and is_villa:
                     print("\nMatch Found (Betis vs Villarreal)!")
                     prediction_data = data.get('prediction', {})
                     print("Prediction Summary:")
                     print(json.dumps(prediction_data, indent=2))
                     found = True
        
        if not found:
            print("\nMatch Betis vs Villarreal not found.")

                
        if not found:
            print("\nMatch Betis vs Villarreal not found in existing predictions.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
