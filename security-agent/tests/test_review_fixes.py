"""Regression tests for the final whole-branch review findings."""
import os
from datetime import datetime, timedelta

import pytest

import config
import scheduler
from conftest import fake_run
from digest.build import build_digest, latest_digest
from digest.sources import SourcesUnavailable, fetch_all
from status.service import check_all, current
from test_digest_build import claude_returning
from test_digest_validate import fake_get, it
from test_web import make_client

NOW = datetime(2026, 10, 24, 12, 0)


# 1 + 8: offline and stale status never read as "All up"

def test_overview_offline_is_not_all_up(db):
    check_all(db, fetch=lambda p: ("unknown", None), https=lambda u: (False, None),
              dns=lambda ip: (False, None), now=datetime.now())
    html = make_client(db).get("/").get_data(as_text=True)
    assert "All up" not in html and "Offline" in html


def test_stale_status_reads_as_no_data(db):
    check_all(db, fetch=lambda p: ("up", None), https=lambda u: (True, 5), dns=lambda ip: (True, 5),
              now=NOW - timedelta(hours=2))
    rows = current(db, now=NOW)
    assert {r["state"] for r in rows} == {"no_data"} and "Stale" in rows[0]["incident"]
    assert current(db, now=NOW - timedelta(hours=2) + timedelta(minutes=5))[0]["state"] == "up"


def test_overview_stale_is_not_all_up(db):
    check_all(db, fetch=lambda p: ("up", None), https=lambda u: (True, 5), dns=lambda ip: (True, 5),
              now=datetime.now() - timedelta(hours=3))
    assert "All up" not in make_client(db).get("/").get_data(as_text=True)


def test_status_page_shows_date(db):
    check_all(db, fetch=lambda p: ("up", None), https=lambda u: (True, 5), dns=lambda ip: (True, 5),
              now=datetime(2026, 10, 24, 14, 5))
    assert "10-24 14:05" in make_client(db).get("/status").get_data(as_text=True)


def test_summary_updated_at_is_last_status_check(db):
    check_all(db, fetch=lambda p: ("up", None), https=lambda u: (True, 5), dns=lambda ip: (True, 5), now=NOW)
    assert dict(db.execute("SELECT updated_at FROM solaris_summary").fetchone())["updated_at"] == NOW.isoformat()


# 2: a half-working network is recorded as no data, not as outages

def test_mostly_failing_probes_record_no_data(db):
    first = config.PROVIDERS[0]["probe"]
    rows = check_all(db, fetch=lambda p: ("unknown", None), https=lambda u: (u == first, 5),
                     dns=lambda ip: (False, None), now=NOW)
    assert {r["state"] for r in rows} == {"no_data"}


def test_one_failing_provider_on_a_working_network_is_down(db):
    last = config.PROVIDERS[-1]["probe"]
    rows = check_all(db, fetch=lambda p: ("unknown", None), https=lambda u: (u != last, 5),
                     dns=lambda ip: (True, 5), now=NOW)
    assert [r["state"] for r in rows].count("down") == 1


# 3: offline digest raises so the scheduler retries; 10: unconfirmed items stay unseen

def test_every_source_failing_raises(db):
    def boom(url):
        raise OSError("offline")
    with pytest.raises(SourcesUnavailable):
        fetch_all(db, get=fake_get({}), parse=boom, now=NOW)


def test_unconfirmed_items_are_not_marked_seen(db):
    lone = it("outlet", "https://a.com/1", "Only one outlet")
    kev = it("primary", "https://cisa.gov/x", "KEV add")
    build_digest(db, [lone, kev], None, set(), now=NOW)
    seen = {r[0] for r in db.execute("SELECT url FROM seen_items")}
    assert seen == {"https://cisa.gov/x"}


# 4: Claude JSON with the wrong types falls back instead of crashing

@pytest.mark.parametrize("group", [
    {"item_ids": 5},
    {"item_ids": [["x"]]},
    {"item_ids": "ID", "summary": ["x"]},
    {"item_ids": ["ID"], "summary": ["x"], "who": {"a": 1}, "action": 3},
])
def test_mistyped_claude_groups_fall_back(db, group):
    p = it("primary", "https://cisa.gov/x", "KEV add")
    g = {k: ([p.id] if v == ["ID"] else p.id if v == "ID" else v) for k, v in group.items()}
    build_digest(db, [p], claude_returning(db, {"groups": [g]}), set(), now=NOW)
    e = latest_digest(db)["entries"]
    assert len(e) == 1 and e[0]["title"] == "KEV add"
    assert e[0]["summary"] is None or isinstance(e[0]["summary"], str)


def test_failed_build_leaves_no_partial_digest(db, monkeypatch):
    import digest.build as build
    p = it("primary", "https://cisa.gov/x", "KEV add")
    monkeypatch.setattr(build.json, "dumps", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    with pytest.raises(RuntimeError):
        build_digest(db, [p], None, set(), now=NOW)
    db.commit()
    assert latest_digest(db) is None


# Scheduler: failed jobs retry later; every job runs under a watchdog

def test_failed_digest_retries_after_delay(db, monkeypatch):
    calls = []

    def flaky(c):
        calls.append(1)
        raise RuntimeError("offline")
    monkeypatch.setattr(scheduler, "JOBS", {"status": lambda c: None, "digest": flaky, "scan": lambda c: None})
    run_due_jobs = scheduler.run_due_jobs
    run_due_jobs(db, NOW)
    assert "digest" not in run_due_jobs(db, NOW + timedelta(minutes=5))
    assert "digest" in run_due_jobs(db, NOW + scheduler.RETRY_AFTER["digest"])
    assert len(calls) == 2


def test_attempt_recorded_before_job_runs(db, monkeypatch):
    seen = []
    monkeypatch.setattr(scheduler, "JOBS", {
        "status": lambda c: seen.append(c.execute("SELECT job FROM job_attempts").fetchall()),
        "digest": lambda c: None, "scan": lambda c: None})
    scheduler.run_due_jobs(db, NOW)
    assert [r[0] for r in seen[0]] == ["status"]


def test_jobs_run_under_watchdog(db, monkeypatch):
    armed = []

    class FakeFH:
        @staticmethod
        def dump_traceback_later(timeout, exit=False, file=None):
            armed.append((timeout, exit))

        @staticmethod
        def cancel_dump_traceback_later():
            armed.append("cancel")
    monkeypatch.setattr(scheduler, "faulthandler", FakeFH)
    monkeypatch.setattr(scheduler, "JOBS", {k: (lambda c: None) for k in ("status", "digest", "scan")})
    scheduler.run_due_jobs(db, NOW)
    assert armed[0] == (scheduler.WATCHDOG_SECONDS["status"], True) and armed[1] == "cancel"


def test_claude_client_has_short_timeout(db, monkeypatch):
    import anthropic

    from analyst import Claude
    got = {}
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: got.update(kw))
    Claude.from_config(db)
    assert got["timeout"] <= 60 and got["max_retries"] <= 1


# 6: special and unreadable files are skipped visibly, never read as clean

def test_fifo_env_is_skipped_not_read(tmp_path):
    from checks.secrets import scan_secrets
    proj = tmp_path / "Projects" / "p"
    proj.mkdir(parents=True)
    os.mkfifo(proj / ".env")
    res = scan_secrets(tmp_path / "Projects", tmp_path)
    assert any("couldn't check" in s for s in res.skipped) and not res.passed


def test_unreadable_env_is_skipped_not_clean(tmp_path):
    from checks.secrets import scan_secrets
    proj = tmp_path / "Projects" / "p"
    proj.mkdir(parents=True)
    f = proj / ".env"
    f.write_text("API_KEY=" + "Q" * 30 + "\n")
    f.chmod(0)
    try:
        res = scan_secrets(tmp_path / "Projects", tmp_path)
    finally:
        f.chmod(0o600)
    assert any("Projects/p/.env" in s for s in res.skipped) and not res.passed


# 5: listeners owned by other users (sshd, screensharing) are seen via netstat

NETSTAT = """Active Internet connections (including servers)
Proto Recv-Q Send-Q  Local Address          Foreign Address        (state)          rxbytes      txbytes  rhiwat  shiwat          process:pid    state  options           gencnt    flags   flags1 usecnt rtncnt fltrs
tcp4       0      0  *.22                   *.*                    LISTEN                 0            0  131072  131072           launchd:1      00100 00000006 00000000000d170f 00000001 00000800      1      0 000000
tcp4       0      0  127.0.0.1.631          *.*                    LISTEN                 0            0  131072  131072            cupsd:38279  00080 00000006 00000000000d090f 00000001 00000800      1      0 000000
tcp6       0      0  ::1.42050              *.*                    LISTEN                 0            0  131072  131072 OneDrive Sync Se:5117   00100 00000006 00000000000027c7 00000001 00000800      1      0 000000
tcp4       0      0  *.5000                 *.*                    LISTEN                 0            0  131072  131072           Python:4242   00000 00000006 00000000000c8da1 00000000 00000800      1      0 000000
tcp4       0      0  10.0.0.5.51000         1.2.3.4.443            ESTABLISHED            0            0  131072  131072           Google:4954   00000 00000006 00000000000c8da1 00000000 00000800      1      0 000000
"""


def test_parse_netstat_listeners():
    from checks.ports import parse_netstat
    ls = {(l.command, l.address, l.port) for l in parse_netstat(NETSTAT)}
    assert ls == {("launchd", "*", 22), ("cupsd", "127.0.0.1", 631), ("OneDrive Sync Se", "::1", 42050),
                  ("Python", "*", 5000)}


def test_root_owned_listener_is_reported(fixture):
    from checks.ports import check_ports
    res = check_ports(run=fake_run({"lsof": fixture("lsof_listen.txt"), "netstat": NETSTAT}))
    keys = {f.key: f for f in res.findings}
    assert keys["port:22:launchd"].severity == "medium"
    assert "cupsd:631" in keys["ports:local-only"].evidence


def test_netstat_missing_is_skipped(fixture):
    from checks.ports import check_ports
    res = check_ports(run=fake_run({"lsof": fixture("lsof_listen.txt")}))
    assert any("other users" in s for s in res.skipped)


# 7: the dashboard only answers its own host, and POSTs only from its own origin

def test_foreign_host_is_rejected(db):
    c = make_client(db)
    assert c.get("/scan", headers={"Host": "evil.example:5007"}).status_code == 403
    assert c.get("/", headers={"Host": f"127.0.0.1:{config.WEB_PORT}"}).status_code == 200


def test_cross_site_post_is_rejected(db):
    c = make_client(db)
    r = c.post("/api/chat", json={"messages": [{"role": "user", "content": "hi"}]},
               headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    r = c.post("/api/chat", json={"messages": [{"role": "user", "content": "hi"}]},
               headers={"Origin": f"http://localhost:{config.WEB_PORT}"})
    assert r.status_code != 403


# The 40h hang: the web thread's first `import flask` and the status job's first `import requests`
# deadlocked on Python's import locks. Everything both threads use is imported before the thread starts.

def test_main_imports_everything_before_threads_start():
    import subprocess
    import sys
    mods = ["web.app", "status.service", "status.official", "requests", "digest.build", "digest.sources",
            "digest.inventory", "scan", "analyst", "flask", "werkzeug.serving", "dns.resolver", "anthropic"]
    code = "import sys, main; print(','.join(m for m in %r if m not in sys.modules))" % mods
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
    assert out.returncode == 0 and out.stdout.strip() == "", out.stdout + out.stderr
