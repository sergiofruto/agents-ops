"""
Rich terminal dashboard for Silicon Intel.
"""

from datetime import datetime
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from rich.markdown import Markdown

import config

console = Console()


def make_live() -> Live:
    return Live(console=console, refresh_per_second=1, screen=True)


def _fmt_secs(secs: int) -> str:
    if secs <= 0:
        return "—"
    h, rem = divmod(secs, 3600)
    m, s   = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def build_layout(state: dict) -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header",  size=3),
        Layout(name="signals", size=7),
        Layout(name="brief",   minimum_size=10),
        Layout(name="footer",  size=3),
    )

    # Header
    layout["header"].update(Panel(
        Text.assemble(
            "  [bold cyan]Silicon Intel[/bold cyan]  ",
            "[dim]Semiconductor Supply Chain + Hardware Security[/dim]",
        ),
        style="bold",
    ))

    # Signal counts
    sig_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 3))
    sig_table.add_column(style="dim")
    sig_table.add_column(style="bold cyan")
    sig_table.add_column(style="dim")
    sig_table.add_column(style="bold")
    sig_table.add_column(style="dim")
    sig_table.add_column(style="bold")

    tweet_count   = state.get("tweet_count", 0)
    infosec_count = state.get("infosec_count", 0)
    semicon_count = state.get("semicon_count", 0)
    mining_count  = state.get("mining_count", 0)
    last_intel    = state.get("last_intel_time", "—")
    last_brief    = state.get("last_brief_time", "—")
    next_intel    = _fmt_secs(state.get("next_intel_secs", 0))
    next_brief    = _fmt_secs(state.get("next_brief_secs", 0))
    seen_tweets   = len(state.get("seen_tweet_ids", set()))

    sig_table.add_row(
        "Tweets (cycle)",   str(tweet_count),
        "Infosec signals",  str(infosec_count),
        "Semicon signals",  str(semicon_count),
    )
    sig_table.add_row(
        "Mining/Lithium",   str(mining_count),
        "Last intel scan",  str(last_intel),
        "Last brief",       str(last_brief),
    )
    sig_table.add_row(
        "Next intel scan",  next_intel,
        "Next brief",       next_brief,
        "Web",              f"http://localhost:{config.WEB_PORT}",
    )

    layout["signals"].update(Panel(sig_table, title="Signal Feed"))

    # Brief
    brief_text = state.get("latest_brief", "Waiting for first brief generation…")
    try:
        brief_renderable = Markdown(brief_text)
    except Exception:
        brief_renderable = Text(brief_text)

    layout["brief"].update(Panel(brief_renderable, title="Latest Intelligence Brief"))

    # Footer
    layout["footer"].update(Panel(
        f"  [dim]Intel: every {config.INTEL_SCAN_INTERVAL_MINUTES}m  "
        f"Brief: every {config.BRIEF_INTERVAL_HOURS}h  "
        f"Web → http://localhost:{config.WEB_PORT}  "
        f"Logs → agent.log[/dim]  "
        f"  [bold]Ctrl-C[/bold] to exit"
    ))

    return layout
