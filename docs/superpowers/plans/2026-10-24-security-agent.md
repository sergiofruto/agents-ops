# Security Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A standalone, always-on Python agent on Sergio's Mac with a local dashboard: a read-only Mac security scan with "How to fix it" guides, a validated daily security digest, a provider and DNS status page, an "Ask the analyst" Claude chat, and a summary row for Solaris.

**Architecture:** Facts first, then Claude. Deterministic collectors (`checks/`, `status/`, `digest/sources.py`) write facts to SQLite. Claude (`analyst.py`, behind a daily budget) only groups, ranks, summarizes and answers over stored facts, and code enforces every rule Claude could break (primary-source rule, known ids only). One scheduler loop runs jobs one at a time; Flask serves the dashboard on 127.0.0.1.

**Tech Stack:** Python 3.11 (`/Users/sergiofruto/anaconda3/bin/python3`), Flask 3, requests, feedparser, dnspython, anthropic SDK, python-dotenv, pytest, SQLite, launchd.

**Spec:** `docs/superpowers/specs/2026-10-24-security-agent-design.md`

## Global Constraints

- Folder `security-agent/`, started with `python main.py`, logs to `security-agent/agent.log`, data in `security-agent/security.db`, config from `security-agent/.env` via `config.py` (same pattern as `analyst-agent/config.py`).
- Dashboard binds **127.0.0.1:5007** only (`WEB_HOST`, `WEB_PORT` in config).
- **Never changes anything on the Mac.** Only read-only commands, run through `checks/shell.py` with an argument list (never `shell=True`) and a timeout. No root, no `sudo`, no installing software.
- **Secret values never leave the redaction step:** not stored, logged, sent to Claude, shown, or synced. Findings carry the secret *kind*, file path (relative to home) and line only.
- **Finding titles never contain paths, hostnames or secret material** (titles go to Solaris). Paths belong in `evidence`.
- Checks run **sequentially**, each command time-boxed (default 30 s, `softwareupdate` 120 s). Scheduled jobs run one at a time on one worker thread.
- Claude: `ANTHROPIC_API_KEY`; daily cap **$1.00** (`AI_DAILY_CAP_USD`), **$0.33** reserved for the digest (`AI_DIGEST_RESERVE_USD`). When the budget or key is missing, every feature still works without Claude text.
- Schedules: status every **5 min**, digest **daily at or after 07:00 local**, scan **every 7 days**, plus "Scan now". Missed jobs run once on startup. Status history covers **7 days**; buckets without checks show **"no data"**.
- Providers: Vercel, Turso, Neon, Anthropic, GitHub, Cloudflare, AWS. DNS: Cloudflare 1.1.1.1, Google 8.8.8.8, Quad9 9.9.9.9.
- Secret severity: tracked by git or in git history = **high**; readable by other users = **medium**; wallet or private key in a plain file = **medium**; shell history or outside a project folder = **medium**; gitignored `.env` in a project with ordinary keys = **info**, all grouped into **one** finding.
- No em dashes in any user-facing text (dashboard copy, guides, prompts' output instructions).
- Tests: `cd security-agent && /Users/sergiofruto/anaconda3/bin/python3 -m pytest tests -q`. Tests never call real network, real Claude or real macOS commands; they use recorded command output, fake HTTP and a fake Claude client.
- **Git:** Sergio normally commits himself. Commit steps below run only if he has OK'd commits for this build. **Never commit anything under `solaris/`** (those files hold his uncommitted work); Task 13 leaves its changes uncommitted.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **The Mac is offline or just woke up:** every probe fails at once. Expected: recorded as "offline / no data", not seven outages. Test in Task 7 (`test_all_probes_failing_records_offline_not_outage`).
2. **A command needs a permission the agent lacks** (Full Disk Access, root, Automation) or isn't present. Expected: that item shows under "couldn't check", the rest of the scan runs, and it never reads as "all clear". Tests in Task 4 (`test_permission_error_becomes_skipped`) and Task 5 (`test_check_crash_is_skipped_not_fatal`).
3. **Huge, binary or unreadable files in `~/Projects`:** expected skipped quietly and fast. Test in Task 2 (`test_large_binary_and_unreadable_files_are_skipped`).
4. **Claude returns malformed JSON or invents item ids:** expected fall back to the deterministic digest; unknown ids dropped. Test in Task 9 (`test_malformed_claude_output_falls_back`).
5. **Feed titles with HTML or `<script>`:** expected shown as text, never rendered. Test in Task 12 (`test_feed_html_is_escaped`).

---

## File Structure

```
security-agent/
  main.py              # logging, db init, Flask thread, scheduler loop
  config.py            # .env values, PROVIDERS, DNS_RESOLVERS, DIGEST_SOURCES, MODEL_PRICES
  database.py          # schema, connect(), small query helpers, solaris_summary view
  models.py            # Finding, CheckResult, Severity, Item, ServiceCheck
  scheduler.py         # due(), JOBS, run_due_jobs()
  scan.py              # run_scan(): sequential checks, store, "new since last"
  budget.py            # cost_usd(), Budget
  analyst.py           # Claude wrapper, scan_overview(), chat() with read-only tools
  checks/
    shell.py           # run(cmd, timeout) -> CmdResult
    redact.py          # SECRET_PATTERNS, find_secrets() -> SecretHit (no values)
    secrets.py         # classify(), scan_secrets()
    ports.py           # parse_lsof(), check_ports()
    performance.py     # parse_ps(), parse_vm_stat(), check_performance()
    basics.py          # FileVault, firewall, SIP, Gatekeeper, XProtect, updates
    persistence.py     # launch agents/daemons signatures, system extensions, profiles
  status/
    official.py        # parse_statuspage(), fetch_official()
    probe.py           # probe_https(), probe_dns()
    service.py         # combine(), check_all(), history()
  digest/
    sources.py         # fetch_* -> list[Item]
    validate.py        # extract_cves(), pre_cluster(), confirmable()
    inventory.py       # collect_inventory(), affects()
    build.py           # build_digest()
  web/
    app.py             # create_app()
    templates/         # base.html (chat panel), index, scan, digest, status
    static/app.js
  launchd/
    com.sergiofruto.security-agent.plist
    install.sh, uninstall.sh
  tests/               # test_*.py + fixtures/ (recorded command output, feed samples)
  requirements.txt, README.md, .gitignore (security.db, agent.log, .env, launchd.log)
```

Modified elsewhere: `solaris/heartbeat.py`, `solaris/sync.py`, `solaris/config.py`, `solaris/turso/schema.sql`, `solaris/test_heartbeat.py`, `solaris/test_sync.py` (Task 13), `analyst-agent/` (Task 14).

---

### Task 1: Scaffold, config, models, database, shell runner

**Files:**
- Create: `security-agent/{config.py,models.py,database.py,checks/__init__.py,checks/shell.py,requirements.txt,.gitignore,tests/conftest.py,tests/test_foundation.py}`

**Interfaces:**
- Produces:
  - `models.Severity = Literal["high", "medium", "low", "info"]`, `SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}`
  - `@dataclass(frozen=True) Finding(key: str, category: str, severity: Severity, title: str, evidence: str, explanation: str, fix: list[str])`. `key` is stable across scans (e.g. `"port:5000:python"`); `category` in `"performance" | "ports" | "secrets" | "basics" | "malware"`.
  - `@dataclass CheckResult(category: str, findings: list[Finding] = [], passed: list[str] = [], skipped: list[str] = [])` (use `field(default_factory=list)`).
  - `@dataclass(frozen=True) CmdResult(ok: bool, stdout: str, stderr: str, error: str | None)`
  - `checks.shell.run(cmd: list[str], timeout: float = 30) -> CmdResult`: never raises; timeout gives `error="timeout"`, missing binary gives `error="not found"`, non-zero exit gives `ok=False` with stderr.
  - `database.connect(path: str | None = None) -> sqlite3.Connection` (row_factory Row, WAL), `database.init_db(conn)`. Tables: `scans(id, started_at, finished_at, status, overview)`, `findings(scan_id, key, category, severity, title, evidence, explanation, fix_json, is_new)`, `scan_checks(scan_id, category, passed_json, skipped_json)`, `status_checks(service, checked_at, state, official, probe_ok, probe_ms, incident)`, `digests(id, day, built_at, used_ai)`, `digest_entries(digest_id, rank, title, summary, who, action, affects_json, sources_json, kev)`, `seen_items(url PRIMARY KEY, first_seen)`, `job_runs(job PRIMARY KEY, last_run)`, `ai_usage(day, job, model, input_tokens, output_tokens, cost_usd)`. View `solaris_summary` is added in Task 13.
  - `tests/conftest.py`: fixture `db` (in-memory, initialised); fixture `fixture(name) -> str` reading `tests/fixtures/<name>`; helper `F(key, sev="medium", title="t", evidence="e", fix=None, category="ports") -> Finding` used by later tests. Later tasks add `fake_run`, `git_repo`/`commit_all`, and Claude fakes here.
  - `config`: `DB_PATH`, `WEB_HOST="127.0.0.1"`, `WEB_PORT=5007`, `ANTHROPIC_API_KEY`, `AI_DAILY_CAP_USD=1.0`, `AI_DIGEST_RESERVE_USD=0.33`, `DIGEST_MODEL`, `CHAT_MODEL` (both default `"claude-haiku-5-5"`), `PROJECTS_ROOT=~/Projects`, `RUNAWAY_PROCESS_COUNT=30`.

- [ ] **Step 1: Write the failing tests** in `tests/test_foundation.py`

```python
def test_init_db_creates_tables(db):
    names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"scans", "findings", "scan_checks", "status_checks", "digests",
            "digest_entries", "seen_items", "job_runs", "ai_usage"} <= names

def test_run_missing_binary_does_not_raise():
    r = shell.run(["/nonexistent/binary"])
    assert r.ok is False and r.error == "not found"

def test_run_timeout_does_not_raise():
    r = shell.run(["/bin/sleep", "5"], timeout=0.2)
    assert r.ok is False and r.error == "timeout"

def test_run_captures_stdout():
    assert shell.run(["/bin/echo", "hi"]).stdout.strip() == "hi"

def test_web_binds_localhost_only():
    assert config.WEB_HOST == "127.0.0.1" and config.WEB_PORT == 5007
```

- [ ] **Step 2: Run** `python -m pytest tests/test_foundation.py -q`. Expected: FAIL (ImportError).
- [ ] **Step 3: Implement** the files above. `requirements.txt`: `flask>=3.0`, `requests>=2.31`, `feedparser>=6.0`, `dnspython>=2.6`, `anthropic>=0.40`, `python-dotenv>=1.0`, `pytest>=8`. `.gitignore`: `security.db*`, `agent.log`, `launchd.log`, `.env`, `__pycache__/`.
- [ ] **Step 4: Run** the tests. Expected: 5 passed.
- [ ] **Step 5: Commit** `git add security-agent && git commit -m "feat(security-agent): scaffold, models, db, shell runner"`

---

### Task 2: Secret detection with redaction and severity rules

**Files:**
- Create: `security-agent/checks/redact.py`, `security-agent/checks/secrets.py`, `security-agent/tests/test_secrets.py`

**Interfaces:**
- Consumes: `Finding`, `CheckResult`, `shell.run`.
- Produces:
  - `@dataclass(frozen=True) SecretHit(kind: str, line: int)`: no value field.
  - `find_secrets(text: str) -> list[SecretHit]`. Kinds: `aws_access_key` (`AKIA[0-9A-Z]{16}`), `anthropic_key` (`sk-ant-[A-Za-z0-9_-]{20,}`), `openai_key` (`sk-(proj-)?[A-Za-z0-9]{20,}`), `github_token` (`gh[pousr]_[A-Za-z0-9]{36,}`), `private_key_block` (`-----BEGIN [A-Z ]*PRIVATE KEY-----`), `wallet_private_key` (a `*PRIVATE_KEY*`/`*WALLET*` assignment whose value is 64 hex chars, optional `0x`), `generic_secret` (an assignment whose name contains KEY, SECRET, TOKEN, PASSWORD or PASSPHRASE with a value of 8+ chars that isn't a placeholder: empty, `changeme`, `xxx…`, `your_…`, `<…>`). One hit per line, most specific kind wins.
  - `classify(hits: list[SecretHit], *, tracked: bool, in_history: bool, other_readable: bool, in_project: bool, shell_history: bool) -> Severity`
  - `scan_secrets(projects_root: Path, home: Path) -> CheckResult` (category `"secrets"`).

Scope: under `projects_root`, files named `.env`, `.env.*`, `*.pem`, `*.key`, `credentials*`; skip dirs `node_modules .git .next .venv venv __pycache__ dist build`; skip files > 1 MB or not UTF-8 decodable or unreadable. Outside projects: `~/.aws/credentials`, `~/.zsh_history`, `~/.bash_history`, and `~/.ssh/id_*` without `.pub` (private keys: finding only when mode & 0o077, title "SSH private key readable by other users"). Git state per file: repo root from `git -C <dir> rev-parse --show-toplevel`; `tracked` from `git ls-files --error-unmatch <path>` ok; `in_history` from `git log --all --format=%H -1 -- <path>` non-empty.

Output: all `info` files grouped into one finding `key="secrets:ignored-env"`, title `"API keys in git-ignored .env files (expected setup)"`, evidence = count plus relative paths. Every other file is its own finding, `key=f"secrets:{relpath}"`, generic title by worst reason (e.g. `"Secret committed to git"`, `"Wallet or private key stored in a plain file"`, `"Secret in shell history"`, `"Secret file readable by other users"`, `"Credentials stored outside a project"`), evidence like `"polymarket-agent/.env: wallet_private_key on line 6"`, and a fix guide per reason (committed: rotate the key, remove from history with `git filter-repo`, add to `.gitignore`; wallet key: move to macOS Keychain via `security add-generic-password` and read it at startup, or a hardware wallet; shell history: rotate, delete the lines, `setopt HIST_IGNORE_SPACE`; permissions: `chmod 600`).

- [ ] **Step 1: Write the failing tests**

```python
PLANTED = "0x" + "ab" * 32
ANTH = "sk-ant-api03-" + "Z" * 40

def test_find_secrets_reports_kind_and_line_only():
    hits = find_secrets(f"A=1\nPOLY_PRIVATE_KEY={PLANTED}\nANTHROPIC_API_KEY={ANTH}\n")
    assert hits == [SecretHit("wallet_private_key", 2), SecretHit("anthropic_key", 3)]

def test_placeholders_are_not_secrets():
    assert find_secrets("API_KEY=\nTOKEN=changeme\nSECRET=your_secret_here\nKEY=<key>\n") == []

@pytest.mark.parametrize("kw,expected", [
    (dict(tracked=True), "high"), (dict(in_history=True), "high"),
    (dict(other_readable=True), "medium"), (dict(in_project=False), "medium"),
    (dict(shell_history=True, in_project=False), "medium"), ({}, "info"),
])
def test_classify(kw, expected):
    base = dict(tracked=False, in_history=False, other_readable=False, in_project=True, shell_history=False)
    assert classify([SecretHit("generic_secret", 1)], **{**base, **kw}) == expected

def test_wallet_key_in_ignored_env_is_medium():
    base = dict(tracked=False, in_history=False, other_readable=False, in_project=True, shell_history=False)
    assert classify([SecretHit("wallet_private_key", 1)], **base) == "medium"

def test_scan_groups_info_and_never_leaks_values(tmp_path, git_repo):
    # git_repo fixture: tmp_path/"Projects"/"proj" initialised as a repo with ".env" in .gitignore
    proj = git_repo
    (proj / ".env").write_text(f"ANTHROPIC_API_KEY={ANTH}\n"); (proj / ".env").chmod(0o600)
    other = proj / "sub"; other.mkdir()
    (other / ".env").write_text(f"POLY_PRIVATE_KEY={PLANTED}\n"); (other / ".env").chmod(0o600)
    res = scan_secrets(tmp_path / "Projects", home=tmp_path)
    keys = {f.key: f for f in res.findings}
    assert "secrets:ignored-env" in keys and keys["secrets:ignored-env"].severity == "info"
    wallet = [f for f in res.findings if f.severity == "medium"]
    assert len(wallet) == 1 and "line 1" in wallet[0].evidence and "/" not in wallet[0].title
    dump = repr(res)
    assert PLANTED not in dump and ANTH not in dump and "ab" * 32 not in dump

def test_committed_secret_is_high(tmp_path, git_repo):
    (git_repo / "config.env").write_text(f"ANTHROPIC_API_KEY={ANTH}\n")
    commit_all(git_repo)  # helper in conftest
    res = scan_secrets(tmp_path / "Projects", home=tmp_path)
    # config.env doesn't match the .env* name rule, so also include *.env in the scope
    assert any(f.severity == "high" for f in res.findings)

def test_large_binary_and_unreadable_files_are_skipped(tmp_path, git_repo):
    (git_repo / ".env.big").write_text("KEY=" + "x" * 2_000_000)
    (git_repo / ".env.bin").write_bytes(b"\xff\xfe\x00" * 100)
    locked = git_repo / ".env.locked"; locked.write_text(f"ANTHROPIC_API_KEY={ANTH}\n"); locked.chmod(0)
    res = scan_secrets(tmp_path / "Projects", home=tmp_path)  # must not raise
    assert all(".env.big" not in f.evidence and ".env.bin" not in f.evidence for f in res.findings)
```

(Scope therefore also includes `*.env`.)

- [ ] **Step 2: Run** `python -m pytest tests/test_secrets.py -q`. Expected: FAIL (ImportError).
- [ ] **Step 3: Implement** `redact.py` and `secrets.py`. Regex matching must never copy the matched value into any object; only the kind and line number survive.
- [ ] **Step 4: Run** the tests. Expected: all pass.
- [ ] **Step 5: Commit** `git commit -m "feat(security-agent): secret detection with redaction" -- security-agent`

---

### Task 3: Open ports and slowness checks

**Files:**
- Create: `security-agent/checks/ports.py`, `security-agent/checks/performance.py`, `security-agent/tests/test_ports_perf.py`, fixtures `lsof_listen.txt`, `ps.txt`, `vm_stat.txt`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) Listener(command: str, pid: int, address: str, port: int)`; `parse_lsof(stdout: str) -> list[Listener]` from `lsof -nP -iTCP -sTCP:LISTEN` (NAME like `*:5000`, `127.0.0.1:5003`, `[::1]:3000`); `is_local(address) -> bool` (`127.0.0.1`, `[::1]`, `localhost`).
  - `check_ports(run=shell.run) -> CheckResult` (category `"ports"`): one finding per (command, port) reachable from the network, `key=f"port:{port}:{command}"`, severity `info` for Apple system daemons (`rapportd`, `ControlCe`, `sharingd`, `AirPlayXP`, `identitys`) and `medium` otherwise. All localhost-only listeners grouped into one `info` finding `key="ports:local-only"`. Fix guide: stop the program, or bind it to `127.0.0.1`, or turn on the firewall's stealth mode. TCP only (UDP left out to keep noise down).
  - `@dataclass(frozen=True) Proc(pid: int, cpu: float, rss_kb: int, name: str)`; `parse_ps(stdout) -> list[Proc]` from `ps -axo pid=,pcpu=,rss=,command=`. `name` = basename of argv[0], and when that is `node`/`python*`, `"<base> <basename of argv[1]>"`.
  - `parse_vm_stat(stdout: str, memsize: int) -> float` returns free fraction = (free + inactive + speculative pages) × page size / memsize.
  - `check_performance(run=shell.run, runaway_count=30) -> CheckResult` (category `"performance"`): runaway group (more than `runaway_count` procs with the same `name`) = `high`, `key=f"perf:runaway:{name}"`, title `"Runaway process copies"`, evidence `"<n> copies of <name>"`; free memory under 10% = `medium` `"Low free memory"`; any process above 80% CPU = `low` `key=f"perf:cpu:{name}"`; always one `info` `"Top memory users"` with the top 5.

- [ ] **Step 1: Write the failing tests**

```python
def test_parse_lsof_addresses(fixture):
    ls = parse_lsof(fixture("lsof_listen.txt"))
    assert Listener("Python", 4242, "*", 5000) in ls
    assert Listener("node", 777, "127.0.0.1", 3000) in ls
    assert Listener("node", 778, "[::1]", 3001) in ls

def test_network_listener_is_medium_and_local_grouped():
    fake = lambda cmd, timeout=30: CmdResult(True, LSOF_SAMPLE, "", None)
    res = check_ports(run=fake)
    by = {f.key: f for f in res.findings}
    assert by["port:5000:Python"].severity == "medium"
    assert by["ports:local-only"].severity == "info"
    assert by["port:7000:ControlCe"].severity == "info"

def test_runaway_postcss_workers_are_high():
    ps = "\n".join(f"{i} 1.0 90000 node /p/.next/dev/build/postcss.js" for i in range(40))
    res = check_performance(run=fake_run({"ps": ps, "vm_stat": VM_OK, "sysctl": "17179869184"}))
    f = next(f for f in res.findings if f.key == "perf:runaway:node postcss.js")
    assert f.severity == "high" and "40 copies" in f.evidence

def test_low_memory_is_medium(fixture):
    free = parse_vm_stat(fixture("vm_stat.txt"), memsize=17179869184)
    assert 0 < free < 1
    res = check_performance(run=fake_run({"ps": "1 0.0 100 /bin/zsh", "vm_stat": VM_LOW, "sysctl": "17179869184"}))
    assert any(f.title == "Low free memory" and f.severity == "medium" for f in res.findings)
```

(`fake_run` lives in `conftest.py`: maps the command's basename to stdout.)

- [ ] **Step 2: Run** `python -m pytest tests/test_ports_perf.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.** Record the three fixtures from real output on this Mac (`lsof -nP -iTCP -sTCP:LISTEN`, `ps -axo pid=,pcpu=,rss=,command=`, `vm_stat`), trimmed to ~30 lines, then add the synthetic lines the tests name.
- [ ] **Step 4: Run.** Expected: all pass.
- [ ] **Step 5: Commit** `git commit -m "feat(security-agent): ports and performance checks" -- security-agent`

---

### Task 4: Safety basics and malware-sign checks

**Files:**
- Create: `security-agent/checks/basics.py`, `security-agent/checks/persistence.py`, `security-agent/tests/test_basics_persistence.py`

**Interfaces:**
- Produces `check_basics(run=shell.run) -> CheckResult` (category `"basics"`) and `check_persistence(run=shell.run, dirs: list[Path] | None = None) -> CheckResult` (category `"malware"`).

| Check | Command | Pass | Finding when not |
|---|---|---|---|
| FileVault | `fdesetup status` | contains `FileVault is On` | high `basics:filevault` |
| Firewall | `/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate` | `enabled` | medium `basics:firewall` |
| SIP | `csrutil status` | `enabled` | high `basics:sip` |
| Gatekeeper | `spctl --status` | `assessments enabled` | high `basics:gatekeeper` |
| XProtect | plist `CFBundleShortVersionString` of `/Library/Apple/System/Library/CoreServices/XProtect.bundle/Contents/Info.plist` | present | passed entry shows the version |
| Updates | `softwareupdate -l` (timeout 120) | `No new software available` | medium `basics:updates`, evidence lists the `* Label:` lines |

Each fix guide gives the System Settings path and the terminal command where one exists (e.g. firewall: System Settings > Network > Firewall, or `sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on` for Sergio to run himself).

Persistence: for each plist in `~/Library/LaunchAgents`, `/Library/LaunchAgents`, `/Library/LaunchDaemons`, read `Program` or `ProgramArguments[0]` with `plistlib`; run `codesign --verify --strict <binary>`; failing or missing binary = medium `malware:launch:<label>` title `"Background item without a valid signature"`. `systemextensionsctl list` = one info finding listing extensions. `profiles list` = low `malware:profiles` when any profile is listed.

Rule for both: a command that errors, times out, is missing, or prints "not permitted"/"requires root" adds a `skipped` entry (`"Firewall: couldn't check (permission)"`) and **no** passed entry.

- [ ] **Step 1: Write the failing tests**

```python
def test_all_on_passes():
    res = check_basics(run=fake_run(BASICS_ALL_ON))
    assert res.findings == [] and len(res.passed) == 6

def test_filevault_off_is_high():
    res = check_basics(run=fake_run({**BASICS_ALL_ON, "fdesetup": "FileVault is Off."}))
    assert [(f.key, f.severity) for f in res.findings] == [("basics:filevault", "high")]

def test_pending_updates_listed():
    out = "Software Update found the following:\n* Label: macOS Tahoe 26.1-25B78\n"
    res = check_basics(run=fake_run({**BASICS_ALL_ON, "softwareupdate": out}))
    assert "macOS Tahoe 26.1" in next(f for f in res.findings if f.key == "basics:updates").evidence

def test_permission_error_becomes_skipped():
    res = check_basics(run=fake_run({**BASICS_ALL_ON, "fdesetup": CmdResult(False, "", "Operation not permitted", None)}))
    assert any("FileVault" in s for s in res.skipped)
    assert not any("FileVault" in p for p in res.passed) and res.findings == []

def test_unsigned_launch_agent_is_medium(tmp_path):
    plist = tmp_path / "com.evil.agent.plist"
    plist.write_bytes(plistlib.dumps({"Label": "com.evil.agent", "ProgramArguments": ["/tmp/evil"]}))
    res = check_persistence(run=fake_run({"codesign": CmdResult(False, "", "not signed at all", None),
                                          "systemextensionsctl": "0 extension(s)", "profiles": ""}),
                            dirs=[tmp_path])
    assert any(f.key == "malware:launch:com.evil.agent" and f.severity == "medium" for f in res.findings)
```

- [ ] **Step 2: Run.** Expected: FAIL. **Step 3: Implement.** **Step 4: Run.** Expected: all pass.
- [ ] **Step 5: Commit** `git commit -m "feat(security-agent): safety basics and malware-sign checks" -- security-agent`

---

### Task 5: Scan orchestration and storage

**Files:**
- Create: `security-agent/scan.py`, `security-agent/tests/test_scan.py`

**Interfaces:**
- Consumes: the five checks.
- Produces:
  - `DEFAULT_CHECKS: list[tuple[str, Callable[[], CheckResult]]]` in order performance, ports, secrets, basics, malware.
  - `class ScanInProgress(Exception)`; module-level `SCAN_LOCK = threading.Lock()`.
  - `run_scan(conn, checks=DEFAULT_CHECKS, *, now=datetime.now) -> int` returns the scan id. Acquires `SCAN_LOCK` non-blocking (raises `ScanInProgress` if held), runs checks one by one, a check that raises becomes `skipped=[f"{name}: couldn't check ({type(exc).__name__})"]`, stores findings with `is_new = key not in the previous completed scan`, marks the scan `done`.
  - `latest_scan(conn) -> dict | None` with `findings` sorted by `SEVERITY_ORDER`, plus `passed`, `skipped`, `overview`, `counts` by severity.
  - Hook: `run_scan` calls `on_done(scan_id)` if given (Task 10 passes the Claude overview).

- [ ] **Step 1: Write the failing tests**

```python
def test_new_since_last_scan(db):
    a = Finding("port:1:x", "ports", "medium", "t", "e", "x", ["f"])
    b = Finding("port:2:y", "ports", "medium", "t", "e", "x", ["f"])
    run_scan(db, [("ports", lambda: CheckResult("ports", [a]))])
    run_scan(db, [("ports", lambda: CheckResult("ports", [a, b]))])
    new = {f["key"]: f["is_new"] for f in latest_scan(db)["findings"]}
    assert new == {"port:1:x": 0, "port:2:y": 1}

def test_check_crash_is_skipped_not_fatal(db):
    def boom(): raise PermissionError("nope")
    sid = run_scan(db, [("basics", boom), ("ports", lambda: CheckResult("ports", passed=["ok"]))])
    s = latest_scan(db)
    assert s["id"] == sid and "basics: couldn't check (PermissionError)" in s["skipped"] and "ok" in s["passed"]

def test_concurrent_scan_refused(db):
    SCAN_LOCK.acquire()
    try:
        with pytest.raises(ScanInProgress): run_scan(db, [])
    finally:
        SCAN_LOCK.release()

def test_checks_run_sequentially(db):
    active = []
    def slow(name):
        def f():
            active.append(name); assert len(active) == 1; time.sleep(0.01); active.pop()
            return CheckResult(name)
        return f
    run_scan(db, [("a", slow("a")), ("b", slow("b"))])
```

- [ ] **Step 2: Run.** Expected: FAIL. **Step 3: Implement.** **Step 4: Run.** Expected: all pass.
- [ ] **Step 5: Commit** `git commit -m "feat(security-agent): scan orchestration and history" -- security-agent`

---

### Task 6: Daily AI budget and Claude wrapper

**Files:**
- Create: `security-agent/budget.py`, the `Claude` class in `security-agent/analyst.py`, `security-agent/tests/test_budget.py`, `tests/fakes.py` (`FakeClaudeClient`)

**Interfaces:**
- Produces:
  - `config.MODEL_PRICES: dict[str, tuple[float, float]]` = USD per million input and output tokens for `claude-haiku-5-5` and `claude-sonnet-5-5`. **Look the current prices up with the `claude-api` skill before filling these in; do not use remembered numbers.**
  - `cost_usd(model: str, input_tokens: int, output_tokens: int) -> float`
  - `class Budget(conn, cap=config.AI_DAILY_CAP_USD, reserve=config.AI_DIGEST_RESERVE_USD)`: `spent_today(day: date) -> float`, `can_spend(job: Literal["digest", "chat", "scan"], day: date) -> bool`, `record(job, model, input_tokens, output_tokens, day) -> float`.
    Rule: `digest` may spend while total < cap. `chat`/`scan` may spend while total < cap - reserve, or while total < cap once a `digest` row exists for that day.
  - `class Claude(client, budget, *, today=date.today)`: `ask(job, *, model, system, messages, tools=None, max_tokens=1024) -> anthropic Message | None`. Returns `None` when there's no client (no API key) or `can_spend` is false; records usage from `response.usage` after each call. `Claude.from_config(conn)` builds the real `anthropic.Anthropic` client only when `ANTHROPIC_API_KEY` is set.
  - `FakeClaudeClient(responses: list)` records every `messages.create(**kwargs)` call in `.calls` and returns the queued responses with a `usage` of `input_tokens`/`output_tokens`.

- [ ] **Step 1: Write the failing tests**

```python
D = date(2026, 10, 24)

def test_reserve_protects_digest(db):
    b = Budget(db, cap=1.0, reserve=0.33)
    db.execute("INSERT INTO ai_usage VALUES (?,?,?,?,?,?)", (D.isoformat(), "chat", "m", 0, 0, 0.67)); db.commit()
    assert b.can_spend("chat", D) is False and b.can_spend("digest", D) is True

def test_reserve_released_after_digest(db):
    b = Budget(db, cap=1.0, reserve=0.33)
    for job, c in [("digest", 0.10), ("chat", 0.60)]:
        db.execute("INSERT INTO ai_usage VALUES (?,?,?,?,?,?)", (D.isoformat(), job, "m", 0, 0, c))
    db.commit()
    assert b.can_spend("chat", D) is True
    db.execute("INSERT INTO ai_usage VALUES (?,?,?,?,?,?)", (D.isoformat(), "chat", "m", 0, 0, 0.31)); db.commit()
    assert b.can_spend("chat", D) is False

def test_new_day_resets(db):
    db.execute("INSERT INTO ai_usage VALUES (?,?,?,?,?,?)", (D.isoformat(), "chat", "m", 0, 0, 5.0)); db.commit()
    assert Budget(db).can_spend("chat", D + timedelta(days=1))

def test_claude_records_usage_and_denies_without_client(db):
    fake = FakeClaudeClient([fake_text("hi", input_tokens=1000, output_tokens=200)])
    c = Claude(fake, Budget(db), today=lambda: D)
    assert c.ask("chat", model="claude-haiku-5-5", system="s", messages=[{"role": "user", "content": "q"}]) is not None
    assert Budget(db).spent_today(D) == pytest.approx(cost_usd("claude-haiku-5-5", 1000, 200))
    assert Claude(None, Budget(db)).ask("chat", model="m", system="s", messages=[]) is None
```

- [ ] **Step 2: Run.** Expected: FAIL. **Step 3: Implement** (prices looked up first). **Step 4: Run.** Expected: all pass.
- [ ] **Step 5: Commit** `git commit -m "feat(security-agent): daily AI budget and Claude wrapper" -- security-agent`

---

### Task 7: Provider and DNS status

**Files:**
- Create: `security-agent/status/{__init__,official,probe,service}.py`, `security-agent/tests/test_status.py`, fixtures `statuspage_ok.json`, `statuspage_minor.json`

**Interfaces:**
- Produces:
  - `config.PROVIDERS: list[dict]` entries `{"id", "name", "official": ("statuspage", base_url) | ("aws", url) | None, "probe": https_url}` and `config.DNS_RESOLVERS = [("dns-cloudflare", "Cloudflare DNS", "1.1.1.1"), ("dns-google", "Google DNS", "8.8.8.8"), ("dns-quad9", "Quad9", "9.9.9.9")]`.
    Starting URLs (Step 1 verifies them): Vercel `https://www.vercel-status.com`, Turso `https://status.turso.tech`, Neon `https://neonstatus.com`, Anthropic `https://status.claude.com`, GitHub `https://www.githubstatus.com`, Cloudflare `https://www.cloudflarestatus.com`; probes `https://api.vercel.com`, `https://api.turso.tech`, `https://console.neon.tech`, `https://api.anthropic.com`, `https://api.github.com`, `https://api.cloudflare.com`, `https://sts.amazonaws.com`.
  - `State = Literal["up", "degraded", "down", "unknown", "no_data"]`
  - `parse_statuspage(summary: dict) -> tuple[State, str | None]`: `status.indicator` none→up, minor→degraded, major/critical→down, maintenance→degraded; incident = first unresolved incident name.
  - `fetch_official(provider, get=requests.get) -> tuple[State, str | None]`: `GET {base}/api/v2/summary.json`, timeout 10; any error → `("unknown", None)`.
  - `probe_https(url, get=requests.get) -> tuple[bool, int | None]`: any HTTP status below 500 within 5 s is reachable; returns (ok, ms).
  - `probe_dns(ip, resolve=None) -> tuple[bool, int | None]`: dnspython resolver with `nameservers=[ip]`, `lifetime=3`, A record for `example.com`.
  - `combine(official: State, probe_ok: bool) -> tuple[State, str | None]`: official down→down; official degraded→degraded; up and probe failed→`("degraded", "Provider says up, but our check failed")`; unknown and probe failed→down; unknown and probe ok→up. DNS (no official) → up/down from the probe.
  - `check_all(conn, *, fetch=fetch_official, https=probe_https, dns=probe_dns, now=...) -> list[dict]`: stores one `status_checks` row per service. **If every probe (HTTPS and DNS) fails, store every row as `no_data` with incident `"Offline: no checks possible"`** (the Mac is offline, not seven outages). Prunes rows older than 8 days.
  - `history(conn, service, now, days=7, bucket_minutes=60) -> list[dict(start, state)]`: worst state per bucket (`down` > `degraded` > `unknown` > `up`); an empty bucket is `no_data`.
  - `current(conn) -> list[dict]` latest row per service, ordered as config.

- [ ] **Step 1: Verify the URLs.** For each statuspage base run `curl -s <base>/api/v2/summary.json | head -c 200` and confirm JSON with `status.indicator`. Replace any that fail with the provider's official status host. For AWS, check whether `https://health.aws.amazon.com/health/status` (or the current official public health feed) returns machine-readable data; if none does, set AWS `official=None` so AWS relies on its probe, and ledger it. Expected: a working list written into `config.PROVIDERS`.
- [ ] **Step 2: Write the failing tests**

```python
def test_parse_statuspage(fixture):
    assert parse_statuspage(json.loads(fixture("statuspage_ok.json"))) == ("up", None)
    state, inc = parse_statuspage(json.loads(fixture("statuspage_minor.json")))
    assert state == "degraded" and inc

@pytest.mark.parametrize("official,probe,expected", [
    ("down", True, "down"), ("degraded", True, "degraded"), ("up", False, "degraded"),
    ("unknown", False, "down"), ("unknown", True, "up"), ("up", True, "up")])
def test_combine(official, probe, expected):
    assert combine(official, probe)[0] == expected

def test_all_probes_failing_records_offline_not_outage(db):
    rows = check_all(db, fetch=lambda p: ("unknown", None), https=lambda u: (False, None), dns=lambda ip: (False, None))
    assert {r["state"] for r in rows} == {"no_data"} and len(rows) == 10

def test_history_marks_gaps_no_data(db):
    now = datetime(2026, 10, 24, 12, 0)
    db.execute("INSERT INTO status_checks VALUES ('github', ?, 'down', 'down', 0, NULL, 'x')", ((now - timedelta(minutes=30)).isoformat(),))
    h = history(db, "github", now, days=1)
    assert len(h) == 24 and h[-1]["state"] == "down" and h[0]["state"] == "no_data"
```

- [ ] **Step 3: Run.** Expected: FAIL. **Step 4: Implement.** **Step 5: Run.** Expected: all pass.
- [ ] **Step 6: Commit** `git commit -m "feat(security-agent): provider and DNS status with history" -- security-agent`

---

### Task 8: Digest sources and the primary-source rule

**Files:**
- Create: `security-agent/digest/{__init__,sources,validate}.py`, `security-agent/tests/test_digest_validate.py`, fixtures `kev.json`, `rss_sample.xml`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) Item(id: str, kind: Literal["primary", "outlet"], source: str, url: str, title: str, published: datetime, text: str, cve_ids: tuple[str, ...], kev: bool = False)`; `id` = sha1 of url, first 12 hex chars.
  - `config.DIGEST_SOURCES: list[dict(name, kind, type, url)]` with `type` in `"kev" | "nvd" | "rss"`. Primary: CISA KEV JSON (`https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json`, entries with `dateAdded` in the window); NVD 2.0 API (`https://services.nvd.nist.gov/rest/json/cves/2.0`, published in the window, CVSS ≥ 9.0 only); vendor RSS for Microsoft MSRC, Chrome Releases, AWS Security Bulletins, GitHub Security Blog, Apple security releases. Outlets (RSS): BleepingComputer, The Record, SecurityWeek, Krebs on Security. **Step 1 verifies each URL parses with feedparser** (Apple in particular may lack a feed; drop failures and ledger them). No social or "tip" sources in this version.
  - `fetch_all(conn, *, window_hours=36, get=requests.get, parse=feedparser.parse, now=None) -> list[Item]` (`now` defaults to the current time): items in the window whose url isn't in `seen_items`. A failing source is logged and skipped. KEV items set `kev=True`; NVD items set `kev` from the KEV list.
  - `extract_cves(text) -> tuple[str, ...]` (`CVE-\d{4}-\d{4,}`, upper-cased, deduped, sorted).
  - `pre_cluster(items) -> list[list[Item]]`: union of items sharing any CVE id; others alone.
  - `confirmable(cluster: list[Item]) -> bool`: any `primary`, or at least 2 distinct outlet hosts (`urlparse(url).hostname`).

- [ ] **Step 1: Verify the feed URLs** with a one-off `python -c "import feedparser; print(len(feedparser.parse(URL).entries))"` per RSS source. Expected: a non-zero count; write the working list into config.
- [ ] **Step 2: Write the failing tests**

```python
def it(kind, url, title="t", text="", kev=False):
    return Item(item_id(url), kind, "s", url, title, NOW, text, extract_cves(title + " " + text), kev)

def test_single_outlet_is_not_confirmable():
    assert confirmable([it("outlet", "https://a.com/1")]) is False

def test_two_outlets_on_different_hosts_confirm():
    assert confirmable([it("outlet", "https://a.com/1"), it("outlet", "https://b.com/2")])
    assert not confirmable([it("outlet", "https://a.com/1"), it("outlet", "https://a.com/2")])

def test_primary_confirms():
    assert confirmable([it("primary", "https://cisa.gov/x")])

def test_pre_cluster_links_by_cve():
    a = it("outlet", "https://a.com/1", "Chrome zero-day CVE-2026-1234")
    b = it("primary", "https://chromereleases.googleblog.com/x", text="fixes cve-2026-1234")
    c = it("outlet", "https://b.com/z", "unrelated")
    clusters = pre_cluster([a, b, c])
    assert sorted(len(x) for x in clusters) == [1, 2]

def test_kev_parse_and_seen_items_skipped(db, fixture):
    items = fetch_all(db, get=fake_get({"known_exploited": fixture("kev.json")}), parse=lambda u: {"entries": []}, now=NOW)
    assert items and all(i.kind == "primary" and i.kev for i in items)
    db.executemany("INSERT INTO seen_items VALUES (?, ?)", [(i.url, NOW.isoformat()) for i in items]); db.commit()
    assert fetch_all(db, get=fake_get({"known_exploited": fixture("kev.json")}), parse=lambda u: {"entries": []}, now=NOW) == []
```

- [ ] **Step 3: Run.** Expected: FAIL. **Step 4: Implement** (reuse the KEV/NVD request shapes from `analyst-agent/intelligence/infosec.py`). **Step 5: Run.** Expected: all pass.
- [ ] **Step 6: Commit** `git commit -m "feat(security-agent): digest sources and primary-source rule" -- security-agent`

---

### Task 9: "Affects you" and building the digest

**Files:**
- Create: `security-agent/digest/inventory.py`, `security-agent/digest/build.py`, `security-agent/tests/test_digest_build.py`

**Interfaces:**
- Consumes: `Item`, `pre_cluster`, `confirmable`, `Claude`.
- Produces:
  - `collect_inventory(projects_root: Path, apps_dir=Path("/Applications"), run=shell.run) -> set[str]`: lower-cased terms from `macos`, `safari`, `sw_vers -productVersion`, `/Applications/*.app` names, provider names from `config.PROVIDERS`, and dependency names from `package.json` (`dependencies` + `devDependencies`) and `requirements.txt` files up to 3 levels under `projects_root` (skip `node_modules`). Apply `ALIASES = {"next": "next.js", "node": "node.js"}`; drop terms under 4 chars except `aws`; drop `STOP = {"rich", "schedule", "requests", "ephem", "dotenv", "types"}`.
  - `affects(text: str, terms: set[str]) -> list[str]`: whole-word, case-insensitive matches, sorted.
  - `build_digest(conn, items: list[Item], claude: Claude | None, terms: set[str], *, now) -> int` returns the digest id. Steps:
    1. `clusters = pre_cluster(items)`.
    2. If Claude is available: send the clusters as JSON (`cluster_id`, items' `id`, `source`, `title`, first 600 chars of `text`) and ask for JSON `{"groups": [{"item_ids": [...], "title", "summary", "who", "action"}]}`, merging clusters about the same event. Prompt rules: calm and specific, no hype words, only use the given items, no em dashes, `action` is "No action needed" when that's true.
    3. Code enforces: unknown ids dropped; each item used at most once (first group wins); items in no group come back as their own pre-clusters; **each group's sources are rebuilt from its item ids** and the group is kept only if `confirmable`.
    4. If Claude is unavailable or the output doesn't parse: confirmable pre-clusters only, title from the first primary item (else the first item), `summary=None`, `used_ai=0`.
    5. `affects` runs on titles + text of each group's items (never on Claude's text). Order: affects-you first, then KEV, then by number of sources. Store `digests`, `digest_entries` (`sources_json` = list of `{source, url, title}`), and add every fetched item url to `seen_items`.
  - `latest_digest(conn) -> dict | None`.

- [ ] **Step 1: Write the failing tests**

```python
def test_affects_matches_whole_words_and_aliases():
    terms = {"next.js", "chrome", "aws"}
    assert affects("Next.js middleware bypass", terms) == ["next.js"]
    assert affects("next week chrome update", terms) == ["chrome"]

def test_unconfirmed_single_outlet_dropped_even_if_claude_keeps_it(db):
    a = it("outlet", "https://a.com/1", "Rumor"); p = it("primary", "https://msrc.microsoft.com/x", "Patch")
    reply = {"groups": [{"item_ids": [a.id], "title": "Rumor", "summary": "s", "who": "w", "action": "a"},
                        {"item_ids": [p.id], "title": "Patch", "summary": "s", "who": "w", "action": "a"}]}
    did = build_digest(db, [a, p], claude_returning(db, reply), set(), now=NOW)
    titles = [e["title"] for e in latest_digest(db)["entries"]]
    assert titles == ["Patch"]

def test_unknown_ids_dropped_and_sources_rebuilt(db):
    p = it("primary", "https://cisa.gov/x", "KEV add")
    reply = {"groups": [{"item_ids": [p.id, "deadbeef0000"], "title": "T", "summary": "s", "who": "w", "action": "a"}]}
    build_digest(db, [p], claude_returning(db, reply), set(), now=NOW)
    e = latest_digest(db)["entries"][0]
    assert [s["url"] for s in e["sources"]] == ["https://cisa.gov/x"]

def test_malformed_claude_output_falls_back(db):
    p = it("primary", "https://cisa.gov/x", "KEV add")
    build_digest(db, [p], claude_returning_text(db, "not json"), set(), now=NOW)
    d = latest_digest(db)
    assert d["used_ai"] == 0 and d["entries"][0]["title"] == "KEV add" and d["entries"][0]["summary"] is None

def test_affects_you_sorted_first(db):
    x = it("primary", "https://a.gov/1", "Windows bug"); y = it("primary", "https://a.gov/2", "Chrome bug")
    build_digest(db, [x, y], None, {"chrome"}, now=NOW)
    assert latest_digest(db)["entries"][0]["title"] == "Chrome bug"
```

- [ ] **Step 2: Run.** Expected: FAIL. **Step 3: Implement.** **Step 4: Run.** Expected: all pass.
- [ ] **Step 5: Commit** `git commit -m "feat(security-agent): validated digest with affects-you" -- security-agent`

---

### Task 10: Analyst: scan overview and chat with read-only tools

**Files:**
- Modify: `security-agent/analyst.py`
- Create: `security-agent/tests/test_analyst.py`

**Interfaces:**
- Consumes: `Claude`, `latest_scan`, `latest_digest`, `status.service.current`, `digest.sources` KEV/NVD fetch helpers.
- Produces:
  - `scan_overview(conn, claude, scan_id) -> str | None`: sends the scan's findings (key, severity, title, evidence, `is_new`) and asks for at most 150 words ranking what to deal with first, citing finding keys in square brackets. Code removes any `[key]` that isn't in the scan. Stores into `scans.overview`. Job `"scan"`.
  - `TOOLS`: `lookup_cve(cve_id)` (NVD description, CVSS, published, plus `kev`), `get_scan()`, `get_digest()`, `get_status()`. All read-only; none runs a command.
  - `chat(conn, claude, messages: list[dict]) -> str`: system prompt says answer only from tool results and the conversation, say "I don't know from the data I have" otherwise, never ask for secret values, never suggest running anything without explaining it, no em dashes. Tool loop up to 5 rounds; unknown tool names answer `{"error": "unknown tool"}`. Budget denied → `"Today's AI budget is used up. It resets at midnight."`; no API key → `"Add ANTHROPIC_API_KEY to security-agent/.env to use the analyst."`

- [ ] **Step 1: Write the failing tests**

```python
def test_overview_strips_unknown_keys(db):
    sid = run_scan(db, [("ports", lambda: CheckResult("ports", [F("port:5000:Python")]))])
    text = scan_overview(db, claude_text(db, "Fix [port:5000:Python] first, then [made:up]."), sid)
    assert "[port:5000:Python]" in text and "made:up" not in text

def test_chat_runs_tool_and_answers(db):
    fake = FakeClaudeClient([tool_use("get_status", {}), fake_text("All providers are up.")])
    assert chat(db, Claude(fake, Budget(db)), [{"role": "user", "content": "anything down?"}]) == "All providers are up."
    assert fake.calls[1]["messages"][-1]["content"][0]["type"] == "tool_result"

def test_chat_when_budget_spent(db):
    db.execute("INSERT INTO ai_usage VALUES (?,?,?,?,?,?)", (date.today().isoformat(), "chat", "m", 0, 0, 9)); db.commit()
    assert "budget" in chat(db, Claude(FakeClaudeClient([]), Budget(db)), [{"role": "user", "content": "q"}])

def test_no_secret_reaches_claude(db, tmp_path, git_repo):
    (git_repo / ".env").write_text(f"POLY_PRIVATE_KEY={PLANTED}\n")
    sid = run_scan(db, [("secrets", lambda: scan_secrets(tmp_path / "Projects", home=tmp_path))])
    fake = FakeClaudeClient([fake_text("ok"), tool_use("get_scan", {}), fake_text("ok")])
    c = Claude(fake, Budget(db))
    scan_overview(db, c, sid); chat(db, c, [{"role": "user", "content": "what did you find?"}])
    sent = json.dumps(fake.calls, default=str)
    assert PLANTED not in sent and "ab" * 32 not in sent
    assert PLANTED not in "\n".join(str(tuple(r)) for r in db.execute("SELECT * FROM findings"))
```

- [ ] **Step 2: Run.** Expected: FAIL. **Step 3: Implement.** **Step 4: Run.** Expected: all pass.
- [ ] **Step 5: Commit** `git commit -m "feat(security-agent): analyst overview and read-only chat" -- security-agent`

---

### Task 11: Scheduler, main loop and launchd

**Files:**
- Create: `security-agent/scheduler.py`, `security-agent/main.py`, `security-agent/launchd/{com.sergiofruto.security-agent.plist,install.sh,uninstall.sh}`, `security-agent/README.md`, `security-agent/tests/test_scheduler.py`

**Interfaces:**
- Produces:
  - `due(job: str, last_run: datetime | None, now: datetime) -> bool`: `status` every 5 min; `scan` every 7 days; `digest` when `last_run` is None or on an earlier date, and `now.hour >= 7`. Never-run jobs are due (so missed jobs run once on startup).
  - `JOBS: dict[str, Callable[[sqlite3.Connection], None]]` = status → `check_all`; digest → `fetch_all` + `collect_inventory` + `build_digest`; scan → `run_scan(..., on_done=scan_overview)` (a `ScanInProgress` is logged and skipped).
  - `run_due_jobs(conn, now) -> list[str]`: runs due jobs one at a time in the order status, digest, scan, records `job_runs` **after** each job (also after a failure, logged, so a broken job doesn't loop), returns the names run.
  - `main.py`: logging to `agent.log` (same format as analyst-agent), `init_db`, Flask (`web.app.create_app`) in a daemon thread on `config.WEB_HOST:WEB_PORT`, then `while True: run_due_jobs(conn, datetime.now()); time.sleep(30)`.
  - plist: `Label com.sergiofruto.security-agent`, `ProgramArguments [/Users/sergiofruto/anaconda3/bin/python3, main.py]`, `WorkingDirectory` = the agent folder, `RunAtLoad true`, `KeepAlive {SuccessfulExit: false}`, `ProcessType Background`, `LowPriorityIO true`, `Nice 10`, stdout/stderr to `launchd.log`.
  - `install.sh`: copies the plist to `~/Library/LaunchAgents/` and runs `launchctl bootstrap gui/$(id -u) <plist>`; `uninstall.sh` runs `launchctl bootout` and removes it. **Sergio runs `install.sh` himself** (it's a persistent change to his Mac); the executor doesn't.
  - README: setup (`pip install -r requirements.txt`, `.env` keys), run by hand, install at login, dashboard URL `http://127.0.0.1:5007`, what's read and what never leaves the Mac.

- [ ] **Step 1: Write the failing tests**

```python
N = datetime(2026, 10, 24, 8, 0)

def test_due_rules():
    assert due("status", None, N) and due("status", N - timedelta(minutes=6), N)
    assert not due("status", N - timedelta(minutes=2), N)
    assert due("digest", N - timedelta(days=1), N) and not due("digest", N.replace(hour=7, minute=5), N)
    assert not due("digest", N - timedelta(days=1), N.replace(hour=6))
    assert due("scan", N - timedelta(days=8), N) and not due("scan", N - timedelta(days=2), N)

def test_missed_jobs_run_once_then_wait(db, monkeypatch):
    calls = []
    monkeypatch.setattr(scheduler, "JOBS", {k: (lambda c, k=k: calls.append(k)) for k in ("status", "digest", "scan")})
    assert run_due_jobs(db, N) == ["status", "digest", "scan"]
    assert run_due_jobs(db, N + timedelta(minutes=1)) == []

def test_failing_job_is_recorded(db, monkeypatch):
    def boom(c): raise RuntimeError("x")
    monkeypatch.setattr(scheduler, "JOBS", {"status": boom, "digest": lambda c: None, "scan": lambda c: None})
    run_due_jobs(db, N)
    assert "status" not in run_due_jobs(db, N + timedelta(minutes=1))

def test_plist_points_at_main():
    p = plistlib.loads(Path("launchd/com.sergiofruto.security-agent.plist").read_bytes())
    assert p["ProgramArguments"][-1] == "main.py" and p["WorkingDirectory"].endswith("/security-agent")
    assert p["RunAtLoad"] is True and p["KeepAlive"] == {"SuccessfulExit": False}
```

- [ ] **Step 2: Run.** Expected: FAIL. **Step 3: Implement.** **Step 4: Run.** Expected: all pass.
- [ ] **Step 5: Commit** `git commit -m "feat(security-agent): scheduler, main loop, launchd" -- security-agent`

---

### Task 12: Dashboard

**Files:**
- Create: `security-agent/web/{__init__,app}.py`, `security-agent/web/templates/{base,index,scan,digest,status}.html`, `security-agent/web/static/app.js`, `security-agent/tests/test_web.py`

**Interfaces:**
- Consumes: `latest_scan`, `run_scan`, `ScanInProgress`, `SCAN_LOCK`, `latest_digest`, `current`, `history`, `Budget.spent_today`, `chat`.
- Produces `create_app(db_factory=database.connect, claude_factory=Claude.from_config) -> Flask` with:
  - `GET /`: overview: last scan time, counts by severity, worst finding, providers not up, top 3 digest items, today's AI spend vs cap.
  - `GET /scan`: Claude overview (if any), findings grouped by severity with a "new" badge, each with evidence, explanation and a "How to fix it" list; then "Passed" and "Couldn't check". "Scan now" button.
  - `GET /digest`: entries with an "Affects you" tag and matched terms, KEV tag, summary/who/action (or "Summary unavailable" when `summary` is null), and source links.
  - `GET /status`: one row per service: state, incident, last checked, 7-day history bar (168 hourly cells, `no_data` cells grey).
  - `POST /api/scan` → 202 `{"started": true}` and runs `run_scan` in a thread; 409 `{"error": "A scan is already running"}` if `SCAN_LOCK` is held. `GET /api/scan/state` → `{"running": bool, "latest_id": int | None}`.
  - `POST /api/chat` with `{"messages": [...]}` (max 20 messages, each content max 4000 chars, else 400) → `{"reply": str}`.
  - Chat panel in `base.html` on every page; `app.js` keeps the conversation in memory and polls `/api/scan/state` every 3 s while a scan runs.
  - Look: dark, simple, matching the other local agent dashboards; Jinja autoescape stays on (no `|safe` on feed or finding text).

- [ ] **Step 1: Write the failing tests**

```python
def test_pages_render_with_empty_db(client):
    for path in ("/", "/scan", "/digest", "/status"):
        assert client.get(path).status_code == 200

def test_scan_conflict(client):
    SCAN_LOCK.acquire()
    try:
        assert client.post("/api/scan").status_code == 409
    finally:
        SCAN_LOCK.release()

def test_feed_html_is_escaped(client, db):
    insert_digest(db, title="<script>alert(1)</script>")
    body = client.get("/digest").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in body and "&lt;script&gt;" in body

def test_chat_rejects_oversized_input(client):
    assert client.post("/api/chat", json={"messages": [{"role": "user", "content": "x" * 5000}]}).status_code == 400

def test_fix_guide_shown(client, db):
    run_scan(db, [("basics", lambda: CheckResult("basics", [F("basics:firewall", fix=["Open System Settings"])]))])
    assert "Open System Settings" in client.get("/scan").get_data(as_text=True)
```

- [ ] **Step 2: Run.** Expected: FAIL. **Step 3: Implement.** **Step 4: Run.** Expected: all pass.
- [ ] **Step 5: Manual check.** `python main.py`, open `http://127.0.0.1:5007`, click "Scan now", wait for it to finish, open each page. Expected: real findings with fix guides, 10 status rows, a digest (or "no digest yet" before 07:00), no errors in `agent.log`, and `ps` shows only one python process for the agent. Stop it with Ctrl-C.
- [ ] **Step 6: Commit** `git commit -m "feat(security-agent): local dashboard and analyst chat" -- security-agent`

---

### Task 13: Solaris summary data (no card, no commit)

**Files:**
- Modify: `security-agent/database.py` (add view), `solaris/heartbeat.py:13-18`, `solaris/config.py`, `solaris/sync.py`, `solaris/turso/schema.sql`, `solaris/test_heartbeat.py`, `solaris/test_sync.py`

**Interfaces:**
- Produces:
  - In the agent DB, view `solaris_summary` with exactly one row: `id=1`, `last_scan_at`, `high`, `medium`, `low`, `info` (latest done scan), `worst_title` (title of its highest-severity finding), `providers_not_up` (latest row per service with state in `degraded`, `down`), `digest_affecting` (entries in the latest digest with non-empty `affects_json`), `updated_at`.
  - Turso table `security_summary` with the same columns, `id INTEGER PRIMARY KEY`.
  - `heartbeat.AGENTS["security"] = ("security-agent", "agent.log")`; `config.SECURITY_DB` path; `sync.py` adds `"security_summary"` to `UPSERTS` and a block that reads `SELECT * FROM solaris_summary` read-only and pushes it, with the same try/except logging as the others.

- [ ] **Step 1: Write the failing tests**

```python
# security-agent/tests/test_solaris_view.py
def test_summary_view_has_only_counts_and_title(db):
    run_scan(db, [("secrets", lambda: CheckResult("secrets", [F("secrets:x", sev="medium", title="Wallet or private key stored in a plain file", evidence="polymarket-agent/.env: wallet_private_key on line 6")]))])
    row = dict(db.execute("SELECT * FROM solaris_summary").fetchone())
    assert row["medium"] == 1 and row["worst_title"] == "Wallet or private key stored in a plain file"
    assert ".env" not in json.dumps(row)

# solaris/test_sync.py
def test_security_summary_upsert_is_idempotent():
    conn = sqlite3.connect(":memory:")
    for s in schema_statements(): conn.execute(s)
    sql, cols = UPSERTS["security_summary"]
    for high in (2, 0):
        conn.execute(sql, [1, "2026-10-24T08:00:00", high, 1, 0, 3, "t", 0, 1, "2026-10-24T08:00:00"])
    assert conn.execute("SELECT COUNT(*), MAX(high) FROM security_summary").fetchone() == (1, 0)
```

`test_heartbeat.py` already asserts `set(rows) == set(heartbeat.AGENTS)`; it keeps passing with the new entry.

- [ ] **Step 2: Run** both suites (`cd solaris && python -m pytest test_heartbeat.py test_sync.py -q`; the agent's suite). Expected: FAIL on the new tests.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** both suites. Expected: all pass.
- [ ] **Step 5: Do not commit.** `solaris/sync.py` and `solaris/turso/schema.sql` already carry Sergio's uncommitted changes and `heartbeat.py` is untracked. Commit only the `security-agent/` view change; list the Solaris files for Sergio in the final message.

---

### Task 14: Move security news out of analyst-agent

**Files:**
- Delete: `analyst-agent/intelligence/infosec.py`
- Modify: `analyst-agent/main.py` (import on line 25, call on line 69, docstring line 7), `analyst-agent/config.py` (NVD, CISA KEV, AWS and OTX settings), `analyst-agent/reporter.py:58-59` (CVE rows), `analyst-agent/database.py:325-332` (`total_cves`, `kev_cves` stats), `analyst-agent/web-next/app/page.tsx:84-86` (CVE stat), `analyst-agent/synthesis.py` docstring mention.

**Interfaces:**
- Consumes nothing new. The `cves` table stays in the analyst DB (old rows are harmless; no migration). `synthesis.py` already filters signals by type, so no infosec signals just means that section is empty.

- [ ] **Step 1: Check for other users.** `grep -rn "infosec\|total_cves\|kev_cves\|NVD_\|CISA_KEV\|OTX" analyst-agent --include='*.py' --include='*.tsx' --include='*.html'`. Expected: only the places listed above (plus `persona.py`'s flavour text, which stays).
- [ ] **Step 2: Remove** the module, its call and config, and the CVE stats in reporter, database stats, web template and web-next page.
- [ ] **Step 3: Verify.** `cd analyst-agent && python -m py_compile *.py intelligence/*.py web/app.py && python -c "import main, reporter, synthesis, web.app"`, then re-run the grep. Expected: compiles and imports cleanly; grep shows no remaining references. Then run `python main.py` for one intel cycle and stop it. Expected: no errors in `analyst.log`.
- [ ] **Step 4: Commit** `git commit -m "refactor(analyst-agent): hand security news to security-agent" -- analyst-agent`
