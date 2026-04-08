from datetime import datetime, timezone
from typing import Optional

from rich import box
from rich.columns import Columns
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

import database

console = Console()


def _fmt_pnl(value: float) -> Text:
    s = f"${value:+.2f}"
    return Text(s, style="bold green" if value >= 0 else "bold red")


def _fmt_status(status: str) -> Text:
    colours = {"open": "yellow", "won": "green", "lost": "red", "void": "dim"}
    return Text(status.upper(), style=colours.get(status, "white"))


def _fmt_pct(value: Optional[float], neutral: str = "—") -> str:
    if value is None:
        return neutral
    return f"{value:.0%}"


def _fmt_tier(tier: str) -> Text:
    colours = {"premium": "bold green", "professional": "cyan", "amateur": "dim", "unknown": "dim"}
    return Text(tier[:4].upper(), style=colours.get(tier, "white"))


def _stats_panel(stats: dict) -> Panel:
    t = Table.grid(expand=True, padding=(0, 2))
    t.add_column(justify="left")
    t.add_column(justify="right")

    t.add_row("Total bets",    str(stats["total"]))
    t.add_row("Open",          str(stats["open"]))
    t.add_row("Won / Lost",    f"{stats['won']} / {stats['lost']}")
    t.add_row("Win rate",      f"{stats['win_rate']}%")
    t.add_row("Simulated P&L", _fmt_pnl(stats["pnl"]))
    t.add_row("ROI",           f"{stats['roi']:+.1f}%")
    t.add_row("Total wagered", f"${stats['total_wagered']:.0f}")

    return Panel(t, title="[bold]Stats[/bold]", border_style="cyan")


def _open_bets_table(bets: list) -> Table:
    t = Table(
        title="Open Bets",
        box=box.SIMPLE_HEAVY,
        expand=True,
        show_lines=False,
    )
    t.add_column("#",        style="dim",   width=4)
    t.add_column("Match",    style="white", ratio=2)
    t.add_column("Outcome",  style="cyan",  ratio=1)
    t.add_column("Mkt%",     justify="right", width=6)
    t.add_column("True%",    justify="right", width=6)
    t.add_column("Edge",     justify="right", width=7)
    t.add_column("FormA/B",  justify="right", width=9)
    t.add_column("H2H",      justify="right", width=8)
    t.add_column("Tier",     justify="right", width=5)
    t.add_column("Score",    justify="right", width=7)
    t.add_column("Stake",    justify="right", width=8)
    t.add_column("Age",      justify="right", width=10)

    now = datetime.now(timezone.utc)
    for bet in bets:
        ts  = datetime.fromisoformat(bet["timestamp"]).replace(tzinfo=timezone.utc)
        age = now - ts
        h, remainder = divmod(int(age.total_seconds()), 3600)
        m            = remainder // 60
        age_str      = f"{h}h {m}m"

        edge_val = bet["edge"]
        edge_str = f"{edge_val:+.1%}" if edge_val is not None else "—"
        edge_style = "green" if (edge_val or 0) >= 0 else "red"

        true_val = bet["true_prob"]
        true_str = f"{true_val:.1%}" if true_val is not None else "—"

        form_a = bet["form_a"]
        form_b = bet["form_b"]
        form_str = (
            f"{form_a:.0%}/{form_b:.0%}" if form_a is not None and form_b is not None
            else "—/—"
        )

        h2h = bet["h2h_winrate"]
        h2h_n = bet["h2h_sample"] or 0
        h2h_str = f"{h2h:.0%}({h2h_n})" if h2h is not None and h2h_n >= 3 else "—"

        tier = bet["league_tier"] or "unknown"
        tier_text = _fmt_tier(tier)

        t.add_row(
            str(bet["id"]),
            bet["question"][:45],
            bet["outcome"][:18],
            f"{bet['price_at_bet']:.1%}",
            true_str,
            Text(edge_str, style=edge_style),
            form_str,
            h2h_str,
            tier_text,
            f"{bet['score']:.3f}",
            f"${bet['virtual_amount']:.0f}",
            age_str,
        )

    if not bets:
        t.add_row("—", "No open bets yet", "", "", "", "", "", "", "", "", "", "")

    return t


def _recent_results_table(all_bets: list, limit: int = 10) -> Table:
    resolved = [b for b in all_bets if b["status"] in ("won", "lost", "void")]
    resolved = resolved[:limit]

    t = Table(
        title="Recent Results",
        box=box.SIMPLE_HEAVY,
        expand=True,
        show_lines=False,
    )
    t.add_column("#",        style="dim",  width=4)
    t.add_column("Question", style="white", ratio=3)
    t.add_column("Outcome",  style="cyan",  ratio=1)
    t.add_column("Status",   width=8)
    t.add_column("Mkt%",     justify="right", width=6)
    t.add_column("Edge",     justify="right", width=7)
    t.add_column("Result",   justify="right", width=7)

    for bet in resolved:
        edge_val = bet["edge"]
        edge_str = f"{edge_val:+.1%}" if edge_val is not None else "—"
        result_str = (
            f"{bet['result_price']:.4f}" if bet["result_price"] is not None else "—"
        )
        t.add_row(
            str(bet["id"]),
            bet["question"][:60],
            bet["outcome"][:20],
            _fmt_status(bet["status"]),
            f"{bet['price_at_bet']:.1%}",
            edge_str,
            result_str,
        )

    if not resolved:
        t.add_row("—", "No resolved bets yet", "", "", "", "", "")

    return t


def build_layout(
    next_scan_secs: int = 0,
    next_track_secs: int = 0,
    last_scan: Optional[str] = None,
    roster_size: int = 0,
) -> Group:
    stats     = database.get_stats()
    all_bets  = database.get_all_bets()
    open_bets = [b for b in all_bets if b["status"] == "open"]

    now_str   = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    scan_str  = f"Next scan in  {next_scan_secs // 60}m {next_scan_secs % 60:02d}s"
    track_str = f"Next track in {next_track_secs // 60}m {next_track_secs % 60:02d}s"
    last_str  = f"Last scan: {last_scan or 'never'}"
    roster_str = f"Teams indexed: {roster_size}"

    header = Panel(
        f"[bold white]{now_str}[/bold white]   "
        f"[yellow]{scan_str}[/yellow]   "
        f"[cyan]{track_str}[/cyan]   "
        f"[dim]{last_str}[/dim]   "
        f"[dim]{roster_str}[/dim]",
        title="[bold green]Dota 2 Dry-Run Agent[/bold green]",
        border_style="green",
    )

    return Group(
        header,
        Columns([_stats_panel(stats)], expand=True),
        _open_bets_table(open_bets),
        _recent_results_table(all_bets),
    )


def make_live() -> Live:
    return Live(
        build_layout(),
        console=console,
        refresh_per_second=1,
        screen=False,
    )
