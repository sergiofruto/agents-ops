import json
import logging
import re
from typing import Optional

import requests
import config

logger = logging.getLogger(__name__)

SESSION = requests.Session()
SESSION.headers.update({"Accept": "application/json"})

_TIMEOUT = 10  # seconds

# Regex to extract "Team A vs Team B" from Dota market questions.
# Handles formats like:
#   "Dota 2: Aurora vs Xtreme Gaming (BO3)"
#   "Will Team Liquid win vs OG? (BO5)"
_VS_RE = re.compile(
    r"(?:dota\s*2\s*[:\-]\s*)?([^vV]+?)\s+vs\.?\s+([^\(\?]+)",
    re.IGNORECASE,
)


def fetch_dota_markets(limit: int = 500) -> list[dict]:
    """
    Fetch active Polymarket markets and client-side filter to Dota 2 moneyline markets.
    """
    url = f"{config.GAMMA_BASE}/markets"
    params = {
        "active": "true",
        "limit": limit,
        "order": "volume24hr",
        "ascending": "false",
    }
    try:
        resp = SESSION.get(url, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            markets = data
        else:
            markets = data.get("data", data.get("markets", []))
    except Exception as exc:
        logger.warning("fetch_dota_markets failed: %s", exc)
        return []

    dota_markets = []
    for m in markets:
        question   = m.get("question", "").lower()
        sport_type = m.get("sportsMarketType", "")
        # Accept moneyline (match winner) and child_moneyline (per-game winner).
        # Also accept markets where the field is absent but "dota" is in the question
        # (some Polymarket markets omit the field entirely).
        is_money = sport_type in ("moneyline", "child_moneyline") or sport_type == ""
        if "dota" in question and is_money:
            dota_markets.append(m)

    logger.info(
        "Fetched %d total markets; %d are Dota 2 (moneyline/child_moneyline)",
        len(markets),
        len(dota_markets),
    )
    return dota_markets


def parse_match_teams(market: dict) -> Optional[tuple[str, str]]:
    """
    Extract (team_a, team_b) from market question string.
    Returns None if parsing fails.
    """
    question = market.get("question", "")
    m = _VS_RE.search(question)
    if not m:
        return None
    team_a = m.group(1).strip().strip("'\"")
    team_b = m.group(2).strip().strip("'\"")
    # Remove trailing format hints like "(BO3)", "?"
    team_a = re.sub(r"\s*[\(\?].*$", "", team_a).strip()
    team_b = re.sub(r"\s*[\(\?].*$", "", team_b).strip()
    if not team_a or not team_b:
        return None
    return team_a, team_b


def fetch_clob_spread(token_id: str) -> Optional[float]:
    """
    Query CLOB API for best buy and sell prices; return the spread.
    Returns None if data unavailable.
    """
    try:
        buy_resp  = SESSION.get(
            f"{config.CLOB_BASE}/price",
            params={"token_id": token_id, "side": "buy"},
            timeout=_TIMEOUT,
        )
        sell_resp = SESSION.get(
            f"{config.CLOB_BASE}/price",
            params={"token_id": token_id, "side": "sell"},
            timeout=_TIMEOUT,
        )
        buy_resp.raise_for_status()
        sell_resp.raise_for_status()

        best_ask = float(buy_resp.json().get("price", 0))
        best_bid = float(sell_resp.json().get("price", 0))

        if best_ask <= 0 or best_bid <= 0:
            return None
        return round(best_ask - best_bid, 6)
    except Exception as exc:
        logger.debug("fetch_clob_spread(%s) failed: %s", token_id, exc)
        return None


def fetch_market_detail(condition_id: str) -> dict:
    """
    Fetch detailed market data from Gamma API by condition_id.
    Returns {} on failure.
    """
    try:
        resp = SESSION.get(
            f"{config.GAMMA_BASE}/markets/{condition_id}",
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("fetch_market_detail(%s) failed: %s", condition_id, exc)
        return {}


def parse_outcome_prices(market: dict) -> list[float]:
    raw = market.get("outcomePrices", [])
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return []
    try:
        return [float(p) for p in raw]
    except Exception:
        return []


def parse_clob_token_ids(market: dict) -> list[str]:
    raw = market.get("clobTokenIds", [])
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return []
    return [str(t) for t in raw]


def parse_outcomes(market: dict) -> list[str]:
    raw = market.get("outcomes", [])
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return []
    return [str(o) for o in raw]
