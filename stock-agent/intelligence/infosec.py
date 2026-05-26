"""
Infosec intelligence feed.

Sources:
  - CISA KEV (Known Exploited Vulnerabilities catalog) — hardware/ICS/firmware subset
  - NIST NVD recent CVEs — filtered for semiconductor/hardware/ICS keywords
  - AWS Security Bulletins RSS — cloud infrastructure signals

Each fetch returns a list of signal dicts consumed by the synthesizer.
All results are cached (TTL configurable) to avoid hammering public APIs.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger("intel.infosec")

# ── Cache ──────────────────────────────────────────────────────────────────────
_cache: dict[str, tuple[float, list[dict]]] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour


def _cached(key: str, ttl: int = CACHE_TTL_SECONDS) -> Optional[list[dict]]:
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < ttl:
            return data
    return None


def _store(key: str, data: list[dict]) -> list[dict]:
    _cache[key] = (time.time(), data)
    return data


# ── Hardware/ICS/Firmware keyword filter ─────────────────────────────────────
# We only surface CVEs relevant to silicon, OT/ICS, firmware, and supply chain.
_HARDWARE_KEYWORDS = [
    # Chip vendors
    "intel", "amd", "nvidia", "qualcomm", "arm", "broadcom", "marvell",
    "mediatek", "realtek", "samsung", "micron", "sk hynix", "western digital",
    "seagate", "sandisk", "kioxia", "tsmc", "asml",
    # Component types
    "firmware", "bios", "uefi", "bootloader", "microcode", "pcie", "ddr",
    "dram", "nand", "soc", "fpga", "asic", "gpu", "cpu",
    # ICS / OT
    "ics", "scada", "plc", "ot ", "modbus", "dnp3", "siemens", "schneider",
    "rockwell", "honeywell", "ge digital", "beckhoff",
    # Hardware attack classes
    "side-channel", "spectre", "meltdown", "rowhammer", "jtag", "spi flash",
    "supply chain", "hardware trojan", "fault injection",
    # Infrastructure
    "hypervisor", "vmware", "xen", "kvm", "esxi",
]


def _is_hardware_relevant(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in _HARDWARE_KEYWORDS)


# ── CISA KEV ──────────────────────────────────────────────────────────────────

def fetch_cisa_kev(days_back: int = 14) -> list[dict]:
    """
    Fetch recently added entries from the CISA KEV catalog.
    Returns hardware/ICS-relevant entries added in the last `days_back` days.
    """
    cache_key = f"cisa_kev_{days_back}"
    if cached := _cached(cache_key):
        logger.debug("CISA KEV: cache hit")
        return cached

    try:
        import urllib.request, json
        url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        logger.error("CISA KEV fetch failed: %s", exc)
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    results: list[dict] = []

    for vuln in data.get("vulnerabilities", []):
        added_str = vuln.get("dateAdded", "")
        try:
            added = datetime.fromisoformat(added_str).replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if added < cutoff:
            continue

        desc = vuln.get("shortDescription", "")
        vendor = vuln.get("vendorProject", "")
        product = vuln.get("product", "")
        combined = f"{vendor} {product} {desc}"

        if not _is_hardware_relevant(combined):
            continue

        results.append({
            "source":      "CISA-KEV",
            "cve_id":      vuln.get("cveID", ""),
            "vendor":      vendor,
            "product":     product,
            "description": desc,
            "date_added":  added_str,
            "due_date":    vuln.get("dueDate", ""),
            "url":         f"https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
            "severity":    "critical",  # all KEV entries are being actively exploited
        })

    logger.info("CISA KEV: %d hardware-relevant entries (last %d days)", len(results), days_back)
    return _store(cache_key, results)


# ── NIST NVD ──────────────────────────────────────────────────────────────────

def fetch_nvd_recent(days_back: int = 7, max_results: int = 100) -> list[dict]:
    """
    Fetch recent CVEs from NIST NVD, filtered for hardware/ICS/firmware relevance.
    Uses the NVD 2.0 REST API (no API key required, 5 req/30s rate limit respected).
    Returns CRITICAL + HIGH severity entries only to limit noise.
    """
    cache_key = f"nvd_{days_back}"
    if cached := _cached(cache_key):
        logger.debug("NVD: cache hit")
        return cached

    try:
        import urllib.request, urllib.parse, json
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%S.000")
        end = now.strftime("%Y-%m-%dT%H:%M:%S.000")

        params = urllib.parse.urlencode({
            "pubStartDate": start,
            "pubEndDate":   end,
            "resultsPerPage": max_results,
            "cvssV3Severity": "CRITICAL",  # Start with critical only
        })
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?{params}"

        req = urllib.request.Request(url, headers={"User-Agent": "silicon-intel-agent/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        logger.error("NVD fetch failed: %s", exc)
        return []

    results: list[dict] = []
    for item in data.get("vulnerabilities", []):
        cve = item.get("cve", {})
        cve_id = cve.get("id", "")

        # Description (prefer English)
        descs = cve.get("descriptions", [])
        desc = next((d["value"] for d in descs if d.get("lang") == "en"), "")

        if not _is_hardware_relevant(desc):
            continue

        # CVSS score
        metrics = cve.get("metrics", {})
        score = None
        severity = "unknown"
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            if key in metrics and metrics[key]:
                m = metrics[key][0].get("cvssData", {})
                score = m.get("baseScore")
                severity = m.get("baseSeverity", "").lower()
                break

        published = cve.get("published", "")

        results.append({
            "source":      "NVD",
            "cve_id":      cve_id,
            "description": desc[:300],
            "severity":    severity,
            "cvss_score":  score,
            "published":   published,
            "url":         f"https://nvd.nist.gov/vuln/detail/{cve_id}",
        })

    logger.info("NVD: %d hardware-relevant CRITICAL CVEs (last %d days)", len(results), days_back)
    return _store(cache_key, results)


# ── AWS Security Bulletins ────────────────────────────────────────────────────

def fetch_aws_security(max_items: int = 10) -> list[dict]:
    """
    Fetch AWS Security Bulletins RSS feed.
    Cloud infrastructure changes that affect semiconductor/AI workloads.
    """
    cache_key = "aws_security"
    if cached := _cached(cache_key, ttl=7200):  # 2h cache
        logger.debug("AWS Security: cache hit")
        return cached

    try:
        import feedparser
        feed = feedparser.parse("https://aws.amazon.com/security/security-bulletins/feed/")
        if feed.get("bozo"):
            logger.warning("AWS feed parse warning: %s", feed.get("bozo_exception"))
    except ImportError:
        logger.error("feedparser not installed — run: pip install feedparser")
        return []
    except Exception as exc:
        logger.error("AWS security feed failed: %s", exc)
        return []

    results: list[dict] = []
    for entry in feed.entries[:max_items]:
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        link = entry.get("link", "")
        published = entry.get("published", "")

        results.append({
            "source":    "AWS-Security",
            "title":     title,
            "summary":   summary[:300],
            "url":       link,
            "published": published,
        })

    logger.info("AWS Security: %d bulletins", len(results))
    return _store(cache_key, results)


# ── Aggregated fetch ──────────────────────────────────────────────────────────

def fetch_all_infosec() -> list[dict]:
    """
    Fetch all infosec signals. Returns a combined, time-sorted list.
    Called from the main intelligence scan loop.
    """
    signals: list[dict] = []
    signals.extend(fetch_cisa_kev(days_back=14))
    signals.extend(fetch_nvd_recent(days_back=7))
    signals.extend(fetch_aws_security())
    return signals


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json, sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    target = sys.argv[1] if len(sys.argv) > 1 else "all"

    if target in ("kev", "all"):
        print("\n── CISA KEV ──")
        for s in fetch_cisa_kev(days_back=30):
            print(f"  {s['cve_id']} [{s['vendor']} / {s['product']}] — {s['description'][:80]}")

    if target in ("nvd", "all"):
        print("\n── NVD CRITICAL ──")
        for s in fetch_nvd_recent(days_back=7):
            print(f"  {s['cve_id']} [{s['cvss_score']}] — {s['description'][:80]}")

    if target in ("aws", "all"):
        print("\n── AWS Security Bulletins ──")
        for s in fetch_aws_security():
            print(f"  {s['title']}")
