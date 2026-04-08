"""
rescore.py — Retrospective LLM re-scoring of open bets with no edge signal.

Usage:
    python rescore.py          # score all open bets missing edge signal
    python rescore.py --all    # score every open bet (even those with a signal)
"""

import argparse
import sqlite3
import config
import database
from signals import compute_edge, _infer_category
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Re-score all open bets, not just edge=N/A")
    args = parser.parse_args()

    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM bets WHERE status='open'"
    if not args.all:
        query += " AND edge_available=0"
    query += " ORDER BY virtual_amount DESC"

    bets = conn.execute(query).fetchall()
    conn.close()

    if not bets:
        console.print("[green]No open bets need re-scoring.[/green]")
        return

    console.print(f"\n[cyan]Re-scoring {len(bets)} open bet(s) with LLM...[/cyan]\n")

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Bet #",      width=6,  justify="right")
    table.add_column("Question",   ratio=4)
    table.add_column("Outcome",    width=6)
    table.add_column("Mkt prob",   width=9,  justify="right")
    table.add_column("Model prob", width=10, justify="right")
    table.add_column("Edge",       width=8,  justify="right")
    table.add_column("Stake",      width=7,  justify="right")
    table.add_column("Assessment", width=14)

    for bet in bets:
        question   = bet["question"]
        outcome    = bet["outcome"]
        mkt_prob   = bet["price_at_bet"]
        stake      = bet["virtual_amount"]
        close_date = None  # not stored; LLM will use its knowledge

        # Flip market prob for "No" bets so we pass the affirmative probability
        effective_mkt_prob = (1.0 - mkt_prob) if outcome.strip().lower() == "no" else mkt_prob

        category = _infer_category(question)
        edge, true_prob = compute_edge(question, category, effective_mkt_prob, close_date)

        # Flip back for "No" bets
        if true_prob is not None and outcome.strip().lower() == "no":
            true_prob = 1.0 - true_prob
            edge = true_prob - mkt_prob

        if true_prob is None:
            model_str  = "[dim]N/A[/dim]"
            edge_str   = "[dim]N/A[/dim]"
            assessment = "[dim]no signal[/dim]"
        else:
            model_str = f"{true_prob:.1%}"
            if edge >= 0.05:
                edge_str   = f"[green]{edge:+.1%}[/green]"
                assessment = "[green]✓ looks good[/green]"
            elif edge >= 0:
                edge_str   = f"[yellow]{edge:+.1%}[/yellow]"
                assessment = "[yellow]~ marginal[/yellow]"
            else:
                edge_str   = f"[red]{edge:+.1%}[/red]"
                assessment = "[red]✗ thesis weak[/red]"

        table.add_row(
            str(bet["id"]),
            question[:65],
            outcome[:6],
            f"{mkt_prob:.1%}",
            model_str,
            edge_str,
            f"${stake:.0f}",
            assessment,
        )

    console.print(table)


if __name__ == "__main__":
    main()
