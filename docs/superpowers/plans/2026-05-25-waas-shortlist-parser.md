# WaaS Shortlist Parser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parse a pasted `workatastartup.com` company-directory JSON dump into a ranked markdown shortlist of target companies for a direct ~$140K US startup role.

**Architecture:** New `job-hunter-agent/waas.py` module wired via a `python main.py --waas [path]` flag. Reuses `score_fit`/`fit_label` from `main.py` (lazy import to avoid a circular import at module load). No DB writes, no cover notes. Output: `reports/waas-shortlist.md`.

**Tech Stack:** Python 3.11, stdlib `json`/`dataclasses`/`html.parser`, PyYAML, pytest 7.4.3.

---

## File Structure

- Create: `job-hunter-agent/waas.py` — loader, dataclasses, normalizer, company scorer, report builder, orchestrator
- Create: `job-hunter-agent/test_data/waas_sample.json` — synthetic fixture mimicking the expected WaaS shape
- Create: `job-hunter-agent/test_waas.py` — pytest tests
- Modify: `job-hunter-agent/main.py` — add `--waas` CLI flag
- Modify: `job-hunter-agent/config/profile.yml` — set `active_applications: []`
- Delete: stale Wellfound HTML + `_files/` dir, three stale reports; clear `.processed`

> **Synthetic-shape caveat:** `waas_sample.json` and `normalize()` are written against an *assumed* WaaS shape (a `{"companies": [...]}` array). Task 8 reconciles them against the real `waas_dump.json`. `load_dump` is tolerant of three shapes so reconciliation is small.

---

### Task 1: Scaffold `waas.py` with dataclasses + `load_dump`

**Files:**
- Create: `job-hunter-agent/waas.py`
- Create: `job-hunter-agent/test_data/waas_sample.json`
- Test: `job-hunter-agent/test_waas.py`

- [ ] **Step 1: Create the synthetic fixture**

Create `job-hunter-agent/test_data/waas_sample.json`:

```json
{
  "companies": [
    {
      "name": "Sophie Labs",
      "slug": "sophie-labs",
      "batch": "W24",
      "team_size": 8,
      "one_liner": "AI copilot for wealth advisors — multi-agent orchestration.",
      "tags": ["AI", "Fintech", "B2B"],
      "locations": ["San Francisco", "Remote"],
      "remote": "yes",
      "jobs": [
        {
          "title": "Senior Full-Stack Engineer",
          "type": "fulltime",
          "location": "Remote",
          "remote": true,
          "salary_range": "$140K - $180K",
          "equity_range": "0.2% - 0.8%",
          "description": "React, Next.js App Router, TypeScript, Tailwind, streaming AI UI, Python backend."
        }
      ]
    },
    {
      "name": "Forklift Robotics",
      "slug": "forklift-robotics",
      "batch": "S23",
      "team_size": 45,
      "one_liner": "Autonomous warehouse forklifts.",
      "tags": ["Hardware", "Robotics"],
      "locations": ["Austin"],
      "remote": false,
      "jobs": [
        {
          "title": "Embedded Systems Engineer",
          "type": "fulltime",
          "location": "Austin",
          "remote": false,
          "salary_range": "$130K - $160K",
          "equity_range": "0.1%",
          "description": "C++, ROS, embedded Linux, motor control."
        }
      ]
    },
    {
      "name": "Ledgerly",
      "slug": "ledgerly",
      "batch": "W25",
      "team_size": 5,
      "one_liner": "LLM-powered accounting automation for SMBs.",
      "tags": ["AI", "Fintech"],
      "locations": ["Remote"],
      "remote": "remote ok",
      "jobs": [
        {
          "title": "Product Engineer (AI)",
          "type": "fulltime",
          "location": "Remote",
          "remote": true,
          "salary_range": "$120K - $150K",
          "equity_range": "0.3% - 1.0%",
          "description": "Next.js, TypeScript, Tailwind, shadcn/ui, Claude API, SSE streaming, Postgres."
        }
      ]
    }
  ]
}
```

- [ ] **Step 2: Write the failing test for `load_dump`**

Create `job-hunter-agent/test_waas.py`:

```python
import json
from pathlib import Path

import pytest

import waas

FIXTURE = Path(__file__).parent / "test_data" / "waas_sample.json"


def test_load_dump_companies_shape():
    companies = waas.load_dump(FIXTURE)
    assert isinstance(companies, list)
    assert len(companies) == 3
    assert companies[0]["name"] == "Sophie Labs"


def test_load_dump_algolia_shape(tmp_path):
    p = tmp_path / "algolia.json"
    p.write_text(json.dumps({"results": [{"hits": [{"name": "A"}, {"name": "B"}]}]}))
    assert [c["name"] for c in waas.load_dump(p)] == ["A", "B"]


def test_load_dump_bare_list(tmp_path):
    p = tmp_path / "bare.json"
    p.write_text(json.dumps([{"name": "X"}]))
    assert waas.load_dump(p)[0]["name"] == "X"


def test_load_dump_unknown_shape_raises(tmp_path):
    p = tmp_path / "weird.json"
    p.write_text(json.dumps({"foo": 1, "bar": 2}))
    with pytest.raises(ValueError, match="foo"):
        waas.load_dump(p)


def test_load_dump_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        waas.load_dump(tmp_path / "nope.json")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd job-hunter-agent && python -m pytest test_waas.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'waas'`

- [ ] **Step 4: Create `waas.py` with imports, dataclasses, and `load_dump`**

Create `job-hunter-agent/waas.py`:

```python
"""
job-hunter-agent/waas.py
========================
Parse a workatastartup.com company-directory JSON dump into a ranked
markdown shortlist of target companies. Company targeting, not applications:
no DB writes, no cover notes.

Usage (via main.py):
    python main.py --waas               # reads waas_dump.json
    python main.py --waas path.json     # explicit dump path
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("job-hunter.waas")

AGENT_DIR = Path(__file__).parent
DEFAULT_DUMP = AGENT_DIR / "waas_dump.json"
REPORT_PATH = AGENT_DIR / "reports" / "waas-shortlist.md"


@dataclass
class Job:
    title: str
    role_type: str
    location: str
    remote: bool
    salary: str | None
    equity: str | None
    text: str


@dataclass
class Company:
    name: str
    batch: str
    team_size: int | None
    location: str
    remote: bool
    tags: list[str]
    one_liner: str
    url: str
    jobs: list[Job]


def load_dump(path: Path) -> list[dict]:
    """Tolerant reader for the WaaS dump. Returns a list of raw company dicts."""
    if not path.exists():
        raise FileNotFoundError(
            f"No WaaS dump at {path}.\n"
            "Grab one: log into workatastartup.com/companies, open DevTools → "
            "Network → Fetch/XHR, find the response that is an array of companies, "
            "Copy response, save it as that path."
        )
    raw = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        if isinstance(raw.get("results"), list):
            hits: list[dict] = []
            for result in raw["results"]:
                hits.extend(result.get("hits", []))
            return hits
        if isinstance(raw.get("companies"), list):
            return raw["companies"]
        raise ValueError(
            f"Unrecognized WaaS dump shape. Top-level keys: {list(raw.keys())}"
        )
    raise ValueError("Unrecognized WaaS dump: JSON root is neither list nor object.")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd job-hunter-agent && python -m pytest test_waas.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
git add job-hunter-agent/waas.py job-hunter-agent/test_waas.py job-hunter-agent/test_data/waas_sample.json
git commit -m "feat(job-hunter): scaffold waas.py with tolerant dump loader"
```

---

### Task 2: `normalize(raw) -> Company`

**Files:**
- Modify: `job-hunter-agent/waas.py`
- Test: `job-hunter-agent/test_waas.py`

- [ ] **Step 1: Write the failing test**

Append to `job-hunter-agent/test_waas.py`:

```python
def test_normalize_full_company():
    companies = waas.load_dump(FIXTURE)
    c = waas.normalize(companies[0])
    assert c.name == "Sophie Labs"
    assert c.batch == "W24"
    assert c.team_size == 8
    assert c.remote is True
    assert "AI" in c.tags
    assert c.url == "https://www.workatastartup.com/companies/sophie-labs"
    assert len(c.jobs) == 1
    job = c.jobs[0]
    assert job.title == "Senior Full-Stack Engineer"
    assert job.remote is True
    assert job.salary == "$140K - $180K"
    assert "next.js" in job.text.lower()


def test_normalize_remote_string_variants():
    c = waas.normalize({"name": "R", "remote": "remote ok", "jobs": []})
    assert c.remote is True
    c2 = waas.normalize({"name": "N", "remote": False, "jobs": []})
    assert c2.remote is False


def test_normalize_missing_fields_degrade():
    c = waas.normalize({"name": "Bare"})
    assert c.name == "Bare"
    assert c.team_size is None
    assert c.jobs == []
    assert c.tags == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd job-hunter-agent && python -m pytest test_waas.py -k normalize -v`
Expected: FAIL — `AttributeError: module 'waas' has no attribute 'normalize'`

- [ ] **Step 3: Implement `normalize` (and `_as_bool_remote`)**

Append to `job-hunter-agent/waas.py`:

```python
def _as_bool_remote(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"yes", "true", "remote", "remote ok", "1"}
    return False


def normalize(raw: dict) -> Company:
    """Map a raw WaaS company dict to a Company. Missing fields degrade gracefully."""
    jobs: list[Job] = []
    for j in raw.get("jobs") or []:
        salary = j.get("salary_range") or j.get("salary") or None
        jobs.append(Job(
            title=j.get("title", ""),
            role_type=j.get("type") or j.get("role_type", ""),
            location=j.get("location", ""),
            remote=_as_bool_remote(j.get("remote")),
            salary=salary,
            equity=j.get("equity_range") or j.get("equity") or None,
            text=" ".join(filter(None, [
                j.get("title", ""),
                j.get("description", ""),
                j.get("location", ""),
                salary or "",
            ])),
        ))

    locations = raw.get("locations")
    if isinstance(locations, list):
        location = ", ".join(locations)
    else:
        location = str(locations or raw.get("location", "") or "")

    team_size = raw.get("team_size", raw.get("company_size"))
    try:
        team_size = int(team_size) if team_size is not None else None
    except (ValueError, TypeError):
        team_size = None

    remote = (
        _as_bool_remote(raw.get("remote"))
        or any(job.remote for job in jobs)
        or "remote" in location.lower()
    )

    slug = raw.get("slug", "")
    url = raw.get("url") or (
        f"https://www.workatastartup.com/companies/{slug}" if slug else ""
    )

    one_liner = raw.get("one_liner") or (raw.get("long_description", "") or "")[:200]

    return Company(
        name=raw.get("name", ""),
        batch=raw.get("batch", ""),
        team_size=team_size,
        location=location,
        remote=remote,
        tags=raw.get("tags") or [],
        one_liner=one_liner,
        url=url,
        jobs=jobs,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd job-hunter-agent && python -m pytest test_waas.py -k normalize -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add job-hunter-agent/waas.py job-hunter-agent/test_waas.py
git commit -m "feat(job-hunter): add WaaS company normalizer"
```

---

### Task 3: `score_company(company, profile)`

**Files:**
- Modify: `job-hunter-agent/waas.py`
- Test: `job-hunter-agent/test_waas.py`

- [ ] **Step 1: Write the failing test**

Append to `job-hunter-agent/test_waas.py`:

```python
import sys

# Ensure main.py is importable as "main" for the lazy score_fit import
sys.path.insert(0, str(Path(__file__).parent))
import main  # noqa: E402

PROFILE = main.load_profile()


def test_score_company_ai_remote_earlystage_ranks_high():
    companies = waas.load_dump(FIXTURE)
    sophie = waas.normalize(companies[0])  # AI, remote, team 8, strong stack
    result = waas.score_company(sophie, PROFILE)
    assert result is not None
    assert result["ai_product"] == 1.0
    assert result["intl_remote"] == 1.0
    assert result["early_stage"] == 1.0
    assert result["best_role"].title == "Senior Full-Stack Engineer"
    assert result["total"] > 0.6


def test_score_company_no_matching_role_filtered():
    companies = waas.load_dump(FIXTURE)
    forklift = waas.normalize(companies[1])  # embedded role, no title/stack match
    assert waas.score_company(forklift, PROFILE) is None


def test_score_company_ledgerly_matches():
    companies = waas.load_dump(FIXTURE)
    ledgerly = waas.normalize(companies[2])  # Product Engineer (AI), remote, team 5
    result = waas.score_company(ledgerly, PROFILE)
    assert result is not None
    assert result["ai_product"] == 1.0
    assert "Early-stage" in " ".join(result["reasons"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd job-hunter-agent && python -m pytest test_waas.py -k score_company -v`
Expected: FAIL — `AttributeError: module 'waas' has no attribute 'score_company'`

- [ ] **Step 3: Implement `score_company`**

Append to `job-hunter-agent/waas.py`:

```python
AI_KEYWORDS = [
    "ai", "llm", "agent", "ml", "machine learning",
    "gpt", "genai", "generative", "model",
]
EARLY_STAGE_TEAM_MAX = 30
WEIGHTS = {"role_fit": 0.40, "ai_product": 0.20, "early_stage": 0.20, "intl_remote": 0.20}


def score_company(company: Company, profile: dict) -> dict | None:
    """
    Company-level fit score. Returns None if no open role matches a primary
    target title with any stack overlap (company filtered from the shortlist).
    """
    # Lazy import avoids a circular import at module load (main.py imports waas).
    from main import score_fit

    primary_titles = [
        t.lower() for t in profile.get("target_roles", {}).get("primary", [])
    ]

    best_role: Job | None = None
    best_role_fit = 0.0
    for job in company.jobs:
        title_l = job.title.lower()
        if not any(all_words_present(t, title_l) for t in primary_titles):
            continue
        detail = score_fit(job.text, profile)
        if detail["stack"] <= 0:
            continue
        if detail["total"] > best_role_fit:
            best_role_fit = detail["total"]
            best_role = job

    if best_role is None:
        return None

    reasons: list[str] = []

    haystack = (company.one_liner + " " + " ".join(company.tags)).lower()
    ai_hits = [k for k in AI_KEYWORDS if k in haystack]
    ai_product = 1.0 if ai_hits else 0.0
    if ai_hits:
        reasons.append(f"AI signal: {', '.join(ai_hits[:3])}")

    if company.team_size is None:
        early_stage = 0.5  # unknown — neutral
    elif company.team_size <= EARLY_STAGE_TEAM_MAX:
        early_stage = 1.0
        reasons.append(f"Early-stage: team {company.team_size}")
    else:
        early_stage = 0.0

    intl_remote = 1.0 if company.remote else 0.0
    if company.remote:
        reasons.append("Remote-friendly")

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
        "intl_remote": intl_remote,
        "best_role": best_role,
        "reasons": reasons,
    }


def all_words_present(phrase: str, haystack_lower: str) -> bool:
    """True if every word of `phrase` (lowercased) appears in haystack."""
    return all(word in haystack_lower for word in phrase.split())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd job-hunter-agent && python -m pytest test_waas.py -k score_company -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add job-hunter-agent/waas.py job-hunter-agent/test_waas.py
git commit -m "feat(job-hunter): add company-level fit scorer"
```

---

### Task 4: `build_report(scored, profile, out_path)`

**Files:**
- Modify: `job-hunter-agent/waas.py`
- Test: `job-hunter-agent/test_waas.py`

- [ ] **Step 1: Write the failing test**

Append to `job-hunter-agent/test_waas.py`:

```python
def test_build_report_writes_ranked_markdown(tmp_path):
    companies = [waas.normalize(c) for c in waas.load_dump(FIXTURE)]
    scored = []
    for c in companies:
        r = waas.score_company(c, PROFILE)
        if r is not None:
            scored.append((c, r))
    scored.sort(key=lambda cs: cs[1]["total"], reverse=True)

    out = tmp_path / "waas-shortlist.md"
    waas.build_report(scored, PROFILE, out)

    text = out.read_text()
    assert "# Work at a Startup — Target Shortlist" in text
    assert "Sophie Labs" in text
    assert "Forklift Robotics" not in text  # filtered out
    assert "| # | Company |" in text
    assert "Why target:" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd job-hunter-agent && python -m pytest test_waas.py -k build_report -v`
Expected: FAIL — `AttributeError: module 'waas' has no attribute 'build_report'`

- [ ] **Step 3: Implement `build_report`**

Append to `job-hunter-agent/waas.py`:

```python
def build_report(
    scored: list[tuple[Company, dict]],
    profile: dict,
    out_path: Path,
    top_n: int = 15,
) -> None:
    """Write a ranked markdown shortlist to out_path."""
    target = profile.get("compensation", {}).get("target_range", "")
    today = datetime.now(timezone.utc).date().isoformat()

    lines: list[str] = [
        "# Work at a Startup — Target Shortlist",
        "",
        f"**Generated:** {today}",
        "**Source:** workatastartup.com company directory",
        f"**Target:** direct US startup role, {target}",
        "",
        f"**{len(scored)} companies matched.** Ranked by fit.",
        "",
        "| # | Company | Batch | Team | Location | Remote | Best role | Salary | Fit |",
        "|---|---------|-------|------|----------|--------|-----------|--------|-----|",
    ]

    for i, (c, s) in enumerate(scored, 1):
        role = s["best_role"]
        team = c.team_size if c.team_size is not None else "—"
        lines.append(
            f"| {i} | [{c.name}]({c.url}) | {c.batch or '—'} | {team} "
            f"| {c.location or '—'} | {'yes' if c.remote else 'no'} | {role.title} "
            f"| {role.salary or '—'} | {s['total']:.0%} |"
        )

    lines += ["", "---", "", f"## Top {min(top_n, len(scored))} — detail", ""]

    for i, (c, s) in enumerate(scored[:top_n], 1):
        team = c.team_size if c.team_size is not None else "—"
        lines += [
            f"### {i}. {c.name} — {s['total']:.0%} fit",
            "",
            f"**Why target:** {'; '.join(s['reasons']) or 'stack match'}",
            "",
        ]
        if c.one_liner:
            lines += [f"> {c.one_liner}", ""]
        lines.append(f"- Batch {c.batch or '—'} · team {team} · {c.location or '—'}")
        if c.url:
            lines.append(f"- {c.url}")
        lines.append("- Open roles:")
        for job in c.jobs:
            where = "remote" if job.remote else (job.location or "on-site")
            sal = f" — {job.salary}" if job.salary else ""
            lines.append(f"  - {job.title} ({where}){sal}")
        lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd job-hunter-agent && python -m pytest test_waas.py -k build_report -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add job-hunter-agent/waas.py job-hunter-agent/test_waas.py
git commit -m "feat(job-hunter): add shortlist markdown report builder"
```

---

### Task 5: `run(dump_path, profile)` orchestrator

**Files:**
- Modify: `job-hunter-agent/waas.py`
- Test: `job-hunter-agent/test_waas.py`

- [ ] **Step 1: Write the failing test**

Append to `job-hunter-agent/test_waas.py`:

```python
def test_run_end_to_end(tmp_path, monkeypatch):
    out = tmp_path / "waas-shortlist.md"
    monkeypatch.setattr(waas, "REPORT_PATH", out)
    summary = waas.run(FIXTURE, PROFILE)
    assert summary["companies_ranked"] == 2  # Sophie + Ledgerly; Forklift filtered
    assert summary["top_company"] in {"Sophie Labs", "Ledgerly"}
    assert out.exists()
    assert summary["report"] == str(out)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd job-hunter-agent && python -m pytest test_waas.py -k run_end_to_end -v`
Expected: FAIL — `AttributeError: module 'waas' has no attribute 'run'`

- [ ] **Step 3: Implement `run`**

Append to `job-hunter-agent/waas.py`:

```python
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
    logger.info(
        "WaaS shortlist: %d companies ranked → %s", len(scored), REPORT_PATH
    )

    return {
        "companies_ranked": len(scored),
        "top_company": scored[0][0].name if scored else "",
        "top_fit": scored[0][1]["total"] if scored else 0.0,
        "report": str(REPORT_PATH),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd job-hunter-agent && python -m pytest test_waas.py -k run_end_to_end -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Run the full test file**

Run: `cd job-hunter-agent && python -m pytest test_waas.py -v`
Expected: PASS (all tests)

- [ ] **Step 6: Commit**

```bash
git add job-hunter-agent/waas.py job-hunter-agent/test_waas.py
git commit -m "feat(job-hunter): add run() orchestrator for WaaS shortlist"
```

---

### Task 6: Wire `--waas` flag into `main.py`

**Files:**
- Modify: `job-hunter-agent/main.py` (argparse block ~line 838; command dispatch ~line 849)

- [ ] **Step 1: Add the argparse argument**

In `main()`, after the `--theirstack` argument (around line 844), add:

```python
    parser.add_argument("--waas", nargs="?", const="waas_dump.json", metavar="PATH",
                        help="Build target shortlist from a workatastartup.com JSON dump")
```

- [ ] **Step 2: Add the command dispatch**

In `main()`, immediately after the `if args.theirstack:` block ends (before the `if args.api:` block, around line 857), add:

```python
    if args.waas:
        import waas
        profile = load_profile()
        dump_path = Path(args.waas)
        if not dump_path.is_absolute():
            dump_path = AGENT_DIR / dump_path
        summary = waas.run(dump_path, profile)
        logger.info("─" * 50)
        logger.info(
            "Shortlist: %d companies | top: %s (%.0f%%) → %s",
            summary["companies_ranked"], summary["top_company"],
            summary["top_fit"] * 100, summary["report"],
        )
        coordinator_outputs = {
            "__completed_tasks__": ["build_waas_shortlist"] if summary["companies_ranked"] else [],
            "companies_ranked": summary["companies_ranked"],
            "top_fit_company": summary["top_company"],
            "top_fit_score": round(summary["top_fit"], 3),
        }
        print(json.dumps({"__coordinator_outputs__": coordinator_outputs}))
        return
```

- [ ] **Step 3: Smoke test against the fixture**

Run: `cd job-hunter-agent && python main.py --waas test_data/waas_sample.json`
Expected: log line "Shortlist: 2 companies | top: …", and a `__coordinator_outputs__` JSON line. `reports/waas-shortlist.md` is written.

- [ ] **Step 4: Verify the report content**

Run: `cd job-hunter-agent && head -20 reports/waas-shortlist.md`
Expected: the markdown header + ranked table with Sophie Labs and Ledgerly, no Forklift Robotics.

- [ ] **Step 5: Commit**

```bash
git add job-hunter-agent/main.py job-hunter-agent/reports/waas-shortlist.md
git commit -m "feat(job-hunter): wire --waas flag into CLI"
```

---

### Task 7: Start-fresh cleanup

**Files:**
- Delete: stale Wellfound HTML + `_files/`, three stale reports
- Modify: `job-hunter-agent/.processed` (clear), `job-hunter-agent/config/profile.yml`

- [ ] **Step 1: Delete the stale Wellfound listing + assets**

```bash
cd job-hunter-agent
rm -f "Senior Full-Stack Engineer at Splink • New York City • Remote (Work from Home) _ Wellfound.html"
rm -rf "Senior Full-Stack Engineer at Splink • New York City • Remote (Work from Home) _ Wellfound_files"
```

- [ ] **Step 2: Delete the three stale reports**

```bash
cd job-hunter-agent
rm -f reports/market-analysis-senior-frontend-2026.md \
      reports/prospera-ai-fullstack-frontend.md \
      reports/homevision-sr-frontend-engineer.md
```

- [ ] **Step 3: Clear `.processed`**

```bash
cd job-hunter-agent && : > .processed
```

- [ ] **Step 4: Empty `active_applications` in `profile.yml`**

In `config/profile.yml`, replace the entire `active_applications:` block (the two `- company:` entries for Prospera AI and HomeVision) with:

```yaml
# Active applications — updated manually
active_applications: []
```

- [ ] **Step 5: Verify nothing references deleted files**

Run: `cd job-hunter-agent && grep -rn "prospera-ai-fullstack\|homevision-sr\|market-analysis-senior" . --include=*.py --include=*.yml --include=*.md | grep -v docs/superpowers || echo "no stale references"`
Expected: `no stale references` (the roadmap mentions report filenames in a tree diagram; that is documentation, leave it).

- [ ] **Step 6: Confirm the kept files remain**

Run: `cd job-hunter-agent && ls reports/`
Expected: `linkedin-article-streaming-ui.md`, `roadmap-2month-120k.md`, `waas-shortlist.md` (no deleted reports).

- [ ] **Step 7: Commit**

```bash
git add -A job-hunter-agent
git commit -m "chore(job-hunter): clear stale listings, start fresh on WaaS"
```

---

### Task 8: Reconcile against the real `waas_dump.json`

> Do this once the real dump exists at `job-hunter-agent/waas_dump.json`. If it is not yet available, STOP after Task 7 and report that this task is pending the sample.

**Files:**
- Modify (if needed): `job-hunter-agent/waas.py` (`normalize`), `job-hunter-agent/test_data/waas_sample.json`

- [ ] **Step 1: Inspect the real dump's top-level shape**

Run: `cd job-hunter-agent && python -c "import json,sys; d=json.load(open('waas_dump.json')); print(type(d).__name__); print(list(d.keys()) if isinstance(d,dict) else 'list len '+str(len(d)))"`
Expected: prints the root type and keys. Confirm `load_dump` handles it (list / `results` / `companies`). If a new wrapper key appears, add a branch to `load_dump` mirroring the existing ones.

- [ ] **Step 2: Inspect one company's fields**

Run: `cd job-hunter-agent && python -c "import waas; c=waas.load_dump(__import__('pathlib').Path('waas_dump.json')); import json; print(json.dumps(c[0], indent=2)[:1500])"`
Expected: the real field names for name, batch, team size, tags, locations, remote, and the jobs array (title, type, location, remote, salary, equity, description).

- [ ] **Step 3: Update `normalize` field mappings to match**

For each real field name that differs from the assumed names in `normalize` (e.g., `team_size` vs `company_size` vs `num_employees`; `jobs` vs `open_roles`; `salary_range` vs `salary`), add it to the corresponding `.get(...)` fallback chain in `normalize`. Keep existing fallbacks so the synthetic fixture still passes.

- [ ] **Step 4: Refresh the fixture from real data (trimmed)**

Replace `test_data/waas_sample.json` with 3 real (trimmed) companies copied from `waas_dump.json`: keep one strong AI/remote/small-team match, one clear non-match (wrong stack/title), one borderline. Preserve the test expectations by choosing companies that satisfy them, or update the assertions in `test_waas.py` to the new company names/values.

- [ ] **Step 5: Run the full suite**

Run: `cd job-hunter-agent && python -m pytest test_waas.py -v`
Expected: PASS (all tests).

- [ ] **Step 6: Generate the real shortlist**

Run: `cd job-hunter-agent && python main.py --waas`
Expected: ranked `reports/waas-shortlist.md` from real data; eyeball the top 10 for sanity (AI startups, small teams, remote, real senior FE/FS/AI roles).

- [ ] **Step 7: Commit**

```bash
git add job-hunter-agent/waas.py job-hunter-agent/test_waas.py job-hunter-agent/test_data/waas_sample.json job-hunter-agent/reports/waas-shortlist.md
git commit -m "feat(job-hunter): reconcile WaaS parser with real dump shape"
```

---

## Self-Review Notes

- **Spec coverage:** load_dump (T1), dataclasses (T1), normalize (T2), score_company w/ 4 signals + filtering (T3), build_report (T4), run + coordinator outputs (T5), CLI `--waas` (T6), start-fresh cleanup incl. `active_applications: []` (T7), real-sample reconciliation (T8). All spec sections covered.
- **Placeholder scan:** none — every code step shows full code; cleanup steps show exact commands.
- **Type consistency:** `Company`/`Job` fields, `score_company` return keys (`total/role_fit/ai_product/early_stage/intl_remote/best_role/reasons`), and `run` summary keys (`companies_ranked/top_company/top_fit/report`) are used consistently across tasks and the `main.py` dispatch.
- **Note:** `score_company` uses a lazy `from main import score_fit`; tests insert the agent dir on `sys.path` and import `main` directly, so the function resolves in both pytest and CLI contexts.
