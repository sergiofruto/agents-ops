# polymarket-agent → VPS Deploy — Design

**Date:** 2026-08-13
**Status:** Approved (pending written-spec review)
**Component:** `polymarket-agent/` + `solaris/sync.py`
**Why:** The agent only runs when Sergio's Mac is on and `main.py` is manually started. It just took a real, unexpected ~$300 loss during a live World Cup market swing while unattended. Resuming live trading (`DRY_RUN=false`) without fixing "only runs when the laptop happens to be on" repeats the same failure mode. Goal: move it to infrastructure that stays up on its own, survives crashes, and tells Sergio when something's wrong — without rewriting the agent's logic.

---

## Goal

Get `polymarket-agent` running continuously on a small VPS, supervised so it restarts on failure and survives reboots, with its live private key handled proportionately to the stakes (~$100 bankroll), and with Sergio notified if it silently stops working. Keep the Solaris dashboard fed with fresh data without moving `sync.py` off the Mac.

## Current state (important)

`polymarket-agent/main.py` is a long-running daemon: `schedule` library drives a scan loop (30 min) and a track loop (15 min) in separate threads, plus a Flask reporter (`web/app.py`, port 5001) and a Rich terminal dashboard — all in one process, started manually (`python main.py`) and only alive while that terminal/laptop session lasts. `DRY_RUN=false` in `.env` — this places real CLOB orders on Polygon using `POLY_PRIVATE_KEY`. The wallet (`0xbA14...962B6`) currently holds $0 USDC / $0 POL after the World Cup loss; a fresh deposit (~$100) is expected before this goes live again. `solaris/sync.py` already runs reliably on the Mac's cron every 15 min, reading `polymarket-agent/bets.db` (among other local SQLite files) read-only and upserting into Turso. No Dockerfile or deploy tooling exists today for any agent.

## Non-Goals

- Not migrating `dota-agent`, `analyst-agent`, or `job-hunter-agent` yet — same pattern, deliberately deferred to a Phase 2 follow-up so the higher-stakes agent (real money) gets proven infra first.
- Not containerizing (no Docker) — a venv + systemd unit is the whole runtime; no meaningful benefit from a container for a single always-on process on a box we fully control.
- Not building CI/CD — no auto-deploy-on-push. Redeploys are a manual `git pull && systemctl restart`, triggered by Sergio or Claude over SSH when there's a code change to ship.
- Not using a secrets manager (Vault/Doppler) — a locked-down `.env` file matches the trust model the key already has on the laptop, and adding an external secrets service is disproportionate at this bankroll size.
- Not exposing the agent's Flask reporter UI (port 5001) publicly — Solaris' web-next dashboard is the intended public view; the raw agent UI stays `localhost`-only, reachable via SSH tunnel if needed.
- Not moving `sync.py` itself off the Mac in this phase — it keeps its proven cron schedule; only a new "pull the VPS's `bets.db` first" step is added.

---

## Architecture

```
Hetzner CX22 (Ubuntu 24.04, non-root user `agents`)
  polymarket-agent/            [git clone, same repo layout as the Mac]
    venv/                      [python3 -m venv, pip install -r requirements.txt]
    .env                       [chmod 600, owned by `agents`]
    bets.db                    [canonical going forward — local Mac copy becomes frozen history]
  systemd: polymarket-agent.service
    ExecStart = venv/bin/python3 main.py
    Restart = on-failure, RestartSec = 30
    EnvironmentFile = .env
  ufw: allow 22/tcp only
  fail2ban: guards sshd
  healthchecks.io ping: fired at the end of every successful scan cycle in main.py's loop

Sergio's Mac (unchanged cron cadence)
  solaris/sync.py  [*/15 cron]
    1. scp/rsync polymarket-agent/bets.db  ←  agents@VPS:~/polymarket-agent/bets.db   (new step)
    2. existing sync logic, unchanged      →  Turso
  dota-agent, analyst-agent, job-hunter-agent — still run locally, untouched (Phase 2)
```

Local `polymarket-agent/main.py` stops being run on the Mac — the VPS copy of `bets.db` becomes the source of truth. The Mac's copy is frozen history from before the migration.

---

## Components

### 1. VPS provisioning & hardening
- Hetzner CX22 (2 vCPU / 4GB / 40GB, ~€4.20/mo), Ubuntu 24.04 LTS.
- Non-root user `agents`, added to sudoers, owns everything under `/home/agents/`.
- SSH: Sergio's existing public key installed at creation; password auth disabled in `sshd_config`.
- `ufw`: default deny incoming, allow `22/tcp` only.
- `fail2ban`: default sshd jail enabled.

### 2. Code delivery
- `git clone` the `claude-code-agents` repo to `/home/agents/claude-code-agents` — same relative paths as the Mac, so `polymarket-agent`'s internal imports need no changes.
- `python3 -m venv venv && venv/bin/pip install -r requirements.txt` inside `polymarket-agent/`.
- `.env` copied over via `scp` directly (not committed — it never touches git), then `chmod 600 .env`.

### 3. Process supervision (systemd)
- `/etc/systemd/system/polymarket-agent.service`:
  ```ini
  [Unit]
  Description=polymarket-agent
  After=network-online.target

  [Service]
  Type=simple
  User=agents
  WorkingDirectory=/home/agents/claude-code-agents/polymarket-agent
  EnvironmentFile=/home/agents/claude-code-agents/polymarket-agent/.env
  ExecStart=/home/agents/claude-code-agents/polymarket-agent/venv/bin/python3 main.py
  Restart=on-failure
  RestartSec=30

  [Install]
  WantedBy=multi-user.target
  ```
- `systemctl enable --now polymarket-agent` — survives reboots, restarts 30s after any crash.

### 4. Redeploy flow
- `polymarket-agent/deploy.sh` (new, on the VPS): `git pull && systemctl restart polymarket-agent`.
- Run manually over SSH whenever there's a code change to ship. No webhook, no auto-trigger.

### 5. Monitoring (healthchecks.io)
- Free healthchecks.io check, ping URL stored as `HEALTHCHECK_URL` in `.env`.
- A `requests.get(HEALTHCHECK_URL, timeout=10)` call added at the end of each successful scan cycle in `main.py`'s scan loop (wrapped in try/except so a network blip never crashes the agent).
- healthchecks.io period set to the 30-min scan interval with a generous grace window (e.g. 60 min) — so a single slow cycle doesn't false-alarm, but Sergio gets an email once the agent has gone quiet for roughly two missed cycles.
- This catches both "process died" (systemd already handles restart, but repeated crash-looping still eventually starves check-ins) and "process alive but every scan is silently erroring."

### 6. Data flow (`sync.py` change)
- One new function in `solaris/sync.py`, run before the existing sync steps: `scp agents@<vps-ip>:~/claude-code-agents/polymarket-agent/bets.db <local tmp path>`, then point the existing polymarket read at that path instead of the local `polymarket-agent/bets.db`.
- Uses the same SSH key already used for `git`/deploy access — no new credential.
- On `scp` failure (VPS unreachable): log and skip the polymarket sync step for that run, same fallback pattern `sync.py` already uses for a missing/broken source DB — never aborts the whole sync.

---

## Data flow & privacy

- `POLY_PRIVATE_KEY` and CLOB API credentials live only in the VPS's `.env` (chmod 600) and the Mac's `.env` (unchanged) — never committed, never sent to Turso/Vercel.
- `bets.db` (trade history, no credentials) is pulled to the Mac by `sync.py` and then flows into Turso exactly as today — same privacy posture as the current deploy.

## Error handling

- systemd: crash → restart after 30s, indefinitely.
- Scan-cycle errors inside the agent: existing per-scan try/except (unchanged) continues to log and move on.
- `sync.py`: VPS unreachable → log + skip polymarket step, rest of sync proceeds (existing per-source fallback pattern).
- healthchecks.io: silent failures (process alive, scans erroring) surface as a missed-check-in email once the agent has been quiet for roughly two scan cycles (~90 min).

## Testing / verification before calling it done

- Reboot the VPS; confirm `polymarket-agent.service` comes back on its own (`systemctl status`).
- Confirm a real scan cycle runs and writes to the VPS's `bets.db`.
- Kill the process manually; confirm systemd restarts it within ~30s.
- Confirm the healthchecks.io ping arrives after a successful scan.
- Confirm `sync.py`'s new pull step lands fresh VPS data in Turso.
- Confirm the Solaris dashboard shows the new data end-to-end.

---

## Phasing

- **Phase 1 (this spec/plan):** VPS provisioning + hardening, systemd pattern (written to be reusable), `polymarket-agent` deployed and verified end-to-end, `sync.py` pull-step added, healthchecks.io wired up.
- **Phase 2 (follow-up, same pattern, separate plan):** `dota-agent`, `analyst-agent`, `job-hunter-agent` migrated to the same VPS using the systemd template from Phase 1. Possibly revisit Claude Code cloud-scheduled routines as an alternative for these lower-stakes, non-financial agents at that time.

## Out of scope (YAGNI)

- Docker/containerization; CI/CD auto-deploy; external secrets manager; public exposure of the agent's Flask UI; migrating the other 3 agents; moving `sync.py` off the Mac.
