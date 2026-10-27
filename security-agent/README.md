# Security Agent

A personal security agent for this Mac, with a local dashboard at **http://127.0.0.1:5007**:

- **Mac check**: slowness, open ports, secrets lying around, built-in protections, signs of malware. Read-only; every finding comes with a "How to fix it" guide.
- **Digest**: a daily security news digest where every entry is backed by a primary source (vendor advisory, CVE record, CISA's exploited list) or two established outlets. Entries that touch your apps and projects go first.
- **Status**: Vercel, Turso, Neon, Anthropic, GitHub, Cloudflare, AWS and three public DNS resolvers, with 7 days of history.
- **Ask the analyst**: a Claude chat that answers from the scan, the digest and the status data.

Design: `docs/superpowers/specs/2026-10-24-security-agent-design.md`.

## Setup

```bash
cd security-agent
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env   # optional: without it, everything works except Claude's text
```

Optional `.env` settings: `AI_DAILY_CAP_USD` (default 1.0), `AI_DIGEST_RESERVE_USD` (0.33), `DIGEST_MODEL` / `CHAT_MODEL` (`claude-haiku-5-5`), `PROJECTS_ROOT` (`~/Projects`).

## Run

```bash
python main.py            # by hand; Ctrl-C to stop
launchd/install.sh        # start now and at every login
launchd/uninstall.sh      # stop and remove from login
```

Schedule: status every 5 minutes, digest once a day from 07:00, Mac scan weekly (plus "Scan now"). Jobs missed while the Mac slept run once when it wakes.

## What stays on this Mac

- The scan only reads; it never changes a setting or deletes anything.
- Secret values are never stored, logged, shown or sent anywhere. Findings say only what kind of secret it is and where (file and line).
- Claude sees findings, digest items and status rows, never file contents.
- Solaris receives one summary row: counts by severity, the worst finding's title, providers not up, and digest items that affect you.

## Tests

```bash
python -m pytest tests -q
```
