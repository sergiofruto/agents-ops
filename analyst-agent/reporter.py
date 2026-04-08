"""
reporter.py — Rich terminal dashboard for The Analyst
"""

from __future__ import annotations

from datetime import datetime
from contextlib import contextmanager

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

import database
import persona

console = Console()

_THREAT_COLORS = {
    "CRITICAL": "bold red",
    "HIGH":     "red",
    "MEDIUM":   "yellow",
    "LOW":      "green",
    "INFO":     "dim",
    "UNKNOWN":  "dim",
}

_SEVERITY_COLORS = _THREAT_COLORS


def _threat_badge(level: str) -> Text:
    color = _THREAT_COLORS.get(level, "white")
    return Text(f" {level} ", style=f"bold {color} on black")


def _header() -> Panel:
    title = Text()
    title.append("THE ANALYST", style="bold cyan")
    title.append("  |  Hermetic Intelligence System", style="dim")
    title.append(f"  |  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", style="dim")
    return Panel(title, style="cyan", box=box.HORIZONTALS)


def _stats_panel() -> Panel:
    stats = database.get_stats()
    cosmic = database.get_latest_cosmic()

    grid = Table.grid(padding=(0, 2))
    grid.add_column("label", style="dim")
    grid.add_column("value", style="bold white")

    grid.add_row("Total signals",  str(stats["total_signals"]))
    grid.add_row("High/Critical",  str(stats["high_signals"]))
    grid.add_row("CVEs tracked",   str(stats["total_cves"]))
    grid.add_row("CISA KEV",       str(stats["kev_cves"]))
    grid.add_row("Briefs issued",  str(stats["total_briefs"]))

    if cosmic:
        grid.add_row("Moon phase", cosmic["moon_phase"])
        retro = "YES" if cosmic["mercury_retrograde"] else "No"
        grid.add_row("Hg retrograde", retro)

    return Panel(grid, title="[bold]Status[/bold]", border_style="blue", box=box.ROUNDED)


def _signals_table() -> Panel:
    signals = database.get_unused_signals(limit=12)
    t = Table(box=box.SIMPLE, show_header=True, header_style="bold dim")
    t.add_column("Severity", width=9)
    t.add_column("Source",   width=8)
    t.add_column("Title",    no_wrap=False)

    for s in signals:
        color = _SEVERITY_COLORS.get(s["severity"], "white")
        t.add_row(
            Text(s["severity"], style=color),
            Text(s["source"],   style="dim"),
            s["title"][:80],
        )

    title_txt = f"[bold]Pending Signals[/bold] ({len(signals)})"
    return Panel(t, title=title_txt, border_style="blue", box=box.ROUNDED)


def _briefs_panel() -> Panel:
    briefs = database.get_recent_briefs(limit=5)
    t = Table(box=box.SIMPLE, show_header=True, header_style="bold dim")
    t.add_column("ID",    width=4)
    t.add_column("Level", width=9)
    t.add_column("Time",  width=17)
    t.add_column("Title", no_wrap=False)

    for b in briefs:
        color = _THREAT_COLORS.get(b["threat_level"], "white")
        t.add_row(
            str(b["id"]),
            Text(b["threat_level"], style=color),
            b["created_at"][:16],
            b["title"][:70],
        )

    return Panel(t, title="[bold]Recent Briefs[/bold]", border_style="magenta", box=box.ROUNDED)


def _latest_brief_panel() -> Panel:
    briefs = database.get_recent_briefs(limit=1)
    if not briefs:
        return Panel(
            Text(
                '"The Lips of Wisdom are closed, except to the ears of Understanding."\n'
                "  — The Kybalion\n\nAwaiting first scan cycle…",
                style="dim italic",
            ),
            title="[bold]Latest Brief[/bold]",
            border_style="magenta",
            box=box.ROUNDED,
        )

    b = briefs[0]
    content = Text()
    content.append(f"{b['opening_quote']}\n\n", style="italic dim")
    content.append("SYNTHESIS\n", style="bold")
    # Show first 400 chars of synthesis
    synth = b["synthesis"][:500].strip()
    content.append(synth + ("…" if len(b["synthesis"]) > 500 else ""), style="white")

    color  = _THREAT_COLORS.get(b["threat_level"], "white")
    header = Text()
    header.append(f"[{b['threat_level']}]  ", style=color)
    header.append(b["title"], style="bold")

    return Panel(
        content,
        title=header,
        border_style="magenta",
        box=box.ROUNDED,
    )


def _countdown_panel(
    next_intel_secs: int,
    next_cosmic_secs: int,
    next_brief_secs: int,
) -> Panel:
    def fmt(s: int) -> str:
        m, sec = divmod(s, 60)
        return f"{m:02d}:{sec:02d}"

    grid = Table.grid(padding=(0, 3))
    grid.add_column("label", style="dim")
    grid.add_column("value", style="bold cyan")
    grid.add_row("Next intel scan",  fmt(next_intel_secs))
    grid.add_row("Next cosmic scan", fmt(next_cosmic_secs))
    grid.add_row("Next brief",       fmt(next_brief_secs))

    return Panel(grid, title="[bold]Timers[/bold]", border_style="dim", box=box.ROUNDED)


def build_layout(
    next_intel_secs:  int = 0,
    next_cosmic_secs: int = 0,
    next_brief_secs:  int = 0,
) -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header",  size=3),
        Layout(name="body"),
        Layout(name="footer",  size=6),
    )
    layout["body"].split_row(
        Layout(name="left",  ratio=1),
        Layout(name="right", ratio=2),
    )
    layout["left"].split_column(
        Layout(name="stats",     size=14),
        Layout(name="countdown", size=7),
    )
    layout["right"].split_column(
        Layout(name="signals",  ratio=1),
        Layout(name="brief",    ratio=1),
    )

    layout["header"].update(_header())
    layout["stats"].update(_stats_panel())
    layout["countdown"].update(_countdown_panel(next_intel_secs, next_cosmic_secs, next_brief_secs))
    layout["signals"].update(_signals_table())
    layout["brief"].update(_latest_brief_panel())
    layout["footer"].update(_briefs_panel())

    return layout


@contextmanager
def make_live():
    with Live(
        build_layout(),
        console=console,
        refresh_per_second=1,
        screen=True,
    ) as live:
        yield live
