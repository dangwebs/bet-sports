
import sys
import os
from unittest.mock import MagicMock
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.domain.services.picks_service import PicksService
from src.domain.entities.entities import Match, TeamStatistics, Team
from src.domain.entities.suggested_pick import MarketType

def verify_new_markets():
    service = PicksService()
    service.learning_weights = MagicMock()
    service.learning_weights.get_market_adjustment.return_value = 1.0
    
    # Mock Data
    home = Team(id="HOME", name="Home FC")
    away = Team(id="AWAY", name="Away FC")
    match = Match(id="M1", home_team=home, away_team=away, league=MagicMock(), match_date=MagicMock())
    
    # Stats: High scoring, high corners context
    h_stats = TeamStatistics(
        team_id="HOME", matches_played=10, wins=5, draws=2, losses=3,
        goals_scored=20, goals_conceded=10, total_corners=60, total_yellow_cards=20
    )
    a_stats = TeamStatistics(
        team_id="AWAY", matches_played=10, wins=3, draws=3, losses=4,
        goals_scored=15, goals_conceded=15, total_corners=50, total_yellow_cards=25
    )
    
    # Predictions
    pred_h_goals = 2.1
    pred_a_goals = 1.2
    h_win_prob = 0.60
    draw_prob = 0.25
    a_win_prob = 0.15
    pred_h_corners = 7.5
    pred_a_corners = 4.5
    pred_h_cards = 2.5
    pred_a_cards = 3.5
    
    print("🚀 Generating Picks with Extended Markets...")
    
    picks_container = service.generate_suggested_picks(
        match=match,
        home_stats=h_stats,
        away_stats=a_stats,
        league_averages=None,
        predicted_home_goals=pred_h_goals,
        predicted_away_goals=pred_a_goals,
        home_win_prob=h_win_prob,
        draw_prob=draw_prob,
        away_win_prob=a_win_prob,
        predicted_home_corners=pred_h_corners,
        predicted_away_corners=pred_a_corners,
        predicted_home_yellow_cards=pred_h_cards,
        predicted_away_yellow_cards=pred_a_cards
    )
    
    generated_types = set(p.market_type for p in picks_container.suggested_picks)
    print(f"📊 Generated {len(picks_container.suggested_picks)} picks covering {len(generated_types)} market types.")
    
    required_new_markets = [
        MarketType.DOUBLE_CHANCE_1X,
        MarketType.DRAW_NO_BET_1,
        MarketType.BTTS_YES,
        MarketType.CORRECT_SCORE,
        MarketType.TEAM_GOALS_OVER,
        MarketType.HOME_CORNERS_OVER,
        MarketType.CORNERS_1X2_1,
        MarketType.AWAY_CARDS_OVER
    ]
    
    all_passed = True
    for m in required_new_markets:
        if m in generated_types:
            print(f"✅ Found {m.value}")
        else:
            print(f"❌ Missing {m.value}")
            all_passed = False
            
    if all_passed:
        print("\n🎉 SUCCESS: All new markets generated correctly!")
    else:
        print("\n⚠️ FAILURE: Some new markets missing.")

if __name__ == "__main__":
    verify_new_markets()
