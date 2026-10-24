import time

import pytest

from conftest import F
from models import CheckResult
from scan import SCAN_LOCK, ScanInProgress, latest_scan, run_scan


def test_new_since_last_scan(db):
    a, b = F("port:1:x"), F("port:2:y")
    run_scan(db, [("ports", lambda: CheckResult("ports", [a]))])
    run_scan(db, [("ports", lambda: CheckResult("ports", [a, b]))])
    new = {f["key"]: f["is_new"] for f in latest_scan(db)["findings"]}
    assert new == {"port:1:x": 0, "port:2:y": 1}


def test_first_scan_marks_everything_new(db):
    run_scan(db, [("ports", lambda: CheckResult("ports", [F("port:1:x")]))])
    assert latest_scan(db)["findings"][0]["is_new"] == 1


def test_check_crash_is_skipped_not_fatal(db):
    def boom():
        raise PermissionError("nope")
    sid = run_scan(db, [("basics", boom), ("ports", lambda: CheckResult("ports", passed=["ok"]))])
    s = latest_scan(db)
    assert s["id"] == sid and "basics: couldn't check (PermissionError)" in s["skipped"] and "ok" in s["passed"]


def test_concurrent_scan_refused(db):
    SCAN_LOCK.acquire()
    try:
        with pytest.raises(ScanInProgress):
            run_scan(db, [])
    finally:
        SCAN_LOCK.release()


def test_checks_run_sequentially(db):
    active = []

    def slow(name):
        def f():
            active.append(name)
            assert len(active) == 1
            time.sleep(0.01)
            active.pop()
            return CheckResult(name)
        return f
    run_scan(db, [("a", slow("a")), ("b", slow("b"))])


def test_latest_scan_sorted_and_counted(db):
    run_scan(db, [("x", lambda: CheckResult("x", [F("a", sev="info"), F("b", sev="high"), F("c", sev="medium")]))])
    s = latest_scan(db)
    assert [f["severity"] for f in s["findings"]] == ["high", "medium", "info"]
    assert s["counts"] == {"high": 1, "medium": 1, "low": 0, "info": 1}
    assert s["findings"][0]["fix"] == ["f"]


def test_on_done_called(db):
    seen = []
    sid = run_scan(db, [], on_done=seen.append)
    assert seen == [sid]


def test_no_scan_yet(db):
    assert latest_scan(db) is None
