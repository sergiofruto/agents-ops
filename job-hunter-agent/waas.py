"""
job-hunter-agent/waas.py
========================
Parse a workatastartup.com company-directory JSON dump (the /companies/fetch
response) into a ranked markdown shortlist of target companies. Company
targeting, not applications: no DB writes, no cover notes.

Usage (via main.py):
    python main.py --waas               # reads waas_dump.json
    python main.py --waas path.json     # explicit dump path
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("job-hunter.waas")

AGENT_DIR = Path(__file__).parent
DEFAULT_DUMP = AGENT_DIR / "waas_dump.json"
REPORT_PATH = AGENT_DIR / "reports" / "waas-shortlist.md"

# WaaS eng_type slugs that match Sergio's target (full-stack / frontend).
TARGET_ENG_SLUGS = {"fs", "fe"}
# Titles we never want even if eng_type matches (people-management, not IC).
MANAGER_WORDS = ("manager", "director", "head of", "vp of", "vp,")

AI_KEYWORDS = [
    "ai", "llm", "agent", "agents", "agentic", "ml", "machine learning",
    "gpt", "genai", "generative", "neural", "computer vision", "nlp",
    "deep learning", "ai-native", "ai-powered", "co-pilot", "copilot",
]
# Word-boundary matcher so short tokens ("ai", "ml") don't match inside
# "domain", "html", etc.
_AI_RE = re.compile(
    r"(?<![a-z])(" + "|".join(re.escape(k) for k in AI_KEYWORDS) + r")(?![a-z])"
)
EARLY_STAGE_TEAM_MAX = 30
WEIGHTS = {"role_fit": 0.40, "ai_product": 0.20, "early_stage": 0.20, "intl_remote": 0.20}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Job:
    title: str
    eng_types: list[str]      # raw slugs, e.g. ["fs"], ["fe"], ["ml"]
    role_type: str            # pretty label, e.g. "Full stack"
    location: str
    remote: bool
    salary: str | None        # pretty_salary_range
    equity: str | None        # pretty_equity_range
    visa: str                 # pretty_sponsors_visa
    text: str                 # blob fed to score_fit


@dataclass
class Company:
    name: str
    batch: str
    team_size: int | None
    location: str
    sector: str
    one_liner: str
    blob: str                 # one_liner + hiring/tech description + sector (AI signal)
    url: str
    jobs: list[Job] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_dump(path: Path) -> list[dict]:
    """Tolerant reader for the WaaS dump. Returns a list of raw company dicts."""
    if not path.exists():
        raise FileNotFoundError(
            f"No WaaS dump at {path}.\n"
            "Grab one: log into workatastartup.com/companies, open DevTools → "
            "Network, search a company name, find the www.workatastartup.com/companies/fetch "
            "response, Copy response, save it as that path."
        )
    raw = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        if isinstance(raw.get("companies"), list):
            return raw["companies"]
        if isinstance(raw.get("results"), list):  # Algolia multi-query shape
            hits: list[dict] = []
            for result in raw["results"]:
                hits.extend(result.get("hits", []))
            return hits
        raise ValueError(
            f"Unrecognized WaaS dump shape. Top-level keys: {list(raw.keys())}"
        )
    raise ValueError("Unrecognized WaaS dump: JSON root is neither list nor object.")


# ---------------------------------------------------------------------------
# Normalizer
# ---------------------------------------------------------------------------

def _as_str(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_as_str(v) for v in value)
    return "" if value is None else str(value)


def _job_is_remote(raw: dict) -> bool:
    # WaaS job.remote is "yes" / "no" / "only"; "only" means remote-only.
    return _as_str(raw.get("remote")).strip().lower() in {"yes", "only", "true"}


def normalize(raw: dict) -> Company:
    """Map a raw WaaS company dict to a Company. Missing fields degrade gracefully."""
    jobs: list[Job] = []
    for j in raw.get("jobs") or []:
        eng_types = j.get("eng_type") or []
        if isinstance(eng_types, str):
            eng_types = [eng_types]
        salary = j.get("pretty_salary_range") or None
        skills = _as_str(j.get("skills"))
        jobs.append(Job(
            title=_as_str(j.get("title")).strip(),
            eng_types=[str(e).lower() for e in eng_types],
            role_type=_as_str(j.get("pretty_eng_type")),
            location=_as_str(j.get("location") or j.get("pretty_location_or_remote")),
            remote=_job_is_remote(j),
            salary=salary,
            equity=j.get("pretty_equity_range") or None,
            visa=_as_str(j.get("pretty_sponsors_visa")),
            text=" ".join(filter(None, [
                _as_str(j.get("title")),
                _as_str(j.get("pretty_eng_type")),
                skills,
                _as_str(j.get("description")),
                salary or "",
            ])),
        ))

    team_size = raw.get("team_size")
    try:
        team_size = int(team_size) if team_size is not None else None
    except (ValueError, TypeError):
        team_size = None

    sector = _as_str(raw.get("primary_vertical")) or " -> ".join(
        filter(None, [_as_str(raw.get("parent_sector")), _as_str(raw.get("child_sector"))])
    )

    one_liner = _as_str(raw.get("one_liner"))
    blob = " ".join([
        one_liner,
        _as_str(raw.get("hiring_description")),
        _as_str(raw.get("tech_description")),
        sector,
    ]).lower()

    slug = _as_str(raw.get("slug"))
    url = (
        f"https://www.workatastartup.com/companies/{slug}" if slug
        else _as_str(raw.get("website_url")) or _as_str(raw.get("website"))
    )

    return Company(
        name=_as_str(raw.get("name")).strip(),
        batch=_as_str(raw.get("batch")),
        team_size=team_size,
        location=_as_str(raw.get("location")),
        sector=sector,
        one_liner=one_liner,
        blob=blob,
        url=url,
        jobs=jobs,
    )


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------

def _is_target_role(job: Job) -> bool:
    if any(w in job.title.lower() for w in MANAGER_WORDS):
        return False
    return bool(set(job.eng_types) & TARGET_ENG_SLUGS)


def _visa_score(visa: str) -> float:
    """How reachable is this role for an Argentina-based contractor."""
    v = visa.lower()
    if "not required" in v:
        return 1.0          # international/contractor explicitly fine
    if "sponsor" in v:
        return 0.6          # US FTE; remote contractor sometimes possible
    if "citizen" in v or "visa only" in v:
        return 0.2          # effectively US-only
    return 0.4              # unknown


def _role_intl(job: Job) -> float:
    """Combined remote + visa reachability for a single role."""
    return (1.0 if job.remote else 0.2) * _visa_score(job.visa)


def score_company(company: Company, profile: dict) -> dict | None:
    """
    Company-level fit score. Returns None if the company has no IC full-stack /
    frontend role (filtered from the shortlist).
    """
    # Lazy import avoids a circular import at module load (main.py imports waas).
    from main import score_fit

    candidates = [j for j in company.jobs if _is_target_role(j)]
    if not candidates:
        return None

    # Pick the most actionable role: best blend of stack fit + reachability.
    best_role: Job | None = None
    best_role_fit = 0.0
    best_combined = -1.0
    for job in candidates:
        detail = score_fit(job.text, profile)
        rfit = round(0.6 * detail["stack"] + 0.4 * detail["role"], 3)
        combined = rfit + _role_intl(job)
        if combined > best_combined:
            best_combined = combined
            best_role_fit = rfit
            best_role = job

    reasons: list[str] = []

    ai_hits = sorted(set(_AI_RE.findall(company.blob)))
    ai_product = 1.0 if ai_hits else 0.0
    if ai_hits:
        reasons.append(f"AI signal: {', '.join(ai_hits[:3])}")

    if company.team_size is None:
        early_stage = 0.5
    elif company.team_size <= EARLY_STAGE_TEAM_MAX:
        early_stage = 1.0
        reasons.append(f"Early-stage: team {company.team_size}")
    else:
        early_stage = 0.0

    intl_remote = _role_intl(best_role)
    if best_role.remote and "not required" in best_role.visa.lower():
        reasons.append("Remote · visa not required")
    elif best_role.remote and "sponsor" in best_role.visa.lower():
        reasons.append("Remote · will sponsor")
    elif best_role.remote:
        reasons.append("Remote · US-only visa")

    total = (
        best_role_fit * WEIGHTS["role_fit"]
        + ai_product * WEIGHTS["ai_product"]
        + early_stage * WEIGHTS["early_stage"]
        + intl_remote * WEIGHTS["intl_remote"]
    )

    return {
        "total": round(total, 3),
        "role_fit": round(best_role_fit, 3),
        "ai_product": ai_product,
        "early_stage": early_stage,
        "intl_remote": round(intl_remote, 3),
        "best_role": best_role,
        "reasons": reasons,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def build_report(
    scored: list[tuple[Company, dict]],
    profile: dict,
    out_path: Path,
    top_n: int = 25,
) -> None:
    """Write a ranked markdown shortlist to out_path."""
    target = profile.get("compensation", {}).get("target_range", "")
    today = datetime.now(timezone.utc).date().isoformat()

    lines: list[str] = [
        "# Work at a Startup — Target Shortlist",
        "",
        f"**Generated:** {today}",
        "**Source:** workatastartup.com (/companies/fetch)",
        f"**Target:** direct US startup role, {target}",
        "",
        f"**{len(scored)} companies matched** (have an IC full-stack / frontend role). "
        "Ranked by fit.",
        "",
        "| # | Company | Batch | Team | Best role | Remote | Visa | Salary | Fit |",
        "|---|---------|-------|------|-----------|--------|------|--------|-----|",
    ]

    for i, (c, s) in enumerate(scored, 1):
        role = s["best_role"]
        team = c.team_size if c.team_size is not None else "—"
        remote = "yes" if role.remote else "no"
        lines.append(
            f"| {i} | [{c.name}]({c.url}) | {c.batch or '—'} | {team} | {role.title} "
            f"| {remote} | {role.visa or '—'} | {role.salary or '—'} | {s['total']:.0%} |"
        )

    lines += ["", "---", "", f"## Top {min(top_n, len(scored))} — detail", ""]

    for i, (c, s) in enumerate(scored[:top_n], 1):
        role = s["best_role"]
        team = c.team_size if c.team_size is not None else "—"
        lines += [
            f"### {i}. {c.name} — {s['total']:.0%} fit",
            "",
            f"**Why target:** {'; '.join(s['reasons']) or 'role match'}",
            "",
        ]
        if c.one_liner:
            lines += [f"> {c.one_liner}", ""]
        lines.append(f"- Batch {c.batch or '—'} · team {team} · {c.location or '—'} · {c.sector or '—'}")
        if c.url:
            lines.append(f"- {c.url}")
        lines.append(
            f"- **Best role:** {role.title} — {role.role_type or '—'} · "
            f"{'remote' if role.remote else 'on-site'} · {role.visa or '—'} · "
            f"{role.salary or 'salary n/a'}"
            + (f" · equity {role.equity}" if role.equity else "")
        )
        other = [j for j in c.jobs if _is_target_role(j) and j is not role]
        if other:
            lines.append("- Other matching roles: " + ", ".join(j.title for j in other))
        lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run(dump_path: Path, profile: dict) -> dict:
    """Load → normalize → score → filter → rank → write report. Returns a summary."""
    raw_companies = load_dump(dump_path)

    scored: list[tuple[Company, dict]] = []
    for raw in raw_companies:
        company = normalize(raw)
        result = score_company(company, profile)
        if result is not None:
            scored.append((company, result))

    scored.sort(key=lambda cs: cs[1]["total"], reverse=True)

    build_report(scored, profile, REPORT_PATH)
    logger.info("WaaS shortlist: %d companies ranked → %s", len(scored), REPORT_PATH)

    return {
        "companies_ranked": len(scored),
        "top_company": scored[0][0].name if scored else "",
        "top_fit": scored[0][1]["total"] if scored else 0.0,
        "report": str(REPORT_PATH),
    }
