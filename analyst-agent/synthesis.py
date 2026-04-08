"""
synthesis.py — The Analyst's unified prediction engine
=======================================================
Takes raw signals (infosec, OSINT, cosmic) and produces a structured
brief in The Analyst's voice.

The brief follows a fixed schema:
  1. Opening quote (Hermetic or Dionysian)
  2. Threat level determination
  3. Cyber/OSINT body — technical signals
  4. Cosmic body — sky weather, Hermetic principle applied
  5. Synthesis — unified prediction, Dionysian interpretation

The Hermetic Principle of Correspondence underlies every brief:
"That which is Above corresponds to that which is Below."
The analyst does not believe the stars *cause* events. He believes
they are running on the same clock.
"""

from __future__ import annotations

import logging
import random
import sqlite3
from datetime import datetime

import database
import persona

logger = logging.getLogger("synthesis")


# ---------------------------------------------------------------------------
# Severity scoring
# ---------------------------------------------------------------------------

_SEV_RANK = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "INFO": 1, "UNKNOWN": 0}


def _aggregate_severity(signals: list[sqlite3.Row]) -> str:
    if not signals:
        return "LOW"
    peak = max(_SEV_RANK.get(s["severity"], 0) for s in signals)
    return next(k for k, v in _SEV_RANK.items() if v == peak)


def _threat_level_from_signals(signals: list[sqlite3.Row]) -> str:
    sev = _aggregate_severity(signals)
    cosmic = [s for s in signals if s["source"] == "cosmic"]
    infosec = [s for s in signals if s["signal_type"] == "infosec"]
    geo = [s for s in signals if s["signal_type"] == "geopolitical"]

    # Elevate if multiple domain convergence
    active_domains = sum([bool(cosmic), bool(infosec), bool(geo)])
    if active_domains >= 3 and sev in ("HIGH", "CRITICAL"):
        return "CRITICAL"
    return sev


# ---------------------------------------------------------------------------
# Body builders
# ---------------------------------------------------------------------------

def _build_cyber_body(signals: list[sqlite3.Row]) -> str:
    infosec_sigs = [s for s in signals if s["signal_type"] in ("infosec",)]
    geo_sigs     = [s for s in signals if s["signal_type"] == "geopolitical"]

    parts = []

    if infosec_sigs:
        parts.append("[ INFOSEC FEED ]")
        for s in infosec_sigs[:6]:
            parts.append(f"  [{s['severity']}] {s['title']}")
            parts.append(f"    {s['body'][:200].rstrip()}")
        parts.append("")

    if geo_sigs:
        parts.append("[ GEOPOLITICAL / OSINT ]")
        for s in geo_sigs[:4]:
            parts.append(f"  [{s['severity']}] {s['title']}")
            parts.append(f"    {s['body'][:200].rstrip()}")
        parts.append("")

    # Dionysian disruption check
    all_titles = " ".join(s["title"] for s in signals)
    matching = [d for d in persona.DIONYSIAN_SIGNALS
                if any(kw.lower() in all_titles.lower()
                       for kw in d.lower().split()[:3])]
    if matching:
        parts.append("[ DIONYSIAN SIGNAL — IRRATIONAL VECTOR DETECTED ]")
        for m in matching[:2]:
            parts.append(f"  ⟡ {m}")
        parts.append("")

    return "\n".join(parts) or "No significant cyber/OSINT signals in this cycle."


def _build_cosmic_body(signals: list[sqlite3.Row]) -> str:
    cosmic_sigs = [s for s in signals if s["source"] == "cosmic"]
    if not cosmic_sigs:
        snap = database.get_latest_cosmic()
        if not snap:
            return "No cosmic data available for this brief."
        body = snap["dominant_themes"]
        moon = snap["moon_phase"]
        retro = bool(snap["mercury_retrograde"])
    else:
        body = cosmic_sigs[0]["body"]
        return body

    import json
    themes = json.loads(body) if isinstance(body, str) else body

    parts = [
        f"Moon Phase: {moon}",
        f"Mercury: {'RETROGRADE — watch communications' if retro else 'Direct'}",
        "",
        "Dominant Cosmic Themes:",
    ]
    for t in themes:
        parts.append(f"  • {t}")
    return "\n".join(parts)


def _choose_hermetic_lens(signals: list[sqlite3.Row]) -> persona.HermeticLens:
    types = {s["signal_type"] for s in signals}
    if "cosmic" in types and ("infosec" in types or "geopolitical" in types):
        return random.choice(persona.HERMETIC_LENSES[:2])  # Mentalism or Correspondence
    if "infosec" in types:
        return persona.get_principle_for_signal("network")
    if "geopolitical" in types:
        return persona.get_principle_for_signal("geopolitical")
    return persona.get_principle_for_signal("cosmic")


def _build_synthesis(
    signals: list[sqlite3.Row],
    threat_level: str,
    lens: persona.HermeticLens,
) -> str:
    infosec_count = sum(1 for s in signals if s["signal_type"] == "infosec")
    geo_count     = sum(1 for s in signals if s["signal_type"] == "geopolitical")
    cosmic_sig    = next((s for s in signals if s["source"] == "cosmic"), None)

    parts = [
        f"HERMETIC PRINCIPLE IN PLAY: {lens.principle.upper()}",
        f"  \"{lens.maxim}\"",
        "",
        f"  Cyber application: {lens.cyber_application}",
        f"  Cosmic application: {lens.cosmic_application}",
        "",
    ]

    # Threat assessment
    parts.append(f"THREAT ASSESSMENT: {threat_level}")

    if threat_level in ("CRITICAL", "HIGH"):
        parts.append(
            "  The grid is vibrating. Multiple domain convergence detected. "
            "What appears in the sky and what appears in the logs are running "
            "on the same clock — as Trismegistus wrote: the measure is the same "
            "above and below. Do not dismiss either."
        )
    elif threat_level == "MEDIUM":
        parts.append(
            "  Moderate activity. The Dionysian undercurrent is present but "
            "has not yet broken through the Apollonian surface. Watch for "
            "the irrational move — the campaign that does not fit the model."
        )
    else:
        parts.append(
            "  The surface is calm. But my mother said: calm before a storm "
            "is still the storm. Maintain posture. The vine of Dionysus grows "
            "quietly before it breaks the walls."
        )

    parts.append("")

    # Mother's note
    parts.append(f"  [ {random.choice(persona.MOTHERS_WORDS)} ]")
    parts.append("")

    # Archetype alert
    if infosec_count > 0:
        archetype = random.choice(list(persona.THREAT_ARCHETYPES.items()))
        parts.append(f"ACTIVE ARCHETYPE — {archetype[0]}")
        parts.append(f"  {archetype[1]}")
        parts.append("")

    parts.append(
        "RECOMMENDATION: Maintain dual awareness. Read the logs. "
        "Then step outside and look at the sky. Both are true."
    )

    return "\n".join(parts)


def _build_title(signals: list[sqlite3.Row], threat_level: str) -> str:
    cosmic = next((s for s in signals if s["source"] == "cosmic"), None)
    moon_phase = ""
    if cosmic:
        # Parse moon from title "Sky Report — Full Moon | 7 active aspects"
        title_parts = cosmic["title"].split("—")
        if len(title_parts) > 1:
            moon_phase = title_parts[1].split("|")[0].strip()

    date_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    moon_tag = f" [{moon_phase}]" if moon_phase else ""
    return f"Intelligence Brief — {date_str} | {threat_level}{moon_tag}"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def synthesise() -> int | None:
    """
    Pull unused signals, build a brief, persist it. Returns brief ID or None.
    """
    logger.info("=== SYNTHESIS STARTED ===")
    signals = database.get_unused_signals(limit=30)

    if not signals:
        logger.info("No unused signals available — skipping brief")
        return None

    threat_level = _threat_level_from_signals(signals)
    lens         = _choose_hermetic_lens(signals)
    quote        = persona.opening_quote()
    title        = _build_title(signals, threat_level)
    summary      = (
        f"Cycle analysed {len(signals)} signals across "
        f"{len({s['source'] for s in signals})} sources. "
        f"Threat level: {threat_level}. "
        f"Hermetic lens: {lens.principle}."
    )

    cyber_body   = _build_cyber_body(signals)
    cosmic_body  = _build_cosmic_body(signals)
    synthesis    = _build_synthesis(signals, threat_level, lens)

    signal_ids = [s["id"] for s in signals]
    brief_id   = database.save_brief(
        title=title,
        threat_level=threat_level,
        summary=summary,
        cyber_body=cyber_body,
        cosmic_body=cosmic_body,
        synthesis=synthesis,
        opening_quote=quote,
        hermetic_principle=lens.principle,
        signal_ids=signal_ids,
    )

    database.mark_signals_used(signal_ids)

    logger.info("=== SYNTHESIS COMPLETE  brief_id=%d  level=%s ===", brief_id, threat_level)
    return brief_id
