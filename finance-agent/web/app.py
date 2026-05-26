"""
Flask web API for finance-agent.
Runs at localhost:5006.

Routes:
  GET  /api/finance/summary          — net worth + goal progress + savings rate
  GET  /api/finance/expenses         — expenses by month (?month=YYYY-MM)
  GET  /api/finance/bills            — all bills + due-soon
  GET  /api/finance/goal             — full goal progress details
  GET  /api/finance/report/latest    — latest monthly strategy report
  POST /api/finance/networth         — add net worth snapshot
  POST /api/finance/bills/<id>/paid  — mark bill as paid
  POST /api/finance/import           — import a statement PDF (path in JSON body)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, jsonify, request
import database
import tracker
import parser as stmt_parser
import config

app = Flask(__name__)


@app.route("/api/finance/summary")
def summary():
    nw      = database.get_latest_net_worth()
    progress = database.get_goal_progress()
    bills   = tracker.get_bills_summary()
    report  = database.get_latest_report()

    return jsonify({
        "net_worth_usd":     nw["total_usd"] if nw else 0,
        "goal_progress_pct": progress["progress_pct"],
        "months_to_goal":    progress["months_invested"],
        "projected_date":    progress["projected_invested"],
        "monthly_fixed":     bills["total_monthly_usd"],
        "due_soon_count":    bills["due_soon_count"],
        "latest_report":     report["month"] if report else None,
        "savings_rate":      report["savings_rate"] if report else None,
        "snapshot_date":     nw["date"] if nw else None,
    })


@app.route("/api/finance/expenses")
def expenses():
    from datetime import date
    month = request.args.get("month", date.today().strftime("%Y-%m"))
    rows  = database.get_expenses_by_month(month)
    summary = database.get_expenses_summary(month)
    return jsonify({
        "month":      month,
        "summary":    summary,
        "total_usd":  sum(summary.values()),
        "count":      len(rows),
        "expenses": [
            {
                "id":          r["id"],
                "date":        r["date"],
                "description": r["description"],
                "amount_ars":  r["amount_ars"],
                "amount_usd":  r["amount_usd"],
                "category":    r["category"],
            }
            for r in rows
        ],
    })


@app.route("/api/finance/bills")
def bills():
    return jsonify(tracker.get_bills_summary())


@app.route("/api/finance/goal")
def goal():
    return jsonify(database.get_goal_progress())


@app.route("/api/finance/report/latest")
def latest_report():
    report = database.get_latest_report()
    if not report:
        return jsonify({"error": "No report yet"}), 404
    return jsonify(dict(report))


@app.route("/api/finance/networth", methods=["POST"])
def add_networth():
    data = request.json or {}
    try:
        total = database.add_net_worth_snapshot(
            wallbit_usd    = float(data.get("wallbit_usd",    0)),
            santander_ars  = float(data.get("santander_ars",  0)),
            santander_usd  = float(data.get("santander_usd",  0)),
            ibkr_usd       = float(data.get("ibkr_usd",       0)),
            polymarket_usd = float(data.get("polymarket_usd", 0)),
            other_usd      = float(data.get("other_usd",      0)),
            notes          = data.get("notes"),
        )
        return jsonify({"total_usd": total, "status": "saved"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/finance/bills/<int:bill_id>/paid", methods=["POST"])
def mark_paid(bill_id: int):
    database.mark_bill_paid(bill_id)
    return jsonify({"status": "marked_paid", "bill_id": bill_id})


@app.route("/api/finance/import", methods=["POST"])
def import_statement():
    data = request.json or {}
    pdf_path = data.get("pdf_path", "")
    if not pdf_path:
        return jsonify({"error": "pdf_path required"}), 400
    imported, skipped = stmt_parser.import_statement(pdf_path)
    return jsonify({"imported": imported, "skipped": skipped})


def run(host: str = "0.0.0.0", port: int = None):
    port = port or config.WEB_PORT
    app.run(host=host, port=port, debug=False, use_reloader=False)
