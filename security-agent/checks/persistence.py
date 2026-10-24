"""Signs of malware: what starts itself in the background, extensions, profiles."""
import plistlib
from pathlib import Path

from checks import shell
from checks.basics import _failed
from models import CheckResult, Finding

DEFAULT_DIRS = [Path.home() / "Library/LaunchAgents", Path("/Library/LaunchAgents"), Path("/Library/LaunchDaemons")]


def _binary(plist: dict) -> str | None:
    if plist.get("Program"):
        return plist["Program"]
    args = plist.get("ProgramArguments") or []
    return args[0] if args else None


def _launch_items(res: CheckResult, run, dirs: list[Path]) -> None:
    checked = 0
    for d in dirs:
        if not d.is_dir():
            continue
        for path in sorted(d.glob("*.plist")):
            try:
                plist = plistlib.loads(path.read_bytes())
            except Exception:
                res.skipped.append(f"Background item {path.name}: couldn't read")
                continue
            label = plist.get("Label") or path.stem
            binary = _binary(plist)
            if not binary:
                continue
            checked += 1
            missing = not Path(binary).exists()
            r = None if missing else run(["/usr/bin/codesign", "--verify", "--strict", binary])
            if missing or not r.ok:
                problem = "points at a program that doesn't exist" if missing else (r.stderr.strip() or r.error or "invalid signature")
                res.findings.append(Finding(
                    f"malware:launch:{label}", "malware", "medium", "Background item without a valid signature",
                    f"{path}: {binary} ({problem[:120]})",
                    "Programs that start themselves in the background without a valid developer signature are a common way malware stays on a Mac. Many are harmless leftovers from uninstalled apps.",
                    ["If you recognise the app, update or reinstall it from the developer.",
                     "If you don't, unload it: launchctl bootout gui/$(id -u) " + str(path),
                     "Then move the .plist to the Trash, and check System Settings > General > Login Items & Extensions."]))
    if checked and not any(f.key.startswith("malware:launch:") for f in res.findings):
        res.passed.append(f"Background items: all {checked} signed")


def check_persistence(run=shell.run, dirs: list[Path] | None = None) -> CheckResult:
    res = CheckResult("malware")
    _launch_items(res, run, DEFAULT_DIRS if dirs is None else dirs)

    r = run(["/usr/bin/systemextensionsctl", "list"])
    if why := _failed(r):
        res.skipped.append(f"System extensions: couldn't check ({why})")
    elif r.stdout.strip().startswith("0 extension"):
        res.passed.append("System extensions: none installed")
    else:
        names = [line.split("\t")[3] for line in r.stdout.splitlines()
                 if line.startswith("*") and len(line.split("\t")) > 3]
        res.findings.append(Finding(
            "malware:extensions", "malware", "info", "System extensions installed",
            ", ".join(names) or r.stdout.strip().splitlines()[0],
            "System extensions run with deep access (network filters, drivers). Each should belong to an app you installed on purpose.",
            ["Review them in System Settings > General > Login Items & Extensions, and remove any you don't recognise."]))

    r = run(["/usr/bin/profiles", "list"])
    if why := _failed(r):
        res.skipped.append(f"Configuration profiles: couldn't check ({why})")
    elif "no configuration profiles" in r.stdout.lower():
        res.passed.append("Configuration profiles: none installed")
    else:
        ids = [line.split("profileIdentifier:")[-1].strip() for line in r.stdout.splitlines() if "profileIdentifier" in line]
        res.findings.append(Finding(
            "malware:profiles", "malware", "low", "Configuration profiles installed",
            ", ".join(ids) or r.stdout.strip()[:200],
            "Profiles can change network, proxy and certificate settings. Adware sometimes installs one; a work or school device may have one on purpose.",
            ["Review them in System Settings > General > Device Management, and remove any you don't recognise."]))
    return res
