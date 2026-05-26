"""
Semiconductor supply chain intelligence.

Sources:
  - SEMI Book-to-Bill ratio (monthly press release RSS)
  - DigiTimes RSS — component spot prices + supply alerts
  - SemiEngineering RSS — process node + packaging news
  - MLCC / passive component signals via TTI / Mouser RSS
  - Component shortage tracker (manual watchlist driven)

Each fetch returns a list of signal dicts consumed by the synthesizer.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger("intel.semicon")

# ── Cache ──────────────────────────────────────────────────────────────────────
_cache: dict[str, tuple[float, list[dict]]] = {}
CACHE_TTL_SECONDS = 3600 * 4  # 4 hours — supply chain moves slowly


def _cached(key: str, ttl: int = CACHE_TTL_SECONDS) -> Optional[list[dict]]:
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < ttl:
            return data
    return None


def _store(key: str, data: list[dict]) -> list[dict]:
    _cache[key] = (time.time(), data)
    return data


# ── Supply chain watchlist ────────────────────────────────────────────────────
# Components to specifically watch for in news feeds.
# Second-order thinking: AI boom → which passive components get squeezed?
COMPONENT_WATCHLIST = [
    # Active components
    "HBM", "CoWoS", "COWOS", "advanced packaging", "chiplet",
    "TSMC", "Samsung foundry", "Intel Foundry", "SMIC",
    "ASML", "EUV", "DUV", "immersion lithography",
    "NVIDIA", "AMD", "Broadcom", "Marvell",
    # Passive / substrate constraints (the MLCC thesis)
    "MLCC", "capacitor", "substrate", "ABF substrate", "FC-BGA",
    "Murata", "TDK", "Yageo", "Kyocera", "Taiyo Yuden",
    "IBIDEN", "Shinko", "AT&S",
    # Memory
    "DRAM", "HBM3", "LPDDR", "DDR5", "NAND", "QLC", "3D NAND",
    "Micron", "SK Hynix", "Samsung memory",
    # Lead times / allocation keywords
    "allocation", "lead time", "spot price", "shortage", "supply crunch",
    "capacity constraint", "demand surge", "inventory correction",
    "double booking", "decommit",
]


def _is_semicon_relevant(text: str) -> bool:
    t = text.lower()
    return any(kw.lower() in t for kw in COMPONENT_WATCHLIST)


# ── RSS feed fetcher ──────────────────────────────────────────────────────────

def _fetch_rss(url: str, source_name: str, max_items: int = 15) -> list[dict]:
    """Generic RSS fetcher. Returns list of normalized signal dicts."""
    try:
        import feedparser
        feed = feedparser.parse(url)
        if feed.get("bozo") and not feed.entries:
            logger.warning("%s feed issue: %s", source_name, feed.get("bozo_exception", ""))
    except ImportError:
        logger.error("feedparser not installed — run: pip install feedparser")
        return []
    except Exception as exc:
        logger.error("%s RSS failed: %s", source_name, exc)
        return []

    results: list[dict] = []
    for entry in feed.entries[:max_items]:
        title   = entry.get("title", "")
        summary = entry.get("summary", entry.get("description", ""))
        link    = entry.get("link", "")
        published = entry.get("published", "")

        combined = f"{title} {summary}"
        if not _is_semicon_relevant(combined):
            continue

        results.append({
            "source":    source_name,
            "title":     title,
            "summary":   summary[:400],
            "url":       link,
            "published": published,
        })

    return results


# ── Individual feed fetchers ──────────────────────────────────────────────────

def fetch_semi_org(max_items: int = 10) -> list[dict]:
    """
    SEMI.org news RSS — book-to-bill, equipment orders, industry associations.
    Book-to-Bill > 1.0 = demand outpacing supply → bullish fab investment.
    """
    cache_key = "semi_org"
    if cached := _cached(cache_key):
        return cached

    results = _fetch_rss(
        "https://www.semi.org/en/rss.xml",
        "SEMI.org",
        max_items,
    )
    logger.info("SEMI.org: %d relevant items", len(results))
    return _store(cache_key, results)


def fetch_semiengineering(max_items: int = 20) -> list[dict]:
    """
    SemiEngineering.com — process node analysis, packaging, EDA news.
    Best source for CoWoS/chiplet/substrate deep dives.
    """
    cache_key = "semiengineering"
    if cached := _cached(cache_key):
        return cached

    results = _fetch_rss(
        "https://semiengineering.com/feed/",
        "SemiEngineering",
        max_items,
    )
    logger.info("SemiEngineering: %d relevant items", len(results))
    return _store(cache_key, results)


def fetch_eetimes(max_items: int = 20) -> list[dict]:
    """
    EE Times — component news, supply chain alerts, industry briefings.
    Good for MLCC / passive component coverage.
    """
    cache_key = "eetimes"
    if cached := _cached(cache_key):
        return cached

    results = _fetch_rss(
        "https://www.eetimes.com/feed/",
        "EE Times",
        max_items,
    )
    logger.info("EE Times: %d relevant items", len(results))
    return _store(cache_key, results)


def fetch_anandtech_archive(max_items: int = 10) -> list[dict]:
    """
    Tom's Hardware RSS — covers chip launches, supply, benchmark leaks.
    (AnandTech is archived — Tom's Hardware is the live successor.)
    """
    cache_key = "tomshardware"
    if cached := _cached(cache_key):
        return cached

    results = _fetch_rss(
        "https://www.tomshardware.com/feeds/all",
        "Tom's Hardware",
        max_items,
    )
    logger.info("Tom's Hardware: %d relevant items", len(results))
    return _store(cache_key, results)


def fetch_theregister_hardware(max_items: int = 10) -> list[dict]:
    """
    The Register — chips + data centre coverage.
    Good for supply chain alerts and vendor announcements.
    """
    cache_key = "theregister"
    if cached := _cached(cache_key):
        return cached

    results = _fetch_rss(
        "https://www.theregister.com/headlines.atom",
        "The Register",
        max_items,
    )
    logger.info("The Register: %d relevant items", len(results))
    return _store(cache_key, results)


# ── Watchlist stock price signal (via yfinance) ───────────────────────────────
# Tracks 1-day moves for semicon stocks as a proxy for supply chain news.

SEMICONDUCTOR_TICKERS = [
    "NVDA", "AMD", "INTC", "TSM", "ASML", "AVGO", "AMAT", "KLAC",
    "LRCX", "MRVL", "SMCI", "ARM", "MU", "WDC",
]

# Japanese/Korean passive component proxies (MLCC thesis)
PASSIVE_TICKERS_ADR = [
    "6981.T",  # Murata Manufacturing
    "6762.T",  # TDK
    "2327.T",  # Yageo (Taiwan)
]


def fetch_semicon_movers(threshold_pct: float = 3.0) -> list[dict]:
    """
    Fetch 1-day price moves for semiconductor tickers.
    Returns only tickers that moved more than threshold_pct.
    Significant moves often precede or follow supply chain announcements.
    """
    cache_key = f"semicon_movers_{threshold_pct}"
    if cached := _cached(cache_key, ttl=1800):  # 30-min cache
        return cached

    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed — run: pip install yfinance")
        return []

    results: list[dict] = []
    tickers = SEMICONDUCTOR_TICKERS  # skip ADR for now — often illiquid

    try:
        data = yf.download(
            tickers,
            period="2d",
            interval="1d",
            progress=False,
            auto_adjust=True,
            timeout=10,
        )
        closes = data["Close"]

        for ticker in tickers:
            try:
                col = closes[ticker] if ticker in closes.columns else closes
                if hasattr(col, "iloc") and len(col) >= 2:
                    prev, curr = float(col.iloc[-2]), float(col.iloc[-1])
                    pct = (curr - prev) / prev * 100
                    if abs(pct) >= threshold_pct:
                        results.append({
                            "source":     "price-mover",
                            "ticker":     ticker,
                            "prev_close": round(prev, 2),
                            "curr_close": round(curr, 2),
                            "pct_change": round(pct, 2),
                            "direction":  "up" if pct > 0 else "down",
                            "signal":     f"{ticker} moved {pct:+.1f}% — watch for supply/demand news",
                        })
            except Exception:
                pass

    except Exception as exc:
        logger.error("yfinance download failed: %s", exc)

    logger.info("Semicon movers: %d tickers moved ≥ %.0f%%", len(results), threshold_pct)
    return _store(cache_key, results)


# ── Aggregated fetch ──────────────────────────────────────────────────────────

def fetch_all_semicon() -> list[dict]:
    """
    Fetch all semiconductor supply chain signals.
    Called from the main intelligence scan loop.
    """
    signals: list[dict] = []
    signals.extend(fetch_semi_org())
    signals.extend(fetch_semiengineering())
    signals.extend(fetch_eetimes())
    signals.extend(fetch_theregister_hardware())
    signals.extend(fetch_semicon_movers(threshold_pct=3.0))
    return signals


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    target = sys.argv[1] if len(sys.argv) > 1 else "all"

    if target in ("semi", "all"):
        print("\n── SEMI.org ──")
        for s in fetch_semi_org():
            print(f"  [{s['published'][:10]}] {s['title']}")

    if target in ("news", "all"):
        for src_fn, label in [
            (fetch_semiengineering, "SemiEngineering"),
            (fetch_eetimes, "EE Times"),
            (fetch_theregister_hardware, "The Register"),
        ]:
            print(f"\n── {label} ──")
            for s in src_fn():
                print(f"  {s['title'][:80]}")

    if target in ("movers", "all"):
        print("\n── Semicon Price Movers ──")
        for s in fetch_semicon_movers():
            print(f"  {s['ticker']:6s} {s['pct_change']:+.1f}%  ${s['curr_close']}")
