import config
from checks import shell


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
