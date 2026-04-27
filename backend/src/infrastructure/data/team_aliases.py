"""
Canonical team alias helpers.

This module provides a small mapping of common team name variants to a
canonical key and a helper to compute a canonical team key for arbitrary
team names. The mapping is intentionally small and can be extended as
needed.
"""

import re
import unicodedata

# Base alias map: common variants -> canonical_key
_RAW_ALIAS_MAP = {
    # Premier League / common
    "manchester united": "manchester_united",
    "man utd": "manchester_united",
    "man united": "manchester_united",
    "manchester city": "manchester_city",
    "man city": "manchester_city",
    "liverpool": "liverpool",
    "chelsea": "chelsea",
    "arsenal": "arsenal",
    "tottenham": "tottenham_hotspur",
    "tottenham hotspur": "tottenham_hotspur",
    "manchester city fc": "manchester_city",
    # Bundesliga
    "bayern munich": "bayern_munich",
    "bayern munchen": "bayern_munich",
    "bayern": "bayern_munich",
    "bayer leverkusen": "bayer_leverkusen",
    "bayer 04 leverkusen": "bayer_leverkusen",
    "borussia dortmund": "borussia_dortmund",
    "fc koln": "fc_cologne",
    "1 fc koln": "fc_cologne",
    "fc cologne": "fc_cologne",
    # Generic examples
    "newcastle united": "newcastle_united",
    "manchester united fc": "manchester_united",
    "bournemouth": "afc_bournemouth",
}


def _normalize_for_map(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode()
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# Pre-normalize keys for faster lookup
ALIAS_MAP = {_normalize_for_map(k): v for k, v in _RAW_ALIAS_MAP.items()}


def canonical_team_key(name: str) -> str:
    """Return a canonical key for a team name.

    If the name matches a known alias, return that canonical key. Otherwise
    return a normalized token-joined key (e.g. 'bayer 04 leverkusen' ->
    'bayer_04_leverkusen').
    """
    s = _normalize_for_map(name)
    if not s:
        return ""
    if s in ALIAS_MAP:
        return ALIAS_MAP[s]
    # Fallback: join tokens with underscore
    tokens = [t for t in s.split() if t]
    return "_".join(tokens)
