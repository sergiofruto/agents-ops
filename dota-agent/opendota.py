"""
OpenDota API client for Dota 2 team stats.

Provides:
  - build_team_roster()        — fetch top-1000 teams, build name→id map
  - compute_true_prob()        — combine Elo + form + H2H into true probability
  - get_recent_form()          — win rate over last N days
  - get_h2h_winrate()          — head-to-head win rate between two teams
  - elo_win_probability()      — standard Elo formula

Caches match data for 1 hour to reduce API latency (2-5s per call).
"""

import difflib
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

import requests
import config

logger = logging.getLogger(__name__)

_SESSION = requests.Session()
_SESSION.headers.update({"Accept": "application/json"})
_TIMEOUT = 15  # seconds (OpenDota can be slow)


# ---------------------------------------------------------------------------
# Token-bucket rate limiter — OpenDota allows 60 req/min; stay under at 55
# ---------------------------------------------------------------------------

class _TokenBucket:
    """Thread-safe token bucket; refills at `rate` tokens per 60 seconds."""

    def __init__(self, rate: int = 55) -> None:
        self._rate = rate
        self._tokens = float(rate)
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until one token is available, then consume it."""
        while True:
            with self._lock:
                now = time.monotonic()
                self._tokens = min(
                    self._rate,
                    self._tokens + (now - self._last) * (self._rate / 60.0),
                )
                self._last = now
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
            time.sleep(0.05)


_rate_limiter = _TokenBucket(rate=55)


def _get(url: str, **kwargs) -> requests.Response:
    """Rate-limited GET for the OpenDota API."""
    _rate_limiter.acquire()
    return _SESSION.get(url, **kwargs)

# ---------------------------------------------------------------------------
# Known alias map: normalised lowercase → canonical team name
# ---------------------------------------------------------------------------
_ALIAS_MAP: dict[str, str] = {
    # Team Liquid
    "liquid":           "team liquid",
    "tl":               "team liquid",
    "team liquid":      "team liquid",

    # Team Secret
    "secret":           "team secret",
    "ts":               "team secret",
    "team secret":      "team secret",

    # Team Spirit
    "spirit":           "team spirit",
    "tspirit":          "team spirit",
    "team spirit":      "team spirit",

    # Team Falcons (TI14 2025 champions)
    "falcons":          "team falcons",
    "team falcons":     "team falcons",

    # Team Yandex (formerly Cyber Goose, acquired June 2025)
    "yandex":           "team yandex",
    "ty":               "team yandex",
    "team yandex":      "team yandex",

    # Tundra Esports
    "tundra":           "tundra esports",
    "tundra esports":   "tundra esports",

    # Xtreme Gaming (Chinese; also tagged WBG.XG since mid-2024)
    "xtreme":           "xtreme gaming",
    "xtreme gaming":    "xtreme gaming",
    "xg":               "xtreme gaming",
    "wbg xg":           "xtreme gaming",

    # OG
    "og":               "og",
    "og esports":       "og",

    # Evil Geniuses
    "eg":               "evil geniuses",
    "evil geniuses":    "evil geniuses",

    # PSG.LGD
    "lgd":              "psg.lgd",
    "psg lgd":          "psg.lgd",
    "psg":              "psg.lgd",

    # Virtus.pro
    "vp":               "virtus.pro",
    "virtus pro":       "virtus.pro",
    "virtus":           "virtus.pro",

    # Natus Vincere
    "navi":             "natus vincere",
    "na'vi":            "natus vincere",
    "natus vincere":    "natus vincere",

    # Natus Vincere Junior
    "navi jr":          "natus vincere junior",
    "navi junior":      "natus vincere junior",

    # Aurora Gaming
    "aurora":           "aurora gaming",
    "aurora gaming":    "aurora gaming",

    # Gaimin Gladiators
    "gaimin":           "gaimin gladiators",
    "gladiators":       "gaimin gladiators",
    "gaimin gladiators": "gaimin gladiators",

    # BetBoom Team
    "bb":               "betboom team",
    "betboom":          "betboom team",
    "betboom team":     "betboom team",

    # Azure Ray
    "azure":            "azure ray",
    "azure ray":        "azure ray",
    "ar":               "azure ray",

    # Entity
    "entity":           "entity",

    # PARIVISION
    "parivision":       "parivision",
    "pari":             "parivision",
    "pv":               "parivision",

    # Heroic (South America)
    "heroic":           "heroic",
    "heral":            "heroic",

    # BOOM Esports (SEA)
    "boom":             "boom esports",
    "boom esports":     "boom esports",

    # Nigma Galaxy
    "nigma":            "nigma galaxy",
    "galaxy":           "nigma galaxy",
    "nigma galaxy":     "nigma galaxy",

    # Wildcard Gaming (NA)
    "wildcard":         "wildcard gaming",
    "wildcard gaming":  "wildcard gaming",

    # Team Nemesis (SEA)
    "nemesis":          "team nemesis",
    "team nemesis":     "team nemesis",

    # All Gamers Global
    "agg":              "all gamers global",
    "all gamers":       "all gamers global",
    "all gamers global": "all gamers global",

    # GamerLegion
    "gamerlegion":      "gamerlegion",
    "gamer legion":     "gamerlegion",
    "gl":               "gamerlegion",

    # paiN Gaming (SA)
    "pain":             "pain gaming",
    "pain gaming":      "pain gaming",

    # Talon Esports (SEA)
    "talon":            "talon esports",
    "talon esports":    "talon esports",

    # Neon Esports (SEA)
    "neon":             "neon esports",
    "neon esports":     "neon esports",

    # Quest Esports
    "quest":            "quest esports",
    "quest esports":    "quest esports",

    # 9Pandas
    "9pandas":          "9pandas",
    "pandas":           "9pandas",

    # Shopify Rebellion (NA, formerly known as NightMare)
    "shopify":          "shopify rebellion",
    "rebellion":        "shopify rebellion",
    "shopify rebellion": "shopify rebellion",
    "sr":               "shopify rebellion",

    # beastcoast (SA)
    "beastcoast":       "beastcoast",
    "bc":               "beastcoast",

    # Infamous (SA)
    "infamous":         "infamous gaming",
    "infamous gaming":  "infamous gaming",

    # Cloud9 (when active in Dota)
    "c9":               "cloud9",
    "cloud 9":          "cloud9",
    "cloud9":           "cloud9",

    # MOUZ / mousesports
    "mouz":             "mouz",
    "mousesports":      "mouz",

    # Vici Gaming (China)
    "vici":             "vici gaming",
    "vg":               "vici gaming",
    "vici gaming":      "vici gaming",

    # RNG / Royal Never Give Up
    "rng":              "royal never give up",
    "royal never give up": "royal never give up",

    # Fnatic
    "fnatic":           "fnatic",

    # Alliance
    "alliance":         "alliance",

    # Team Zero
    "zero":             "team zero",
    "team zero":        "team zero",

    # Execration (SEA)
    "execration":       "execration",
    "exe":              "execration",

    # Nouns Esports (NA)
    "nouns":            "nouns esports",
    "nouns esports":    "nouns esports",
}

# ---------------------------------------------------------------------------
# Module-level roster cache
# ---------------------------------------------------------------------------
# Maps normalised name → (team_id, rating)
_roster: dict[str, tuple[int, float]] = {}
_roster_built_at: Optional[datetime] = None
_ROSTER_TTL_HOURS = 6

# Match data cache: team_id → (matches_list, fetched_at)
_match_cache: dict[int, tuple[list[dict], datetime]] = {}
_MATCH_CACHE_TTL_HOURS = 1

# Known overrides (name → id) for disambiguation
_KNOWN_TEAM_IDS: dict[str, int] = {}


# ---------------------------------------------------------------------------
# Roster building
# ---------------------------------------------------------------------------

def build_team_roster(limit: int = 1000) -> None:
    """
    Fetch top `limit` teams from OpenDota, build normalised name→(id, rating) map.
    Called once at startup; refreshes automatically every ROSTER_TTL_HOURS.
    """
    global _roster, _roster_built_at

    url = f"{config.OPENDOTA_BASE}/api/teams"
    params = {"limit": limit}
    try:
        resp = _get(url, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        teams = resp.json()
    except Exception as exc:
        logger.warning("build_team_roster failed: %s", exc)
        return

    new_roster: dict[str, tuple[int, float]] = {}
    for team in teams:
        tid    = team.get("team_id")
        name   = team.get("name", "")
        rating = float(team.get("rating") or 0)
        if not tid or not name:
            continue
        key = _normalise(name)
        # Keep highest-rated entry when duplicates exist
        if key not in new_roster or rating > new_roster[key][1]:
            new_roster[key] = (int(tid), rating)

    _roster = new_roster
    _roster_built_at = datetime.utcnow()
    logger.info("Built team roster: %d unique teams indexed", len(_roster))


def _maybe_refresh_roster() -> None:
    if _roster_built_at is None or (
        datetime.utcnow() - _roster_built_at > timedelta(hours=_ROSTER_TTL_HOURS)
    ):
        build_team_roster()


# ---------------------------------------------------------------------------
# Team name resolution
# ---------------------------------------------------------------------------

def _normalise(name: str) -> str:
    """Lowercase, strip punctuation noise, collapse whitespace."""
    import re
    name = name.lower()
    name = re.sub(r"[.\-_]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def resolve_team_id(name: str) -> Optional[tuple[int, float]]:
    """
    Multi-stage fuzzy match to find (team_id, rating) for `name`.
    Returns None if no confident match found.
    """
    _maybe_refresh_roster()

    norm = _normalise(name)

    # Stage 1: explicit override
    if norm in _KNOWN_TEAM_IDS:
        tid = _KNOWN_TEAM_IDS[norm]
        # find rating from roster if available
        for key, (rid, rating) in _roster.items():
            if rid == tid:
                return tid, rating
        return tid, 0.0

    # Stage 2: alias map
    canonical = _ALIAS_MAP.get(norm)
    if canonical:
        norm = _normalise(canonical)

    # Stage 3: exact match
    if norm in _roster:
        return _roster[norm]

    # Stage 4: substring match (roster key contains norm or vice versa)
    for key, val in _roster.items():
        if norm in key or key in norm:
            return val

    # Stage 5: difflib close match (cutoff 0.80)
    keys = list(_roster.keys())
    matches = difflib.get_close_matches(norm, keys, n=1, cutoff=0.80)
    if matches:
        return _roster[matches[0]]

    logger.debug("resolve_team_id: no match for %r", name)
    return None


# ---------------------------------------------------------------------------
# Match data fetching with cache
# ---------------------------------------------------------------------------

def _fetch_team_matches(team_id: int, limit: int = 50) -> list[dict]:
    """Fetch recent matches for a team; cached for 1 hour."""
    now = datetime.utcnow()
    if team_id in _match_cache:
        cached, fetched_at = _match_cache[team_id]
        if now - fetched_at < timedelta(hours=_MATCH_CACHE_TTL_HOURS):
            return cached

    url = f"{config.OPENDOTA_BASE}/api/teams/{team_id}/matches"
    params = {"limit": limit}
    try:
        resp = _get(url, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        matches = resp.json()
        _match_cache[team_id] = (matches, now)
        return matches
    except Exception as exc:
        logger.warning("_fetch_team_matches(%d) failed: %s", team_id, exc)
        return []


# ---------------------------------------------------------------------------
# Signal computations
# ---------------------------------------------------------------------------

def elo_win_probability(rating_a: float, rating_b: float) -> float:
    """Standard Elo formula: probability that A beats B."""
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def get_recent_form(team_id: int, days: int = 30) -> Optional[float]:
    """
    Return win rate for `team_id` over the last `days` days.
    Returns None if fewer than 3 matches found (insufficient sample).
    """
    matches = _fetch_team_matches(team_id)
    if not matches:
        return None

    cutoff_ts = time.time() - days * 86400
    recent = [
        m for m in matches
        if (m.get("start_time") or 0) >= cutoff_ts
    ]
    if len(recent) < 3:
        return None

    wins = sum(1 for m in recent if m.get("radiant") == m.get("radiant_win"))
    return wins / len(recent)


def get_h2h_winrate(team_a_id: int, team_b_id: int, days: int = 180) -> tuple[float, int]:
    """
    Return (team_a win rate vs team_b, number of matches).
    Looks at team_a's match history filtered to games against team_b.
    """
    matches = _fetch_team_matches(team_a_id)
    if not matches:
        return 0.5, 0

    cutoff_ts = time.time() - days * 86400
    h2h = [
        m for m in matches
        if (m.get("start_time") or 0) >= cutoff_ts
        and m.get("opposing_team_id") == team_b_id
    ]
    if not h2h:
        return 0.5, 0

    wins = sum(1 for m in h2h if m.get("radiant") == m.get("radiant_win"))
    return wins / len(h2h), len(h2h)


def _get_league_tier(market: dict) -> str:
    """
    Infer tournament tier from market text fields.
    Returns 'premium', 'professional', 'amateur', or 'unknown'.

    Checked in priority order: premium → professional → amateur → unknown.
    """
    text = " ".join(filter(None, [
        market.get("question", ""),
        str(market.get("tags", "")),
        market.get("groupItemTitle", ""),
        market.get("category", ""),
        market.get("description", ""),
    ])).lower()

    # Premium: The International, Valve Majors, and named top-tier circuit events.
    # List ordered from most specific to least to avoid false sub-string conflicts.
    _PREMIUM = (
        "the international",
        " ti ",                     # "... TI ..." (space-padded to avoid team names)
        "major",                    # Lima Major, Bali Major, etc.
        "dreamleague",              # DreamLeague Season N (ESL Gaming)
        "blast slam",               # BLAST Slam I-V
        "pgl wallachia",
        "pgl lausanne",
        "pgl arlington",
        "pgl stockholm",
        "pgl",                      # catch remaining PGL events
        "esl one",
        "esl pro",                  # ESL Pro League
        "betboom dacha",
        "fissure universe",
        "fissure playground",
        "riyadh masters",
        "esports world cup",
        "weplay championship",
        "weplay esports",
        "dpc major",                # Dota Pro Circuit Majors (not regional leagues)
        "dpc championship",
    )
    if any(kw in text for kw in _PREMIUM):
        return "premium"

    # Professional: regional circuits, division play, qualifiers, smaller leagues.
    _PROFESSIONAL = (
        "regional league",
        "regional qualifier",
        "division i",
        "division ii",
        "pro league",
        "qualifier",
        "open qualifier",
        "series",
        "league",
    )
    if any(kw in text for kw in _PROFESSIONAL):
        return "professional"

    # Amateur: community cups, open invitationals.
    _AMATEUR = (
        "amateur",
        "invitational",
        "community cup",
        "open cup",
    )
    if any(kw in text for kw in _AMATEUR):
        return "amateur"

    return "unknown"


def compute_true_prob(
    team_a_name: str,
    team_b_name: str,
    market: Optional[dict] = None,
) -> Optional[dict]:
    """
    Compute a model-derived true probability for team_a beating team_b.

    Returns dict with keys:
        true_prob, elo_prob, form_a, form_b, h2h_winrate, h2h_sample, league_tier
    Returns None if team resolution fails for either team.
    """
    result_a = resolve_team_id(team_a_name)
    result_b = resolve_team_id(team_b_name)

    if result_a is None or result_b is None:
        logger.debug(
            "compute_true_prob: could not resolve %r or %r", team_a_name, team_b_name
        )
        return None

    team_a_id, rating_a = result_a
    team_b_id, rating_b = result_b

    elo_prob = elo_win_probability(rating_a, rating_b)

    form_a = get_recent_form(team_a_id)
    form_b = get_recent_form(team_b_id)

    h2h_rate, h2h_sample = get_h2h_winrate(team_a_id, team_b_id)

    league_tier = _get_league_tier(market) if market else "unknown"

    # ---- Elo + form adjustment ----
    form_adj = 0.0
    if form_a is not None and form_b is not None:
        form_adj = (form_a - form_b) * 0.15

    elo_adj = max(0.05, min(0.95, elo_prob + form_adj))

    # ---- H2H blending ----
    if h2h_sample >= 5:
        h2h_weight = min(0.25, h2h_sample / 40)
        raw_true_prob = (1 - h2h_weight) * elo_adj + h2h_weight * h2h_rate
    else:
        raw_true_prob = elo_adj

    # ---- Calibration shrinkage ----
    # Backtest showed the model overshoots by ~5-6pp at all confidence levels.
    # Shrink toward 0.5 by CALIBRATION_FACTOR to correct systematic overconfidence.
    true_prob = 0.5 + (raw_true_prob - 0.5) * config.CALIBRATION_FACTOR

    return {
        "true_prob":     round(true_prob, 4),
        "raw_true_prob": round(raw_true_prob, 4),
        "elo_prob":      round(elo_prob, 4),
        "form_a":      round(form_a, 4) if form_a is not None else None,
        "form_b":      round(form_b, 4) if form_b is not None else None,
        "h2h_winrate": round(h2h_rate, 4),
        "h2h_sample":  h2h_sample,
        "league_tier": league_tier,
    }
