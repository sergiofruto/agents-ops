"""Fetch candidate news items. Facts only: no summarising, no judging."""
import hashlib
import html
import logging
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

import feedparser
import requests

import config

logger = logging.getLogger("digest.sources")

CVE_RE = re.compile(r"CVE-\d{4}-\d{4,}", re.I)
KEV_LINK = "https://www.cisa.gov/known-exploited-vulnerabilities-catalog?search_api_fulltext={}"
NVD_LINK = "https://nvd.nist.gov/vuln/detail/{}"


@dataclass(frozen=True)
class Item:
    id: str
    kind: Literal["primary", "outlet"]
    source: str
    url: str
    title: str
    published: datetime
    text: str
    cve_ids: tuple[str, ...]
    kev: bool = False


def item_id(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:12]


def extract_cves(text: str) -> tuple[str, ...]:
    return tuple(sorted({m.upper() for m in CVE_RE.findall(text)}))


def _plain(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(s or ""))).strip()


def _make(kind, source, url, title, published, text, kev=False, cves=None) -> Item:
    title, text = _plain(title), _plain(text)[:2000]
    return Item(item_id(url), kind, source, url, title, published, text,
                tuple(sorted(set(cves))) if cves else extract_cves(f"{title} {text}"), kev)


def _kev_items(src, get, since: datetime) -> list[Item]:
    data = get(src["url"], timeout=30).json()
    out = []
    for v in data.get("vulnerabilities", []):
        added = datetime.strptime(v["dateAdded"], "%Y-%m-%d")
        if added.date() < since.date():
            continue
        title = f"{v['vendorProject']} {v['product']}: {v['vulnerabilityName']}"
        text = f"{v.get('shortDescription', '')} Required action: {v.get('requiredAction', '')}"
        out.append(_make(src["kind"], src["name"], KEV_LINK.format(v["cveID"]), title, added, text,
                         kev=True, cves=[v["cveID"]]))
    return out


def _kev_ids(get) -> set[str]:
    try:
        data = get(config.DIGEST_SOURCES[0]["url"], timeout=30).json()
        return {v["cveID"] for v in data.get("vulnerabilities", [])}
    except Exception:
        return set()


def _nvd_items(src, get, since: datetime, now: datetime) -> list[Item]:
    utc = lambda d: d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000")  # noqa: E731
    resp = get(src["url"], params={"pubStartDate": utc(since), "pubEndDate": utc(now), "resultsPerPage": 200}, timeout=30)
    resp.raise_for_status()
    kev = None
    out = []
    for entry in resp.json().get("vulnerabilities", []):
        cve = entry.get("cve", {})
        score = None
        for key in ("cvssMetricV40", "cvssMetricV31", "cvssMetricV30"):
            for m in cve.get("metrics", {}).get(key, []):
                score = float(m["cvssData"]["baseScore"])
                break
            if score is not None:
                break
        if score is None or score < config.NVD_MIN_CVSS:
            continue
        desc = next((d["value"] for d in cve.get("descriptions", []) if d.get("lang") == "en"), "")
        published = datetime.fromisoformat(cve.get("published", now.isoformat())[:19])
        kev = _kev_ids(get) if kev is None else kev
        out.append(_make(src["kind"], src["name"], NVD_LINK.format(cve["id"]), f"{cve['id']} (CVSS {score})",
                         published, desc, kev=cve["id"] in kev, cves=[cve["id"]]))
    return out


def _parse_url(url: str):
    resp = requests.get(url, timeout=20, headers={"User-Agent": "security-agent/1.0"})
    resp.raise_for_status()
    return feedparser.parse(resp.content)


def _entry_time(e) -> datetime | None:
    t = e.get("published_parsed") or e.get("updated_parsed")
    if not t:
        return None
    return datetime(*t[:6], tzinfo=timezone.utc).astimezone().replace(tzinfo=None)


def _rss_items(src, parse, since: datetime) -> list[Item]:
    feed = parse(src["url"])
    pattern = re.compile(src["title_filter"], re.I) if src.get("title_filter") else None
    out = []
    for e in feed.get("entries", []):
        published = _entry_time(e)
        title, link = e.get("title", ""), e.get("link", "")
        # Only web links: a feed could carry javascript: or data: URLs, which the dashboard would render as hrefs
        if not published or published < since or not link.startswith(("https://", "http://")) \
                or (pattern and not pattern.search(title)):
            continue
        out.append(_make(src["kind"], src["name"], link, title, published, e.get("summary", "")))
    return out


def fetch_all(conn: sqlite3.Connection, *, window_hours: int = 36, get=requests.get, parse=_parse_url,
              now: datetime | None = None, sources: list[dict] | None = None) -> list[Item]:
    now = now or datetime.now()
    since = now - timedelta(hours=window_hours)
    seen = {r[0] for r in conn.execute("SELECT url FROM seen_items")}
    items: list[Item] = []
    for src in sources or config.DIGEST_SOURCES:
        try:
            if src["type"] == "kev":
                got = _kev_items(src, get, since)
            elif src["type"] == "nvd":
                got = _nvd_items(src, get, since, now)
            else:
                got = _rss_items(src, parse, since)
        except Exception as exc:
            logger.warning("digest source %s failed: %s", src["name"], type(exc).__name__)
            continue
        got.sort(key=lambda i: i.published, reverse=True)
        items += got[:config.DIGEST_MAX_PER_SOURCE]
    unique, urls = [], set()
    for i in items:
        if i.url not in seen and i.url not in urls:
            urls.add(i.url)
            unique.append(i)
    return unique
