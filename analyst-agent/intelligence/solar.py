"""
intelligence/solar.py — Solar & space weather from NOAA
=========================================================
"The Sun is God's image." — Corpus Hermeticum XI

The Analyst's mother taught him to watch solar weather. Not because
she believed in omens, but because she understood physics: solar flares
disrupt ionospheric propagation, degrade GPS accuracy, induce currents
in power grids and undersea cables, and affect satellite operations.
HF radio goes dark. SIGINT collectors go blind. Those who know the
solar rhythm gain a timing advantage.

Data sources (all free, no API key):
  • NOAA SWPC — X-ray flux, flare events, Kp index, solar wind
  • NOAA GOES — primary X-ray flux for flare classification
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests

logger = logging.getLogger("solar")

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "TheAnalyst/0.1 (solar-intel)"})

# ---------------------------------------------------------------------------
# NOAA SWPC endpoints
# ---------------------------------------------------------------------------
_URLS = {
    "xray_1m":      "https://services.swpc.noaa.gov/json/goes/primary/xrays-1-minute.json",
    "flares_7d":    "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-7day.json",
    "kp_hourly":    "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
    "solar_wind":   "https://services.swpc.noaa.gov/products/solar-wind/plasma-7-day.json",
    "geomag":       "https://services.swpc.noaa.gov/products/geospace/geomag-indices-forecast.json",
}

# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

def _classify_flux(flux: float | None) -> str:
    """Return GOES X-ray class from W/m² flux."""
    if flux is None or flux <= 0:
        return "A"
    if flux >= 1e-3:   return "X"
    if flux >= 1e-4:   return "M"
    if flux >= 1e-5:   return "C"
    if flux >= 1e-6:   return "B"
    return "A"


def _flux_severity(cls: str) -> str:
    return {"X": "CRITICAL", "M": "HIGH", "C": "MEDIUM", "B": "LOW", "A": "INFO"}.get(cls, "INFO")


def _kp_label(kp: float) -> str:
    if kp >= 8: return "Extreme (G4-G5)"
    if kp >= 6: return "Strong (G2-G3)"
    if kp >= 5: return "Minor Storm (G1)"
    if kp >= 4: return "Active"
    return "Quiet"


def _kp_severity(kp: float) -> str:
    if kp >= 7: return "CRITICAL"
    if kp >= 5: return "HIGH"
    if kp >= 4: return "MEDIUM"
    return "LOW"


# ---------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------

def _get(url: str) -> Any | None:
    try:
        r = _SESSION.get(url, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        logger.warning("NOAA fetch failed %s: %s", url, exc)
        return None


def _current_xray() -> dict:
    """Latest 1-minute X-ray flux reading."""
    data = _get(_URLS["xray_1m"])
    if not data:
        return {"flux": None, "cls": "A", "severity": "INFO", "time": None}

    # Two energy bands: 1-8Å (long) and 0.5-4Å (short)
    # Use the long-band (1-8Å) as the standard GOES classification band
    long_band = [d for d in data if d.get("energy") == "0.1-0.8nm"]
    if not long_band:
        long_band = data  # fallback

    latest = long_band[-1]
    flux = latest.get("flux") or latest.get("observed_flux")
    try:
        flux = float(flux)
    except (TypeError, ValueError):
        flux = None

    cls = _classify_flux(flux)
    return {
        "flux":     flux,
        "cls":      cls,
        "severity": _flux_severity(cls),
        "time":     latest.get("time_tag"),
    }


def _recent_flares() -> list[dict]:
    """Flare events from the last 7 days."""
    data = _get(_URLS["flares_7d"])
    if not data:
        return []

    flares = []
    for f in data[-20:]:  # last 20 events
        try:
            flares.append({
                "time":       f.get("begin_time") or f.get("time_tag"),
                "class":      f.get("max_class") or f.get("xray_class", "?"),
                "max_flux":   f.get("max_xrflux"),
                "active_region": f.get("noaa_active_region"),
            })
        except Exception:
            continue
    return flares[-10:]  # trim


def _current_kp() -> dict:
    """Latest planetary Kp index (geomagnetic activity)."""
    data = _get(_URLS["kp_hourly"])
    if not data or len(data) < 2:
        return {"kp": None, "label": "Unknown", "severity": "INFO"}

    # First row is headers; subsequent rows are [time, kp, ...]
    try:
        rows = [r for r in data[1:] if r[1] is not None]
        latest = rows[-1]
        kp = float(latest[1])
        return {
            "kp":      round(kp, 1),
            "label":   _kp_label(kp),
            "severity": _kp_severity(kp),
            "time":    latest[0],
        }
    except Exception:
        return {"kp": None, "label": "Unknown", "severity": "INFO"}


def _solar_wind() -> dict:
    """Latest solar wind plasma density and speed."""
    data = _get(_URLS["solar_wind"])
    if not data or len(data) < 2:
        return {"speed": None, "density": None}
    try:
        rows = [r for r in data[1:] if r[1] is not None]
        latest = rows[-1]
        return {
            "time":    latest[0],
            "density": float(latest[1]) if latest[1] else None,  # p/cm³
            "speed":   float(latest[2]) if latest[2] else None,  # km/s
            "temp":    float(latest[3]) if latest[3] else None,  # K
        }
    except Exception:
        return {"speed": None, "density": None}


# ---------------------------------------------------------------------------
# Hermetic interpretation
# ---------------------------------------------------------------------------

def _interpret(xray: dict, kp: dict, wind: dict) -> str:
    """The Analyst's mother would say…"""
    lines = []

    cls = xray.get("cls", "A")
    kp_val = kp.get("kp")
    speed = wind.get("speed")

    if cls in ("X", "M"):
        lines.append(
            f"Solar class {cls} flare active. HF radio degraded. "
            "SIGINT collectors operating under ionospheric noise. "
            "This is a window where the electromagnetic environment works against clarity — "
            "and for those who know it, against their adversaries too."
        )

    if kp_val and kp_val >= 5:
        lines.append(
            f"Kp {kp_val:.1f} — geomagnetic storm in progress. "
            "Induced currents in long conductors: pipelines, power grids, undersea cables. "
            "She said: when the sky is agitated, the earth feels it in its bones."
        )

    if speed and speed > 600:
        lines.append(
            f"Solar wind speed {speed:.0f} km/s — elevated. "
            "Coronal mass ejection trailing. Satellite drag anomalies expected."
        )

    if not lines:
        lines.append(
            "Solar weather is quiet. The electromagnetic environment is nominal. "
            "Propagation is clean. This is a good window for SIGINT collection — "
            "and for adversaries."
        )

    return " ".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_solar_status() -> dict:
    """
    Return a complete solar weather status dict for the API and dashboard.
    """
    xray  = _current_xray()
    kp    = _current_kp()
    wind  = _solar_wind()
    flares = _recent_flares()

    # Overall alert level — worst of xray + kp
    sev_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
    overall_sev = max(
        [xray["severity"], kp["severity"]],
        key=lambda s: sev_rank.get(s, 0),
    )

    return {
        "updated":      datetime.now(timezone.utc).isoformat(),
        "alert_level":  overall_sev,
        "xray":         xray,
        "kp":           kp,
        "solar_wind":   wind,
        "recent_flares": flares,
        "interpretation": _interpret(xray, kp, wind),
    }
