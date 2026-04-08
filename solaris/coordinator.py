"""
coordinator.py — Solaris multi-agent orchestrator
==================================================
1. Discovers all agent roadmap.yaml files in sibling directories
2. Builds a dependency DAG and topological-sorts the execution order
3. Dispatches each agent as a subprocess, injecting context via env var
4. Collects outputs and calls roadmap_updater after each run
5. Triggers daily_log.py for Claude synthesis at the end
"""

import json
import logging
import os
import subprocess
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
SOLARIS_DIR = Path(__file__).parent
DAILY_LOGS_DIR = SOLARIS_DIR / "daily_logs"
DAILY_LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(SOLARIS_DIR / "coordinator.log"),
    ],
)
logger = logging.getLogger("coordinator")

AGENTS_ROOT = SOLARIS_DIR.parent   # claude-code-agents/


# ---------------------------------------------------------------------------
# Roadmap discovery & loading
# ---------------------------------------------------------------------------

def find_roadmaps() -> list[Path]:
    """Find all roadmap.yaml files in sibling agent directories."""
    return sorted(AGENTS_ROOT.glob("*/roadmap.yaml"))


def load_roadmap(path: Path) -> dict:
    with open(path) as f:
        data = yaml.safe_load(f)
    data["_path"] = str(path)
    return data


def load_all_roadmaps() -> dict[str, dict]:
    """Returns {agent_id: roadmap_dict} for all enabled agents."""
    roadmaps = {}
    for path in find_roadmaps():
        try:
            rm = load_roadmap(path)
            agent_id = rm["agent"]["id"]
            if not rm["agent"].get("enabled", True):
                logger.info("Agent %s is disabled — skipping", agent_id)
                continue
            roadmaps[agent_id] = rm
            logger.info("Loaded roadmap: %s (%s)", agent_id, path)
        except Exception as exc:
            logger.warning("Failed to load roadmap at %s: %s", path, exc)
    return roadmaps


# ---------------------------------------------------------------------------
# DAG + topological sort
# ---------------------------------------------------------------------------

def build_dag(roadmaps: dict[str, dict]) -> dict[str, list[str]]:
    """Returns adjacency list: {agent_id: [dep_ids...]}"""
    dag = {}
    for agent_id, rm in roadmaps.items():
        deps = rm.get("depends_on") or []
        valid_deps = []
        for dep in deps:
            if dep not in roadmaps:
                logger.warning(
                    "Agent %s depends on %s which has no roadmap — ignoring",
                    agent_id, dep,
                )
            else:
                valid_deps.append(dep)
        dag[agent_id] = valid_deps
    return dag


def topological_sort(dag: dict[str, list[str]]) -> list[str]:
    """
    Kahn's algorithm. Returns agents in valid execution order.
    Raises RuntimeError on circular dependency.
    """
    in_degree: dict[str, int] = defaultdict(int)
    graph: dict[str, list[str]] = defaultdict(list)

    for node, deps in dag.items():
        if node not in in_degree:
            in_degree[node] = 0
        for dep in deps:
            graph[dep].append(node)
            in_degree[node] += 1

    queue = deque(node for node in dag if in_degree[node] == 0)
    order = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(order) != len(dag):
        cycle_nodes = [n for n in dag if n not in order]
        raise RuntimeError(f"Dependency cycle detected among: {cycle_nodes}")

    return order


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

def build_context(
    agent_id: str,
    roadmap: dict,
    upstream_outputs: dict[str, dict],
) -> dict:
    """
    Build the context dict injected into an agent at dispatch time.
    Contains: tasks for today, agent memory, upstream outputs.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Active tasks: always include recurrent ones + non-done one-shots
    tasks_today = [
        t for t in (roadmap.get("tasks") or [])
        if t.get("recurrent", False) or t.get("status") not in ("done", "skipped")
    ]

    # Collect upstream outputs this agent declared it needs
    requested_keys = (roadmap.get("inputs") or {}).get("upstream_outputs") or []
    upstream = {}
    for key in requested_keys:
        # key format: "agent-id.output_key"
        parts = key.split(".", 1)
        if len(parts) == 2:
            src_agent, out_key = parts
            if src_agent in upstream_outputs and out_key in upstream_outputs[src_agent]:
                upstream[key] = upstream_outputs[src_agent][out_key]

    return {
        "agent_id":        agent_id,
        "date":            today,
        "tasks_today":     tasks_today,
        "memory":          roadmap.get("memory") or {},
        "upstream_outputs": upstream,
    }


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def dispatch_agent(agent_id: str, roadmap: dict, context: dict) -> dict:
    """
    Run an agent as a subprocess.
    Context is injected via the COORDINATOR_CONTEXT environment variable (JSON).

    Agents can report outputs back by printing a JSON line to stdout:
        {"__coordinator_outputs__": {"key": value, ...}}

    Returns a result dict:
        status           "ok" | "error" | "timeout"
        outputs          dict of output key/values parsed from stdout
        returncode       process exit code (int)
        stdout           last 5000 chars of stdout
        stderr           last 2000 chars of stderr
        duration_seconds float
    """
    agent_cfg  = roadmap["agent"]
    agent_path = (SOLARIS_DIR / agent_cfg["path"]).resolve()
    entry      = agent_cfg.get("entry", "main.py")
    max_mins   = (roadmap.get("schedule") or {}).get("max_runtime_minutes", 30)

    script = agent_path / entry
    if not script.exists():
        logger.error("Entry script not found: %s", script)
        return {
            "status":   "error",
            "outputs":  {},
            "error":    f"Entry script not found: {script}",
            "duration_seconds": 0,
        }

    env = {
        **os.environ,
        "COORDINATOR_MODE":    "1",
        "COORDINATOR_CONTEXT": json.dumps(context),
    }

    logger.info("→ Dispatching %-30s [timeout=%dm]", agent_id, max_mins)
    start = datetime.now(timezone.utc)

    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(agent_path),
            env=env,
            capture_output=True,
            text=True,
            timeout=max_mins * 60,
        )
        duration = (datetime.now(timezone.utc) - start).total_seconds()

        # Parse outputs: scan stdout lines in reverse for the sentinel JSON
        outputs = {}
        for line in reversed((proc.stdout or "").strip().splitlines()):
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict) and "__coordinator_outputs__" in parsed:
                    outputs = parsed["__coordinator_outputs__"]
                    break
            except Exception:
                continue

        status = "ok" if proc.returncode == 0 else "error"

        if status == "error":
            logger.error(
                "✗ %s exited with code %d\n  STDERR: %s",
                agent_id, proc.returncode, (proc.stderr or "")[-1000:].strip(),
            )
        else:
            logger.info("✓ %s finished in %.1fs | outputs: %s", agent_id, duration, outputs)

        return {
            "status":           status,
            "outputs":          outputs,
            "returncode":       proc.returncode,
            "stdout":           (proc.stdout or "")[-5000:],
            "stderr":           (proc.stderr or "")[-2000:],
            "duration_seconds": round(duration, 1),
        }

    except subprocess.TimeoutExpired:
        duration = (datetime.now(timezone.utc) - start).total_seconds()
        logger.error("✗ %s timed out after %dm", agent_id, max_mins)
        return {"status": "timeout", "outputs": {}, "duration_seconds": round(duration, 1)}

    except Exception as exc:
        logger.error("✗ Failed to dispatch %s: %s", agent_id, exc)
        return {"status": "error", "outputs": {}, "error": str(exc), "duration_seconds": 0}


# ---------------------------------------------------------------------------
# Post-run hooks (implemented in steps 3 & 4)
# ---------------------------------------------------------------------------

def _call_roadmap_updater(agent_id: str, roadmap_path: str, result: dict) -> None:
    try:
        import roadmap_updater
        roadmap_updater.update(agent_id, roadmap_path, result)
    except ImportError:
        logger.debug("roadmap_updater not yet available — skipping")
    except Exception as exc:
        logger.warning("roadmap_updater failed for %s: %s", agent_id, exc)


def _call_daily_log(run_summary: dict) -> None:
    try:
        import daily_log
        daily_log.write(run_summary)
    except ImportError:
        logger.debug("daily_log not yet available — skipping")
    except Exception as exc:
        logger.warning("daily_log synthesis failed: %s", exc)


# ---------------------------------------------------------------------------
# Main orchestration loop
# ---------------------------------------------------------------------------

def run() -> None:
    now = datetime.now(timezone.utc)
    logger.info("=" * 60)
    logger.info("SOLARIS COORDINATOR  %s", now.strftime("%Y-%m-%d %H:%M UTC"))
    logger.info("=" * 60)

    # 1. Discover and load all agent roadmaps
    roadmaps = load_all_roadmaps()
    if not roadmaps:
        logger.error("No roadmap.yaml files found under %s — nothing to do.", AGENTS_ROOT)
        return

    # 2. Resolve execution order via DAG
    dag = build_dag(roadmaps)
    try:
        order = topological_sort(dag)
    except RuntimeError as exc:
        logger.error("Cannot resolve execution order: %s", exc)
        return

    logger.info("Execution order: %s", " → ".join(order))
    logger.info("-" * 60)

    # 3. Dispatch agents in dependency order
    upstream_outputs: dict[str, dict] = {}
    run_results:      dict[str, dict] = {}

    for agent_id in order:
        roadmap = roadmaps[agent_id]
        context = build_context(agent_id, roadmap, upstream_outputs)
        result  = dispatch_agent(agent_id, roadmap, context)

        run_results[agent_id] = result

        if result.get("outputs"):
            upstream_outputs[agent_id] = result["outputs"]

        _call_roadmap_updater(agent_id, roadmap["_path"], result)

    # 4. Summary
    ok      = [a for a, r in run_results.items() if r["status"] == "ok"]
    errors  = [a for a, r in run_results.items() if r["status"] == "error"]
    timeout = [a for a, r in run_results.items() if r["status"] == "timeout"]

    logger.info("-" * 60)
    logger.info(
        "RUN COMPLETE  ok=%d  error=%d  timeout=%d  total=%.1fs",
        len(ok), len(errors), len(timeout),
        sum(r.get("duration_seconds", 0) for r in run_results.values()),
    )
    if errors:
        logger.warning("Failed agents  : %s", errors)
    if timeout:
        logger.warning("Timed-out agents: %s", timeout)

    # 5. Daily log synthesis (Claude call — daily_log.py step 4)
    _call_daily_log({
        "date":            now.strftime("%Y-%m-%d"),
        "execution_order": order,
        "results":         run_results,
        "upstream_outputs": upstream_outputs,
    })

    logger.info("=" * 60)


if __name__ == "__main__":
    run()
