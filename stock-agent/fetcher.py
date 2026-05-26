"""
Market data fetcher.

- yfinance   → OHLCV + computed technicals (free, unlimited)
- Alpha Vantage → news sentiment + fundamentals (25 calls/day free, cached 24h)
"""

import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests
import yfinance as yf
import pandas as pd

import config

# ── yfinance session with browser-like headers ────────────────────────────
_yf_session = requests.Session()
_yf_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
})

logger = logging.getLogger("fetcher")

# ── Alpha Vantage cache (in-memory, 24h TTL) ──────────────────────────────
_av_cache: dict[str, tuple[datetime, dict]] = {}
_AV_TTL = timedelta(hours=24)
_AV_BASE = "https://www.alphavantage.co/query"
_av_session = requests.Session()


def _av_get(params: dict) -> Optional[dict]:
    """Rate-limited Alpha Vantage call with 24h cache."""
    cache_key = json.dumps(sorted(params.items()))
    if cache_key in _av_cache:
        cached_at, data = _av_cache[cache_key]
        if datetime.now(timezone.utc) - cached_at < _AV_TTL:
            return data

    params["apikey"] = config.ALPHA_VANTAGE_KEY
    try:
        resp = _av_session.get(_AV_BASE, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if "Note" in data or "Information" in data:
            logger.warning("Alpha Vantage rate limit hit")
            return None
        _av_cache[cache_key] = (datetime.now(timezone.utc), data)
        return data
    except Exception as exc:
        logger.error("Alpha Vantage request failed: %s", exc)
        return None


# ── OHLCV + technicals via yfinance ──────────────────────────────────────

# ── Batch OHLCV cache (refreshed once per scan) ───────────────────────────
_ohlcv_cache: dict[str, pd.DataFrame] = {}
_ohlcv_cache_time: Optional[datetime] = None
_OHLCV_CACHE_TTL = timedelta(minutes=25)  # slightly less than scan interval


def prefetch_all_ohlcv(symbols: list[str], asset_types: list[str], period: str = "3mo") -> None:
    """
    Batch-download OHLCV for all symbols in one yf.download() call.
    Called once at the start of each scan — avoids per-ticker rate limits.
    """
    global _ohlcv_cache, _ohlcv_cache_time

    tickers = [f"{s}-USD" if t == "crypto" else s for s, t in zip(symbols, asset_types)]
    logger.info("Batch-fetching OHLCV for %d symbols…", len(tickers))
    try:
        raw = yf.download(
            tickers,
            period=period,
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=False,
            session=_yf_session,
        )
        _ohlcv_cache.clear()
        for sym, ticker_sym in zip(symbols, tickers):
            try:
                if len(tickers) == 1:
                    df = raw.copy()
                else:
                    df = raw[ticker_sym].dropna(how="all")
                if not df.empty:
                    _ohlcv_cache[sym] = df
                    logger.debug("Cached OHLCV for %s (%d bars)", sym, len(df))
                else:
                    logger.warning("No OHLCV data returned for %s", sym)
            except KeyError:
                logger.warning("No OHLCV data in batch for %s", sym)
        _ohlcv_cache_time = datetime.now(timezone.utc)
        logger.info("OHLCV batch complete — %d/%d symbols cached", len(_ohlcv_cache), len(symbols))
    except Exception as exc:
        logger.error("Batch OHLCV fetch failed: %s", exc)


def get_ohlcv(symbol: str, asset_type: str = "stock", period: str = "3mo") -> Optional[pd.DataFrame]:
    """Return daily OHLCV DataFrame. Uses batch cache if available, falls back to single fetch."""
    if symbol in _ohlcv_cache:
        return _ohlcv_cache[symbol]

    # Fallback: single fetch with backoff
    ticker_sym = f"{symbol}-USD" if asset_type == "crypto" else symbol
    for attempt in range(3):
        try:
            time.sleep(2 + attempt * 3)
            ticker = yf.Ticker(ticker_sym, session=_yf_session)
            df = ticker.history(period=period)
            if df.empty:
                logger.warning("No OHLCV data for %s", ticker_sym)
                return None
            return df
        except Exception as exc:
            if "Too Many Requests" in str(exc) and attempt < 2:
                logger.warning("yfinance rate limited for %s — retry %d/3", ticker_sym, attempt + 1)
                continue
            logger.error("yfinance error for %s: %s", ticker_sym, exc)
            return None
    return None


def get_current_price(symbol: str, asset_type: str = "stock") -> Optional[float]:
    ticker_sym = f"{symbol}-USD" if asset_type == "crypto" else symbol
    for attempt in range(3):
        try:
            time.sleep(1.0 + attempt * 2)
            ticker = yf.Ticker(ticker_sym, session=_yf_session)
            data = ticker.fast_info
            price = data.get("last_price") or data.get("regularMarketPrice")
            return float(price) if price else None
        except Exception as exc:
            if "Too Many Requests" in str(exc) and attempt < 2:
                logger.warning("yfinance rate limited for %s — retry %d/3", ticker_sym, attempt + 1)
                continue
            logger.error("Price fetch failed for %s: %s", ticker_sym, exc)
            return None
    return None


def compute_technicals(df: pd.DataFrame) -> dict:
    """
    Compute RSI(14), MACD(12,26,9), Bollinger Bands(20,2), SMA(20/50), volume ratio.
    Returns a flat dict of indicator values (latest bar).
    """
    close  = df["Close"]
    volume = df["Volume"]

    # RSI
    delta  = close.diff()
    gain   = delta.clip(lower=0).rolling(14).mean()
    loss   = (-delta.clip(upper=0)).rolling(14).mean()
    rs     = gain / loss.replace(0, float("nan"))
    rsi    = 100 - (100 / (1 + rs))

    # MACD
    ema12  = close.ewm(span=12, adjust=False).mean()
    ema26  = close.ewm(span=26, adjust=False).mean()
    macd   = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist   = macd - signal

    # Bollinger Bands
    sma20  = close.rolling(20).mean()
    std20  = close.rolling(20).std()
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20
    bb_pct   = (close - bb_lower) / (bb_upper - bb_lower)  # 0=lower, 1=upper

    # SMA crossover
    sma50  = close.rolling(50).mean()

    # Volume ratio (today vs 20-day avg)
    vol_avg   = volume.rolling(20).mean()
    vol_ratio = volume / vol_avg.replace(0, float("nan"))

    return {
        "price":      float(close.iloc[-1]),
        "rsi":        float(rsi.iloc[-1]),
        "macd":       float(macd.iloc[-1]),
        "macd_signal":float(signal.iloc[-1]),
        "macd_hist":  float(hist.iloc[-1]),
        "bb_pct":     float(bb_pct.iloc[-1]),
        "bb_upper":   float(bb_upper.iloc[-1]),
        "bb_lower":   float(bb_lower.iloc[-1]),
        "sma20":      float(sma20.iloc[-1]),
        "sma50":      float(sma50.iloc[-1]) if len(close) >= 50 else None,
        "vol_ratio":  float(vol_ratio.iloc[-1]),
        "price_chg_1d": float((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2]) if len(close) >= 2 else 0.0,
        "price_chg_5d": float((close.iloc[-1] - close.iloc[-6]) / close.iloc[-6]) if len(close) >= 6 else 0.0,
    }


# ── Alpha Vantage: news sentiment ─────────────────────────────────────────

def get_news_sentiment(symbol: str) -> Optional[dict]:
    """
    Returns latest news + overall sentiment score for a symbol.
    Cached 24h (AV free tier: 25 calls/day).
    """
    data = _av_get({"function": "NEWS_SENTIMENT", "tickers": symbol, "limit": "10"})
    if not data or "feed" not in data:
        return None

    feed = data["feed"]
    if not feed:
        return None

    # Aggregate sentiment scores across articles
    scores = []
    headlines = []
    for article in feed[:10]:
        for ts in article.get("ticker_sentiment", []):
            if ts.get("ticker") == symbol:
                try:
                    scores.append(float(ts["ticker_sentiment_score"]))
                except (KeyError, ValueError):
                    pass
        headlines.append(article.get("title", ""))

    avg_score = sum(scores) / len(scores) if scores else 0.0
    label = "Bullish" if avg_score > 0.15 else "Bearish" if avg_score < -0.15 else "Neutral"

    return {
        "avg_sentiment_score": round(avg_score, 3),
        "sentiment_label":     label,
        "article_count":       len(feed),
        "headlines":           headlines[:5],
    }


# ── Alpha Vantage: fundamentals ───────────────────────────────────────────

def get_fundamentals(symbol: str) -> Optional[dict]:
    """Company overview — P/E, market cap, sector. Cached 24h."""
    data = _av_get({"function": "OVERVIEW", "symbol": symbol})
    if not data or "Symbol" not in data:
        return None
    return {
        "sector":       data.get("Sector"),
        "pe_ratio":     data.get("PERatio"),
        "market_cap":   data.get("MarketCapitalization"),
        "52w_high":     data.get("52WeekHigh"),
        "52w_low":      data.get("52WeekLow"),
        "analyst_target": data.get("AnalystTargetPrice"),
        "description":  (data.get("Description") or "")[:300],
    }
