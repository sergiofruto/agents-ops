import sys
import os

# Allow imports from parent directory when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, render_template
import database

app = Flask(__name__, template_folder="templates")

# Ensure DB tables exist whether Flask starts standalone or via main.py
with app.app_context():
    database.init_db()


@app.route("/")
def index():
    stats    = database.get_stats()
    all_bets = database.get_all_bets()
    bets     = [dict(b) for b in all_bets]
    return render_template("index.html", stats=stats, bets=bets)


@app.route("/api/stats")
def api_stats():
    return jsonify(database.get_stats())


@app.route("/api/bets")
def api_bets():
    bets = [dict(b) for b in database.get_all_bets()]
    return jsonify(bets)


def run(host: str = "0.0.0.0", port: int = 5000) -> None:
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    run()
