"""Combine both signals per service, store them, and read history back."""
import sqlite3
from datetime import datetime, timedelta

import config
from status.official import State, fetch_official
from status.probe import probe_dns, probe_https

SEVERITY = {"down": 3, "degraded": 2, "unknown": 1, "up": 0}
OFFLINE = "Offline: no checks possible"


def combine(official: State, probe_ok: bool) -> tuple[State, str | None]:
    if official == "down":
        return "down", None
    if official == "degraded":
        return "degraded", None
    if official == "up":
        return ("up", None) if probe_ok else ("degraded", "Provider says up, but our check failed")
    return ("up", None) if probe_ok else ("down", None)


def _services() -> list[tuple[str, str]]:
    return [(p["id"], p["name"]) for p in config.PROVIDERS] + [(i, n) for i, n, _ in config.DNS_RESOLVERS]


def check_all(conn: sqlite3.Connection, *, fetch=fetch_official, https=probe_https, dns=probe_dns,
              now: datetime | None = None) -> list[dict]:
    now = now or datetime.now()
    rows = []
    for p in config.PROVIDERS:
        official, incident = fetch(p)
        ok, ms = https(p["probe"])
        state, note = combine(official, ok)
        rows.append(dict(service=p["id"], name=p["name"], state=state, official=official,
                         probe_ok=int(ok), probe_ms=ms, incident=incident or note))
    for sid, name, ip in config.DNS_RESOLVERS:
        ok, ms = dns(ip)
        rows.append(dict(service=sid, name=name, state="up" if ok else "down", official=None,
                         probe_ok=int(ok), probe_ms=ms, incident=None))
    if not any(r["probe_ok"] for r in rows):
        # Every check failed at once: this Mac is offline, not every provider
        for r in rows:
            r.update(state="no_data", incident=OFFLINE)
    for r in rows:
        r["checked_at"] = now.isoformat()
        conn.execute("INSERT INTO status_checks VALUES (?,?,?,?,?,?,?)",
                     (r["service"], r["checked_at"], r["state"], r["official"], r["probe_ok"], r["probe_ms"], r["incident"]))
    conn.execute("DELETE FROM status_checks WHERE checked_at < ?", ((now - timedelta(days=8)).isoformat(),))
    conn.commit()
    return rows


def current(conn: sqlite3.Connection) -> list[dict]:
    out = []
    for sid, name in _services():
        r = conn.execute("SELECT * FROM status_checks WHERE service=? ORDER BY checked_at DESC LIMIT 1", (sid,)).fetchone()
        out.append({"service": sid, "name": name, **(dict(r) if r else {"state": "no_data", "checked_at": None, "incident": None})})
    return out


def history(conn: sqlite3.Connection, service: str, now: datetime, days: int = config.STATUS_HISTORY_DAYS,
            bucket_minutes: int = 60) -> list[dict]:
    step = timedelta(minutes=bucket_minutes)
    n = int(timedelta(days=days) / step)
    start = now - n * step
    buckets: list[str | None] = [None] * n
    for checked_at, state in conn.execute(
            "SELECT checked_at, state FROM status_checks WHERE service=? AND checked_at >= ? AND checked_at <= ?",
            (service, start.isoformat(), now.isoformat())):
        i = min(int((datetime.fromisoformat(checked_at) - start) / step), n - 1)
        if state == "no_data":
            continue
        if buckets[i] is None or SEVERITY.get(state, 0) > SEVERITY.get(buckets[i], 0):
            buckets[i] = state
    return [{"start": (start + i * step).isoformat(), "state": s or "no_data"} for i, s in enumerate(buckets)]
