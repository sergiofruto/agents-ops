import logging
from typing import Optional
import requests
import config

logger = logging.getLogger(__name__)

SESSION = requests.Session()
SESSION.headers.update({"Accept": "application/json"})

_TIMEOUT = 10  # seconds


def fetch_active_markets(limit: int = 200) -> list[dict]:
    """
    Fetch active markets from Gamma API ordered by 24h volume descending.
    Returns a list of market dicts (may be empty on error).
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
        # Gamma returns either a list directly or {"data": [...]}
        if isinstance(data, list):
            return data
        return data.get("data", data.get("markets", []))
    except Exception as exc:
        logger.warning("fetch_active_markets failed: %s", exc)
        return []


def fetch_clob_spread(token_id: str) -> Optional[float]:
    """
    Query CLOB API for best buy and sell prices, return the spread.
    Spread = best_ask - best_bid (as a fraction, e.g. 0.03 = 3%)
    Returns None if data is unavailable.
    """
    try:
        buy_resp  = SESSION.get(f"{config.CLOB_BASE}/price",
                                params={"token_id": token_id, "side": "buy"},
                                timeout=_TIMEOUT)
        sell_resp = SESSION.get(f"{config.CLOB_BASE}/price",
                                params={"token_id": token_id, "side": "sell"},
                                timeout=_TIMEOUT)
        buy_resp.raise_for_status()
        sell_resp.raise_for_status()

        best_ask = float(buy_resp.json().get("price", 0))   # cost to buy YES
        best_bid = float(sell_resp.json().get("price", 0))  # amount from selling YES

        if best_ask <= 0 or best_bid <= 0:
            return None
        return round(best_ask - best_bid, 6)
    except Exception as exc:
        logger.debug("fetch_clob_spread(%s) failed: %s", token_id, exc)
        return None


def fetch_midpoint(token_id: str) -> Optional[float]:
    """
    Fetch CLOB mid-point price for a token.
    Returns None on failure.
    """
    try:
        resp = SESSION.get(
            f"{config.CLOB_BASE}/midpoint",
            params={"token_id": token_id},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return float(resp.json().get("mid", 0)) or None
    except Exception as exc:
        logger.debug("fetch_midpoint(%s) failed: %s", token_id, exc)
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
