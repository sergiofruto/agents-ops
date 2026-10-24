"""Which programs listen for network connections, and who can reach them."""
from dataclasses import dataclass

from checks import shell
from models import CheckResult, Finding

LOCAL_ADDRESSES = {"127.0.0.1", "[::1]", "localhost"}
# Apple's own daemons that listen on the network by design (lsof truncates names to 9 chars)
APPLE_DAEMONS = {"rapportd", "ControlCe", "sharingd", "AirPlayXP", "identitys"}


@dataclass(frozen=True)
class Listener:
    command: str
    pid: int
    address: str
    port: int


def parse_lsof(stdout: str) -> list[Listener]:
    out = []
    for line in stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 10 or parts[-1] != "(LISTEN)":
            continue
        address, _, port = parts[-2].rpartition(":")
        if not port.isdigit():
            continue
        out.append(Listener(parts[0], int(parts[1]), address, int(port)))
    return out


def is_local(address: str) -> bool:
    return address in LOCAL_ADDRESSES


def check_ports(run=shell.run) -> CheckResult:
    res = CheckResult("ports")
    r = run(["/usr/sbin/lsof", "-nP", "-iTCP", "-sTCP:LISTEN"])
    if r.error:
        res.skipped.append(f"Open ports: couldn't check ({r.error})")
        return res
    seen: set[tuple[str, int]] = set()
    local: list[str] = []
    for ln in parse_lsof(r.stdout):
        if (ln.command, ln.port) in seen:
            continue
        seen.add((ln.command, ln.port))
        if is_local(ln.address):
            local.append(f"{ln.command}:{ln.port}")
            continue
        apple = ln.command in APPLE_DAEMONS
        res.findings.append(Finding(
            f"port:{ln.port}:{ln.command}", "ports", "info" if apple else "medium",
            "macOS service reachable from the network" if apple else "Program reachable from the network",
            f"{ln.command} (pid {ln.pid}) listens on {ln.address}:{ln.port}",
            ("A built-in macOS service (AirDrop, Handoff, AirPlay and similar). Expected, but it is only safe on networks you trust."
             if apple else
             "Any device on the same network (a café or office Wi-Fi, for example) can try to connect to this program."),
            (["If you don't use AirDrop or AirPlay Receiver, turn them off in System Settings > General > AirDrop & Handoff.",
              "Turn on the firewall's stealth mode: System Settings > Network > Firewall > Options."]
             if apple else
             ["If you don't need it, stop the program.",
              "If it's a dev server, bind it to 127.0.0.1 instead of all interfaces (for Flask: app.run(host=\"127.0.0.1\")).",
              "Turn on the firewall and stealth mode: System Settings > Network > Firewall."])))
    if local:
        res.findings.append(Finding(
            "ports:local-only", "ports", "info", "Programs listening on this Mac only",
            ", ".join(local),
            "These only accept connections from this Mac, so other devices can't reach them.",
            ["Nothing to do."]))
    if not any(f.severity == "medium" for f in res.findings):
        res.passed.append("Open ports: nothing unexpected reachable from the network")
    return res
