import sqlite3
import os
import sys
import config

DOTA_AGENT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "../dota-agent"))


def _open_ro(path: str) -> sqlite3.Connection | None:
    """Open a SQLite DB read-only; return None if file doesn't exist."""
    if not os.path.exists(path):
        return None
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def get_polymarket_stats() -> dict:
    conn = _open_ro(config.POLYMARKET_DB)
    if conn is None:
        return {"available": False}
    try:
        total = conn.execute("SELECT COUNT(*) FROM bets").fetchone()[0]
        open_ = conn.execute("SELECT COUNT(*) FROM bets WHERE status='open'").fetchone()[0]
        won   = conn.execute("SELECT COUNT(*) FROM bets WHERE status='won'").fetchone()[0]
        lost  = conn.execute("SELECT COUNT(*) FROM bets WHERE status='lost'").fetchone()[0]

        row = conn.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN status='won'  THEN potential_payout - virtual_amount ELSE 0 END), 0)
              - COALESCE(SUM(CASE WHEN status='lost' THEN virtual_amount ELSE 0 END), 0) AS pnl,
                COALESCE(SUM(CASE WHEN status IN ('won','lost') THEN virtual_amount ELSE 0 END), 0) AS wagered
            FROM bets
        """).fetchone()
        pnl, wagered = row["pnl"], row["wagered"]

        resolved = won + lost
        win_rate = round(won / resolved * 100, 1) if resolved else 0.0
        roi      = round(pnl / wagered * 100, 1) if wagered else 0.0

        # Detect live mode: any bet has a non-null order_id
        try:
            live_count = conn.execute(
                "SELECT COUNT(*) FROM bets WHERE order_id IS NOT NULL"
            ).fetchone()[0]
            is_live = live_count > 0
        except sqlite3.OperationalError:
            is_live = False

        recent = conn.execute("""
            SELECT question, outcome, virtual_amount, edge, kelly_stake, status, timestamp
            FROM bets ORDER BY id DESC LIMIT 5
        """).fetchall()
        recent_bets = [dict(r) for r in recent]

    finally:
        conn.close()

    return {
        "available": True,
        "is_live": is_live,
        "total": total,
        "open": open_,
        "won": won,
        "lost": lost,
        "win_rate": win_rate,
        "pnl": round(pnl, 2),
        "roi": roi,
        "recent_bets": recent_bets,
    }


def get_dota_stats() -> dict:
    conn = _open_ro(config.DOTA_DB)
    if conn is None:
        return {"available": False}
    try:
        total = conn.execute("SELECT COUNT(*) FROM bets").fetchone()[0]
        open_ = conn.execute("SELECT COUNT(*) FROM bets WHERE status='open'").fetchone()[0]
        won   = conn.execute("SELECT COUNT(*) FROM bets WHERE status='won'").fetchone()[0]
        lost  = conn.execute("SELECT COUNT(*) FROM bets WHERE status='lost'").fetchone()[0]

        row = conn.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN status='won'  THEN potential_payout - virtual_amount ELSE 0 END), 0)
              - COALESCE(SUM(CASE WHEN status='lost' THEN virtual_amount ELSE 0 END), 0) AS pnl,
                COALESCE(SUM(CASE WHEN status IN ('won','lost') THEN virtual_amount ELSE 0 END), 0) AS wagered
            FROM bets
        """).fetchone()
        pnl, wagered = row["pnl"], row["wagered"]

        resolved = won + lost
        win_rate = round(won / resolved * 100, 1) if resolved else 0.0
        roi      = round(pnl / wagered * 100, 1) if wagered else 0.0

        # Latest backtest accuracy
        model_accuracy = None
        elo_accuracy   = None
        try:
            bs = conn.execute(
                "SELECT model_accuracy, elo_accuracy FROM backtest_summary ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if bs:
                model_accuracy = round(bs["model_accuracy"] * 100, 1)
                elo_accuracy   = round(bs["elo_accuracy"] * 100, 1)
        except sqlite3.OperationalError:
            pass

        recent = conn.execute("""
            SELECT question, outcome, virtual_amount, edge, kelly_stake, status,
                   timestamp, team_a, team_b, tournament
            FROM bets ORDER BY id DESC LIMIT 5
        """).fetchall()
        recent_bets = [dict(r) for r in recent]

    finally:
        conn.close()

    return {
        "available": True,
        "is_live": False,
        "total": total,
        "open": open_,
        "won": won,
        "lost": lost,
        "win_rate": win_rate,
        "pnl": round(pnl, 2),
        "roi": roi,
        "model_accuracy": model_accuracy,
        "elo_accuracy": elo_accuracy,
        "recent_bets": recent_bets,
    }


def get_polymarket_all_bets() -> list:
    conn = _open_ro(config.POLYMARKET_DB)
    if conn is None:
        return []
    try:
        rows = conn.execute("""
            SELECT id, question, outcome, price_at_bet, virtual_amount, potential_payout,
                   score, edge, kelly_stake, status, timestamp, order_id
            FROM bets ORDER BY id DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_dota_all_bets() -> list:
    conn = _open_ro(config.DOTA_DB)
    if conn is None:
        return []
    try:
        rows = conn.execute("""
            SELECT id, question, outcome, team_a, team_b, tournament, league_tier,
                   price_at_bet, virtual_amount, potential_payout, score, edge,
                   true_prob, elo_prob, form_a, form_b, h2h_winrate, h2h_sample,
                   kelly_stake, status, timestamp
            FROM bets ORDER BY id DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_dota_analytics() -> dict:
    conn = _open_ro(config.DOTA_DB)
    backtest_history = []
    if conn is not None:
        try:
            rows = conn.execute("""
                SELECT run_at, days, n_teams, n_matches, model_accuracy, elo_accuracy,
                       model_brier, elo_brier, calibration_factor
                FROM backtest_summary ORDER BY id DESC
            """).fetchall()
            backtest_history = [dict(r) for r in rows]
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()

    team_rankings = []
    roster_available = False
    try:
        if DOTA_AGENT_DIR not in sys.path:
            sys.path.insert(0, DOTA_AGENT_DIR)
        import opendota
        roster = opendota._roster
        if roster:
            team_rankings = sorted(
                [{"name": name, "elo": rating} for name, (_, rating) in roster.items()],
                key=lambda x: x["elo"],
                reverse=True,
            )
            roster_available = True
    except Exception:
        pass

    return {
        "backtest_history": backtest_history,
        "team_rankings": team_rankings,
        "roster_available": roster_available,
    }
