"""
Rich terminal dashboard for finance-agent.
"""

from datetime import datetime, date
from typing import Optional

from rich import box
from rich.columns import Columns
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

import database
import tracker

console = Console()


def _progress_bar(current: float, target: float, width: int = 40) -> Text:
    pct = min(current / target, 1.0) if target > 0 else 0
    filled = int(pct * width)
    bar = "█" * filled + "░" * (width - filled)
    color = "green" if pct >= 0.5 else "yellow" if pct >= 0.25 else "red"
    return Text(f"[{bar}] {pct:.1%}", style=color)


def _goal_panel() -> Panel:
    p = database.get_goal_progress()
    nw = database.get_latest_net_worth()

    t = Table.grid(expand=True, padding=(0, 2))
    t.add_column(justify="left", style="dim")
    t.add_column(justify="right")

    t.add_row("Current",        f"[bold green]${p['current']:,.0f}[/bold green]")
    t.add_row("Target",         f"${p['target']:,.0f}")
    t.add_row("Gap",            f"[yellow]${p['gap']:,.0f}[/yellow]")
    t.add_row("Progress",       _progress_bar(p["current"], p["target"]))
    t.add_row("Months (flat)",  f"{p['months_flat']} → {p['projected_flat']}")
    t.add_row("Months (7% ETF)",f"[cyan]{p['months_invested']}[/cyan] → [cyan]{p['projected_invested']}[/cyan]")

    if nw:
        t.add_row("", "")
        t.add_row("Wallbit",    f"${nw['wallbit_usd']:,.0f}")
        t.add_row("Santander",  f"${nw['santander_usd']:,.0f}  (ARS ${nw['santander_ars']:,.0f})")
        t.add_row("IBKR",       f"${nw['ibkr_usd']:,.0f}")
        t.add_row("Polymarket", f"${nw['polymarket_usd']:,.0f}")
        t.add_row("Snapshot",   f"[dim]{nw['date']}[/dim]")

    return Panel(t, title="[bold]Casa con Patio — $100k Goal[/bold]", border_style="green")


def _bills_panel() -> Panel:
    summary   = tracker.get_bills_summary()
    ars_alert = tracker.check_ars_exposure()

    t = Table.grid(expand=True, padding=(0, 2))
    t.add_column(justify="left", style="dim")
    t.add_column(justify="right")

    t.add_row("Monthly fixed", f"[bold]${summary['total_monthly_usd']:,.0f}[/bold]")
    t.add_row("Bills tracked", str(summary["bill_count"]))

    # ARS exposure alert
    if ars_alert:
        t.add_row("", "")
        t.add_row(
            "[bold red]⚠ ARS ALERT[/bold red]",
            f"[red]ARS ${ars_alert['santander_ars']:,.0f}[/red]",
        )
        t.add_row(
            "  USD equiv",
            f"[red]${ars_alert['ars_in_usd']:,.0f} (excess ${ars_alert['excess_usd']:,.0f})[/red]",
        )
        t.add_row(
            "  Action",
            "[yellow]Convert excess → Wallbit[/yellow]",
        )
    else:
        t.add_row("ARS exposure", "[green]OK[/green]")

    due = summary["due_soon"]
    if due:
        t.add_row("", "")
        t.add_row("[bold yellow]Due soon[/bold yellow]", "")
        for bill in due:
            days = tracker._days_until_due(bill["due_day"])
            style = "bold red" if days <= 1 else "yellow"
            t.add_row(
                f"  {bill['name']}",
                f"[{style}]${bill['amount_usd']:.0f} in {days}d[/{style}]",
            )
    else:
        t.add_row("Due soon", "[green]None[/green]")

    return Panel(t, title="[bold]Bills & Alerts[/bold]", border_style="yellow")


def _expenses_panel(month: Optional[str] = None) -> Panel:
    if not month:
        month = date.today().strftime("%Y-%m")

    summary = database.get_expenses_summary(month)
    t = Table.grid(expand=True, padding=(0, 2))
    t.add_column(justify="left", style="dim")
    t.add_column(justify="right")

    total = sum(summary.values())
    t.add_row(f"[bold]{month}[/bold]", f"[bold]${total:,.2f}[/bold]")
    t.add_row("", "")

    for cat, amt in list(summary.items())[:8]:
        pct = (amt / total * 100) if total > 0 else 0
        t.add_row(f"  {cat}", f"${amt:,.0f} ({pct:.0f}%)")

    if not summary:
        t.add_row("", "[dim]No expenses imported yet[/dim]")
        t.add_row("", "[dim]Run: python main.py import <pdf>[/dim]")

    return Panel(t, title="[bold]Expenses This Month[/bold]", border_style="cyan")


def _report_panel() -> Panel:
    report = database.get_latest_report()
    t = Table.grid(expand=True, padding=(0, 1))
    t.add_column(justify="left")

    if report:
        t.add_row(f"[bold]{report['month']}[/bold]  savings rate: [green]{report['savings_rate']:.0%}[/green]")
        t.add_row("")
        # Word-wrap strategy text at ~60 chars
        text = report["strategy_text"] or ""
        words = text.split()
        line, lines = [], []
        for w in words:
            line.append(w)
            if len(" ".join(line)) > 60:
                lines.append(" ".join(line[:-1]))
                line = [w]
        if line:
            lines.append(" ".join(line))
        for l in lines[:8]:
            t.add_row(f"[dim]{l}[/dim]")
    else:
        t.add_row("[dim]No monthly report yet.[/dim]")
        t.add_row("[dim]Run on the 1st of the month.[/dim]")

    return Panel(t, title="[bold]Latest Strategy Report[/bold]", border_style="magenta")


def build_layout(last_update: Optional[str] = None) -> Group:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updated = f"Updated: {last_update or now_str}"

    header = Panel(
        f"[bold white]{now_str}[/bold white]   [dim]{updated}[/dim]",
        title="[bold green]Finance Agent — Personal Advisor[/bold green]",
        border_style="green",
    )

    top_row = Columns([_goal_panel(), _bills_panel()], expand=True)
    bot_row = Columns([_expenses_panel(), _report_panel()], expand=True)

    return Group(header, top_row, bot_row)


def make_live() -> Live:
    return Live(
        build_layout(),
        console=console,
        refresh_per_second=1,
        screen=False,
    )
