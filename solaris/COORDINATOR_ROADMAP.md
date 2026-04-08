# Solaris Coordinator — Build Plan (Option C: Hybrid DAG + LLM Synthesis)

## Architecture
- Python DAG handles orchestration (deterministic, free)
- Claude handles end-of-day synthesis only (one API call)

## Build Order

1. [x] Define `roadmap.yaml` schema — task declarations, dependencies, schedule, outputs
2. [x] Write `coordinator.py` — reads all agent roadmap.yaml files, topological sort, dispatches each agent's `run(context)`
3. [x] Write `roadmap_updater.py` — marks tasks done/blocked/skipped after each agent run, rewrites roadmap.yaml
4. [x] Write `SOLARIS.md` + `daily_log.py` — system prompt + Claude synthesis call at end of day
5. [x] Add `roadmap.yaml` to each agent (polymarket-agent, analyst-agent, dota-agent, job-hunter-agent)

## File Structure
```
solaris/
  coordinator.py          ← main orchestrator (Python DAG)
  roadmap_updater.py      ← updates agent roadmap.yaml after runs
  daily_log.py            ← Claude synthesis call
  SOLARIS.md              ← system prompt for daily_log.py
  daily_logs/             ← YYYY-MM-DD.md output files

polymarket-agent/roadmap.yaml
analyst-agent/roadmap.yaml
dota-agent/roadmap.yaml
job-hunter-agent/roadmap.yaml
```

## Execution Flow
```
startup
  └── read all roadmap.yaml files
  └── build dependency DAG
  └── topological sort → execution order

for each agent in order:
  └── inject: tasks_today + memory context + upstream outputs
  └── run agent.run(context)
  └── collect: outputs, logs, errors
  └── roadmap_updater.py → mark tasks done/blocked

end of day:
  └── daily_log.py (Claude call)
      └── input: all agent outputs + current roadmap state
      └── output: daily_logs/YYYY-MM-DD.md
               → what ran, what was skipped, blockers, suggestions
```
