import sys
import os

# Allow imports from parent directory when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from flask import Flask, jsonify, render_template
import database

app = Flask(__name__, template_folder="templates")

@app.template_filter("strftime")
def _strftime(ts):
    try:
        return datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d")
    except Exception:
        return "—"

# Ensure DB tables exist whether Flask starts standalone or via main.py
with app.app_context():
    database.init_db()


@app.route("/")
def index():
    stats    = database.get_stats()
    all_bets = database.get_all_bets()
    bets     = [dict(b) for b in all_bets]

    bt_summary = database.get_latest_backtest()
    bt_matches: list[dict] = []
    if bt_summary:
        bt_matches = [dict(m) for m in database.get_backtest_matches(bt_summary["id"], limit=50)]
    bt_summary = dict(bt_summary) if bt_summary else None

    return render_template("index.html", stats=stats, bets=bets,
                           bt_summary=bt_summary, bt_matches=bt_matches)


@app.route("/api/stats")
def api_stats():
    return jsonify(database.get_stats())


@app.route("/api/bets")
def api_bets():
    bets = [dict(b) for b in database.get_all_bets()]
    return jsonify(bets)


@app.route("/api/backtest")
def api_backtest():
    summary = database.get_latest_backtest()
    if not summary:
        return jsonify({"summary": None, "matches": []})
    s = dict(summary)
    matches = [dict(m) for m in database.get_backtest_matches(s["id"], limit=50)]
    return jsonify({"summary": s, "matches": matches})


def run(host: str = "0.0.0.0", port: int = 5002) -> None:
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    run()
