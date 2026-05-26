"""
Critical minerals & mining intelligence.

Focus: Argentina's Lithium Triangle (Salta, Jujuy, Catamarca) + global
lithium/copper/rare earth supply chain signals.

Sources:
  - Mining Press Argentina (Spanish, local coverage)
  - Mining.com RSS (global)
  - USGS Mineral Resources news
  - Key ticker movers: lithium producers + Argentine plays

Investment context — Salta Province:
  - 2,000+ direct jobs, USD 14.6B projected investment over next decade
  - Key projects: Pastos Grandes (LAC), Cauchari-Olaroz (Lithium Americas/Ganfeng),
    Sal de Vida (Arcadium/Rio Tinto), Lindero (Fortuna Silver)
  - Bottleneck: technical workforce (geologists, engineers, lab techs)
  - Risk: Argentine macro (FX controls, policy), water rights, community consent
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger("intel.mining")

CACHE_TTL_SECONDS = 3600 * 4  # 4 hours
_cache: dict[str, tuple[float, list[dict]]] = {}


def _cached(key: str, ttl: int = CACHE_TTL_SECONDS) -> Optional[list[dict]]:
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < ttl:
            return data
    return None


def _store(key: str, data: list[dict]) -> list[dict]:
    _cache[key] = (time.time(), data)
    return data


# ── Keyword filters ───────────────────────────────────────────────────────────

_LITHIUM_KEYWORDS = [
    # Argentina-specific
    "salta", "jujuy", "catamarca", "puna", "litio", "lithium triangle",
    "cauchari", "olaroz", "pastos grandes", "sal de vida", "pozuelos",
    "rincon", "livent", "arcadium",
    # Global lithium supply chain
    "lithium", "lithium carbonate", "lithium hydroxide", "spodumene",
    "brine", "hard rock lithium", "DLE", "direct lithium extraction",
    "LFP", "NMC", "battery grade",
    # Key companies (Salta/Jujuy exposure)
    "lithium americas", "LAC", "ganfeng", "posco", "catl", "allkem",
    "livent", "albemarle", "SQM", "pilbara", "ioneer",
    "rio tinto", "fortuna silver",
    # Adjacent critical minerals
    "copper", "cobalt", "nickel", "rare earth", "REE", "graphite",
    "manganese", "vanadium",
    # Argentina macro / mining policy
    "RIGI", "régimen de incentivo", "minería argentina",
    "secretaría de minería", "inversión minera", "royalties",
    "YPF litio",
]

_ARGENTINA_KEYWORDS = [
    "argentina", "argentino", "salta", "jujuy", "catamarca", "neuquén",
    "san juan", "mendoza", "vaca muerta",
]


def _is_relevant(text: str) -> bool:
    t = text.lower()
    return any(kw.lower() in t for kw in _LITHIUM_KEYWORDS)


def _is_argentina_relevant(text: str) -> bool:
    t = text.lower()
    return any(kw.lower() in t for kw in _ARGENTINA_KEYWORDS + _LITHIUM_KEYWORDS)


# ── RSS fetcher ───────────────────────────────────────────────────────────────

def _fetch_rss(url: str, source_name: str, max_items: int = 20,
               relevance_fn=None) -> list[dict]:
    if relevance_fn is None:
        relevance_fn = _is_relevant
    try:
        import feedparser
        feed = feedparser.parse(url, request_headers={"User-Agent": "silicon-intel/1.0"})
    except ImportError:
        logger.error("feedparser not installed — run: pip install feedparser")
        return []
    except Exception as exc:
        logger.error("%s fetch failed: %s", source_name, exc)
        return []

    results = []
    for entry in feed.entries[:max_items]:
        title   = entry.get("title", "")
        summary = entry.get("summary", entry.get("description", ""))
        link    = entry.get("link", "")
        published = entry.get("published", entry.get("updated", ""))

        if not relevance_fn(f"{title} {summary}"):
            continue

        results.append({
            "source":    source_name,
            "title":     title,
            "summary":   summary[:400],
            "url":       link,
            "published": published,
        })
    return results


# ── Individual feeds ──────────────────────────────────────────────────────────

def fetch_mining_press_argentina(max_items: int = 20) -> list[dict]:
    """
    MiningPress.com.ar — best Spanish-language source for Argentine mining.
    Covers Salta/Jujuy project updates, policy, investment rounds.
    """
    cache_key = "mining_press_ar"
    if cached := _cached(cache_key):
        return cached

    results = _fetch_rss(
        "https://miningpress.com/feed/",
        "MiningPress AR",
        max_items,
        relevance_fn=_is_argentina_relevant,
    )
    logger.info("MiningPress AR: %d relevant items", len(results))
    return _store(cache_key, results)


def fetch_mining_com(max_items: int = 25) -> list[dict]:
    """
    Mining.com — global coverage, good for lithium price + company news.
    """
    cache_key = "mining_com"
    if cached := _cached(cache_key):
        return cached

    results = _fetch_rss(
        "https://www.mining.com/feed/",
        "Mining.com",
        max_items,
    )
    logger.info("Mining.com: %d relevant items", len(results))
    return _store(cache_key, results)


def fetch_kitco_metals(max_items: int = 15) -> list[dict]:
    """
    Kitco News — commodity prices + mining finance coverage.
    """
    cache_key = "kitco"
    if cached := _cached(cache_key):
        return cached

    results = _fetch_rss(
        "https://www.kitco.com/rss/Kitco-News.xml",
        "Kitco",
        max_items,
    )
    logger.info("Kitco: %d relevant items", len(results))
    return _store(cache_key, results)


def fetch_ambito_economia(max_items: int = 20) -> list[dict]:
    """
    Ambito Financiero — Argentine financial newspaper.
    Covers RIGI policy, mining investment, FX, country risk.
    """
    cache_key = "ambito"
    if cached := _cached(cache_key):
        return cached

    results = _fetch_rss(
        "https://www.ambito.com/rss/pages/economia.xml",
        "Ambito",
        max_items,
        relevance_fn=_is_argentina_relevant,
    )
    logger.info("Ambito: %d relevant items", len(results))
    return _store(cache_key, results)


# ── Lithium price tracker (via yfinance proxies) ──────────────────────────────

# Publicly traded lithium / Argentine mining proxies
LITHIUM_TICKERS = {
    "ALB":   "Albemarle — global lithium leader",
    "SQM":   "SQM — Chilean brine, regional bellwether",
    "LAC":   "Lithium Americas — Pastos Grandes (Salta) + Thacker Pass",
    "ALTM":  "Arcadium Lithium — Sal de Vida (Catamarca/Salta)",
    "PLL":   "Piedmont Lithium",
    "LTHM":  "Livent (now Arcadium) legacy ticker",
    "LIT":   "Global X Lithium & Battery Tech ETF",
    "COPX":  "Global X Copper Miners ETF — Argentina copper exposure",
}


def fetch_lithium_movers(threshold_pct: float = 2.0) -> list[dict]:
    """
    1-day moves for lithium producer tickers.
    Lower threshold than semicon (2% vs 3%) — lithium stocks are more volatile.
    """
    cache_key = f"lithium_movers_{threshold_pct}"
    if cached := _cached(cache_key, ttl=1800):
        return cached

    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed")
        return []

    tickers = list(LITHIUM_TICKERS.keys())
    results: list[dict] = []

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
                            "source":      "lithium-mover",
                            "ticker":      ticker,
                            "description": LITHIUM_TICKERS.get(ticker, ""),
                            "prev_close":  round(prev, 2),
                            "curr_close":  round(curr, 2),
                            "pct_change":  round(pct, 2),
                            "direction":   "up" if pct > 0 else "down",
                        })
            except Exception:
                pass

    except Exception as exc:
        logger.error("yfinance lithium download failed: %s", exc)

    logger.info("Lithium movers: %d tickers moved ≥ %.0f%%", len(results), threshold_pct)
    return _store(cache_key, results)


# ── Salta investment context (static, updated manually) ──────────────────────
# Key facts for the synthesizer's Argentina lens.

SALTA_CONTEXT = """
**Salta Province — Lithium Investment Snapshot (2025-2026)**
- Direct jobs: 2,000+ (lithium sector alone)
- Projected investment: USD 14.6B over next decade
- Key bottleneck: technical workforce (geologists, mining engineers, lab technicians)
- Active projects:
  - Pastos Grandes (Lithium Americas / LAC) — brine, construction phase
  - Cauchari-Olaroz (Lithium Americas + Ganfeng Lithium) — production stage
  - Sal de Vida (Arcadium Lithium / Rio Tinto) — development
  - Lindero (Fortuna Silver) — gold/silver, operating
- Regulatory framework: RIGI (Régimen de Incentivo para Grandes Inversiones)
  — 30-year tax/FX stability for investments > USD 200M
- Key risks: Argentine peso volatility, water rights in puna, community consent,
  grid connectivity, skilled labor shortage
- Infrastructure gap: road/rail to port (Antofagasta corridor), power supply
- Opportunity angle: local services, logistics, training/education providers,
  engineering firms, water treatment
"""


# ── Aggregated fetch ──────────────────────────────────────────────────────────

def fetch_all_mining() -> list[dict]:
    """Fetch all mining/lithium signals. Called from main intel scan loop."""
    signals: list[dict] = []
    signals.extend(fetch_mining_press_argentina())
    signals.extend(fetch_mining_com())
    signals.extend(fetch_kitco_metals())
    signals.extend(fetch_ambito_economia())
    signals.extend(fetch_lithium_movers())
    return signals


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import logging as _logging
    _logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")

    target = sys.argv[1] if len(sys.argv) > 1 else "all"

    print(SALTA_CONTEXT)

    if target in ("news", "all"):
        for fn, label in [
            (fetch_mining_press_argentina, "MiningPress AR"),
            (fetch_mining_com, "Mining.com"),
            (fetch_kitco_metals, "Kitco"),
            (fetch_ambito_economia, "Ambito"),
        ]:
            print(f"\n── {label} ──")
            for s in fn():
                print(f"  {s['title'][:90]}")

    if target in ("movers", "all"):
        print("\n── Lithium Price Movers ──")
        for s in fetch_lithium_movers():
            print(f"  {s['ticker']:6s} {s['pct_change']:+.1f}%  ${s['curr_close']}  — {s['description']}")
