from flask import Flask, render_template, jsonify, request, abort
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import database
import agents
import market_data
import good_morning

app = Flask(__name__)


def _dashboard_data() -> dict:
    poly = agents.get_polymarket_stats()
    dota = agents.get_dota_stats()
    btc  = market_data.get_btc()
    stocks = market_data.get_stocks()
    fng  = market_data.get_fear_greed()
    pipeline = database.pipeline_counts()
    return {
        "polymarket": poly,
        "dota": dota,
        "btc": btc,
        "stocks": stocks,
        "fear_greed": fng,
        "pipeline": pipeline,
    }


@app.route("/")
def index():
    data = _dashboard_data()
    jobs = database.get_all_jobs()
    return render_template("index.html", data=data, jobs=jobs)


@app.route("/api/dashboard")
def api_dashboard():
    return jsonify(_dashboard_data())


# ── Jobs ────────────────────────────────────────────────────────────────────

@app.route("/api/jobs", methods=["GET"])
def api_get_jobs():
    return jsonify(database.get_all_jobs())


@app.route("/api/jobs", methods=["POST"])
def api_add_job():
    body = request.get_json(force=True) or {}
    required = ("company", "role")
    if not all(body.get(k) for k in required):
        abort(400, "company and role are required")
    job_id = database.add_job(
        company=body["company"],
        role=body["role"],
        url=body.get("url"),
        salary_min=body.get("salary_min"),
        salary_max=body.get("salary_max"),
        location=body.get("location", "Remote"),
        status=body.get("status", "bookmarked"),
    )
    return jsonify({"id": job_id}), 201


@app.route("/api/jobs/<int:job_id>", methods=["PATCH"])
def api_update_job(job_id: int):
    body = request.get_json(force=True) or {}
    updated = database.update_job(job_id, **body)
    if not updated:
        abort(400, "No valid fields to update")
    return jsonify({"ok": True})


@app.route("/api/jobs/<int:job_id>", methods=["DELETE"])
def api_delete_job(job_id: int):
    database.delete_job(job_id)
    return jsonify({"ok": True})


@app.route("/api/jobs/<int:job_id>/interviews", methods=["POST"])
def api_add_interview(job_id: int):
    body = request.get_json(force=True) or {}
    if not body.get("stage"):
        abort(400, "stage is required")
    iid = database.add_interview(
        job_id=job_id,
        stage=body["stage"],
        scheduled_at=body.get("scheduled_at"),
        notes=body.get("notes"),
    )
    return jsonify({"id": iid}), 201


@app.route("/api/jobs/<int:job_id>/interviews", methods=["GET"])
def api_get_interviews(job_id: int):
    return jsonify(database.get_interviews(job_id))


@app.route("/api/interviews/<int:interview_id>", methods=["PATCH"])
def api_update_interview(interview_id: int):
    body = request.get_json(force=True) or {}
    updated = database.update_interview(interview_id, **body)
    if not updated:
        abort(400, "No valid fields to update")
    return jsonify({"ok": True})


# ── Good Morning ─────────────────────────────────────────────────────────────

@app.route("/api/good-morning")
def api_good_morning():
    return jsonify(good_morning.morning_report())


@app.route("/api/good-morning/start/<agent>", methods=["POST"])
def api_start_agent(agent: str):
    return jsonify(good_morning.start_agent(agent))


@app.route("/api/good-morning/backtest", methods=["POST"])
def api_run_backtest():
    return jsonify(good_morning.run_dota_backtest())


# ── JSON data routes ──────────────────────────────────────────────────────────

@app.route("/api/polymarket/bets")
def api_polymarket_bets():
    return jsonify(agents.get_polymarket_all_bets())


@app.route("/api/dota/bets")
def api_dota_bets():
    return jsonify(agents.get_dota_all_bets())


@app.route("/api/dota/analytics")
def api_dota_analytics():
    return jsonify(agents.get_dota_analytics())


# ── Detail pages ──────────────────────────────────────────────────────────────

@app.route("/polymarket")
def page_polymarket():
    return render_template("polymarket.html",
        stats=agents.get_polymarket_stats(),
        bets=agents.get_polymarket_all_bets())


@app.route("/dota")
def page_dota():
    return render_template("dota.html",
        stats=agents.get_dota_stats(),
        bets=agents.get_dota_all_bets(),
        analytics=agents.get_dota_analytics())
