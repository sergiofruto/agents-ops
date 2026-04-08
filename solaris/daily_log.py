"""
daily_log.py — Solaris end-of-day synthesis
============================================
Called by coordinator.py after all agents have run.
Builds a rich prompt from the run summary + current roadmap state,
calls Claude, and writes the result to daily_logs/YYYY-MM-DD.md.
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import yaml

logger = logging.getLogger("daily_log")

SOLARIS_DIR    = Path(__file__).parent
SOLARIS_MD     = SOLARIS_DIR / "SOLARIS.md"
DAILY_LOGS_DIR = SOLARIS_DIR / "daily_logs"
AGENTS_ROOT    = SOLARIS_DIR.parent

MODEL   = os.getenv("SOLARIS_LOG_MODEL", "claude-opus-4-6")
MAX_TOKENS = 1200


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

def write(run_summary: dict) -> None:
    """
    Synthesize a daily log from run_summary and write to daily_logs/YYYY-MM-DD.md.
    Never raises — logs and returns on any error.
    """
    try:
        _write(run_summary)
    except Exception as exc:
        logger.error("daily_log.write failed: %s", exc)


# ---------------------------------------------------------------------------
# Internal implementation
# ---------------------------------------------------------------------------

def _write(run_summary: dict) -> None:
    date      = run_summary.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path  = DAILY_LOGS_DIR / f"{date}.md"

    DAILY_LOGS_DIR.mkdir(exist_ok=True)

    system_prompt = _load_system_prompt()
    user_prompt   = _build_user_prompt(run_summary, date)

    logger.info("Calling Claude for daily log synthesis (%s)…", date)

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set — cannot generate daily log")
        _write_fallback(out_path, run_summary, date)
        return

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    content = message.content[0].text.strip()
    _write_log(out_path, date, content, run_summary)
    logger.info("Daily log written → %s", out_path)


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _load_system_prompt() -> str:
    if SOLARIS_MD.exists():
        return SOLARIS_MD.read_text(encoding="utf-8")
    return (
        "You are Solaris, a multi-agent coordinator. "
        "Write a concise daily operations log from the run summary provided."
    )


def _build_user_prompt(run_summary: dict, date: str) -> str:
    sections: list[str] = [f"# Run summary for {date}\n"]

    # ── Execution order ────────────────────────────────────────────────────
    order = run_summary.get("execution_order") or []
    sections.append(f"**Execution order:** {' → '.join(order) if order else 'none'}\n")

    # ── Per-agent results ──────────────────────────────────────────────────
    results = run_summary.get("results") or {}
    sections.append("## Agent results\n")
    for agent_id, result in results.items():
        status   = result.get("status", "unknown")
        duration = result.get("duration_seconds", 0)
        outputs  = {k: v for k, v in (result.get("outputs") or {}).items() if not k.startswith("__")}
        err      = result.get("error", "")
        sections.append(
            f"### {agent_id}\n"
            f"- status: {status}\n"
            f"- duration: {duration}s\n"
            f"- outputs: {outputs or 'none'}\n"
            + (f"- error: {err}\n" if err else "")
        )

    # ── Current roadmap state ──────────────────────────────────────────────
    sections.append("## Current roadmap state\n")
    for roadmap_path in sorted(AGENTS_ROOT.glob("*/roadmap.yaml")):
        try:
            with open(roadmap_path) as f:
                rm = yaml.safe_load(f)
            agent_id = rm["agent"]["id"]
            tasks    = rm.get("tasks") or []
            memory   = rm.get("memory") or {}

            counts = {"active": 0, "done": 0, "blocked": 0, "skipped": 0}
            for t in tasks:
                s = t.get("status", "active")
                counts[s] = counts.get(s, 0) + 1

            blocked_names = [t["id"] for t in tasks if t.get("status") == "blocked"]

            sections.append(
                f"### {agent_id}\n"
                f"- last_run: {memory.get('last_run', 'never')}\n"
                f"- last_status: {memory.get('last_status', 'unknown')}\n"
                f"- tasks: {counts}\n"
                + (f"- blocked tasks: {blocked_names}\n" if blocked_names else "")
            )
        except Exception as exc:
            sections.append(f"### {roadmap_path.parent.name}\n- error reading roadmap: {exc}\n")

    # ── Previous log for continuity ────────────────────────────────────────
    prev_log = _load_previous_log(date)
    if prev_log:
        sections.append("## Previous daily log (yesterday)\n")
        # Trim to avoid blowing the context window
        sections.append(prev_log[:2000] + ("\n…[truncated]" if len(prev_log) > 2000 else ""))

    return "\n".join(sections)


def _load_previous_log(today: str) -> str:
    """Find the most recent daily log before today."""
    logs = sorted(DAILY_LOGS_DIR.glob("*.md"), reverse=True)
    for log in logs:
        if log.stem < today:
            return log.read_text(encoding="utf-8")
    return ""


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def _write_log(path: Path, date: str, content: str, run_summary: dict) -> None:
    """Write the final markdown file with a header block."""
    results  = run_summary.get("results") or {}
    ok       = sum(1 for r in results.values() if r.get("status") == "ok")
    errors   = sum(1 for r in results.values() if r.get("status") == "error")
    timeouts = sum(1 for r in results.values() if r.get("status") == "timeout")
    total_s  = sum(r.get("duration_seconds", 0) for r in results.values())

    header = (
        f"---\n"
        f"date: {date}\n"
        f"agents_ok: {ok}\n"
        f"agents_error: {errors}\n"
        f"agents_timeout: {timeouts}\n"
        f"total_duration_seconds: {total_s}\n"
        f"model: {MODEL}\n"
        f"---\n\n"
    )
    path.write_text(header + content + "\n", encoding="utf-8")


def _write_fallback(path: Path, run_summary: dict, date: str) -> None:
    """Write a plain-text fallback log when Claude is unavailable."""
    results = run_summary.get("results") or {}
    lines   = [f"# Solaris Daily Log — {date}\n", "_Claude synthesis unavailable — raw summary_\n"]
    for agent_id, result in results.items():
        status   = result.get("status", "unknown")
        duration = result.get("duration_seconds", 0)
        outputs  = {k: v for k, v in (result.get("outputs") or {}).items() if not k.startswith("__")}
        lines.append(f"## {agent_id}\n- status: {status}  duration: {duration}s  outputs: {outputs}\n")

    path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Fallback daily log written → %s", path)


# ---------------------------------------------------------------------------
# CLI — run standalone for testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")

    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            summary = json.load(f)
    else:
        # Minimal synthetic summary for smoke test
        summary = {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "execution_order": ["analyst-agent", "polymarket-agent"],
            "results": {
                "analyst-agent":    {"status": "ok",    "duration_seconds": 12.3, "outputs": {}},
                "polymarket-agent": {"status": "error", "duration_seconds": 4.1,  "outputs": {},
                                     "error": "CLOB credentials missing"},
            },
            "upstream_outputs": {},
        }

    write(summary)
