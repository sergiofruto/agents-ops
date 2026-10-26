"""Local dashboard. Reads stored facts; the only things it starts are a scan and a chat reply."""
import threading
from datetime import date, datetime

from flask import Flask, jsonify, render_template, request

import config
import database
from analyst import Claude, chat, scan_overview
from budget import Budget
from digest.build import latest_digest
from scan import SCAN_LOCK, ScanInProgress, latest_scan, run_scan
from status.service import current, history

MAX_MESSAGES = 20
MAX_CHARS = 4000

_local = threading.local()


def _thread_conn():
    """One connection per thread, reused across requests (Flask serves each request on a thread)."""
    if getattr(_local, "conn", None) is None:
        _local.conn = database.connect()
        database.init_db(_local.conn)
    return _local.conn


def _valid_messages(body) -> list[dict] | None:
    msgs = body.get("messages") if isinstance(body, dict) else None
    if not isinstance(msgs, list) or not 0 < len(msgs) <= MAX_MESSAGES:
        return None
    for m in msgs:
        if (not isinstance(m, dict) or m.get("role") not in ("user", "assistant")
                or not isinstance(m.get("content"), str) or not 0 < len(m["content"]) <= MAX_CHARS):
            return None
    return msgs if msgs[-1]["role"] == "user" else None


def create_app(db_factory=_thread_conn, claude_factory=Claude.from_config) -> Flask:
    app = Flask(__name__)

    @app.context_processor
    def _spend():
        conn = db_factory()
        return {"ai_spent": Budget(conn).spent_today(date.today()), "ai_cap": config.AI_DAILY_CAP_USD}

    @app.get("/")
    def index():
        conn = db_factory()
        services = current(conn)
        digest = latest_digest(conn)
        return render_template("index.html", page="overview", scan=latest_scan(conn), services=services,
                               not_up=[s for s in services if s["state"] in ("degraded", "down")],
                               digest=digest, top=(digest["entries"][:3] if digest else []))

    @app.get("/scan")
    def scan_page():
        return render_template("scan.html", page="scan", scan=latest_scan(db_factory()), running=SCAN_LOCK.locked())

    @app.get("/digest")
    def digest_page():
        return render_template("digest.html", page="digest", digest=latest_digest(db_factory()))

    @app.get("/status")
    def status_page():
        conn = db_factory()
        now = datetime.now()
        rows = [{**s, "history": history(conn, s["service"], now)} for s in current(conn)]
        return render_template("status.html", page="status", rows=rows)

    @app.post("/api/scan")
    def start_scan():
        if SCAN_LOCK.locked():
            return jsonify(error="A scan is already running"), 409

        def work():
            conn = db_factory()
            try:
                run_scan(conn, on_done=lambda sid: scan_overview(conn, claude_factory(conn), sid))
            except ScanInProgress:
                pass
        threading.Thread(target=work, daemon=True, name="scan").start()
        return jsonify(started=True), 202

    @app.get("/api/scan/state")
    def scan_state():
        s = latest_scan(db_factory())
        return jsonify(running=SCAN_LOCK.locked(), latest_id=s["id"] if s else None)

    @app.post("/api/chat")
    def chat_api():
        msgs = _valid_messages(request.get_json(silent=True))
        if msgs is None:
            return jsonify(error=f"Send 1 to {MAX_MESSAGES} messages of up to {MAX_CHARS} characters, ending with a question."), 400
        conn = db_factory()
        return jsonify(reply=chat(conn, claude_factory(conn), msgs))

    return app
