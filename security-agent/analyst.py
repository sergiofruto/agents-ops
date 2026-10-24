"""Claude as the security analyst: it reasons over stored facts, never collects them."""
import logging
from datetime import date

import config
from budget import Budget, Job

logger = logging.getLogger("analyst")


class Claude:
    """Budget-gated access to the Messages API. Returns None instead of calling when it can't spend."""

    def __init__(self, client, budget: Budget, *, today=date.today):
        self.client, self.budget, self.today = client, budget, today
        self.last_failure: str | None = None   # "budget" or "api" after ask() returns None

    @classmethod
    def from_config(cls, conn) -> "Claude":
        client = None
        if config.ANTHROPIC_API_KEY:
            import anthropic
            client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        return cls(client, Budget(conn))

    @property
    def available(self) -> bool:
        return self.client is not None

    def ask(self, job: Job, *, model: str, system: str, messages: list, tools=None, max_tokens: int = 1024):
        self.last_failure = None
        if self.client is None:
            return None
        if not self.budget.can_spend(job, self.today()):
            self.last_failure = "budget"
            return None
        kwargs = dict(model=model, max_tokens=max_tokens, system=system, messages=messages)
        if tools:
            kwargs["tools"] = tools
        try:
            response = self.client.messages.create(**kwargs)
        except Exception as exc:
            logger.warning("Claude call failed (%s): %s", job, type(exc).__name__)
            self.last_failure = "api"
            return None
        self.budget.record(job, model, response.usage.input_tokens, response.usage.output_tokens, self.today())
        return response


def text_of(response) -> str:
    return "".join(b.text for b in response.content if getattr(b, "type", "") == "text").strip()


# ---------------------------------------------------------------------------
# Scan overview and chat. Store lookups are imported lazily: digest.build imports this module.
# ---------------------------------------------------------------------------
import json  # noqa: E402
import re  # noqa: E402

import requests  # noqa: E402

NO_BUDGET = "Today's AI budget is used up. It resets at midnight."
NO_KEY = "Add ANTHROPIC_API_KEY to security-agent/.env to use the analyst."
NO_API = "I couldn't reach Claude just now. Check the connection and try again."
MAX_TOOL_ROUNDS = 5
CVE_ID = re.compile(r"^CVE-\d{4}-\d{4,}$")

OVERVIEW_SYSTEM = """You are a calm security analyst reviewing a routine scan of the user's own Mac.
You get the scan's findings as JSON. In at most 150 words, say what to deal with first and why,
in plain language. Cite each finding you mention by its key in square brackets, like [basics:firewall].
Mention only findings in the data. No hype, no em dashes. Don't repeat the fix steps; the dashboard shows them."""

CHAT_SYSTEM = """You are a security analyst for one person, answering questions about their own Mac,
their security news digest and the status of the services their projects use.
Answer only from tool results and this conversation. If the data doesn't answer the question,
say "I don't know from the data I have" and suggest what to check. Use the tools before answering
questions about the scan, the digest, provider status or a CVE.
Never ask for passwords, keys or other secret values. If you suggest a terminal command, explain
what it does and that the user runs it themselves; you can't run anything.
Be concise and calm. Never use em dashes."""

TOOLS = [
    {"name": "lookup_cve", "description": "Look up a CVE in NVD (description, CVSS score, publish date) and whether CISA lists it as actively exploited.",
     "input_schema": {"type": "object", "properties": {"cve_id": {"type": "string", "description": "e.g. CVE-2026-1234"}},
                      "required": ["cve_id"], "additionalProperties": False}},
    {"name": "get_scan", "description": "The latest Mac scan: findings with severity and evidence, checks that passed, and checks that couldn't run.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "get_digest", "description": "The latest security news digest: entries, who is affected, actions, sources, and which ones affect this user.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "get_status", "description": "Current status of the user's providers (Vercel, Turso, Neon, Anthropic, GitHub, Cloudflare, AWS) and public DNS resolvers.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
]


def _lookup_cve(cve_id: str, get=requests.get) -> dict:
    cve_id = (cve_id or "").strip().upper()
    if not CVE_ID.match(cve_id):
        return {"error": "not a CVE id"}
    try:
        resp = get("https://services.nvd.nist.gov/rest/json/cves/2.0", params={"cveId": cve_id}, timeout=20)
        resp.raise_for_status()
        vulns = resp.json().get("vulnerabilities", [])
    except Exception:
        return {"error": "NVD lookup failed"}
    if not vulns:
        return {"error": "CVE not found in NVD"}
    cve = vulns[0]["cve"]
    score = None
    for key in ("cvssMetricV40", "cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        if cve.get("metrics", {}).get(key):
            score = float(cve["metrics"][key][0]["cvssData"]["baseScore"])
            break
    try:
        kev = {v["cveID"] for v in get(config.DIGEST_SOURCES[0]["url"], timeout=30).json().get("vulnerabilities", [])}
    except Exception:
        kev = None
    return {"cve_id": cve_id,
            "description": next((d["value"] for d in cve.get("descriptions", []) if d.get("lang") == "en"), ""),
            "cvss": score, "published": cve.get("published"),
            "actively_exploited_kev": (cve_id in kev) if kev is not None else "unknown"}


def _scan_facts(conn) -> dict | None:
    from scan import latest_scan
    s = latest_scan(conn)
    if not s:
        return None
    return {"scanned_at": s["finished_at"], "counts": s["counts"], "passed": s["passed"], "skipped": s["skipped"],
            "findings": [{k: f[k] for k in ("key", "severity", "title", "evidence", "is_new")} for f in s["findings"]]}


def run_tool(conn, name: str, args: dict, get=requests.get) -> dict:
    if name == "lookup_cve":
        return _lookup_cve(args.get("cve_id", ""), get=get)
    if name == "get_scan":
        return _scan_facts(conn) or {"error": "no scan yet"}
    if name == "get_digest":
        from digest.build import latest_digest
        d = latest_digest(conn)
        if not d:
            return {"error": "no digest yet"}
        return {"day": d["day"], "entries": [{k: e[k] for k in ("title", "summary", "who", "action", "affects", "kev")}
                                             | {"sources": [s["url"] for s in e["sources"]]} for e in d["entries"]]}
    if name == "get_status":
        from status.service import current
        return {"services": [{k: r.get(k) for k in ("name", "state", "incident", "checked_at")} for r in current(conn)]}
    return {"error": "unknown tool"}


def scan_overview(conn, claude: Claude, scan_id: int) -> str | None:
    facts = _scan_facts(conn)
    if not facts or not claude.available:
        return None
    resp = claude.ask("scan", model=config.DIGEST_MODEL, system=OVERVIEW_SYSTEM, max_tokens=600,
                      messages=[{"role": "user", "content": json.dumps(facts)}])
    if not resp:
        return None
    keys = {f["key"] for f in facts["findings"]}
    text = re.sub(r"\s*\[([^\]]+)\]", lambda m: m.group(0) if m.group(1) in keys else "", text_of(resp)).strip()
    conn.execute("UPDATE scans SET overview=? WHERE id=?", (text, scan_id))
    conn.commit()
    return text


def chat(conn, claude: Claude, messages: list[dict]) -> str:
    if not claude.available:
        return NO_KEY
    msgs = [{"role": m["role"], "content": m["content"]} for m in messages]
    for _ in range(MAX_TOOL_ROUNDS):
        resp = claude.ask("chat", model=config.CHAT_MODEL, system=CHAT_SYSTEM, messages=msgs, tools=TOOLS, max_tokens=2000)
        if resp is None:
            return NO_API if claude.last_failure == "api" else NO_BUDGET
        if resp.stop_reason != "tool_use":
            return text_of(resp) or "I don't know from the data I have."
        msgs.append({"role": "assistant", "content": resp.content})
        results = [{"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(run_tool(conn, b.name, b.input or {}))}
                   for b in resp.content if getattr(b, "type", "") == "tool_use"]
        msgs.append({"role": "user", "content": results})
    return "I couldn't finish that answer. Try a narrower question."
