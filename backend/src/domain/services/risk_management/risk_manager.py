"""
Risk Manager Service

Responsible for enforcing portfolio-level constraints (Anti-Fragility).
Ensures we don't over-expose the bankroll on a single day or correlated events.
Includes strict financial circuit breakers and EV validation.
"""

import logging
import math
from typing import Any, Dict, List

from src.domain.entities.entities import Match
from src.domain.entities.suggested_pick import SuggestedPick

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Financial controller that filters picks to respect risk limits.
    Enforces Rule 11 (Financial Risk Management) strictly.
    """

    # Maximum total bankroll exposure per day (e.g., 5%)
    MAX_DAILY_EXPOSURE = 0.05

    # Maximum exposure per league (diversification)
    MAX_LEAGUE_EXPOSURE = 0.03

    # HARD CAP per single bet (Safety Net)
    MAX_SINGLE_STAKE = 0.05

    def apply_portfolio_constraints(
        self, all_picks: List[Dict[str, Any]]  # List of {match_id, pick, league_id}
    ) -> List[Dict[str, Any]]:
        """
        Takes a raw list of potential picks and filters/reduces stakes
        to fit within the global risk budget.

        Input: List of dicts with 'pick': SuggestedPick, 'match': Match
        """
        # 1. Filter Invalid Picks (Pre-Sort)
        valid_picks = []
        for item in all_picks:
            current_pick: SuggestedPick = item["pick"]

            # --- CIRCUIT BREAKERS & DATA SANITY ---
            if not self._validate_financial_integrity(current_pick):
                # Instead of dropping, we keep them for ACCURACY tracking but disable
                # financial recommendation
                # This ensures we have "Stats" even if we don't have "Bets"
                logger.info(
                    "Pick retained for TRACKING only (Financial Invalid): %s | "
                    "Odds: %s",
                    current_pick.market_type,
                    current_pick.odds,
                )
                current_pick.is_recommended = False
                current_pick.suggested_stake = 0.0
                current_pick.kelly_percentage = 0.0
                current_pick.reasoning += " (Tracking Only: No Financial Value)"
                # valid_picks.append(item)
                # Proceed to next check or append?
                # If we append here and continue, we skip EV check which is good.
                valid_picks.append(item)
                continue

            # --- EV+ VALIDATION ---
            # Rule: prob * odds > 1.0 (unless Hedging)
            # pick.probability is the calculated probability (0.0 - 1.0)
            _implied_prob = 1.0 / current_pick.odds if current_pick.odds > 0 else 0
            ev = (current_pick.probability * current_pick.odds) - 1.0

            # Strict > 0 check (floating point safe)
            if ev <= 0.0001:
                # Same here: High confidence picks might be getting dropped due to bad
                # odds.
                # We keep them for tracking if probability is decent (e.g. > 50%)
                if current_pick.probability > 0.50:
                    logger.info(
                        "Pick retained for TRACKING only (Low EV): %s | EV=%0.4f",
                        current_pick.market_type,
                        ev,
                    )
                    current_pick.is_recommended = False
                    current_pick.suggested_stake = 0.0
                    current_pick.kelly_percentage = 0.0
                    current_pick.reasoning += " (Tracking Only: Low EV)"
                    valid_picks.append(item)
                    continue
                else:
                    logger.info(
                        "Pick rejected (Low EV & Low Prob): %s. EV=%0.4f",
                        current_pick.market_type,
                        ev,
                    )
                    continue

            # --- ODDS FRESHNESS CHECK ---
            # Assuming pick has an 'odds_timestamp' field or similar.
            # If not yet present, we skip strict check but log warning.
            # TODO: Add timestamp check when field is available.

            valid_picks.append(item)

        # 2. Sort by EV * Priority
        sorted_candidates = sorted(
            valid_picks,
            key=lambda x: x["pick"].expected_value * x["pick"].priority_score,
            reverse=True,
        )

        approved_picks = []
        current_daily_exposure = 0.0
        league_exposure: Dict[str, float] = {}

        for item in sorted_candidates:
            candidate_pick: SuggestedPick = item["pick"]
            match: Match = item["match"]
            league_id = match.league.id

            # Safe retrieval of stake
            stake_pct = candidate_pick.kelly_percentage

            # --- HARD CAP ENFORCEMENT ---
            if stake_pct > self.MAX_SINGLE_STAKE:
                reason = f" (Stake Capped: Exceeds {self.MAX_SINGLE_STAKE*100}% Limit)"
                candidate_pick.reasoning += reason
                candidate_pick.kelly_percentage = self.MAX_SINGLE_STAKE
                candidate_pick.suggested_stake = round(
                    candidate_pick.kelly_percentage * 100, 2
                )
                stake_pct = self.MAX_SINGLE_STAKE

            # Check constraints
            if current_daily_exposure + stake_pct > self.MAX_DAILY_EXPOSURE:
                remaining = self.MAX_DAILY_EXPOSURE - current_daily_exposure
                if remaining < 0.005:  # Less than 0.5% left? Stop.
                    candidate_pick.reasoning += (
                        " (Rechazado: Límite Diario de Riesgo alcanzado)."
                    )
                    continue

                # Cap stake to fit budget
                stake_pct = remaining
                candidate_pick.kelly_percentage = round(stake_pct, 4)
                candidate_pick.suggested_stake = round(stake_pct * 100, 2)
                candidate_pick.reasoning += " (Stake Reducido: Límite Diario)."

            # Check League Limits
            current_league_exp = league_exposure.get(league_id, 0.0)
            if current_league_exp + stake_pct > self.MAX_LEAGUE_EXPOSURE:
                candidate_pick.reasoning += (
                    " (Rechazado: Límite de Exposición por Liga)."
                )
                continue

            # Approve
            approved_picks.append(item)
            current_daily_exposure += stake_pct
            league_exposure[league_id] = current_league_exp + stake_pct

            if current_daily_exposure >= self.MAX_DAILY_EXPOSURE:
                break

        return approved_picks

    def _validate_financial_integrity(self, pick: SuggestedPick) -> bool:
        """
        Circuit Breaker: Ensure financial values are sane.
        Returns False if values are corrupted (NaN, Inf, Negative).
        """
        try:
            # Check for NaN / Inf
            if (
                not math.isfinite(pick.probability)
                or not math.isfinite(pick.odds)
                or not math.isfinite(pick.kelly_percentage)
            ):
                return False

            # Logical Bounds
            if pick.probability < 0 or pick.probability > 1.0:
                return False
            if pick.odds < 1.01 or pick.odds > 1000.0:
                return False  # Outlier odds
            if (
                pick.kelly_percentage < 0 or pick.kelly_percentage > 1.0
            ):  # Stake > 100% is absurd
                return False

            return True
        except Exception as e:
            logger.error("Financial integrity validation failed: %s", e, exc_info=True)
            return False  # Fail-safe: reject bet on error
