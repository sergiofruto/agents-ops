"""Why the Mac feels slow: heavy processes, runaway copies, free memory."""
import os
import re
from collections import Counter
from dataclasses import dataclass

import config
from checks import shell
from models import CheckResult, Finding

LOW_MEMORY = 0.10
HIGH_CPU = 80.0


@dataclass(frozen=True)
class Proc:
    pid: int
    cpu: float
    rss_kb: int
    name: str


def _name(argv: list[str]) -> str:
    base = os.path.basename(argv[0])
    if base == "node" or base.startswith("python"):
        script = next((a for a in argv[1:] if not a.startswith("-")), None)
        if script:
            return f"{base} {os.path.basename(script)}"
    return base


def parse_ps(stdout: str) -> list[Proc]:
    out = []
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            out.append(Proc(int(parts[0]), float(parts[1]), int(parts[2]), _name(parts[3:])))
        except ValueError:
            continue
    return out


def parse_vm_stat(stdout: str, memsize: int) -> float:
    m = re.search(r"page size of (\d+) bytes", stdout)
    page = int(m.group(1)) if m else 4096
    pages = {k.strip(): int(v.strip().rstrip(".")) for k, v in re.findall(r"^Pages ([a-z ]+):\s+(\d+)\.?$", stdout, re.M)}
    free = pages.get("free", 0) + pages.get("inactive", 0) + pages.get("speculative", 0)
    return free * page / memsize


def check_performance(run=shell.run, runaway_count: int = config.RUNAWAY_PROCESS_COUNT) -> CheckResult:
    res = CheckResult("performance")
    ps = run(["/bin/ps", "-axo", "pid=,pcpu=,rss=,command="])
    if ps.error or not ps.ok:
        res.skipped.append(f"Processes: couldn't check ({ps.error or 'ps failed'})")
    else:
        procs = parse_ps(ps.stdout)
        counts = Counter(p.name for p in procs)
        runaway = [(n, c) for n, c in counts.items() if c > runaway_count]
        for name, n in runaway:
            res.findings.append(Finding(
                f"perf:runaway:{name}", "performance", "high", "Runaway process copies",
                f"{n} copies of {name}",
                "Hundreds of copies of the same worker eat memory until the Mac freezes. A stale dev-server cache is the usual cause.",
                ["Stop the dev server that started them (Ctrl-C in its terminal).",
                 f"If they keep running, end them: pkill -f \"{name.split(' ')[-1]}\"",
                 "For Next.js projects, delete the project's .next folder before starting again."]))
        if not runaway:
            res.passed.append("Processes: no runaway copies")
        seen = set()
        for p in sorted(procs, key=lambda p: -p.cpu):
            if p.cpu > HIGH_CPU and p.name not in seen:
                seen.add(p.name)
                res.findings.append(Finding(
                    f"perf:cpu:{p.name}", "performance", "low", "Process using a lot of CPU",
                    f"{p.name} (pid {p.pid}) at {p.cpu:.0f}% CPU",
                    "One busy process can make everything else feel slow and drain the battery.",
                    ["Check Activity Monitor > CPU. If you don't recognise it or don't need it now, quit it."]))
        top = sorted(procs, key=lambda p: -p.rss_kb)[:5]
        if top:
            res.findings.append(Finding(
                "perf:top-memory", "performance", "info", "Top memory users",
                ", ".join(f"{p.name} ({p.rss_kb // 1024} MB)" for p in top),
                "The programs holding the most memory right now.",
                ["Quit the ones you aren't using if the Mac feels slow."]))

    vm = run(["/usr/bin/vm_stat"])
    mem = run(["/usr/sbin/sysctl", "-n", "hw.memsize"])
    if vm.error or mem.error or not vm.ok or not mem.stdout.strip().isdigit():
        res.skipped.append("Memory: couldn't check")
    else:
        free = parse_vm_stat(vm.stdout, int(mem.stdout.strip()))
        if free < LOW_MEMORY:
            res.findings.append(Finding(
                "perf:low-memory", "performance", "medium", "Low free memory",
                f"{free:.0%} of memory free",
                "When memory runs out, macOS swaps to disk and everything slows down.",
                ["Open Activity Monitor > Memory and quit the biggest apps you aren't using.",
                 "Restart long-running dev servers and browsers with many tabs."]))
        else:
            res.passed.append(f"Memory: {free:.0%} free")
    return res
