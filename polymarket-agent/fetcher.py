import logging
import time
from typing import Optional
import requests
import config

logger = logging.getLogger(__name__)

SESSION = requests.Session()
SESSION.headers.update({"Accept": "application/json"})

_TIMEOUT = 10  # seconds
_RETRY_DELAYS = (0, 2, 5)  # seconds before each attempt (3 total)


def _get(url: str, params: dict | None = None, *, label: str = "") -> Optional[requests.Response]:
    """
    GET with exponential backoff retry. Returns the Response on success, None on failure.
    Retries on network errors and 5xx/429 responses.
    """
    for attempt, delay in enumerate(_RETRY_DELAYS):
        if delay:
            time.sleep(delay)
        try:
            resp = SESSION.get(url, params=params, timeout=_TIMEOUT)
            if resp.status_code in (429, 502, 503, 504):
                logger.debug(
                    "%s HTTP %d (attempt %d/%d) — retrying",
                    label or url, resp.status_code, attempt + 1, len(_RETRY_DELAYS),
                )
                continue
            resp.raise_for_status()
            return resp
        except requests.exceptions.ConnectionError as exc:
            logger.debug("%s connection error (attempt %d): %s", label or url, attempt + 1, exc)
        except requests.exceptions.Timeout:
            logger.debug("%s timed out (attempt %d)", label or url, attempt + 1)
        except Exception as exc:
            logger.debug("%s error (attempt %d): %s", label or url, attempt + 1, exc)
    logger.warning("%s failed after %d attempts", label or url, len(_RETRY_DELAYS))
    return None


def fetch_active_markets(limit: int = 200) -> list[dict]:
    """
    Fetch active markets from Gamma API ordered by 24h volume descending.
    Returns a list of market dicts (may be empty on error).
    """
    resp = _get(
        f"{config.GAMMA_BASE}/markets",
        params={"active": "true", "limit": limit, "order": "volume24hr", "ascending": "false"},
        label="fetch_active_markets",
    )
    if resp is None:
        return []
    data = resp.json()
    if isinstance(data, list):
        return data
    return data.get("data", data.get("markets", []))


def fetch_clob_spread(token_id: str) -> Optional[float]:
    """
    Query CLOB API for best buy and sell prices, return the spread.
    Spread = best_ask - best_bid (as a fraction, e.g. 0.03 = 3%)
    Returns None if data is unavailable.
    """
    buy_resp  = _get(f"{config.CLOB_BASE}/price", {"token_id": token_id, "side": "buy"},
                     label=f"clob_spread_buy/{token_id[:8]}")
    sell_resp = _get(f"{config.CLOB_BASE}/price", {"token_id": token_id, "side": "sell"},
                     label=f"clob_spread_sell/{token_id[:8]}")
    if buy_resp is None or sell_resp is None:
        return None
    best_ask = float(buy_resp.json().get("price", 0))
    best_bid = float(sell_resp.json().get("price", 0))
    if best_ask <= 0 or best_bid <= 0:
        return None
    return round(best_ask - best_bid, 6)


def fetch_midpoint(token_id: str) -> Optional[float]:
    """
    Fetch CLOB mid-point price for a token.
    Returns None on failure.
    """
    resp = _get(
        f"{config.CLOB_BASE}/midpoint",
        {"token_id": token_id},
        label=f"midpoint/{token_id[:8]}",
    )
    if resp is None:
        return None
    return float(resp.json().get("mid", 0)) or None


def fetch_market_detail(condition_id: str) -> dict:
    """
    Fetch detailed market data from Gamma API by condition_id.
    Returns {} on failure.
    """
    resp = _get(
        f"{config.GAMMA_BASE}/markets/{condition_id}",
        label=f"market_detail/{condition_id[:8]}",
    )
    return resp.json() if resp is not None else {}
