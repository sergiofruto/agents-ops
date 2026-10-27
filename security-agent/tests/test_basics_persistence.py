import plistlib

from checks.basics import check_basics
from checks.persistence import check_persistence
from conftest import fake_run
from models import CmdResult

BASICS_ALL_ON = {
    "fdesetup": "FileVault is On.\n",
    "socketfilterfw": "Firewall is enabled. (State = 1)\n",
    "csrutil": "System Integrity Protection status: enabled.\n",
    "spctl": "assessments enabled\n",
    "PlistBuddy": "5368\n",
    "softwareupdate": "Software Update Tool\n\nFinding available software\nNo new software available.\n",
}
NO_PROFILES = "There are no configuration profiles installed for user 'u'\n"


def test_all_on_passes():
    res = check_basics(run=fake_run(BASICS_ALL_ON))
    assert res.findings == [] and len(res.passed) == 6


def test_filevault_off_is_high():
    res = check_basics(run=fake_run({**BASICS_ALL_ON, "fdesetup": "FileVault is Off."}))
    assert [(f.key, f.severity) for f in res.findings] == [("basics:filevault", "high")]


def test_firewall_off_is_medium():
    res = check_basics(run=fake_run({**BASICS_ALL_ON, "socketfilterfw": "Firewall is disabled. (State = 0)"}))
    assert [(f.key, f.severity) for f in res.findings] == [("basics:firewall", "medium")]


def test_pending_updates_listed():
    out = "Software Update found the following:\n* Label: macOS Tahoe 26.1-25B78\n"
    res = check_basics(run=fake_run({**BASICS_ALL_ON, "softwareupdate": out}))
    assert "macOS Tahoe 26.1" in next(f for f in res.findings if f.key == "basics:updates").evidence


def test_permission_error_becomes_skipped():
    res = check_basics(run=fake_run({**BASICS_ALL_ON, "fdesetup": CmdResult(False, "", "Operation not permitted", None)}))
    assert any("FileVault" in s for s in res.skipped)
    assert not any("FileVault" in p for p in res.passed) and res.findings == []


def test_unsigned_launch_agent_is_medium(tmp_path):
    plist = tmp_path / "com.evil.agent.plist"
    plist.write_bytes(plistlib.dumps({"Label": "com.evil.agent", "ProgramArguments": ["/tmp/evil"]}))
    res = check_persistence(run=fake_run({"codesign": CmdResult(False, "", "not signed at all", None),
                                          "systemextensionsctl": "0 extension(s)", "profiles": NO_PROFILES}),
                            dirs=[tmp_path])
    assert any(f.key == "malware:launch:com.evil.agent" and f.severity == "medium" for f in res.findings)


def test_signed_launch_agent_passes_and_no_profiles(tmp_path):
    (tmp_path / "com.good.plist").write_bytes(plistlib.dumps({"Label": "com.good", "Program": "/bin/ls"}))
    res = check_persistence(run=fake_run({"codesign": "", "systemextensionsctl": "0 extension(s)", "profiles": NO_PROFILES}),
                            dirs=[tmp_path])
    assert not [f for f in res.findings if f.severity != "info"]
    assert any("Configuration profiles" in p for p in res.passed)


def test_installed_profile_is_low(tmp_path):
    out = "There are 1 configuration profiles installed for user 'u'\n_computerlevel[1] attribute: profileIdentifier: com.corp.mdm\n"
    res = check_persistence(run=fake_run({"systemextensionsctl": "0 extension(s)", "profiles": out}), dirs=[tmp_path])
    assert any(f.key == "malware:profiles" and f.severity == "low" for f in res.findings)
