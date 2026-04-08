"""
intelligence/infosec.py — Cybersecurity signal collection
==========================================================
Sources:
  • NIST NVD  — recent CVEs (free, optional API key for higher rate limits)
  • CISA KEV  — Known Exploited Vulnerabilities catalog (no key)
  • AWS Security Bulletins RSS feed (no key)
  • AlienVault OTX pulse feed (optional key)

All results are saved to intel_signals and cves via database.py.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import requests

import config
import database

logger = logging.getLogger("infosec")

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "TheAnalyst/0.1 (intel-agent; contact: operator)",
    "Accept": "application/json",
})

# ---------------------------------------------------------------------------
# CISA KEV
# ---------------------------------------------------------------------------

_KEV_CACHE: dict = {}
_KEV_LOADED = False


def _load_kev() -> set[str]:
    """Return set of CVE IDs in CISA Known Exploited Vulnerabilities catalog."""
    global _KEV_CACHE, _KEV_LOADED
    try:
        resp = _SESSION.get(config.CISA_KEV_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        vuln_ids = {v["cveID"] for v in data.get("vulnerabilities", [])}
        _KEV_CACHE = vuln_ids
        _KEV_LOADED = True
        logger.info("CISA KEV loaded: %d known exploited CVEs", len(vuln_ids))
        return vuln_ids
    except Exception as exc:
        logger.warning("Failed to load CISA KEV: %s", exc)
        return set()


def is_kev(cve_id: str) -> bool:
    if not _KEV_LOADED:
        _load_kev()
    return cve_id in _KEV_CACHE


# ---------------------------------------------------------------------------
# NIST NVD — Recent CVEs
# ---------------------------------------------------------------------------

_AWS_KEYWORDS = re.compile(
    r"\b(AWS|Amazon Web Services|EC2|S3|IAM|Lambda|CloudFront|EKS|ECS|RDS|"
    r"Route53|CloudTrail|VPC|Cognito|SageMaker|Bedrock)\b",
    re.IGNORECASE,
)


def _cvss_to_severity(cvss: float | None) -> str:
    if cvss is None:
        return "UNKNOWN"
    if cvss >= 9.0:
        return "CRITICAL"
    if cvss >= 7.0:
        return "HIGH"
    if cvss >= 4.0:
        return "MEDIUM"
    return "LOW"


def fetch_recent_cves() -> int:
    """
    Pull CVEs published in the last NVD_DAYS_BACK days from NIST NVD.
    Returns count of new signals saved.
    """
    kev_ids = _load_kev()

    end   = datetime.now(timezone.utc)
    start = end - timedelta(days=config.NVD_DAYS_BACK)

    params: dict = {
        "pubStartDate": start.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "pubEndDate":   end.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "resultsPerPage": 100,
    }
    headers = {}
    if config.NVD_API_KEY:
        headers["apiKey"] = config.NVD_API_KEY

    saved = 0
    try:
        resp = _SESSION.get(config.NVD_BASE, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("NVD fetch failed: %s", exc)
        return 0

    for item in data.get("vulnerabilities", []):
        cve = item.get("cve", {})
        cve_id = cve.get("id", "")
        if not cve_id:
            continue

        # Description
        desc = ""
        for d in cve.get("descriptions", []):
            if d.get("lang") == "en":
                desc = d.get("value", "")
                break

        # CVSS score — prefer v3.1, fallback v3.0, then v2
        cvss_score: float | None = None
        metrics = cve.get("metrics", {})
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            if key in metrics and metrics[key]:
                try:
                    cvss_score = float(metrics[key][0]["cvssData"]["baseScore"])
                    break
                except (KeyError, IndexError, ValueError):
                    pass

        severity   = _cvss_to_severity(cvss_score)
        published  = cve.get("published", "")
        kev        = cve_id in kev_ids
        aws_rel    = bool(_AWS_KEYWORDS.search(desc))

        database.upsert_cve(cve_id, published, severity, cvss_score, desc, kev, aws_rel)

        # Promote to signal if CRITICAL/HIGH or KEV
        if severity in ("CRITICAL", "HIGH") or kev:
            tags = []
            if kev:
                tags.append("CISA-KEV")
            if aws_rel:
                tags.append("AWS")

            signal_title = f"{cve_id} [{severity}]{' [' + ','.join(tags) + ']' if tags else ''}"
            signal_body  = desc[:600] + ("…" if len(desc) > 600 else "")
            if cvss_score is not None:
                signal_body = f"CVSS: {cvss_score:.1f}  |  {signal_body}"

            database.save_signal(
                source="nvd",
                signal_type="infosec",
                severity=severity if not kev else "CRITICAL",
                title=signal_title,
                body=signal_body,
                raw_json={"cve_id": cve_id, "cvss": cvss_score, "kev": kev, "aws": aws_rel},
            )
            saved += 1

    logger.info("NVD scan complete: %d high-signal CVEs saved", saved)
    return saved


# ---------------------------------------------------------------------------
# AWS Security Bulletins RSS
# ---------------------------------------------------------------------------

def fetch_aws_bulletins() -> int:
    """Fetch AWS Security Bulletins RSS and save as signals."""
    saved = 0
    try:
        resp = _SESSION.get(config.AWS_SECURITY_RSS, timeout=20)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception as exc:
        logger.warning("AWS RSS fetch failed: %s", exc)
        return 0

    ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
    items = root.findall(".//item")

    for item in items[:10]:  # latest 10
        title  = (item.findtext("title") or "").strip()
        link   = (item.findtext("link")  or "").strip()
        pub    = (item.findtext("pubDate") or "").strip()
        desc   = (item.findtext("description") or "").strip()

        # Only emit items from the last 7 days
        try:
            from email.utils import parsedate_to_datetime
            pub_dt = parsedate_to_datetime(pub)
            if (datetime.now(timezone.utc) - pub_dt).days > 7:
                continue
        except Exception:
            pass

        body = f"Published: {pub}\n{link}\n\n{desc[:400]}"
        database.save_signal(
            source="aws_rss",
            signal_type="infosec",
            severity="HIGH",
            title=f"AWS Security Bulletin: {title}",
            body=body,
            raw_json={"title": title, "link": link, "pub": pub},
        )
        saved += 1

    logger.info("AWS bulletins: %d recent bulletins saved", saved)
    return saved


# ---------------------------------------------------------------------------
# AlienVault OTX — threat pulses
# ---------------------------------------------------------------------------

def fetch_otx_pulses() -> int:
    """Fetch subscribed AlienVault OTX pulses (requires API key)."""
    if not config.OTX_API_KEY:
        logger.debug("OTX key not configured — skipping")
        return 0

    saved = 0
    try:
        resp = _SESSION.get(
            f"{config.OTX_BASE}/pulses/subscribed",
            headers={"X-OTX-API-KEY": config.OTX_API_KEY},
            params={"limit": 20, "modified_since": (
                datetime.now(timezone.utc) - timedelta(days=1)
            ).strftime("%Y-%m-%dT%H:%M:%S")},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("OTX fetch failed: %s", exc)
        return 0

    for pulse in data.get("results", []):
        name    = pulse.get("name", "")
        tlp     = pulse.get("tlp", "white").upper()
        tags    = ", ".join(pulse.get("tags", []))
        ioc_cnt = len(pulse.get("indicators", []))
        desc    = pulse.get("description", "")[:400]

        severity = "HIGH" if tlp in ("RED", "AMBER") else "MEDIUM"

        database.save_signal(
            source="otx",
            signal_type="infosec",
            severity=severity,
            title=f"OTX Pulse [{tlp}]: {name}",
            body=f"Tags: {tags}  |  IOC count: {ioc_cnt}\n{desc}",
            raw_json={"pulse_id": pulse.get("id"), "tlp": tlp, "ioc_count": ioc_cnt},
        )
        saved += 1

    logger.info("OTX: %d pulses saved", saved)
    return saved


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_infosec_scan() -> dict[str, int]:
    """Run all infosec intelligence collection tasks."""
    logger.info("=== INFOSEC SCAN STARTED ===")
    results = {
        "cves":     fetch_recent_cves(),
        "aws":      fetch_aws_bulletins(),
        "otx":      fetch_otx_pulses(),
    }
    logger.info("=== INFOSEC SCAN COMPLETE  total=%d ===", sum(results.values()))
    return results
