/**
 * Suggested betting pick from AI
 */
export interface SuggestedPick {
  market_type: string;
  market_label: string;
  probability: number;
  confidence_level: "high" | "medium" | "low";
  reasoning: string;
  risk_level: number;
  is_recommended: boolean;
  priority_score: number;

  // Historical/result properties
  was_correct?: boolean;
  expected_value?: number;
  confidence?: number;
  is_contrarian?: boolean;
  pick_code?: string; // Short code like '1', 'X', '2', 'O2.5'

  // Betting Management
  suggested_stake?: number;
  kelly_percentage?: number;
  opening_odds?: number;
  closing_odds?: number;
  clv_beat?: boolean;
  odds?: number;

  // ML/AI Confirmation (synced with backend SuggestedPickDTO)
  is_ml_confirmed?: boolean;
  is_ia_confirmed?: boolean;
  formatted_reasoning?: string;
  ml_confidence?: number;

  // Backend SSOT fields
  color_code?: string; // Hex color from backend
  result?: string; // WIN, LOSS, VOID, PENDING
}

/**
 * Container for all suggested picks for a match
 */
export interface MatchSuggestedPicks {
  match_id: string;
  suggested_picks: SuggestedPick[];
  combination_warning?: string;
  highlights_url?: string;
  real_time_odds?: Record<string, number>;
  generated_at: string;
}
