"""All settings, loaded from .env via python-dotenv."""
import os
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")

DB_PATH = os.getenv("DB_PATH", str(HERE / "security.db"))
LOG_PATH = str(HERE / "agent.log")

# Dashboard: reachable from this Mac only
WEB_HOST = "127.0.0.1"
WEB_PORT = int(os.getenv("WEB_PORT", "5007"))

# Claude
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
AI_DAILY_CAP_USD = float(os.getenv("AI_DAILY_CAP_USD", "1.0"))
AI_DIGEST_RESERVE_USD = float(os.getenv("AI_DIGEST_RESERVE_USD", "0.33"))
DIGEST_MODEL = os.getenv("DIGEST_MODEL", "claude-haiku-5-5")
CHAT_MODEL = os.getenv("CHAT_MODEL", "claude-haiku-5-5")

# Mac check
PROJECTS_ROOT = Path(os.getenv("PROJECTS_ROOT", str(Path.home() / "Projects")))
RUNAWAY_PROCESS_COUNT = int(os.getenv("RUNAWAY_PROCESS_COUNT", "30"))

# USD per million (input, output) tokens. Source: claude-api skill model table, checked 2026-10-24.
MODEL_PRICES: dict[str, tuple[float, float]] = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
}

# Status page. "official" is (kind, url); kinds: statuspage, betterstack, statusio, aws.
# Each URL was checked against the live service on 2026-10-24.
PROVIDERS = [
    {"id": "vercel", "name": "Vercel", "official": ("statuspage", "https://www.vercel-status.com/api/v2/summary.json"),
     "probe": "https://api.vercel.com"},
    {"id": "turso", "name": "Turso", "official": ("betterstack", "https://status.turso.tech/index.json"),
     "probe": "https://api.turso.tech"},
    {"id": "neon", "name": "Neon", "official": ("statusio", "https://api.status.io/1.0/status/6878fc85709daa75be6c7e3c"),
     "probe": "https://console.neon.tech"},
    {"id": "anthropic", "name": "Anthropic", "official": ("statuspage", "https://status.claude.com/api/v2/summary.json"),
     "probe": "https://api.anthropic.com"},
    {"id": "github", "name": "GitHub", "official": ("statuspage", "https://www.githubstatus.com/api/v2/summary.json"),
     "probe": "https://api.github.com"},
    {"id": "cloudflare", "name": "Cloudflare", "official": ("statuspage", "https://www.cloudflarestatus.com/api/v2/summary.json"),
     "probe": "https://api.cloudflare.com"},
    {"id": "aws", "name": "AWS", "official": ("aws", "https://health.aws.amazon.com/public/currentevents"),
     "probe": "https://sts.amazonaws.com"},
]
DNS_RESOLVERS = [
    ("dns-cloudflare", "Cloudflare DNS", "1.1.1.1"),
    ("dns-google", "Google DNS", "8.8.8.8"),
    ("dns-quad9", "Quad9", "9.9.9.9"),
]
STATUS_HISTORY_DAYS = 7

# Digest sources. "primary" can confirm an item on its own; "outlet" needs a second outlet.
# Each URL was checked with feedparser / curl on 2026-10-24. Apple has no working security feed;
# its exploited bugs arrive through CISA KEV.
DIGEST_SOURCES = [
    {"name": "CISA KEV", "kind": "primary", "type": "kev",
     "url": "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"},
    {"name": "NVD (critical)", "kind": "primary", "type": "nvd",
     "url": "https://services.nvd.nist.gov/rest/json/cves/2.0"},
    {"name": "Microsoft MSRC", "kind": "primary", "type": "rss",
     "url": "https://api.msrc.microsoft.com/update-guide/rss"},
    {"name": "Chrome Releases", "kind": "primary", "type": "rss",
     "url": "https://chromereleases.googleblog.com/feeds/posts/default", "title_filter": "Stable Channel Update"},
    {"name": "AWS Security Bulletins", "kind": "primary", "type": "rss",
     "url": "https://aws.amazon.com/security/security-bulletins/rss/feed/"},
    {"name": "GitHub Security Blog", "kind": "outlet", "type": "rss", "url": "https://github.blog/security/feed/"},
    {"name": "BleepingComputer", "kind": "outlet", "type": "rss", "url": "https://www.bleepingcomputer.com/feed/"},
    {"name": "The Record", "kind": "outlet", "type": "rss", "url": "https://therecord.media/feed"},
    {"name": "SecurityWeek", "kind": "outlet", "type": "rss", "url": "https://www.securityweek.com/feed/"},
    {"name": "Krebs on Security", "kind": "outlet", "type": "rss", "url": "https://krebsonsecurity.com/feed/"},
]
DIGEST_MAX_PER_SOURCE = 20
NVD_MIN_CVSS = 9.0
DIGEST_MAX_ENTRIES = 15
