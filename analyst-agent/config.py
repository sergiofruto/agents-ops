"""
config.py — The Analyst agent settings
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Agent identity
# ---------------------------------------------------------------------------
AGENT_NAME    = "The Analyst"
AGENT_VERSION = "0.1.0"

# ---------------------------------------------------------------------------
# Scan intervals
# ---------------------------------------------------------------------------
INTEL_INTERVAL_MINUTES  = int(os.getenv("INTEL_INTERVAL_MINUTES", "60"))   # OSINT + infosec scan
COSMIC_INTERVAL_MINUTES = int(os.getenv("COSMIC_INTERVAL_MINUTES", "360")) # Sky calculations (6h)
BRIEF_INTERVAL_MINUTES  = int(os.getenv("BRIEF_INTERVAL_MINUTES", "120"))  # Synthesise + publish

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DB_PATH = os.getenv("DB_PATH", "analyst.db")

# ---------------------------------------------------------------------------
# Web
# ---------------------------------------------------------------------------
WEB_HOST = os.getenv("WEB_HOST", "127.0.0.1")
WEB_PORT = int(os.getenv("WEB_PORT", "5003"))

# ---------------------------------------------------------------------------
# Intelligence sources
# ---------------------------------------------------------------------------

# OpenSky Network — no key required for anonymous (rate-limited)
OPENSKY_BASE = "https://opensky-network.org/api"
OPENSKY_USERNAME = os.getenv("OPENSKY_USERNAME", "")
OPENSKY_PASSWORD = os.getenv("OPENSKY_PASSWORD", "")

# NIST NVD — CVE feed (optional API key for higher rate limits)
NVD_API_KEY  = os.getenv("NVD_API_KEY", "")
NVD_BASE     = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_DAYS_BACK = int(os.getenv("NVD_DAYS_BACK", "3"))   # fetch CVEs published in last N days

# CISA KEV — Known Exploited Vulnerabilities (no key)
CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

# AlienVault OTX — threat intelligence (optional)
OTX_API_KEY = os.getenv("OTX_API_KEY", "")
OTX_BASE    = "https://otx.alienvault.com/api/v1"

# Shodan — infrastructure intel (optional)
SHODAN_API_KEY = os.getenv("SHODAN_API_KEY", "")

# MarineTraffic / aisstream.io (optional — for live AIS)
AIS_API_KEY = os.getenv("AIS_API_KEY", "")

# AWS Security Bulletins RSS
AWS_SECURITY_RSS = "https://aws.amazon.com/security/security-bulletins/rss/feed/"

# ---------------------------------------------------------------------------
# Geographies of interest for OSINT scans
# ---------------------------------------------------------------------------
# Bounding boxes: (lat_min, lat_max, lon_min, lon_max)
REGIONS_OF_INTEREST: dict[str, tuple[float, float, float, float]] = {
    "South China Sea":   ( 0.0,  25.0,  105.0,  125.0),
    "Strait of Hormuz":  (22.0,  27.0,   55.0,   60.0),
    "Red Sea":           (12.0,  30.0,   32.0,   44.0),
    "Baltic Sea":        (53.0,  66.0,    9.0,   30.0),
    "Taiwan Strait":     (21.0,  27.0,  118.0,  122.0),
    "Eastern Ukraine":   (46.0,  52.0,   34.0,   40.0),
}

# ---------------------------------------------------------------------------
# Cosmic — location of observer (for accurate asc/local houses)
# ---------------------------------------------------------------------------
OBSERVER_LAT  = float(os.getenv("OBSERVER_LAT",  "40.7128"))  # New York default
OBSERVER_LON  = float(os.getenv("OBSERVER_LON",  "-74.0060"))
OBSERVER_ELEV = float(os.getenv("OBSERVER_ELEV", "10"))       # metres

# Which planets to watch
WATCHED_PLANETS: list[str] = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]

# Orb tolerance in degrees for aspects
ASPECT_ORB = float(os.getenv("ASPECT_ORB", "8.0"))
