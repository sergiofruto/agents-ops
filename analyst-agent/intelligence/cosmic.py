"""
intelligence/cosmic.py — Cosmic weather analysis
=================================================
"The sky is not decoration. It is the original broadcast medium."
  — The Analyst's mother

Uses ephem to compute:
  • Planetary positions (sign, degree, house)
  • Active aspects between planets (conjunction, opposition, square, trine, sextile)
  • Moon phase
  • Mercury retrograde status
  • Dominant themes derived from Hermetic correspondence

The Analyst interprets sky patterns through the Hermetic Principle of
Correspondence: what unfolds at the macrocosmic level echoes in the
microcosmic — markets, networks, geopolitics.

Planetary cyber correspondences (mother's notes, annotated):
  Mercury  — networks, comms, data transit, supply chains
  Venus    — alliances, finance, soft power
  Mars     — aggression, kinetic ops, offensive campaigns
  Jupiter  — expansion, espionage scale, overreach
  Saturn   — infrastructure, control systems, sanctions, walls
  Uranus   — disruption, zero-days, unexpected pivots
  Neptune  — deception, disinformation, fog of war
  Pluto    — transformation, hidden power, state-level covert ops
  Moon     — public sentiment, social media currents, timing
  Sun      — leadership targets, critical infrastructure
"""

from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import NamedTuple

import ephem

import config
import database

logger = logging.getLogger("cosmic")


# ---------------------------------------------------------------------------
# Aspect definitions
# ---------------------------------------------------------------------------

class AspectDef(NamedTuple):
    name:   str
    angle:  float   # degrees
    orb:    float   # degrees
    nature: str     # harmonious / tense / neutral


ASPECTS: list[AspectDef] = [
    AspectDef("Conjunction",  0.0,  8.0, "neutral"),   # intensification
    AspectDef("Opposition", 180.0,  8.0, "tense"),     # polarity / conflict
    AspectDef("Square",      90.0,  7.0, "tense"),     # friction / action
    AspectDef("Trine",      120.0,  8.0, "harmonious"),
    AspectDef("Sextile",     60.0,  6.0, "harmonious"),
    AspectDef("Quincunx",   150.0,  3.0, "tense"),     # blind spots / adjustments
]


# ---------------------------------------------------------------------------
# Hermetic / cyber theme mapping per planet pair + aspect
# ---------------------------------------------------------------------------

# Planetary cyber domain correspondences
_PLANET_DOMAIN: dict[str, str] = {
    "Sun":     "leadership targets / critical infrastructure",
    "Moon":    "public sentiment / social media currents",
    "Mercury": "networks / comms / data transit / supply chains",
    "Venus":   "alliances / finance / soft power",
    "Mars":    "aggression / kinetic ops / offensive campaigns",
    "Jupiter": "expansion / espionage scale / overreach",
    "Saturn":  "infrastructure / control systems / sanctions",
    "Uranus":  "disruption / zero-days / unexpected pivots",
    "Neptune": "deception / disinformation / fog of war",
    "Pluto":   "transformation / hidden power / covert ops",
}

def _planet_domains(p1: str, p2: str) -> str:
    d1 = _PLANET_DOMAIN.get(p1, p1)
    d2 = _PLANET_DOMAIN.get(p2, p2)
    return f"{d1} vs {d2}"


# Generic templates for aspect natures (fallback when pair not in specific dict)
_ASPECT_NATURE_TEMPLATES: dict[str, str] = {
    "tense":      "{{p1}}-{{p2}} tension: friction between {domains}",
    "harmonious": "{{p1}}-{{p2}} flow: cooperative energies across {domains}",
    "neutral":    "{{p1}}-{{p2}} conjunction: amplification at the intersection of {domains}",
}

_THEMES: dict[tuple[str, str, str], str] = {
    # (planet_a, planet_b, aspect_name)
    ("Mars",    "Uranus",  "Conjunction"):  "Sudden offensive cyber action; zero-day deployment",
    ("Mars",    "Uranus",  "Opposition"):   "Escalating cyber-conflict; disruptive attacks on infrastructure",
    ("Mars",    "Saturn",  "Square"):       "State-vs-infrastructure conflict; critical systems under stress",
    ("Mercury", "Neptune", "Conjunction"):  "Disinformation peak; network deception campaigns active",
    ("Mercury", "Neptune", "Square"):       "Misleading intelligence; comms compromised",
    ("Mercury", "Saturn",  "Opposition"):   "Communications infrastructure blockade; censorship or outage",
    ("Jupiter", "Pluto",   "Conjunction"):  "Massive covert expansion; large-scale state espionage",
    ("Saturn",  "Pluto",   "Conjunction"):  "Systemic collapse and restructuring; infrastructure transformation",
    ("Mars",    "Neptune", "Square"):       "Covert military operations; deniable offensive actions",
    ("Sun",     "Pluto",   "Opposition"):   "Leadership under existential threat; power-struggle moment",
    ("Uranus",  "Pluto",   "Square"):       "Civilisational disruption; technological revolution triggering unrest",
    ("Mars",    "Jupiter", "Opposition"):   "Overextended aggression; campaign overreach",
    ("Mercury", "Uranus",  "Trine"):        "Breakthrough comms technology; unexpected intelligence windfall",
    ("Venus",   "Saturn",  "Square"):       "Alliance breakdown; diplomatic friction",
    ("Moon",    "Mars",    "Conjunction"):  "Public anger peak; social media as weapon",
    ("Moon",    "Neptune", "Square"):       "Mass delusion wave; coordinated disinformation going viral",
}


def _get_theme(p1: str, p2: str, aspect: str, nature: str = "tense") -> str | None:
    specific = _THEMES.get((p1, p2, aspect)) or _THEMES.get((p2, p1, aspect))
    if specific:
        return specific
    # Fallback: domain-aware template based on aspect nature
    template = _ASPECT_NATURE_TEMPLATES.get(nature, "")
    if template:
        domains = _planet_domains(p1, p2)
        return template.format(domains=domains).replace("{p1}", p1).replace("{p2}", p2)
    return None


# ---------------------------------------------------------------------------
# Ephem helpers
# ---------------------------------------------------------------------------

_PLANET_OBJECTS: dict[str, ephem.Body] = {
    "Sun":     ephem.Sun(),
    "Moon":    ephem.Moon(),
    "Mercury": ephem.Mercury(),
    "Venus":   ephem.Venus(),
    "Mars":    ephem.Mars(),
    "Jupiter": ephem.Jupiter(),
    "Saturn":  ephem.Saturn(),
    "Uranus":  ephem.Uranus(),
    "Neptune": ephem.Neptune(),
    "Pluto":   ephem.Pluto(),
}

_SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


def _sign(ecliptic_lon_deg: float) -> str:
    return _SIGN_NAMES[int(ecliptic_lon_deg / 30) % 12]


def _compute_positions(dt: datetime) -> dict[str, dict]:
    """Return {planet: {lon, lat, sign, degree_in_sign}} for all watched planets."""
    obs = ephem.Observer()
    obs.lat  = str(config.OBSERVER_LAT)
    obs.lon  = str(config.OBSERVER_LON)
    obs.elev = config.OBSERVER_ELEV
    obs.date = ephem.Date(dt)

    positions = {}
    for name in config.WATCHED_PLANETS:
        obj = _PLANET_OBJECTS[name]
        obj.compute(obs)

        # Convert RA/Dec to ecliptic longitude
        ecl = ephem.Ecliptic(obj, epoch=ephem.Date(dt))
        lon_deg = math.degrees(float(ecl.lon)) % 360

        positions[name] = {
            "lon":           round(lon_deg, 4),
            "sign":          _sign(lon_deg),
            "degree_in_sign": round(lon_deg % 30, 2),
        }
    return positions


def _compute_aspects(positions: dict[str, dict]) -> list[dict]:
    """Find active aspects between planet pairs."""
    planets = list(positions.keys())
    found   = []

    for i in range(len(planets)):
        for j in range(i + 1, len(planets)):
            p1, p2 = planets[i], planets[j]
            lon1   = positions[p1]["lon"]
            lon2   = positions[p2]["lon"]
            diff   = abs(lon1 - lon2) % 360
            if diff > 180:
                diff = 360 - diff

            for aspect in ASPECTS:
                if abs(diff - aspect.angle) <= min(aspect.orb, config.ASPECT_ORB):
                    exact_orb = round(abs(diff - aspect.angle), 2)
                    theme = _get_theme(p1, p2, aspect.name, aspect.nature)
                    found.append({
                        "planet_a":  p1,
                        "planet_b":  p2,
                        "aspect":    aspect.name,
                        "nature":    aspect.nature,
                        "orb":       exact_orb,
                        "angle_diff": round(diff, 2),
                        "theme":     theme,
                    })

    # Sort: tense first, then by tightness of orb
    found.sort(key=lambda a: (0 if a["nature"] == "tense" else 1, a["orb"]))
    return found


def _moon_phase(moon: ephem.Moon, sun: ephem.Sun, dt: datetime) -> str:
    obs = ephem.Observer()
    obs.date = ephem.Date(dt)
    moon.compute(obs)
    sun.compute(obs)

    moon_ecl = ephem.Ecliptic(moon, epoch=ephem.Date(dt))
    sun_ecl  = ephem.Ecliptic(sun,  epoch=ephem.Date(dt))

    diff = (math.degrees(float(moon_ecl.lon)) - math.degrees(float(sun_ecl.lon))) % 360

    if diff < 22.5:    return "New Moon"
    if diff < 67.5:    return "Waxing Crescent"
    if diff < 112.5:   return "First Quarter"
    if diff < 157.5:   return "Waxing Gibbous"
    if diff < 202.5:   return "Full Moon"
    if diff < 247.5:   return "Waning Gibbous"
    if diff < 292.5:   return "Last Quarter"
    if diff < 337.5:   return "Waning Crescent"
    return "New Moon"


def _is_mercury_retrograde(dt: datetime) -> bool:
    """Check if Mercury appears to move retrograde (negative daily motion)."""
    obs = ephem.Observer()
    obs.date = ephem.Date(dt)

    m1 = ephem.Mercury()
    m1.compute(obs)
    ecl1 = ephem.Ecliptic(m1, epoch=ephem.Date(dt))

    obs.date = ephem.Date(dt) + 1  # one day later
    m2 = ephem.Mercury()
    m2.compute(obs)
    ecl2 = ephem.Ecliptic(m2, epoch=ephem.Date(obs.date))

    return float(ecl2.lon) < float(ecl1.lon)


def _dominant_themes(aspects: list[dict], mercury_retro: bool, moon_phase: str) -> list[str]:
    """Derive thematic signals from the sky picture."""
    themes = []

    # From active aspects
    for a in aspects:
        if a.get("theme"):
            themes.append(a["theme"])

    # Mercury retrograde
    if mercury_retro:
        themes.append(
            "Mercury retrograde: review agreements; expect communication failures, "
            "software deployment issues, and OPSEC lapses from rushed decisions"
        )

    # Moon phase — all phases carry meaning
    moon_meanings = {
        "New Moon":        "covert operations favoured; low public visibility; seeds planted now mature unseen",
        "Waxing Crescent": "momentum building; new campaigns gaining traction; watch for early indicators",
        "First Quarter":   "friction and decision points; campaigns reach first resistance; test of resolve",
        "Waxing Gibbous":  "refinement under pressure; threat actors adapt; intelligence fills in",
        "Full Moon":       "maximum visibility; expose/disclosure energy; public sentiment peaks; leaks likely",
        "Waning Gibbous":  "harvest phase; operations in consolidation; persistence malware digs in",
        "Last Quarter":    "release and reorientation; old campaigns wind down; new vectors being seeded",
        "Waning Crescent": "rest before the dark; quiet reconnaissance; actors position for the next cycle",
    }
    moon_meaning = moon_meanings.get(moon_phase, "")
    if moon_meaning:
        themes.append(f"{moon_phase}: {moon_meaning}")

    return themes[:6]  # cap at 6 themes per brief


# ---------------------------------------------------------------------------
# Signal severity from sky picture
# ---------------------------------------------------------------------------

def _sky_severity(aspects: list[dict]) -> str:
    tense = [a for a in aspects if a["nature"] == "tense"]
    critical_pairs = {
        ("Mars", "Uranus"), ("Saturn", "Pluto"), ("Jupiter", "Pluto"),
        ("Mars", "Neptune"), ("Uranus", "Pluto"),
    }
    for a in tense:
        pair = (a["planet_a"], a["planet_b"])
        rpair = (a["planet_b"], a["planet_a"])
        if pair in critical_pairs or rpair in critical_pairs:
            return "HIGH"
    if len(tense) >= 3:
        return "HIGH"
    if len(tense) >= 1:
        return "MEDIUM"
    return "LOW"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_cosmic_scan() -> int:
    """Compute sky picture for now, persist snapshot, emit signal."""
    logger.info("=== COSMIC SCAN STARTED ===")
    dt = datetime.utcnow()

    positions  = _compute_positions(dt)
    aspects    = _compute_aspects(positions)
    moon_phase = _moon_phase(ephem.Moon(), ephem.Sun(), dt)
    merc_retro = _is_mercury_retrograde(dt)
    themes     = _dominant_themes(aspects, merc_retro, moon_phase)

    snap_id = database.save_cosmic_snapshot(
        planet_positions=positions,
        active_aspects=aspects,
        moon_phase=moon_phase,
        mercury_retrograde=merc_retro,
        dominant_themes=themes,
    )

    # Build a human-readable sky report
    severity = _sky_severity(aspects)

    aspect_lines = "\n".join(
        f"  {a['planet_a']} {a['aspect']} {a['planet_b']} "
        f"(orb {a['orb']}°, {a['nature']})"
        + (f"\n    → {a['theme']}" if a.get('theme') else "")
        for a in aspects[:8]
    )

    planet_lines = "  |  ".join(
        f"{name}: {pos['sign']} {pos['degree_in_sign']:.1f}°"
        for name, pos in positions.items()
    )

    body = (
        f"UTC: {dt.strftime('%Y-%m-%d %H:%M')}\n"
        f"Moon Phase: {moon_phase}\n"
        f"Mercury Retrograde: {'YES' if merc_retro else 'No'}\n\n"
        f"Planetary Positions:\n  {planet_lines}\n\n"
        f"Active Aspects:\n{aspect_lines}\n\n"
        f"Dominant Themes:\n"
        + "\n".join(f"  • {t}" for t in themes)
    )

    sig_id = database.save_signal(
        source="cosmic",
        signal_type="cosmic",
        severity=severity,
        title=f"Sky Report — {moon_phase} | {len(aspects)} active aspects",
        body=body,
        raw_json={"snapshot_id": snap_id, "moon_phase": moon_phase, "mercury_retro": merc_retro},
    )

    logger.info(
        "=== COSMIC SCAN COMPLETE  moon=%s  aspects=%d  severity=%s ===",
        moon_phase, len(aspects), severity,
    )
    return 1
