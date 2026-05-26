"""
job-hunter-agent/main.py
=========================
Reads job posting HTML files, scores fit against profile.yml,
generates a tailored cover note via Claude, and syncs to Solaris DB.

Usage:
    python main.py                    # process all unprocessed HTML files
    python main.py --api              # fetch jobs from Arbeitnow API
    python main.py --api --pages 5   # fetch N pages (25 jobs/page)
    python main.py --cover <id>       # regenerate cover note for a job ID
    python main.py --list             # list all jobs in Solaris DB

Coordinator integration:
    Runs in coordinator mode when COORDINATOR_MODE=1.
    Emits __coordinator_outputs__ JSON to stdout at the end.
"""

import argparse
import json
import logging
import os
import re
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import yaml
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
AGENT_DIR   = Path(__file__).parent
CONFIG_FILE = AGENT_DIR / "config" / "profile.yml"
SOLARIS_DB  = AGENT_DIR.parent / "solaris" / "solaris.db"
PROCESSED_LOG = AGENT_DIR / ".processed"   # tracks which HTML files were done

# Load env — own .env first, then fall back to solaris/.env (shared keys)
load_dotenv(AGENT_DIR / ".env")
load_dotenv(AGENT_DIR.parent / "solaris" / ".env")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("job-hunter")

# ---------------------------------------------------------------------------
# HTML parser — extracts visible text from a saved job posting
# ---------------------------------------------------------------------------

class _TextExtractor(HTMLParser):
    SKIP_TAGS = {"script", "style", "noscript", "svg", "meta", "link", "head"}

    def __init__(self):
        super().__init__()
        self.texts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag.lower() in self.SKIP_TAGS:
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if self._skip == 0:
            stripped = data.strip()
            if stripped:
                self.texts.append(stripped)


class _NextDataExtractor(HTMLParser):
    """Captures the content of <script id="__NEXT_DATA__">."""
    def __init__(self):
        super().__init__()
        self.texts: list[str] = []
        self._in_next_data = False

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script":
            attrs_dict = dict(attrs)
            if attrs_dict.get("id") == "__NEXT_DATA__":
                self._in_next_data = True

    def handle_endtag(self, tag):
        if tag.lower() == "script":
            self._in_next_data = False

    def handle_data(self, data):
        if self._in_next_data and data.strip():
            self.texts.append(data)


def _extract_wellfound_next_data(html: str) -> str:
    """
    Parse Wellfound / AngelList HTML — content lives in __NEXT_DATA__ Apollo state.
    Returns a flat text string suitable for scoring, or empty string if not found.
    """
    extractor = _NextDataExtractor()
    extractor.feed(html)
    if not extractor.texts:
        return ""

    try:
        data = json.loads(extractor.texts[0])
    except json.JSONDecodeError:
        return ""

    # Navigate to Apollo state
    apollo = (
        data.get("props", {})
            .get("pageProps", {})
            .get("apolloState", {})
            .get("data", {})
    )
    if not apollo:
        return ""

    # Find the JobListing:* key with a description
    job = None
    for key, value in apollo.items():
        if key.startswith("JobListing:") and isinstance(value, dict) and value.get("description"):
            job = value
            break

    if not job:
        return ""

    parts: list[str] = []

    title = job.get("title", "")
    if title:
        parts.append(f"Title: {title}")

    # Company name — look up via companyId or StartupRole ref
    company_ref = job.get("startup", {})
    if isinstance(company_ref, dict):
        company_id = company_ref.get("id") or company_ref.get("__ref", "")
        company_node = apollo.get(company_id, {})
        company_name = company_node.get("name", "")
        if company_name:
            parts.append(f"Company: {company_name}")

    compensation = job.get("compensation", "")
    if compensation:
        parts.append(f"Compensation: {compensation}")

    remote = job.get("remote")
    if remote:
        parts.append("Remote: yes")
        locations = job.get("acceptedRemoteLocationNames", [])
        if locations:
            parts.append(f"Remote locations: {', '.join(locations)}")

    visa = job.get("visaSponsorship")
    if visa:
        parts.append(f"Visa sponsorship: {visa}")

    years_exp = job.get("yearsExperienceMin")
    if years_exp is not None:
        parts.append(f"Years experience minimum: {years_exp}")

    # Skills — resolve refs
    skills_refs = job.get("skills", [])
    if isinstance(skills_refs, list):
        skill_names = []
        for ref in skills_refs:
            if isinstance(ref, dict):
                node_id = ref.get("__ref", "")
                node = apollo.get(node_id, {})
                name = node.get("displayValue") or node.get("name") or node.get("slug", "")
                if name:
                    skill_names.append(name)
        if skill_names:
            parts.append(f"Skills: {', '.join(skill_names)}")

    description = job.get("description", "")
    if description:
        parts.append(f"\nJob Description:\n{description}")

    return "\n".join(parts)


def extract_text(html_path: Path) -> str:
    html = html_path.read_text(encoding="utf-8", errors="ignore")

    # Try Wellfound / Next.js SPA pattern first
    next_data_text = _extract_wellfound_next_data(html)
    if next_data_text:
        return next_data_text

    # Fallback: visible text extraction for regular HTML
    parser = _TextExtractor()
    parser.feed(html)
    return "\n".join(parser.texts)


# ---------------------------------------------------------------------------
# Profile loader
# ---------------------------------------------------------------------------

def load_profile() -> dict:
    if not CONFIG_FILE.exists():
        logger.error("profile.yml not found at %s", CONFIG_FILE)
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Fit scorer
# ---------------------------------------------------------------------------

def score_fit(job_text: str, profile: dict) -> dict:
    """
    Score a job posting against the candidate profile.
    Returns a dict with per-dimension scores and a total (0.0–1.0).
    """
    text_lower = job_text.lower()
    weights    = profile.get("scoring_weights", {})
    stack      = profile.get("experience", {}).get("tech_stack", {})
    target     = profile.get("compensation", {})

    # ── Stack match ───────────────────────────────────────────────────────
    all_skills = []
    for skills in stack.values():
        all_skills.extend([s.lower() for s in (skills or [])])

    matched = [s for s in all_skills if s in text_lower]
    stack_score = min(1.0, len(matched) / max(len(all_skills) * 0.4, 1))

    # ── Role match ────────────────────────────────────────────────────────
    primary_roles = [r.lower() for r in (profile.get("target_roles", {}).get("primary") or [])]
    role_hits     = sum(1 for r in primary_roles if any(word in text_lower for word in r.split()))
    role_score    = min(1.0, role_hits / max(len(primary_roles), 1))

    # Seniority signal — bonus if "senior" or "staff" in posting
    if any(w in text_lower for w in ["senior", "staff", "lead", "principal"]):
        role_score = min(1.0, role_score + 0.2)

    # ── Remote policy ─────────────────────────────────────────────────────
    if "fully remote" in text_lower or "100% remote" in text_lower or "remote-first" in text_lower:
        remote_score = 1.0
    elif "remote" in text_lower:
        remote_score = 0.7
    elif "hybrid" in text_lower:
        remote_score = 0.4
    else:
        remote_score = 0.1

    # ── Equity ────────────────────────────────────────────────────────────
    equity_keywords = ["equity", "stock", "options", "vesting", "esop", "shares", "%"]
    equity_hits     = sum(1 for kw in equity_keywords if kw in text_lower)
    equity_score    = min(1.0, equity_hits / 3)

    # ── Salary ────────────────────────────────────────────────────────────
    # Try to extract salary numbers from text
    salary_score = 0.5  # neutral default
    numbers = re.findall(r"\$?([\d,]+)[kK]?", job_text)
    parsed  = []
    for n in numbers:
        try:
            v = float(n.replace(",", ""))
            if 50 <= v <= 500:           # likely thousands
                parsed.append(v * 1000)
            elif 50000 <= v <= 500000:   # already in dollars
                parsed.append(v)
        except ValueError:
            continue

    if parsed:
        mid = (min(parsed) + max(parsed)) / 2
        try:
            min_target = float(re.sub(r"[^\d]", "", target.get("minimum", "120000")))
        except Exception:
            min_target = 120000
        if mid >= min_target:
            salary_score = 1.0
        elif mid >= min_target * 0.85:
            salary_score = 0.7
        else:
            salary_score = 0.3

    # ── Weighted total ────────────────────────────────────────────────────
    w_stack  = weights.get("stack_match",   0.30)
    w_role   = weights.get("role_match",    0.25)
    w_remote = weights.get("remote_policy", 0.15)
    w_equity = weights.get("equity",        0.15)
    w_salary = weights.get("salary",        0.15)

    total = (
        stack_score  * w_stack  +
        role_score   * w_role   +
        remote_score * w_remote +
        equity_score * w_equity +
        salary_score * w_salary
    )

    return {
        "total":        round(total, 3),
        "stack":        round(stack_score, 3),
        "role":         round(role_score, 3),
        "remote":       round(remote_score, 3),
        "equity":       round(equity_score, 3),
        "salary":       round(salary_score, 3),
        "stack_matched": matched[:10],
    }


def fit_label(score: float) -> str:
    if score >= 0.75: return "STRONG"
    if score >= 0.55: return "GOOD"
    if score >= 0.40: return "MAYBE"
    return "WEAK"


# ---------------------------------------------------------------------------
# Cover note generator
# ---------------------------------------------------------------------------

def generate_cover_note(job_text: str, profile: dict, company_name: str = "") -> str:
    """Call Claude to generate a tailored cover note."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — skipping cover note generation")
        return ""

    try:
        import anthropic
        candidate  = profile.get("candidate", {})
        narrative  = profile.get("narrative", {})
        experience = profile.get("experience", {})

        system = f"""You are writing a cover note for {candidate.get('full_name', 'the candidate')}.

Candidate profile:
- Headline: {narrative.get('headline', '')}
- Exit story: {narrative.get('exit_story', '').strip()}
- Superpowers: {', '.join(narrative.get('superpowers', []))}
- Stack: {', '.join(sum([v for v in experience.get('tech_stack', {}).values()], []))}
- Key experience: {', '.join([f"{c['name']} — {c['highlight']}" for c in experience.get('companies', [])])}

Write a concise, direct cover note (4–5 short paragraphs).
- Lead with a specific hook about the company or role
- Reference 1–2 concrete proof points
- Show you understand the problem they're solving
- End with a clear call to action
- No filler phrases like "I am excited to" or "I believe I would be a great fit"
- Tone: confident, direct, human — not corporate
- Max 250 words"""

        user = f"""Company: {company_name or 'the company'}

Job posting (trimmed):
{job_text[:3000]}

Write the cover note."""

        client   = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=os.getenv("LLM_COVER_MODEL", "claude-opus-4-6"),
            max_tokens=600,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text.strip()

    except Exception as exc:
        logger.error("Cover note generation failed: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# Solaris DB sync
# ---------------------------------------------------------------------------

def extract_company_from_filename(path: Path) -> str:
    """Best-effort company name from a Wellfound/LinkedIn filename."""
    name = path.stem
    # Wellfound format: "Role at Company • City • Remote _ Wellfound"
    m = re.search(r" at ([^•·|]+)", name)
    if m:
        return m.group(1).strip()
    return name[:40]


def extract_role_from_filename(path: Path) -> str:
    name = path.stem
    m = re.match(r"^([^•·|@]+?)(?:\s+at\s+|\s+@\s+)", name)
    if m:
        return m.group(1).strip()
    return "Engineer"


def sync_to_solaris(
    company: str,
    role: str,
    score: dict,
    cover_note: str,
    source_file: str,
    job_text: str,
    url: str = "",
) -> int | None:
    """Insert or update job in Solaris DB. Returns job id."""
    if not SOLARIS_DB.exists():
        logger.warning("Solaris DB not found at %s — skipping sync", SOLARIS_DB)
        return None

    now = datetime.now(timezone.utc).isoformat()
    notes = (
        f"Fit score: {score['total']:.0%} ({fit_label(score['total'])}) | "
        f"stack={score['stack']:.0%} role={score['role']:.0%} remote={score['remote']:.0%} "
        f"equity={score['equity']:.0%} salary={score['salary']:.0%}\n"
        f"Matched stack: {', '.join(score['stack_matched'])}\n"
        f"Source: {source_file}"
    )
    if cover_note:
        notes += f"\n\n--- COVER NOTE ---\n{cover_note}"

    try:
        conn = sqlite3.connect(str(SOLARIS_DB))
        cur  = conn.cursor()

        # Check if already exists by company + role
        existing = cur.execute(
            "SELECT id FROM jobs WHERE company=? AND role=?", (company, role)
        ).fetchone()

        if existing:
            cur.execute(
                "UPDATE jobs SET notes=?, url=COALESCE(NULLIF(?, ''), url), updated_at=? WHERE id=?",
                (notes, url or "", now, existing[0]),
            )
            conn.commit()
            conn.close()
            logger.info("Updated existing job #%d — %s / %s", existing[0], company, role)
            return existing[0]
        else:
            cur.execute(
                """INSERT INTO jobs (company, role, url, status, notes, updated_at)
                   VALUES (?, ?, ?, 'bookmarked', ?, ?)""",
                (company, role, url or None, notes, now),
            )
            job_id = cur.lastrowid
            conn.commit()
            conn.close()
            logger.info("Added job #%d — %s / %s", job_id, company, role)
            return job_id

    except Exception as exc:
        logger.error("Solaris DB sync failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Arbeitnow API
# ---------------------------------------------------------------------------

ARBEITNOW_API    = "https://www.arbeitnow.com/api/job-board-api"
THEIRSTACK_API   = "https://api.theirstack.com/v1/jobs/search"

# Map profile tech stack entries to TheirStack technology slugs
_SLUG_MAP = {
    "typescript": "typescript", "react": "react", "next.js": "next-js",
    "tailwind": "tailwind-css", "node.js": "node-js", "python": "python",
    "flask": "flask", "postgresql": "postgresql", "sqlite": "sqlite",
    "redis": "redis", "aws": "amazon-web-services", "docker": "docker",
    "github actions": "github-actions",
}


def _html_to_text(html: str) -> str:
    """Strip HTML tags from a string."""
    parser = _TextExtractor()
    parser.feed(html)
    return "\n".join(parser.texts)


def _profile_keywords(profile: dict) -> list[str]:
    """Flat list of tech keywords from profile for pre-filter."""
    stack = profile.get("experience", {}).get("tech_stack", {})
    keywords = []
    for skills in stack.values():
        keywords.extend([s.lower() for s in (skills or [])])
    return keywords


def fetch_arbeitnow(profile: dict, pages: int = 3, min_score: float = 0.40) -> list[dict]:
    """
    Fetch jobs from Arbeitnow API, score each, return results above min_score.
    Skips already-processed slugs.
    """
    processed = load_processed()
    keywords  = _profile_keywords(profile)
    results   = []

    for page in range(1, pages + 1):
        url = f"{ARBEITNOW_API}?page={page}"
        logger.info("Fetching Arbeitnow page %d/%d …", page, pages)

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "job-hunter-agent/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                payload = json.loads(resp.read().decode())
        except Exception as exc:
            logger.error("Arbeitnow fetch failed (page %d): %s", page, exc)
            break

        jobs = payload.get("data", [])
        if not jobs:
            break

        for job in jobs:
            slug = job.get("slug", "")
            if slug in processed:
                continue

            # Pre-filter: skip non-remote and jobs with no keyword overlap
            if not job.get("remote"):
                continue

            description_html = job.get("description", "")
            text = (
                f"Title: {job.get('title', '')}\n"
                f"Company: {job.get('company_name', '')}\n"
                f"Location: {job.get('location', '')}\n"
                f"Remote: yes\n"
                f"Tags: {', '.join(job.get('tags', []))}\n\n"
                + _html_to_text(description_html)
            )
            text_lower = text.lower()

            # Require at least 2 keyword hits before scoring
            hits = sum(1 for kw in keywords if kw in text_lower)
            if hits < 2:
                continue

            score = score_fit(text, profile)
            if score["total"] < min_score:
                continue

            label = fit_label(score["total"])
            company = job.get("company_name", "Unknown")
            role    = job.get("title", "Engineer")

            logger.info(
                "  [API] %s / %s | fit=%s (%.0f%%) | stack=%s",
                company, role, label, score["total"] * 100,
                ", ".join(score["stack_matched"][:4]) or "none",
            )

            cover_note = ""
            if score["total"] >= 0.55:
                logger.info("  Generating cover note …")
                cover_note = generate_cover_note(text, profile, company)

            job_id = sync_to_solaris(company, role, score, cover_note, f"arbeitnow:{slug}", text, url=job.get("url", ""))
            mark_processed(slug)

            results.append({
                "company":    company,
                "role":       role,
                "score":      score,
                "label":      label,
                "job_id":     job_id,
                "cover_note": bool(cover_note),
                "url":        job.get("url", ""),
                "source":     "arbeitnow",
            })

        # Be polite — small delay between pages
        if page < pages:
            time.sleep(0.5)

    logger.info("Arbeitnow: scanned %d page(s), %d qualifying jobs found", pages, len(results))
    return results


def fetch_theirstack(profile: dict, pages: int = 3, max_age_days: int = 7, min_score: float = 0.40) -> list[dict]:
    """
    Search jobs via TheirStack API, score each, return results above min_score.
    Filters by target roles + tech stack from profile. Skips already-processed IDs.
    """
    api_key = os.getenv("THEIRSTACK_API_KEY", "")
    if not api_key:
        logger.warning("THEIRSTACK_API_KEY not set — skipping TheirStack fetch")
        return []

    processed = load_processed()

    # Build technology slugs from profile stack
    stack = profile.get("experience", {}).get("tech_stack", {})
    all_skills = [s.lower() for skills in stack.values() for s in (skills or [])]
    tech_slugs = [_SLUG_MAP[s] for s in all_skills if s in _SLUG_MAP]

    # Target role titles
    target_titles = profile.get("target_roles", {}).get("primary", [])

    results = []

    for page in range(pages):
        body = {
            "page":                  page,
            "limit":                 25,
            "job_country_code_or":   ["US"],
            "posted_at_max_age_days": max_age_days,
            "remote":                True,
        }
        if target_titles:
            body["job_title_or"] = target_titles

        logger.info("Fetching TheirStack page %d/%d …", page + 1, pages)

        try:
            payload_bytes = json.dumps(body).encode()
            req = urllib.request.Request(
                THEIRSTACK_API,
                data=payload_bytes,
                method="POST",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type":  "application/json",
                    "User-Agent":    "job-hunter-agent/1.0",
                },
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                payload = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="ignore")
            logger.error("TheirStack fetch failed (page %d): %s — %s", page + 1, exc, body[:300])
            break
        except Exception as exc:
            logger.error("TheirStack fetch failed (page %d): %s", page + 1, exc)
            break

        jobs = payload.get("data", [])
        meta = payload.get("metadata", {})
        logger.info("  TheirStack: %d results (total=%s)", len(jobs), meta.get("total_results", "?"))

        if not jobs:
            break

        for job in jobs:
            job_id_str = f"theirstack:{job.get('id', '')}"
            if job_id_str in processed:
                continue

            # Build flat text for scorer
            salary_str = job.get("salary_string", "")
            min_sal    = job.get("min_annual_salary_usd")
            max_sal    = job.get("max_annual_salary_usd")
            if not salary_str and min_sal:
                salary_str = f"${min_sal:,} - ${max_sal:,}" if max_sal else f"${min_sal:,}"

            tech_names = (job.get("company_object") or {}).get("technology_names", [])

            text = "\n".join(filter(None, [
                f"Title: {job.get('job_title', '')}",
                f"Company: {job.get('company', '')}",
                f"Location: {job.get('location', '')}",
                "Remote: yes" if job.get("remote") else "",
                f"Salary: {salary_str}" if salary_str else "",
                f"Seniority: {job.get('seniority', '')}",
                f"Technologies: {', '.join(tech_names)}" if tech_names else "",
                f"Keywords: {', '.join(job.get('keyword_slugs', []))}",
                "",
                job.get("description", ""),
            ]))

            score  = score_fit(text, profile)
            if score["total"] < min_score:
                continue

            label   = fit_label(score["total"])
            company = job.get("company", "Unknown")
            role    = job.get("job_title", "Engineer")

            logger.info(
                "  [TheirStack] %s / %s | fit=%s (%.0f%%) | stack=%s",
                company, role, label, score["total"] * 100,
                ", ".join(score["stack_matched"][:4]) or "none",
            )

            cover_note = ""
            if score["total"] >= 0.55:
                logger.info("  Generating cover note …")
                cover_note = generate_cover_note(text, profile, company)

            db_id = sync_to_solaris(company, role, score, cover_note, job_id_str, text, url=job.get("url", ""))
            mark_processed(job_id_str)

            results.append({
                "company":    company,
                "role":       role,
                "score":      score,
                "label":      label,
                "job_id":     db_id,
                "cover_note": bool(cover_note),
                "url":        job.get("url", ""),
                "source":     "theirstack",
            })

        if page < pages - 1:
            time.sleep(0.5)

    logger.info("TheirStack: scanned %d page(s), %d qualifying jobs found", pages, len(results))
    return results


# ---------------------------------------------------------------------------
# Processed file tracker
# ---------------------------------------------------------------------------

def load_processed() -> set[str]:
    if not PROCESSED_LOG.exists():
        return set()
    return set(PROCESSED_LOG.read_text().splitlines())


def mark_processed(filename: str):
    with open(PROCESSED_LOG, "a") as f:
        f.write(filename + "\n")


# ---------------------------------------------------------------------------
# Process a single HTML file
# ---------------------------------------------------------------------------

def process_file(html_path: Path, profile: dict, force: bool = False) -> dict | None:
    """
    Parse, score, generate cover note, sync to Solaris.
    Returns result dict or None if skipped.
    """
    processed = load_processed()
    if html_path.name in processed and not force:
        logger.debug("Skipping %s — already processed", html_path.name)
        return None

    logger.info("Processing: %s", html_path.name)

    text    = extract_text(html_path)
    company = extract_company_from_filename(html_path)
    role    = extract_role_from_filename(html_path)
    score   = score_fit(text, profile)
    label   = fit_label(score["total"])

    logger.info(
        "  %s / %s | fit=%s (%.0f%%) | stack=%s remote=%s equity=%s",
        company, role, label, score["total"] * 100,
        ", ".join(score["stack_matched"][:5]) or "none",
        f"{score['remote']:.0%}", f"{score['equity']:.0%}",
    )

    cover_note = ""
    if score["total"] >= 0.40:   # only generate notes for plausible fits
        logger.info("  Generating cover note via Claude…")
        cover_note = generate_cover_note(text, profile, company)
        if cover_note:
            logger.info("  Cover note generated (%d chars)", len(cover_note))
    else:
        logger.info("  Fit too low (%.0f%%) — skipping cover note", score["total"] * 100)

    job_id = sync_to_solaris(company, role, score, cover_note, html_path.name, text)
    mark_processed(html_path.name)

    return {
        "company":    company,
        "role":       role,
        "score":      score,
        "label":      label,
        "job_id":     job_id,
        "cover_note": bool(cover_note),
    }


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

def cmd_list():
    if not SOLARIS_DB.exists():
        print("Solaris DB not found.")
        return
    conn = sqlite3.connect(str(SOLARIS_DB))
    conn.row_factory = sqlite3.Row
    jobs = conn.execute(
        "SELECT id, company, role, status, updated_at FROM jobs ORDER BY id DESC"
    ).fetchall()
    conn.close()
    print(f"\n{'ID':>4}  {'Company':<25} {'Role':<35} {'Status':<12} Updated")
    print("-" * 90)
    for j in jobs:
        print(f"{j['id']:>4}  {j['company']:<25} {j['role']:<35} {j['status']:<12} {j['updated_at'][:10]}")
    print()


def cmd_cover(job_id: int):
    if not SOLARIS_DB.exists():
        print("Solaris DB not found.")
        return
    conn = sqlite3.connect(str(SOLARIS_DB))
    conn.row_factory = sqlite3.Row
    job = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    if not job:
        print(f"Job #{job_id} not found.")
        return

    profile = load_profile()
    # Reconstruct text from notes if no HTML available
    logger.info("Regenerating cover note for #%d — %s", job_id, job["company"])
    note = generate_cover_note(job["notes"] or "", profile, job["company"])
    if note:
        print(f"\n{'─'*60}")
        print(f"Cover note for {job['company']} — {job['role']}")
        print('─'*60)
        print(note)
        print('─'*60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Job Hunter Agent")
    parser.add_argument("--cover",  type=int, metavar="JOB_ID", help="Regenerate cover note for a job")
    parser.add_argument("--list",   action="store_true", help="List all jobs in Solaris DB")
    parser.add_argument("--force",  action="store_true", help="Re-process already processed files")
    parser.add_argument("--dry-run", action="store_true", help="Score only, no DB writes or cover notes")
    parser.add_argument("--api",        action="store_true", help="Fetch jobs from Arbeitnow API")
    parser.add_argument("--theirstack", action="store_true", help="Fetch jobs from TheirStack API")
    parser.add_argument("--waas", nargs="?", const="waas_dump.json", metavar="PATH",
                        help="Build target shortlist from a workatastartup.com JSON dump")
    parser.add_argument("--pages",      type=int, default=3, metavar="N", help="Pages to fetch from API (default: 3)")
    parser.add_argument("--days",       type=int, default=7, metavar="N", help="Max age in days for TheirStack results (default: 7)")
    args = parser.parse_args()

    if args.list:
        cmd_list()
        return

    if args.cover:
        cmd_cover(args.cover)
        return

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

    if args.theirstack:
        profile = load_profile()
        results = fetch_theirstack(profile, pages=args.pages, max_age_days=args.days)
        logger.info("─" * 50)
        for r in sorted(results, key=lambda x: x["score"]["total"], reverse=True):
            logger.info(
                "  %s [%s] %.0f%% — %s / %s  %s",
                "📝" if r["cover_note"] else "  ",
                r["label"], r["score"]["total"] * 100,
                r["company"], r["role"], r.get("url", ""),
            )
        coordinator_outputs = {
            "__completed_tasks__": ["process_wellfound_queue"] if results else [],
            "jobs_assessed":   len(results),
            "jobs_added":      sum(1 for r in results if r["job_id"]),
            "top_fit_company": results[0]["company"] if results else "",
            "top_fit_score":   round(results[0]["score"]["total"], 3) if results else 0.0,
        }
        print(json.dumps({"__coordinator_outputs__": coordinator_outputs}))
        return

    if args.api:
        profile = load_profile()
        results = fetch_arbeitnow(profile, pages=args.pages)
        logger.info("─" * 50)
        for r in sorted(results, key=lambda x: x["score"]["total"], reverse=True):
            logger.info(
                "  %s [%s] %.0f%% — %s / %s  %s",
                "📝" if r["cover_note"] else "  ",
                r["label"], r["score"]["total"] * 100,
                r["company"], r["role"], r.get("url", ""),
            )
        coordinator_outputs = {
            "__completed_tasks__": ["process_wellfound_queue"] if results else [],
            "jobs_assessed":  len(results),
            "jobs_added":     sum(1 for r in results if r["job_id"]),
            "top_fit_company": results[0]["company"] if results else "",
            "top_fit_score":  round(results[0]["score"]["total"], 3) if results else 0.0,
        }
        print(json.dumps({"__coordinator_outputs__": coordinator_outputs}))
        return

    # ── Main flow: process all HTML files ────────────────────────────────
    profile    = load_profile()
    html_files = sorted(AGENT_DIR.glob("*.html"))

    if not html_files:
        logger.info("No HTML files found in %s", AGENT_DIR)
        logger.info("Drop job posting HTML files here and re-run.")
        return

    logger.info("Found %d HTML file(s) to process", len(html_files))

    results     = []
    jobs_added  = 0
    top_company = ""
    top_score   = 0.0

    for html_path in html_files:
        result = process_file(html_path, profile, force=args.force)
        if result:
            results.append(result)
            if result["job_id"]:
                jobs_added += 1
            if result["score"]["total"] > top_score:
                top_score   = result["score"]["total"]
                top_company = result["company"]

    # ── Summary ───────────────────────────────────────────────────────────
    logger.info("─" * 50)
    logger.info("Processed %d file(s)  |  %d added to Solaris", len(results), jobs_added)
    for r in sorted(results, key=lambda x: x["score"]["total"], reverse=True):
        logger.info(
            "  %s [%s] %.0f%% — %s / %s",
            "📝" if r["cover_note"] else "  ",
            r["label"], r["score"]["total"] * 100,
            r["company"], r["role"],
        )

    # ── Coordinator outputs ───────────────────────────────────────────────
    coordinator_outputs = {
        "__completed_tasks__": ["process_wellfound_queue"] if results else [],
        "jobs_assessed":  len(results),
        "jobs_added":     jobs_added,
        "top_fit_company": top_company,
        "top_fit_score":  round(top_score, 3),
    }
    print(json.dumps({"__coordinator_outputs__": coordinator_outputs}))


if __name__ == "__main__":
    main()
