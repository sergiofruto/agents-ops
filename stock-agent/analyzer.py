"""
Signal analyzer — rule-based + LLM synthesis.

Rule layer:  RSI, MACD, Bollinger Bands, SMA crossover, volume spike
LLM layer:   Claude API synthesizes all signals + news → BUY/SELL/HOLD + confidence

Returns a TradeSignal dataclass or None if no actionable signal.
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

import anthropic

import config
import fetcher
import database

logger = logging.getLogger("analyzer")


@dataclass
class TradeSignal:
    symbol:        str
    asset_type:    str          # 'stock' | 'crypto'
    direction:     str          # 'BUY' | 'SELL'
    confidence:    float        # 0.0 – 1.0
    entry_price:   float
    rule_signals:  list[str]    # human-readable list of fired rules
    reasoning:     str          # LLM explanation


# ── Rule engine ───────────────────────────────────────────────────────────

def _run_rules(tech: dict) -> tuple[list[str], list[str]]:
    """
    Returns (buy_signals, sell_signals) as lists of fired rule names.
    Each fired rule is a string like "RSI oversold (28.4)".
    """
    buy, sell = [], []
    rsi   = tech.get("rsi")
    mhist = tech.get("macd_hist")
    bpct  = tech.get("bb_pct")
    sma20 = tech.get("sma20")
    sma50 = tech.get("sma50")
    vrat  = tech.get("vol_ratio", 1.0)

    # RSI
    if rsi is not None:
        if rsi < 32:
            buy.append(f"RSI oversold ({rsi:.1f})")
        elif rsi > 68:
            sell.append(f"RSI overbought ({rsi:.1f})")

    # MACD histogram direction
    if mhist is not None:
        if mhist > 0 and tech.get("macd", 0) > tech.get("macd_signal", 0):
            buy.append(f"MACD bullish crossover (hist={mhist:.3f})")
        elif mhist < 0 and tech.get("macd", 0) < tech.get("macd_signal", 0):
            sell.append(f"MACD bearish crossover (hist={mhist:.3f})")

    # Bollinger Bands
    if bpct is not None:
        if bpct < 0.05:
            buy.append(f"Price near lower Bollinger Band (bb%={bpct:.2f})")
        elif bpct > 0.95:
            sell.append(f"Price near upper Bollinger Band (bb%={bpct:.2f})")

    # SMA crossover (20 vs 50)
    if sma20 and sma50:
        if sma20 > sma50 * 1.005:
            buy.append(f"SMA20 above SMA50 ({sma20:.2f} > {sma50:.2f})")
        elif sma20 < sma50 * 0.995:
            sell.append(f"SMA20 below SMA50 ({sma20:.2f} < {sma50:.2f})")

    # Volume confirmation
    if vrat and vrat > 1.8:
        note = f"Volume spike ({vrat:.1f}x avg)"
        if buy:
            buy.append(note)
        elif sell:
            sell.append(note)

    return buy, sell


# ── LLM synthesis ─────────────────────────────────────────────────────────

def _llm_synthesize(
    symbol: str,
    asset_type: str,
    tech: dict,
    buy_signals: list[str],
    sell_signals: list[str],
    news: Optional[dict],
    fundamentals: Optional[dict],
) -> tuple[str, float, str]:
    """
    Ask Claude to synthesize signals and return (direction, confidence, reasoning).
    Falls back to rule-based direction if LLM unavailable.
    """
    if not config.ANTHROPIC_API_KEY:
        direction  = "BUY" if len(buy_signals) > len(sell_signals) else "SELL"
        confidence = min(0.5 + 0.1 * max(len(buy_signals), len(sell_signals)), 0.85)
        return direction, round(confidence, 2), "LLM unavailable — rule-based fallback"

    news_block = ""
    if news:
        news_block = f"""
News sentiment: {news['sentiment_label']} (score={news['avg_sentiment_score']})
Recent headlines:
{chr(10).join('- ' + h for h in news['headlines'][:3])}
"""

    fund_block = ""
    if fundamentals:
        fund_block = f"""
Fundamentals: sector={fundamentals.get('sector')}, P/E={fundamentals.get('pe_ratio')}, analyst target={fundamentals.get('analyst_target')}
"""

    prompt = f"""You are a quantitative trading analyst. Analyze the following signals for {symbol} ({asset_type}) and decide whether to BUY, SELL, or HOLD.

Technical snapshot:
- Price: ${tech['price']:.4f}
- RSI(14): {tech.get('rsi', 'N/A'):.1f}
- MACD histogram: {tech.get('macd_hist', 'N/A'):.4f}
- Bollinger Band %: {tech.get('bb_pct', 'N/A'):.2f}
- 1d change: {tech.get('price_chg_1d', 0)*100:.2f}%
- 5d change: {tech.get('price_chg_5d', 0)*100:.2f}%
- Volume ratio: {tech.get('vol_ratio', 1):.1f}x

BUY signals fired: {buy_signals or 'none'}
SELL signals fired: {sell_signals or 'none'}
{news_block}{fund_block}
Respond ONLY with a JSON object:
{{"direction": "BUY" | "SELL" | "HOLD", "confidence": 0.0-1.0, "reasoning": "1-2 sentence explanation"}}"""

    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        # strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        return result["direction"], float(result["confidence"]), result["reasoning"]
    except Exception as exc:
        logger.warning("LLM synthesis failed for %s: %s", symbol, exc)
        direction  = "BUY" if len(buy_signals) > len(sell_signals) else "SELL"
        confidence = min(0.5 + 0.1 * max(len(buy_signals), len(sell_signals)), 0.85)
        return direction, round(confidence, 2), "LLM error — rule-based fallback"


# ── Public API ────────────────────────────────────────────────────────────

def analyze(symbol: str, asset_type: str) -> Optional[TradeSignal]:
    """
    Full pipeline for one symbol:
      1. Fetch OHLCV + compute technicals
      2. Run rule engine
      3. Fetch news + fundamentals (AV, cached)
      4. LLM synthesis
      5. Return TradeSignal if actionable, else None
    """
    logger.info("Analyzing %s (%s)", symbol, asset_type)

    df = fetcher.get_ohlcv(symbol, asset_type)
    if df is None or len(df) < 26:
        logger.warning("Insufficient OHLCV data for %s", symbol)
        return None

    tech = fetcher.compute_technicals(df)
    database.save_price_snapshot(symbol, tech["price"])

    buy_signals, sell_signals = _run_rules(tech)
    total_rules = len(buy_signals) + len(sell_signals)

    if total_rules < config.MIN_RULE_SIGNALS:
        logger.info(
            "%s: only %d rule signals (min=%d) — skipping LLM",
            symbol, total_rules, config.MIN_RULE_SIGNALS,
        )
        return None

    # Only fetch AV data if we have enough rule signals to justify a call
    news         = fetcher.get_news_sentiment(symbol) if asset_type == "stock" else None
    fundamentals = fetcher.get_fundamentals(symbol)   if asset_type == "stock" else None

    direction, confidence, reasoning = _llm_synthesize(
        symbol, asset_type, tech,
        buy_signals, sell_signals, news, fundamentals,
    )

    all_signals = buy_signals if direction == "BUY" else sell_signals

    database.save_signal(
        symbol=symbol,
        asset_type=asset_type,
        direction=direction,
        confidence=confidence,
        rule_signals=json.dumps(all_signals),
        reasoning=reasoning,
        acted=False,
    )

    if direction == "HOLD":
        logger.info("%s → HOLD (confidence=%.2f)", symbol, confidence)
        return None

    if confidence < config.MIN_CONFIDENCE:
        logger.info(
            "%s → %s but confidence %.2f < threshold %.2f — skipping",
            symbol, direction, confidence, config.MIN_CONFIDENCE,
        )
        return None

    logger.info(
        "%s → %s confidence=%.2f signals=%s",
        symbol, direction, confidence, all_signals,
    )

    return TradeSignal(
        symbol=symbol,
        asset_type=asset_type,
        direction=direction,
        confidence=confidence,
        entry_price=tech["price"],
        rule_signals=all_signals,
        reasoning=reasoning,
    )
