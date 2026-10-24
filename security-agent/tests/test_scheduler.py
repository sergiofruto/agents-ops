import plistlib
from datetime import datetime, timedelta
from pathlib import Path

import scheduler
from scheduler import due, run_due_jobs

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
    assert calls == ["status", "digest", "scan"]


def test_failing_job_is_recorded(db, monkeypatch):
    def boom(c):
        raise RuntimeError("x")
    monkeypatch.setattr(scheduler, "JOBS", {"status": boom, "digest": lambda c: None, "scan": lambda c: None})
    run_due_jobs(db, N)
    assert "status" not in run_due_jobs(db, N + timedelta(minutes=1))


def test_plist_points_at_main():
    p = plistlib.loads(Path("launchd/com.sergiofruto.security-agent.plist").read_bytes())
    assert p["ProgramArguments"][-1] == "main.py" and p["WorkingDirectory"].endswith("/security-agent")
    assert p["RunAtLoad"] is True and p["KeepAlive"] == {"SuccessfulExit": False}
    assert p["ProcessType"] == "Background" and p["LowPriorityIO"] is True
