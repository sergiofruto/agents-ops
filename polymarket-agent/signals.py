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

# Regex to parse "Will the price of <asset> be above/below $<strike> on <date>?"
_PRICE_RE = re.compile(
    r"(?i)will\s+(?:the\s+)?price\s+of\s+(\w+)\s+be\s+(above|below)\s+\$?([\d,]+)\s+on\s+(.+?)[\?!]?$"
)


def _resolve_coin_id(asset_token: str) -> Optional[str]:
    return _COIN_ID_MAP.get(asset_token.lower())


def _fetch_crypto_data(coin_id: str) -> Optional[tuple[float, float]]:
    """Return (spot_price, annualised_sigma) using CoinGecko, with 1h caching."""
    now = time.time()
    if coin_id in _crypto_cache:
        expires, spot, sigma = _crypto_cache[coin_id]
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

        # 30-day daily closes for vol
        r2 = _SESSION.get(
            f"{_COINGECKO_BASE}/coins/{coin_id}/market_chart",
            params={"vs_currency": "usd", "days": 30, "interval": "daily"},
            timeout=_TIMEOUT,
        )
        r2.raise_for_status()
        prices_raw = r2.json().get("prices", [])
        closes = [p[1] for p in prices_raw if p[1] > 0]

        if len(closes) < 5:
            return None

        # Daily log-returns → annualised sigma
        log_returns = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
        n = len(log_returns)
        mean = sum(log_returns) / n
        variance = sum((x - mean) ** 2 for x in log_returns) / (n - 1)
        daily_sigma = math.sqrt(variance)
        annual_sigma = daily_sigma * math.sqrt(365)

        _crypto_cache[coin_id] = (now + _CRYPTO_CACHE_TTL, spot, annual_sigma)
        return spot, annual_sigma

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


def _crypto_edge(
    question: str,
    polymarket_prob: float,
    close_date: Optional[str] = None,
) -> tuple[Optional[float], Optional[float]]:
    """Return (edge, true_prob) for a crypto price question, or (None, None)."""
    m = _PRICE_RE.search(question)
    if not m:
        return None, None

    asset_token, direction, strike_str, expiry_str = m.groups()
    direction = direction.lower()

    # Skip range markets ("between … and …")
    if "between" in question.lower() and "and" in question.lower():
        return None, None

    coin_id = _resolve_coin_id(asset_token)
    if not coin_id:
        return None, None

    try:
        strike = float(strike_str.replace(",", ""))
    except ValueError:
        return None, None

    result = _fetch_crypto_data(coin_id)
    if result is None:
        return None, None
    spot, sigma = result

    if sigma <= 0 or spot <= 0 or strike <= 0:
        return None, None

    # Days to expiry
    if close_date:
        try:
            if isinstance(close_date, str):
                close_dt = datetime.fromisoformat(close_date.replace("Z", "+00:00"))
            else:
                close_dt = close_date
            if close_dt.tzinfo is None:
                close_dt = close_dt.replace(tzinfo=timezone.utc)
            days_to_expiry = (close_dt - datetime.now(timezone.utc)).days
        except Exception:
            days_to_expiry = 30
    else:
        days_to_expiry = 30

    days_to_expiry = max(days_to_expiry, 1)
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


def _tokenise(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", text.lower()))


def _best_event_match(question: str, events: list) -> Optional[dict]:
    q_tokens = _tokenise(question)
    best_score = 0
    best_event = None

    for event in events:
        home = event.get("home_team", "")
        away = event.get("away_team", "")
        event_tokens = _tokenise(f"{home} {away}")
        overlap = len(q_tokens & event_tokens)
        if overlap > best_score:
            best_score = overlap
            best_event = event

    if best_score < 1:
        return None
    return best_event


def _fair_prob_from_event(event: dict, question: str) -> Optional[float]:
    """Vig-remove odds from top-3 bookmakers and return the fair probability for the matched team."""
    bookmakers = event.get("bookmakers", [])[:3]
    if not bookmakers:
        return None

    q_tokens = _tokenise(question)

    outcome_probs: list[float] = []

    for bm in bookmakers:
        for market in bm.get("markets", []):
            if market.get("key") != "h2h":
                continue
            outcomes = market.get("outcomes", [])
            raw = [1.0 / float(o["price"]) for o in outcomes if float(o.get("price", 0)) > 0]
            if not raw:
                continue
            total = sum(raw)
            fair = [p / total for p in raw]

            # Find the outcome matching the question
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
        return _crypto_edge(question, polymarket_prob, close_date)
    if category == "sports":
        return _sports_edge(question, polymarket_prob)
    return None, None
