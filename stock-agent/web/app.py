"""Flask web dashboard for Silicon Intel."""

from flask import Flask, jsonify, render_template
import database
import config

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/intel")
def intel():
    """Recent intelligence signals (last 24h)."""
    tweets, infosec, semicon = database.get_recent_signals(hours=24)
    return jsonify({
        "tweets":  tweets[:20],
        "infosec": infosec[:20],
        "semicon": [s for s in semicon if s.get("source") != "price-mover"][:20],
        "movers":  [s for s in semicon if s.get("source") == "price-mover"],
    })


@app.route("/api/movers")
def movers():
    """Semiconductor price movers."""
    from intelligence.semicon import fetch_semicon_movers
    return jsonify(fetch_semicon_movers())


# Legacy endpoints kept for Solaris dashboard compatibility
@app.route("/api/stats")
def stats():
    return jsonify({
        "stats":    database.get_stats(),
        "bankroll": database.get_live_bankroll(),
        "exposure": database.get_open_exposure(),
    })


@app.route("/api/positions")
def positions():
    return jsonify(database.get_open_positions())


def run(host: str = "127.0.0.1", port: int = 5005):
    app.run(host=host, port=port, debug=False, use_reloader=False)
