"""
roadmap_updater.py — Solaris post-run roadmap writer
=====================================================
Called by coordinator.py after each agent finishes.
Updates the agent's roadmap.yaml in-place:
  - memory.last_run, last_status, last_output
  - task statuses: done / blocked / reset-to-active for recurrents
  - preserves all other fields untouched

Agents report completed tasks via their coordinator output:
    {"__coordinator_outputs__": {"__completed_tasks__": ["task_id", ...]}}
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

import yaml

logger = logging.getLogger("roadmap_updater")


# ---------------------------------------------------------------------------
# Public entry-point called by coordinator
# ---------------------------------------------------------------------------

def update(agent_id: str, roadmap_path: str, result: dict) -> None:
    """
    Load roadmap_path, apply result, write back.
    Never raises — logs and returns on any error so a bad update
    never blocks the rest of the coordinator run.
    """
    try:
        _update(agent_id, roadmap_path, result)
    except Exception as exc:
        logger.error("roadmap_updater failed for %s: %s", agent_id, exc)


# ---------------------------------------------------------------------------
# Internal implementation
# ---------------------------------------------------------------------------

def _update(agent_id: str, roadmap_path: str, result: dict) -> None:
    path = Path(roadmap_path)
    if not path.exists():
        logger.warning("roadmap_updater: %s not found — skipping", roadmap_path)
        return

    with open(path) as f:
        roadmap = yaml.safe_load(f)

    now        = datetime.now(timezone.utc).isoformat(timespec="seconds")
    status     = result.get("status", "error")   # "ok" | "error" | "timeout"
    outputs    = result.get("outputs") or {}

    # ── 1. Update memory block ──────────────────────────────────────────────
    if "memory" not in roadmap or roadmap["memory"] is None:
        roadmap["memory"] = {}

    roadmap["memory"]["last_run"]    = now
    roadmap["memory"]["last_status"] = status
    roadmap["memory"]["last_output"] = {
        k: v for k, v in outputs.items()
        if not k.startswith("__")   # strip internal sentinel keys
    }

    # ── 2. Update task statuses ─────────────────────────────────────────────
    completed_tasks: list[str] = outputs.get("__completed_tasks__", [])
    tasks = roadmap.get("tasks") or []

    for task in tasks:
        tid      = task.get("id", "")
        current  = task.get("status", "active")
        recurrent = task.get("recurrent", False)

        if recurrent:
            # Recurrent tasks always reset to active at the start of each day.
            # We set them to "active" here so the next run picks them up.
            task["status"] = "active"

        elif tid in completed_tasks:
            # Agent explicitly reported this task done
            task["status"] = "done"
            logger.info("  Task %-30s → done", tid)

        elif status == "error" and current == "active":
            # Agent errored out — mark active tasks as blocked so the daily log
            # surfaces them. Recurrent tasks are excluded (handled above).
            task["status"] = "blocked"
            logger.warning("  Task %-30s → blocked (agent error)", tid)

        # "done" non-recurrent tasks and "skipped" tasks are left untouched.

    roadmap["tasks"] = tasks

    # ── 3. Write back ───────────────────────────────────────────────────────
    _write_yaml(path, roadmap)
    logger.info(
        "Updated roadmap for %s — status=%s  completed=%s",
        agent_id, status, completed_tasks or "none",
    )


# ---------------------------------------------------------------------------
# YAML writer — clean, consistent output
# ---------------------------------------------------------------------------

def _write_yaml(path: Path, data: dict) -> None:
    """
    Write roadmap dict back to YAML.
    Produces a clean file with block style and sorted keys disabled
    (preserves field order as defined in the schema).
    """
    content = yaml.dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        indent=2,
    )
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI — call directly for debugging
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 3:
        print("Usage: python roadmap_updater.py <roadmap.yaml> <result.json>")
        print("  result.json example: {\"status\": \"ok\", \"outputs\": {\"__completed_tasks__\": [\"scan_markets\"]}}")
        sys.exit(1)

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")

    roadmap_path = sys.argv[1]
    result       = json.loads(sys.argv[2])
    agent_id     = yaml.safe_load(open(roadmap_path))["agent"]["id"]

    update(agent_id, roadmap_path, result)
    print("Done.")
