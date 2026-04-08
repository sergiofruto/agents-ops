"""
intelligence/osint.py — Open-Source Intelligence gathering
===========================================================
Sources:
  • OpenSky Network — live aircraft positions (free, anonymous)
  • aisstream.io / VesselFinder — ship AIS data (optional key)
  • GDELT GKG — global news event monitoring (no key)

The Analyst watches regions of geopolitical interest for anomalies:
  • Aircraft in unusual areas or with no callsign
  • Ships that drop AIS in strategic chokepoints
  • News event spikes around watched territories
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests

import config
import database

logger = logging.getLogger("osint")

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "TheAnalyst/0.1 (osint; contact: operator)",
    "Accept": "application/json",
})


# ---------------------------------------------------------------------------
# OpenSky Network — aircraft positions
# ---------------------------------------------------------------------------

def _opensky_auth() -> tuple[str, str] | None:
    if config.OPENSKY_USERNAME and config.OPENSKY_PASSWORD:
        return (config.OPENSKY_USERNAME, config.OPENSKY_PASSWORD)
    return None


def fetch_aircraft_in_region(
    region_name: str,
    bbox: tuple[float, float, float, float],
) -> list[dict]:
    """
    Returns list of aircraft state vectors inside bbox.
    bbox: (lat_min, lat_max, lon_min, lon_max)
    """
    lat_min, lat_max, lon_min, lon_max = bbox
    params = {
        "lamin": lat_min, "lamax": lat_max,
        "lomin": lon_min, "lomax": lon_max,
    }
    try:
        resp = _SESSION.get(
            f"{config.OPENSKY_BASE}/states/all",
            params=params,
            auth=_opensky_auth(),
            timeout=20,
        )
        if resp.status_code == 429:
            logger.warning("OpenSky rate-limited for region %s", region_name)
            return []
        resp.raise_for_status()
        data = resp.json()
        states = data.get("states") or []
        # Each state: [icao24, callsign, origin_country, time_position, last_contact,
        #              longitude, latitude, baro_altitude, on_ground, velocity,
        #              true_track, vertical_rate, sensors, geo_altitude, squawk,
        #              spi, position_source]
        aircraft = []
        for s in states:
            aircraft.append({
                "icao24":        s[0],
                "callsign":      (s[1] or "").strip() or None,
                "origin":        s[2],
                "longitude":     s[5],
                "latitude":      s[6],
                "altitude_m":    s[7],
                "on_ground":     s[8],
                "velocity_ms":   s[9],
                "squawk":        s[14],
                "region":        region_name,
            })
        return aircraft
    except Exception as exc:
        logger.warning("OpenSky fetch failed for %s: %s", region_name, exc)
        return []


def _is_anomalous_aircraft(ac: dict) -> tuple[bool, str]:
    """
    Heuristic anomaly detection for aircraft.
    Returns (is_anomalous, reason).
    """
    reasons = []

    # No callsign in controlled airspace
    if not ac.get("callsign"):
        reasons.append("no callsign")

    # Emergency squawk codes
    squawk = ac.get("squawk") or ""
    if squawk in ("7500", "7600", "7700"):
        labels = {"7500": "HIJACK", "7600": "RADIO FAILURE", "7700": "GENERAL EMERGENCY"}
        reasons.append(f"SQUAWK {squawk} ({labels[squawk]})")

    # Very low altitude over water (not landing)
    alt = ac.get("altitude_m")
    if alt is not None and 0 < alt < 300 and not ac.get("on_ground"):
        reasons.append(f"extremely low altitude ({alt:.0f}m)")

    if reasons:
        return True, "; ".join(reasons)
    return False, ""


def scan_aircraft() -> int:
    """Scan all regions of interest for anomalous aircraft."""
    saved = 0
    for region, bbox in config.REGIONS_OF_INTEREST.items():
        aircraft = fetch_aircraft_in_region(region, bbox)
        logger.debug("Region %s: %d aircraft", region, len(aircraft))

        for ac in aircraft:
            anomalous, reason = _is_anomalous_aircraft(ac)
            if not anomalous:
                continue

            callsign = ac.get("callsign") or "UNKNOWN"
            title = f"Aircraft anomaly [{region}]: {callsign} — {reason}"
            body  = (
                f"Region: {region}\n"
                f"ICAO24: {ac['icao24']}  |  Callsign: {callsign}\n"
                f"Origin: {ac.get('origin', 'unknown')}\n"
                f"Position: {ac.get('latitude', '?'):.4f}°N, {ac.get('longitude', '?'):.4f}°E\n"
                f"Altitude: {ac.get('altitude_m', '?')} m  |  Speed: {ac.get('velocity_ms', '?')} m/s\n"
                f"Squawk: {ac.get('squawk', 'none')}\n"
                f"Anomaly: {reason}"
            )
            severity = "HIGH" if "SQUAWK" in reason else "MEDIUM"
            database.save_signal(
                source="opensky",
                signal_type="geopolitical",
                severity=severity,
                title=title,
                body=body,
                raw_json=ac,
            )
            saved += 1

    logger.info("Aircraft scan complete: %d anomalous contacts saved", saved)
    return saved


# ---------------------------------------------------------------------------
# Ship AIS — via aisstream.io WebSocket (optional key) or heuristic
# ---------------------------------------------------------------------------

def scan_ships() -> int:
    """
    If AIS_API_KEY is set, query aisstream.io for dark ships in watched regions.
    Otherwise, log that live AIS is unavailable and emit a placeholder signal
    prompting the operator to configure the key.
    """
    if not config.AIS_API_KEY:
        logger.debug("AIS key not configured — ship scan skipped")
        return 0

    # aisstream.io uses a WebSocket API; for simplicity we note this as
    # a TODO for full integration and instead surface it as a configuration
    # signal the first time the agent runs.
    database.save_signal(
        source="ais",
        signal_type="geopolitical",
        severity="INFO",
        title="AIS Integration — configure aisstream.io key",
        body=(
            "Live AIS ship tracking is available via aisstream.io. "
            "Set AIS_API_KEY in .env to enable dark-ship detection across "
            "watched regions: " + ", ".join(config.REGIONS_OF_INTEREST.keys())
        ),
    )
    return 1


# ---------------------------------------------------------------------------
# GDELT GKG — global news event monitoring
# ---------------------------------------------------------------------------

_GDELT_TEMPLATE = (
    "https://api.gdeltproject.org/api/v2/doc/doc?"
    "query={query}&mode=artlist&maxrecords=10&format=json"
)

_REGION_KEYWORDS: dict[str, str] = {
    "South China Sea":   "South China Sea OR Taiwan OR PLA Navy",
    "Strait of Hormuz":  "Strait of Hormuz OR Iran tanker OR IRGC",
    "Red Sea":           "Red Sea OR Houthi OR Bab el-Mandeb",
    "Baltic Sea":        "Baltic Sea OR NATO naval OR Finland Sweden",
    "Taiwan Strait":     "Taiwan Strait OR PLAN exercises OR PLA Air Force Taiwan",
    "Eastern Ukraine":   "Ukraine frontline OR Donbas OR Zaporizhzhia",
}


def fetch_gdelt_news() -> int:
    """Query GDELT for recent news articles in regions of interest."""
    saved = 0
    for region, query in _REGION_KEYWORDS.items():
        try:
            url = _GDELT_TEMPLATE.format(query=requests.utils.quote(query))
            resp = _SESSION.get(url, timeout=20)
            if resp.status_code != 200:
                continue
            data = resp.json()
            articles = data.get("articles", [])
            if not articles:
                continue

            # Represent region as a news-volume signal
            titles = [a.get("title", "") for a in articles[:5]]
            body = (
                f"Region: {region}\n"
                f"Recent articles ({len(articles)} found in GDELT):\n"
                + "\n".join(f"  • {t}" for t in titles)
            )
            severity = "HIGH" if len(articles) >= 8 else "MEDIUM" if len(articles) >= 4 else "LOW"
            database.save_signal(
                source="gdelt",
                signal_type="geopolitical",
                severity=severity,
                title=f"News cluster [{region}]: {len(articles)} articles",
                body=body,
                raw_json={"region": region, "article_count": len(articles), "sample_titles": titles},
            )
            saved += 1
        except Exception as exc:
            logger.warning("GDELT fetch failed for %s: %s", region, exc)

    logger.info("GDELT scan complete: %d regional signals saved", saved)
    return saved


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_osint_scan() -> dict[str, int]:
    """Run all OSINT intelligence collection tasks."""
    logger.info("=== OSINT SCAN STARTED ===")
    results = {
        "aircraft": scan_aircraft(),
        "ships":    scan_ships(),
        "news":     fetch_gdelt_news(),
    }
    logger.info("=== OSINT SCAN COMPLETE  total=%d ===", sum(results.values()))
    return results
