"""
signals.py — Implied-edge computation for crypto and sports markets.

Public API
----------
compute_edge(question, category, polymarket_prob, close_date=None)
    -> tuple[float | None, float | None]   # (edge, true_prob)

kelly_stake(true_prob, entry_price, bankroll, fraction, min_bet, max_bet)
    -> float
"""

from __future__ import annotations

import logging
import math
import re
import time
from datetime import datetime, timezone
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared HTTP session
# ---------------------------------------------------------------------------

_SESSION = requests.Session()
_SESSION.headers.update({"Accept": "application/json", "User-Agent": "polymarket-agent/1.0"})

_TIMEOUT = 10

# ---------------------------------------------------------------------------
# Kelly helper (shared by analyzer and backtest)
# ---------------------------------------------------------------------------

def kelly_stake(
    true_prob: float,
    entry_price: float,
    bankroll: float,
    fraction: float,
    min_bet: float,
    max_bet: float,
) -> float:
    """Return a Half-Kelly bet size in dollars, clamped to [min_bet, max_bet]."""
    if entry_price <= 0 or entry_price >= 1:
        return 0.0
    b = (1.0 / entry_price) - 1.0           # net decimal odds
    if b <= 0:
        return 0.0
    f_star = (true_prob * (b + 1) - 1) / b  # full Kelly fraction
    if f_star <= 0:
        return 0.0
    raw = fraction * f_star * bankroll
    return max(min_bet, min(raw, max_bet))


# ---------------------------------------------------------------------------
# Category inference (mirrors backtest.py)
# ---------------------------------------------------------------------------

_CRYPTO_KEYWORDS = [
    "bitcoin", "btc", "eth", "ethereum", "crypto", "solana", "sol",
    "xrp", "doge", "token", "defi", "nft", "blockchain", "coin",
    "dogecoin", "ripple", "cardano", "ada", "bnb", "binance",
]
_SPORTS_KEYWORDS = [
    "nfl", "nba", "mlb", "nhl", "soccer", "football", "basketball",
    "baseball", "tennis", "golf", "championship", "super bowl",
    "world cup", "league", "match", "game", "team", "player",
    "wins", "beat", "score",
    # Bundesliga
    "bundesliga", "mainz", "hoffenheim", "pauli", "freiburg", "augsburg",
    "bochum", "wolfsburg", "dortmund", "leverkusen", "frankfurt", "stuttgart",
    # EPL
    "arsenal", "chelsea", "liverpool", "manchester", "tottenham", "newcastle",
    "west ham", "everton", "aston villa",
    # NBA
    "lakers", "celtics", "warriors", "bulls", "nets", "knicks",
    # NFL
    "patriots", "chiefs", "49ers", "cowboys", "eagles", "ravens",
]


def _infer_category(question: str) -> str:
    q = question.lower()
    if any(kw in q for kw in _CRYPTO_KEYWORDS):
        return "crypto"
    if any(kw in q for kw in _SPORTS_KEYWORDS):
        return "sports"
    return "other"


# ---------------------------------------------------------------------------
# Crypto edge — log-normal binary probability via CoinGecko
# ---------------------------------------------------------------------------

# Coin name/ticker → CoinGecko ID
_COIN_ID_MAP: dict[str, str] = {
    "bitcoin": "bitcoin",  "btc": "bitcoin",
    "ethereum": "ethereum", "eth": "ethereum",
    "solana": "solana",    "sol": "solana",
    "dogecoin": "dogecoin", "doge": "dogecoin",
    "ripple": "ripple",    "xrp": "ripple",
    "cardano": "cardano",  "ada": "cardano",
    "binance": "binancecoin", "bnb": "binancecoin",
    "avalanche": "avalanche-2", "avax": "avalanche-2",
    "polkadot": "polkadot", "dot": "polkadot",
    "chainlink": "chainlink", "link": "chainlink",
    "litecoin": "litecoin", "ltc": "litecoin",
    "shiba": "shiba-inu",  "shib": "shiba-inu",
    "polygon": "matic-network", "matic": "matic-network",
    "uniswap": "uniswap",  "uni": "uniswap",
}

# Cache: coin_id -> (expires_at, spot_price, annualised_sigma)
_crypto_cache: dict[str, tuple[float, float, float]] = {}
_CRYPTO_CACHE_TTL = 3600  # 1 hour

_COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Pattern 1: "Will the price of <asset> be above/below $<strike> on <date>?"
_PRICE_RE = re.compile(
    r"(?i)will\s+(?:the\s+)?price\s+of\s+(\w+)\s+be\s+(above|below)\s+\$?([\d,]+(?:\.\d+)?[kK]?)\s+on\s+(.+?)[\?!]?$"
)
# Pattern 2: "Will <asset> reach/hit $<strike> …?" → direction=above
# Handles "by March 31", "in April", "February 23-March 1" (date range → use last date)
_REACH_RE = re.compile(
    r"(?i)will\s+(\w+)\s+(?:reach|hit)\s+\$?([\d,]+(?:\.\d+)?[kK]?)(?:\s+(?:(?:in|by|before|on)\s+)?(.+?))?[\?!]?$"
)
# Pattern 3: "Will <asset> dip to/drop to/fall to $<strike> …?" → direction=below
_DIP_RE = re.compile(
    r"(?i)will\s+(\w+)\s+(?:dip|drop|fall)\s+(?:to|below)\s+\$?([\d,]+(?:\.\d+)?[kK]?)(?:\s+(?:(?:in|by|before|on)\s+)?(.+?))?[\?!]?$"
)


def _resolve_coin_id(asset_token: str) -> Optional[str]:
    return _COIN_ID_MAP.get(asset_token.lower())


def _annualised_sigma(closes: list[float]) -> float:
    """Compute annualised sigma from a list of daily closing prices."""
    log_returns = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    n = len(log_returns)
    mean = sum(log_returns) / n
    variance = sum((x - mean) ** 2 for x in log_returns) / (n - 1)
    return math.sqrt(variance) * math.sqrt(365)


def _fetch_crypto_data(coin_id: str, days_to_expiry: int = 30) -> Optional[tuple[float, float]]:
    """
    Return (spot_price, blended_annualised_sigma) using CoinGecko, with 1h caching.

    Vol blending: short expiry → weight 7d vol more (captures recent regime);
    long expiry → weight 30d vol more (smooths out spikes).
      weight_7d  = max(0, 1 - days_to_expiry / 30)   → 1.0 at 0d, 0.0 at 30d+
      weight_30d = 1 - weight_7d
    """
    cache_key = f"{coin_id}:{days_to_expiry}"
    now = time.time()
    if cache_key in _crypto_cache:
        expires, spot, sigma = _crypto_cache[cache_key]
        if now < expires:
            return spot, sigma

    try:
        # Spot price
        r = _SESSION.get(
            f"{_COINGECKO_BASE}/simple/price",
            params={"ids": coin_id, "vs_currencies": "usd"},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        spot = float(r.json()[coin_id]["usd"])

        # 30-day daily closes (also contains the last 7 days)
        r2 = _SESSION.get(
            f"{_COINGECKO_BASE}/coins/{coin_id}/market_chart",
            params={"vs_currency": "usd", "days": 30, "interval": "daily"},
            timeout=_TIMEOUT,
        )
        r2.raise_for_status()
        prices_raw = r2.json().get("prices", [])
        closes_30d = [p[1] for p in prices_raw if p[1] > 0]

        if len(closes_30d) < 5:
            return None

        sigma_30d = _annualised_sigma(closes_30d)

        # 7-day slice for short-window vol
        closes_7d = closes_30d[-8:] if len(closes_30d) >= 8 else closes_30d
        sigma_7d  = _annualised_sigma(closes_7d) if len(closes_7d) >= 3 else sigma_30d

        # Blend: nearer expiry → trust recent vol more
        w_short = max(0.0, 1.0 - days_to_expiry / 30.0)
        w_long  = 1.0 - w_short
        blended_sigma = w_short * sigma_7d + w_long * sigma_30d

        _crypto_cache[cache_key] = (now + _CRYPTO_CACHE_TTL, spot, blended_sigma)
        logger.debug(
            "Vol blend for %s | dte=%dd | σ_7d=%.2f σ_30d=%.2f σ_blend=%.2f (w_short=%.0f%%)",
            coin_id, days_to_expiry, sigma_7d, sigma_30d, blended_sigma, w_short * 100,
        )
        return spot, blended_sigma

    except Exception as exc:
        logger.debug("CoinGecko fetch error for %s: %s", coin_id, exc)
        return None


def _norm_cdf(x: float) -> float:
    """Standard normal CDF — use scipy if available, otherwise a pure-Python approximation."""
    try:
        from scipy.stats import norm as _norm
        return float(_norm.cdf(x))
    except ImportError:
        # Abramowitz & Stegun approximation (error < 7.5e-8)
        t = 1.0 / (1.0 + 0.2316419 * abs(x))
        poly = t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))))
        p = 1.0 - (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * x * x) * poly
        return p if x >= 0 else 1.0 - p


def _parse_strike(s: str) -> Optional[float]:
    """Parse strike string like '84,000', '84000', '84k', '84K'."""
    s = s.replace(",", "").strip()
    if s.lower().endswith("k"):
        try:
            return float(s[:-1]) * 1000
        except ValueError:
            return None
    try:
        return float(s)
    except ValueError:
        return None


def _crypto_edge(
    question: str,
    polymarket_prob: float,
    close_date: Optional[str] = None,
) -> tuple[Optional[float], Optional[float]]:
    """Return (edge, true_prob) for a crypto price question, or (None, None)."""
    # Skip range markets ("between … and …")
    if "between" in question.lower() and "and" in question.lower():
        return None, None

    asset_token = direction = strike_str = expiry_str = None

    m = _PRICE_RE.search(question)
    if m:
        asset_token, direction, strike_str, expiry_str = m.groups()
        direction = direction.lower()
    else:
        m2 = _REACH_RE.search(question)
        if m2:
            asset_token, strike_str, expiry_str = m2.groups()
            direction = "above"
        else:
            m3 = _DIP_RE.search(question)
            if m3:
                asset_token, strike_str, expiry_str = m3.groups()
                direction = "below"

    if not asset_token or not strike_str:
        return None, None

    coin_id = _resolve_coin_id(asset_token)
    if not coin_id:
        return None, None

    strike = _parse_strike(strike_str)
    if strike is None:
        return None, None

    # Days to expiry — prefer close_date arg, fall back to parsed expiry string
    # Computed before _fetch_crypto_data so vol blending can use it.
    if not close_date and expiry_str:
        close_date = expiry_str
    days_to_expiry = 30  # fallback
    if close_date:
        try:
            if isinstance(close_date, str):
                # Handle "in March", "by March 31", "February 23-March 1" (use last date)
                all_month_matches = list(re.finditer(
                    r'\b(january|february|march|april|may|june|july|august|'
                    r'september|october|november|december)\b(?:\s+(\d{1,2}))?(?:,?\s+(\d{4}))?',
                    close_date.lower()
                ))
                if all_month_matches and not re.search(r'\d{4}-\d{2}-\d{2}', close_date):
                    month_names = ['january','february','march','april','may','june',
                                   'july','august','september','october','november','december']
                    month_match = all_month_matches[-1]  # use last (end of range)
                    month_num = month_names.index(month_match.group(1)) + 1
                    day   = int(month_match.group(2)) if month_match.group(2) else 28
                    year  = int(month_match.group(3)) if month_match.group(3) else datetime.now(timezone.utc).year
                    close_dt = datetime(year, month_num, day, tzinfo=timezone.utc)
                else:
                    close_dt = datetime.fromisoformat(close_date.replace("Z", "+00:00"))
            else:
                close_dt = close_date
            if close_dt.tzinfo is None:
                close_dt = close_dt.replace(tzinfo=timezone.utc)
            days_to_expiry = max(1, (close_dt - datetime.now(timezone.utc)).days)
        except Exception:
            days_to_expiry = 30

    days_to_expiry = max(days_to_expiry, 1)

    result = _fetch_crypto_data(coin_id, days_to_expiry)
    if result is None:
        return None, None
    spot, sigma = result

    if sigma <= 0 or spot <= 0 or strike <= 0:
        return None, None

    T = days_to_expiry / 365.0

    try:
        d2 = (math.log(spot / strike) - 0.5 * sigma ** 2 * T) / (sigma * math.sqrt(T))
    except (ValueError, ZeroDivisionError):
        return None, None

    prob_above = _norm_cdf(d2)

    true_prob = prob_above if direction == "above" else (1.0 - prob_above)
    edge = true_prob - polymarket_prob
    return edge, true_prob


# ---------------------------------------------------------------------------
# Sports edge — The Odds API (4h TTL cache)
# ---------------------------------------------------------------------------

_ODDS_API_BASE = "https://api.the-odds-api.com/v4/sports"

# Cache: sport_key -> (fetched_at, events_list)
_odds_cache: dict[str, tuple[float, list]] = {}
_ODDS_CACHE_TTL = 4 * 3600  # 4 hours

# Keyword → API sport key
_SPORT_KEY_MAP = [
    # Bundesliga
    (["bundesliga", "mainz", "hoffenheim", "pauli", "freiburg", "augsburg",
      "bochum", "wolfsburg", "dortmund", "leverkusen", "frankfurt", "stuttgart",
      "hertha", "schalke", "koeln", "gladbach"],
     "soccer_germany_bundesliga"),
    # EPL
    (["arsenal", "chelsea", "liverpool", "manchester", "tottenham", "newcastle",
      "west ham", "everton", "aston villa", "brighton", "brentford", "fulham",
      "epl", "premier league"],
     "soccer_epl"),
    # NBA
    (["nba", "lakers", "celtics", "warriors", "bulls", "nets", "knicks",
      "heat", "bucks", "76ers", "suns", "clippers", "nuggets", "mavericks",
      "raptors", "spurs", "jazz", "grizzlies", "pelicans", "hawks"],
     "basketball_nba"),
    # NCAAB
    (["ncaa", "ncaab", "hawkeyes", "huskies", "cavaliers", "blue devils",
      "tar heels", "wildcats", "hoosiers", "badgers", "spartans"],
     "basketball_ncaab"),
    # NFL
    (["nfl", "patriots", "chiefs", "49ers", "cowboys", "eagles", "ravens",
      "broncos", "packers", "steelers", "bears", "giants", "rams", "bengals",
      "chargers", "seahawks", "buccaneers", "saints", "falcons", "panthers",
      "super bowl"],
     "americanfootball_nfl"),
    # MLB
    (["mlb", "yankees", "red sox", "dodgers", "cubs", "cardinals", "giants",
      "astros", "braves", "mets", "phillies", "world series"],
     "baseball_mlb"),
    # NHL
    (["nhl", "bruins", "rangers", "penguins", "blackhawks", "red wings",
      "maple leafs", "canadiens", "flyers", "capitals", "lightning"],
     "icehockey_nhl"),
]


def _detect_sport_key(question: str) -> Optional[str]:
    q = question.lower()
    for keywords, sport_key in _SPORT_KEY_MAP:
        if any(kw in q for kw in keywords):
            return sport_key
    return None


def _fetch_odds(sport_key: str, odds_api_key: str) -> Optional[list]:
    now = time.time()
    if sport_key in _odds_cache:
        fetched_at, events = _odds_cache[sport_key]
        if now - fetched_at < _ODDS_CACHE_TTL:
            return events

    try:
        r = _SESSION.get(
            f"{_ODDS_API_BASE}/{sport_key}/odds",
            params={
                "regions": "us",
                "markets": "h2h",
                "oddsFormat": "decimal",
                "apiKey": odds_api_key,
            },
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        events = r.json()
        _odds_cache[sport_key] = (now, events)
        return events
    except Exception as exc:
        logger.debug("The Odds API error for %s: %s", sport_key, exc)
        return None


# Canonical team name aliases — maps common abbreviations/nicknames to the
# full name that the Odds API uses in home_team / away_team fields.
_TEAM_ALIASES: dict[str, str] = {
    # Soccer
    "man city": "manchester city",   "man utd": "manchester united",
    "man united": "manchester united", "spurs": "tottenham hotspur",
    "tottenham": "tottenham hotspur", "wolves": "wolverhampton wanderers",
    "leicester": "leicester city",    "brighton": "brighton & hove albion",
    "newcastle": "newcastle united",  "west ham": "west ham united",
    "nott forest": "nottingham forest", "bvb": "borussia dortmund",
    "dortmund": "borussia dortmund",  "leverkusen": "bayer leverkusen",
    "gladbach": "borussia monchengladbach",
    # NBA
    "sixers": "philadelphia 76ers",   "blazers": "portland trail blazers",
    "thunder": "oklahoma city thunder",
    # NFL
    "niners": "san francisco 49ers",  "pats": "new england patriots",
    "pack": "green bay packers",
}


def _normalise_team(name: str) -> str:
    """Lower-case and expand a single known alias (used for API team names)."""
    n = name.strip().lower()
    return _TEAM_ALIASES.get(n, n)


def _expand_aliases(text: str) -> str:
    """Replace all alias substrings in `text` with their canonical form."""
    t = text.lower()
    for alias, canonical in sorted(_TEAM_ALIASES.items(), key=lambda x: -len(x[0])):
        t = t.replace(alias, canonical)
    return t


def _tokenise(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", _expand_aliases(text)))


def _best_event_match(question: str, events: list) -> Optional[dict]:
    q_tokens = _tokenise(question)
    best_score = 0
    best_event = None

    for event in events:
        home = _normalise_team(event.get("home_team", ""))
        away = _normalise_team(event.get("away_team", ""))
        event_tokens = set(re.findall(r"[a-z]+", f"{home} {away}"))
        overlap = len(q_tokens & event_tokens)
        if overlap > best_score:
            best_score = overlap
            best_event = event

    if best_score < 1:
        return None
    return best_event


def _fair_prob_from_event(event: dict, question: str, market_key: str = "h2h") -> Optional[float]:
    """Vig-remove odds from top-3 bookmakers and return the fair probability for the matched team."""
    bookmakers = event.get("bookmakers", [])[:3]
    if not bookmakers:
        return None

    q_tokens = _tokenise(question)
    outcome_probs: list[float] = []

    for bm in bookmakers:
        for market in bm.get("markets", []):
            if market.get("key") != market_key:
                continue
            outcomes = market.get("outcomes", [])
            raw = [1.0 / float(o["price"]) for o in outcomes if float(o.get("price", 0)) > 0]
            if not raw:
                continue
            total = sum(raw)
            fair = [p / total for p in raw]

            best_overlap = 0
            best_fair = None
            for o, f in zip(outcomes, fair):
                name_tokens = _tokenise(o.get("name", ""))
                overlap = len(q_tokens & name_tokens)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_fair = f

            if best_fair is not None and best_overlap >= 1:
                outcome_probs.append(best_fair)

    if not outcome_probs:
        return None
    return sum(outcome_probs) / len(outcome_probs)


# ---------------------------------------------------------------------------
# Outrights (tournament winner) markets
# ---------------------------------------------------------------------------

# Keywords that identify "Who wins X tournament?" style questions,
# mapped to the Odds API sport key.
_OUTRIGHTS_KEY_MAP: list[tuple[list[str], str]] = [
    (["fifa world cup", "world cup winner"],            "soccer_fifa_world_cup_winner"),
    (["nba finals", "nba championship"],                "basketball_nba_championship_winner"),
    (["stanley cup", "nhl championship"],               "icehockey_nhl_championship_winner"),
    (["super bowl", "nfl championship"],                "americanfootball_nfl_super_bowl_winner"),
    (["world series", "mlb championship"],              "baseball_mlb_world_series_winner"),
    (["masters tournament"],                            "golf_masters_tournament_winner"),
    (["pga championship"],                              "golf_pga_championship_winner"),
    (["us open"],                                       "golf_us_open_winner"),
    (["the open championship", "british open"],         "golf_the_open_championship_winner"),
    (["ncaa championship", "march madness", "ncaab"],   "basketball_ncaab_championship_winner"),
    (["ncaaf championship", "college football playoff"], "americanfootball_ncaaf_championship_winner"),
]

# Cache for outrights: sport_key → (fetched_at, events_list)
_outrights_cache: dict[str, tuple[float, list]] = {}


def _detect_outrights_key(question: str) -> Optional[str]:
    q = question.lower()
    for keywords, sport_key in _OUTRIGHTS_KEY_MAP:
        if any(kw in q for kw in keywords):
            return sport_key
    return None


def _fetch_outrights(sport_key: str, odds_api_key: str) -> Optional[list]:
    now = time.time()
    if sport_key in _outrights_cache:
        fetched_at, events = _outrights_cache[sport_key]
        if now - fetched_at < _ODDS_CACHE_TTL:
            return events
    try:
        r = _SESSION.get(
            f"{_ODDS_API_BASE}/{sport_key}/odds",
            params={
                "regions": "us",
                "markets": "outrights",
                "oddsFormat": "decimal",
                "apiKey": odds_api_key,
            },
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        events = r.json()
        _outrights_cache[sport_key] = (now, events)
        return events
    except Exception as exc:
        logger.debug("Outrights API error for %s: %s", sport_key, exc)
        return None


def _outrights_edge(
    question: str,
    polymarket_prob: float,
    odds_api_key: str,
) -> tuple[Optional[float], Optional[float]]:
    """Return (edge, true_prob) for a tournament winner question."""
    sport_key = _detect_outrights_key(question)
    if not sport_key:
        return None, None

    events = _fetch_outrights(sport_key, odds_api_key)
    if not events:
        return None, None

    # Outrights usually returns a single event; search all of them
    true_prob = None
    for event in events:
        tp = _fair_prob_from_event(event, question, market_key="outrights")
        if tp is not None:
            true_prob = tp
            break

    if true_prob is None:
        return None, None

    edge = true_prob - polymarket_prob
    return edge, true_prob


def _sports_edge(
    question: str,
    polymarket_prob: float,
) -> tuple[Optional[float], Optional[float]]:
    """Return (edge, true_prob) for a sports question, or (None, None)."""
    try:
        import config
        odds_api_key = config.ODDS_API_KEY
    except Exception:
        return None, None

    if not odds_api_key:
        return None, None

    # Try outrights first (tournament winner questions)
    if _detect_outrights_key(question):
        return _outrights_edge(question, polymarket_prob, odds_api_key)

    sport_key = _detect_sport_key(question)
    if not sport_key:
        return None, None

    events = _fetch_odds(sport_key, odds_api_key)
    if not events:
        return None, None

    event = _best_event_match(question, events)
    if not event:
        return None, None

    true_prob = _fair_prob_from_event(event, question)
    if true_prob is None:
        return None, None

    edge = true_prob - polymarket_prob
    return edge, true_prob


# ---------------------------------------------------------------------------
# LLM edge — Claude probability estimate for "other" markets (and fallback)
# ---------------------------------------------------------------------------

# Cache: question_key -> (expires_at, true_prob)
_llm_cache: dict[str, tuple[float, float]] = {}
_LLM_CACHE_TTL = 4 * 3600  # 4 hours

_LLM_SYSTEM_PROMPT = """\
You are a calibrated probability forecaster for prediction markets.
Given a Yes/No market question and its resolution deadline, output your best estimate
of the probability that the question resolves YES.

Be calibrated: a 70% probability should be right about 70% of the time.
Consider base rates, recent news trends, and the specificity of the claim.

Respond with ONLY valid JSON in this exact format (no other text):
{"probability": 0.XX, "confidence": "low|medium|high", "reasoning": "one sentence"}
"""


def _llm_edge(
    question: str,
    polymarket_prob: float,
    close_date=None,
) -> tuple[Optional[float], Optional[float]]:
    """Return (edge, true_prob) using Claude as the probability model."""
    try:
        import config as _cfg
        if not _cfg.LLM_EDGE_ENABLED or not _cfg.ANTHROPIC_API_KEY:
            return None, None
    except Exception:
        return None, None

    cache_key = question.strip().lower()
    now = time.time()
    if cache_key in _llm_cache:
        expires, cached_prob = _llm_cache[cache_key]
        if now < expires:
            return cached_prob - polymarket_prob, cached_prob

    deadline_str = ""
    if close_date:
        deadline_str = f"\nResolution deadline: {close_date}"

    # Always ask for P(YES) — caller handles "No" outcome flip
    user_msg = f"Market question: {question}{deadline_str}\n\nWhat is the probability this resolves YES?"

    try:
        import anthropic
        import config as _cfg
        import json as _json

        client = anthropic.Anthropic(api_key=_cfg.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=_cfg.LLM_EDGE_MODEL,
            max_tokens=128,
            system=_LLM_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = response.content[0].text.strip()
        # Strip markdown code fences if present (```json ... ``` or ``` ... ```)
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw).strip()
        data = _json.loads(raw)

        true_prob = float(data["probability"])
        confidence = data.get("confidence", "medium")

        if not (0.0 < true_prob < 1.0):
            return None, None

        # Discard low-confidence signals — not worth overriding MIN_EDGE filter
        if confidence == "low":
            return None, None

        _llm_cache[cache_key] = (now + _LLM_CACHE_TTL, true_prob)
        edge = true_prob - polymarket_prob
        logger.debug(
            "LLM edge | q='%s' | market=%.2f | model=%.2f | edge=%+.2f | conf=%s | reason=%s",
            question[:60], polymarket_prob, true_prob, edge, confidence,
            data.get("reasoning", ""),
        )
        return edge, true_prob

    except Exception as exc:
        logger.debug("LLM edge error for '%s': %s", question[:60], exc)
        return None, None


# ---------------------------------------------------------------------------
# Public dispatcher
# ---------------------------------------------------------------------------

def compute_edge(
    question: str,
    category: str,
    polymarket_prob: float,
    close_date=None,
) -> tuple[Optional[float], Optional[float]]:
    """
    Returns (edge, true_prob). Both None if signal unavailable.

    edge      = true_prob - polymarket_prob  (positive = we have an edge)
    true_prob = model-derived probability
    """
    if category == "crypto":
        edge, true_prob = _crypto_edge(question, polymarket_prob, close_date)
        if edge is not None:
            return edge, true_prob
        # Fallback to LLM if BSM couldn't parse the question
        return _llm_edge(question, polymarket_prob, close_date)

    if category == "sports":
        edge, true_prob = _sports_edge(question, polymarket_prob)
        if edge is not None:
            return edge, true_prob
        # Fallback to LLM if no matching odds event found
        return _llm_edge(question, polymarket_prob, close_date)

    # "other" category — politics, macro, elections, etc.
    return _llm_edge(question, polymarket_prob, close_date)
