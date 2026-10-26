# Security Agent: design

Status: ready for Sergio's review (builder check done)
Date: 2026-10-24

## Intent

A personal cybersecurity agent that runs on Sergio's Mac. It is both a useful daily tool and a practice ground for **using Claude as a security analyst**, which is the main thing Sergio wants to have at hand.

It replaces three things he does badly today:

1. Wondering why the Mac is slow, or whether something on it is exposed, with no routine way to check.
2. Following security news on Twitter, where everything is hype or doom and nothing is easy to trust or track.
3. Not knowing, when something breaks, whether it's his code or a provider (Vercel, Turso, Neon, Anthropic, GitHub, Cloudflare, AWS) or DNS.

## Goals

- **Mac check:** a routine, read-only health and security scan of this Mac, with plain explanations and a "How to fix it" guide for every finding.
- **Validated digest:** a short daily security digest where every item is backed by a primary source, readable in about 5 minutes. Items that affect Sergio's own setup are flagged at the top.
- **Status page:** live status of the providers his projects depend on, plus the main public DNS resolvers.
- **Ask the analyst:** a chat panel where Claude answers questions grounded in the latest scan, digest and status data.
- **Solaris card:** a small summary of all of the above on the Solaris dashboard.

## Non-goals (for now)

- **Automatic fixes.** The agent never changes anything on the Mac. A "fix it" button is a possible later step, not this one.
- **Experiment sandbox.** Wanted in the future. The design should leave room for it (see "Room to grow") but nothing is built now.
- **Notifications or alerts.** Outages and findings only show on the dashboard.
- **Replacing a real antivirus or EDR.** This is a routine hygiene check, not malware removal.

## Anti-goals (would make it a failure even if it works)

- **A secret value leaves the Mac.** No API key, password, wallet key, token or file content goes to Claude, to Solaris, into logs or onto the dashboard. Only the type of secret and where it is (file path and line).
- **Claude invents facts.** A digest item without a primary source, or a finding Claude made up rather than one the checks collected, defeats the point of "validated".
- **Hype tone.** The digest should be calm and specific: what happened, who's affected, what to do.
- **The scan itself makes the Mac slow or freezes it.** Given the recent Turbopack freezes, scans must be light, sequential and time-boxed.

## Decided by Sergio

1. **Always on.** The agent starts automatically at login (a launchd user agent) and runs in the background, so the weekly scan, the status refresh, the 7-day history and the daily digest happen without him starting it. It can still be run by hand with `python main.py`. Jobs missed while the Mac was asleep or off run once on startup; gaps in status history are shown as "no data", not as an outage.
2. **Takes over security news from analyst-agent.** The new agent owns the security feeds (NVD, CISA's Known Exploited Vulnerabilities list, AWS security, AlienVault OTX if useful). analyst-agent keeps OSINT and the cosmic side, and its infosec module is removed as part of this work, so Solaris doesn't show two overlapping security cards. Code from `analyst-agent/intelligence/infosec.py` may be reused.
3. **Solaris: data now, card later.** This build adds the agent to `heartbeat.py` and makes `sync.py` push the summary row to Turso. The card in `solaris/web-next` is built later, after the current uncommitted Solaris work is committed, and is out of scope here.
4. **Claude spending cap: $1/day.** About a third (~$0.33) is held back for the daily digest, so a busy chat day can't stop the digest from being built. Both numbers are configurable in `.env`.

## Core principle: facts first, then Claude

Plain, deterministic code collects facts (scan results, provider status, news items from primary sources). Claude only reasons over those facts: it ranks, groups, explains and writes guides. It never adds a fact of its own. Every Claude output points back to the facts it used. This pattern is the main thing the project is meant to practice.

## Part 1: Mac check

Read-only. Runs when Sergio clicks "Scan" on the dashboard, plus automatically once a week while the agent is running.

What it looks at:

- **Slowness:** top processes by CPU and memory, free memory and memory pressure, things that start at login or run in the background (login items, LaunchAgents and LaunchDaemons), and runaway process counts (e.g. hundreds of copies of the same worker, as in the Turbopack fork storm).
- **Open ports:** every listening port, the program behind it, and whether it's bound to localhost only or to all interfaces (reachable from the network, the riskier case).
- **Sensitive data lying around:** secrets in plain files, scoped to the home folder and common places: `.env` files under `~/Projects`, cloud credential files (`~/.aws`, etc.), shell history, and SSH private keys with loose permissions. The Polymarket wallet key in `polymarket-agent/.env` is a real example it should find. Output is the secret type plus file path and line, never the value.
  - **Severity rules (Claude's call):** a gitignored `.env` inside a project folder holding ordinary API keys is expected setup. All of those are grouped into one "info" finding, so they don't bury real issues. Severity goes up when a secret is **tracked by git or present in git history** (high), sits in a file **readable by other users** (medium), is a **wallet or private key** in a plain file (medium, with a guide to move it somewhere safer), or is in **shell history or outside a project folder** (medium). This means the check reads git state (tracked files and history) for repos under `~/Projects`, not only files on disk.
- **Safety basics:** FileVault, the macOS firewall, SIP, Gatekeeper, XProtect, and pending macOS updates.
- **Malware signs:** background items (LaunchAgents/Daemons, login items) without a valid developer signature, unknown system extensions, and installed configuration profiles.

Each finding has: a severity (high, medium, low or info), a short title, the evidence (redacted), a plain explanation of why it matters, and a **"How to fix it" guide** with exact steps Sergio can follow himself. Scans are stored so he can compare with the previous scan ("new since last time").

## Part 2: Validated digest

Built once a day.

- **Sources that can make an item true (primary):** vendor security advisories (e.g. Apple, Microsoft, Google/Chrome, AWS, Cloudflare, GitHub), official CVE records (NVD), CISA's Known Exploited Vulnerabilities list, and established security outlets. An item gets in if it has a primary source, **or** at least two established outlets report the same thing.
- **Sources that can only tip (not enough alone):** social media, personal blogs and aggregators. A tip becomes an item only once a primary source confirms it.
- **What Claude does:** groups duplicate stories, writes a plain-language summary, says who's affected and whether Sergio needs to act, and lists the sources behind each item.
- **"Affects you" flag:** items are matched against what this Mac and Sergio's projects actually use (macOS version, browsers, installed apps, the providers on the status page, and the main dependencies of his projects) and float to the top.
- Security incidents at a monitored provider (e.g. a breach) appear in the digest too.

## Part 3: Status page

Refreshes every few minutes while the agent is running.

- **Providers:** Vercel, Turso, Neon, Anthropic, GitHub, Cloudflare, AWS.
- **DNS resolvers:** Cloudflare (1.1.1.1), Google (8.8.8.8), Quad9 (9.9.9.9).
- **Two signals per service:**
  - **What the provider says:** its official status page or feed (most use a standard machine-readable status page; AWS has its own health feed).
  - **What we see:** a quick probe from the Mac (does the API host answer, does a DNS lookup through that resolver succeed, and how fast).
  - When the two disagree (the provider says "operational" but the probe fails), show both.
- **What shows:** up, degraded or down; any open incident title; time since last check; a short history (the last 7 days) so flaky services stand out.

## Part 4: Ask the analyst

A chat panel on the dashboard.

- Claude answers using the latest scan, the digest and the status data as context.
- It has **read-only** tools: look up a CVE, check CISA's exploited list, and read stored scan, digest and status data.
- It never runs commands on the Mac and never sees secret values.
- Example questions: "Is this open port a problem?", "Does this CVE affect me?", "Why is my Mac slow today?"

## Part 5: Solaris card

The agent keeps its data in local SQLite, like the other agents. Solaris's existing `sync.py` (cron on the Mac, pushes to Turso) adds this agent. The card UI itself is built later (see "Decided by Sergio", item 3):

- **Liveness:** add it to `heartbeat.py`'s `AGENTS` map.
- **A summary row only:** last scan time, count of findings by severity, the title of the worst finding, how many providers are not up, and the number of digest items that affect Sergio.
- No finding details, paths or digest bodies go to Turso.

## Constraints

- **Language and shape:** Python, standalone, with its own local web dashboard, like the other agents. Started with `python main.py`.
- **Runs locally on this Mac** (MacBook Pro M1, 16 GB). Uses only built-in macOS tools and Python libraries; no root, no kernel extensions, no installing system software.
- **Light on the machine:** checks run one at a time with timeouts; a scan must not noticeably slow the Mac.
- **Claude:** Anthropic API via `ANTHROPIC_API_KEY` in the agent's `.env`. A **daily spending cap** of $1 on API calls, with ~$0.33 reserved for the digest, and today's spend shown on the dashboard. When the cap is hit, the dashboard still works without Claude's summaries.
- **Privacy:** secrets are redacted before any data is stored, logged, sent to Claude or synced to Solaris.
- **Writing:** no em dashes in user-facing text.

## Room to grow (design for it, don't build it)

- **Fix it buttons** for safe cases (e.g. turn on the firewall), reusing the "How to fix it" guides.
- **Experiment sandbox:** a separate, isolated place to try security tools and exercises. Keep the analyst's tools pluggable so a sandbox can be added as another tool later.
- **Notifications** for high-severity findings or provider outages.

## Left to the builder

- Agent folder name, local port and dashboard look (match the other agents unless there's a reason not to).
- Exact data sources and their parsers for the digest and status page, within the rules above.
- Which Claude model to use for each job, within the spending cap.
- Database schema, scheduling library and project layout.
- How secrets are detected (patterns and heuristics), as long as values never leave the redaction step.
