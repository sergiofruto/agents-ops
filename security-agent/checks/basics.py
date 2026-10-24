"""Built-in macOS protections: are they on, and is the system up to date."""
import re

from checks import shell
from models import CheckResult, Finding

XPROTECT_PLIST = "/Library/Apple/System/Library/CoreServices/XProtect.bundle/Contents/Info.plist"

# (label, command, text that means "on", key, severity, title, why, fix)
TOGGLES = [
    ("FileVault", ["/usr/bin/fdesetup", "status"], "FileVault is On",
     "basics:filevault", "high", "Disk encryption (FileVault) is off",
     "Without FileVault, anyone who gets your Mac can read every file on the disk without your password.",
     ["System Settings > Privacy & Security > FileVault > Turn On.",
      "Store the recovery key somewhere safe outside this Mac."]),
    ("Firewall", ["/usr/libexec/ApplicationFirewall/socketfilterfw", "--getglobalstate"], "enabled",
     "basics:firewall", "medium", "Firewall is off",
     "The firewall blocks unwanted incoming connections, which matters most on public Wi-Fi and for dev servers listening on all interfaces.",
     ["System Settings > Network > Firewall > turn it on.",
      "Under Options, turn on stealth mode.",
      "Or in Terminal: sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on"]),
    ("System Integrity Protection", ["/usr/bin/csrutil", "status"], "enabled",
     "basics:sip", "high", "System Integrity Protection is off",
     "SIP stops malware, even with admin rights, from changing core parts of macOS.",
     ["Restart into Recovery (hold the power button at startup), open Terminal and run: csrutil enable, then restart."]),
    ("Gatekeeper", ["/usr/sbin/spctl", "--status"], "assessments enabled",
     "basics:gatekeeper", "high", "Gatekeeper is off",
     "Gatekeeper blocks apps that aren't signed by an identified developer or notarized by Apple.",
     ["In Terminal: sudo spctl --master-enable",
      "Then check System Settings > Privacy & Security > Allow applications from: App Store & Known Developers."]),
]

_DENIED = re.compile(r"(?i)not permitted|requires root|must be run as root|permission denied")


def _failed(r) -> str | None:
    """Why a command result can't be trusted as an answer, or None if it can."""
    if r.error:
        return r.error
    if _DENIED.search(r.stdout + r.stderr):
        return "permission"
    if not r.ok:
        return "command failed"
    return None


def check_basics(run=shell.run) -> CheckResult:
    res = CheckResult("basics")
    for label, cmd, on_text, key, sev, title, why, fix in TOGGLES:
        r = run(cmd)
        if why_not := _failed(r):
            res.skipped.append(f"{label}: couldn't check ({why_not})")
        elif on_text in r.stdout:
            res.passed.append(f"{label}: on")
        else:
            res.findings.append(Finding(key, "basics", sev, title, r.stdout.strip()[:200], why, list(fix)))

    r = run(["/usr/libexec/PlistBuddy", "-c", "Print CFBundleShortVersionString", XPROTECT_PLIST])
    if why_not := _failed(r):
        res.skipped.append(f"XProtect: couldn't check ({why_not})")
    else:
        res.passed.append(f"XProtect: version {r.stdout.strip()}")

    r = run(["/usr/sbin/softwareupdate", "-l"], timeout=120)
    labels = re.findall(r"^\* Label: (.+)$", r.stdout, re.M)
    if why_not := _failed(r):
        res.skipped.append(f"macOS updates: couldn't check ({why_not})")
    elif labels:
        res.findings.append(Finding(
            "basics:updates", "basics", "medium", "macOS updates pending",
            "; ".join(labels),
            "Updates fix security holes that are often already being exploited by the time they ship.",
            ["System Settings > General > Software Update > Update Now.",
             "Turn on Automatic Updates, including Security Responses and system files."]))
    elif "No new software available" in r.stdout:
        res.passed.append("macOS updates: up to date")
    else:
        res.skipped.append("macOS updates: couldn't check (unexpected output)")
    return res
