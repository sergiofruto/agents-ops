"""Secrets lying around in plain files: where they are and how exposed.

Values never leave checks.redact; findings carry kind, path and line only.
"""
import os
import stat
from pathlib import Path

from checks import shell
from checks.redact import SecretHit, find_secrets
from models import CheckResult, Finding, Severity

SKIP_DIRS = {"node_modules", ".git", ".next", ".venv", "venv", "__pycache__", "dist", "build"}
MAX_BYTES = 1_000_000
MAX_HISTORY_BYTES = 20_000_000
KEY_KINDS = {"wallet_private_key", "private_key_block"}

_REASONS = {
    "committed": (
        "Secret committed to git",
        "Anyone with a copy of this repository, now or later, can read the secret, even after you delete the file.",
        ["Rotate the secret now: create a new key with the provider and revoke the old one.",
         "Remove the file from git: git rm --cached <file>, then add it to .gitignore.",
         "If the repository was ever pushed, also remove it from history with git filter-repo, or treat the old key as public forever."],
    ),
    "readable": (
        "Secret file readable by other users",
        "Other accounts and processes running as other users on this Mac can read this file.",
        ["Restrict the file to your user: chmod 600 <file>"],
    ),
    "wallet": (
        "Wallet or private key stored in a plain file",
        "A private key gives full control of whatever it signs for. Any malware or leaked backup that reads this file can drain the wallet or impersonate you.",
        ["Keep only small amounts in a wallet whose key sits in a file.",
         "Move the key to the macOS Keychain: security add-generic-password -a $USER -s <name> -w, and read it at startup with security find-generic-password -s <name> -w.",
         "For larger amounts, use a hardware wallet."],
    ),
    "shell": (
        "Secret in shell history",
        "Shell history is a plain file that is easy to copy, sync or paste by mistake.",
        ["Rotate the secret.",
         "Delete the lines from the history file in a text editor, then open a new terminal.",
         "Add setopt HIST_IGNORE_SPACE to ~/.zshrc and start commands that hold secrets with a space."],
    ),
    "outside": (
        "Credentials stored outside a project",
        "Long-lived credentials in your home folder are a common target for malware and supply-chain attacks.",
        ["Prefer short-lived credentials (for AWS: aws sso login) over static keys.",
         "Rotate any key you no longer recognise, and chmod 600 the file."],
    ),
}


def _reason(hits: list[SecretHit], *, tracked: bool, in_history: bool, other_readable: bool,
            in_project: bool, shell_history: bool) -> str | None:
    if tracked or in_history:
        return "committed"
    if other_readable:
        return "readable"
    if any(h.kind in KEY_KINDS for h in hits):
        return "wallet"
    if shell_history:
        return "shell"
    if not in_project:
        return "outside"
    return None


def classify(hits: list[SecretHit], *, tracked: bool, in_history: bool, other_readable: bool,
             in_project: bool, shell_history: bool) -> Severity:
    reason = _reason(hits, tracked=tracked, in_history=in_history, other_readable=other_readable,
                     in_project=in_project, shell_history=shell_history)
    return {"committed": "high", None: "info"}.get(reason, "medium")


def _is_candidate(name: str) -> bool:
    return (name == ".env" or name.startswith(".env.") or name.endswith(".env")
            or name.endswith((".pem", ".key")) or name.startswith("credentials"))


def _read(path: Path, limit: int, lenient: bool = False) -> str | None:
    try:
        if path.stat().st_size > limit:
            return None
        return path.read_text(errors="replace" if lenient else "strict")
    except (OSError, UnicodeDecodeError):
        return None


def _other_readable(path: Path) -> bool:
    try:
        return bool(path.stat().st_mode & (stat.S_IRGRP | stat.S_IROTH))
    except OSError:
        return False


class _Git:
    """Tracked / in-history lookups, with the repo root cached per directory."""

    def __init__(self):
        self._roots: dict[str, str | None] = {}

    def _root(self, d: str) -> str | None:
        if d not in self._roots:
            r = shell.run(["git", "-C", d, "rev-parse", "--show-toplevel"])
            self._roots[d] = r.stdout.strip() if r.ok else None
        return self._roots[d]

    def state(self, path: Path) -> tuple[bool, bool]:
        root = self._root(str(path.parent))
        if not root:
            return False, False
        rel = os.path.relpath(path, root)
        tracked = shell.run(["git", "-C", root, "ls-files", "--error-unmatch", "--", rel]).ok
        hist = shell.run(["git", "-C", root, "log", "--all", "--format=%H", "-1", "--", rel])
        return tracked, bool(hist.ok and hist.stdout.strip())


def _evidence(rel: str, hits: list[SecretHit]) -> str:
    return f"{rel}: " + "; ".join(f"{h.kind} on line {h.line}" for h in hits)


def _finding(reason: str, rel: str, hits: list[SecretHit], severity: Severity) -> Finding:
    title, why, fix = _REASONS[reason]
    return Finding(f"secrets:{rel}", "secrets", severity, title, _evidence(rel, hits), why, list(fix))


def scan_secrets(projects_root: Path, home: Path) -> CheckResult:
    res = CheckResult("secrets")
    git = _Git()
    expected: list[str] = []

    def consider(path: Path, *, in_project: bool, shell_history: bool = False):
        text = _read(path, MAX_HISTORY_BYTES if shell_history else MAX_BYTES, lenient=shell_history)
        if not text:
            return
        hits = find_secrets(text)
        if not hits:
            return
        tracked, in_history = git.state(path) if in_project else (False, False)
        flags = dict(tracked=tracked, in_history=in_history, other_readable=_other_readable(path),
                     in_project=in_project, shell_history=shell_history)
        rel = os.path.relpath(path, home)
        reason = _reason(hits, **flags)
        if reason is None:
            expected.append(rel)
        else:
            res.findings.append(_finding(reason, rel, hits, classify(hits, **flags)))

    if projects_root.is_dir():
        for dirpath, dirnames, filenames in os.walk(projects_root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in sorted(filenames):
                if _is_candidate(name):
                    consider(Path(dirpath) / name, in_project=True)
    else:
        res.skipped.append(f"Projects folder: couldn't check ({projects_root} not found)")

    aws = home / ".aws" / "credentials"
    if aws.exists():
        consider(aws, in_project=False)
    for hist in (".zsh_history", ".bash_history"):
        if (home / hist).exists():
            consider(home / hist, in_project=False, shell_history=True)

    ssh = home / ".ssh"
    if ssh.is_dir():
        for key in sorted(ssh.glob("id_*")):
            if key.suffix == ".pub":
                continue
            try:
                loose = key.stat().st_mode & 0o077
            except OSError:
                continue
            if loose:
                rel = os.path.relpath(key, home)
                res.findings.append(Finding(
                    f"secrets:{rel}", "secrets", "medium", "SSH private key readable by other users",
                    f"{rel}: permissions {oct(key.stat().st_mode & 0o777)}",
                    "SSH refuses keys like this for a reason: other users on this Mac can copy it and log in as you.",
                    [f"chmod 600 ~/{rel}"]))

    if expected:
        res.findings.append(Finding(
            "secrets:ignored-env", "secrets", "info",
            "API keys in git-ignored .env files (expected setup)",
            f"{len(expected)} file(s): " + ", ".join(expected),
            "Keeping keys in a git-ignored .env file is the normal setup for local projects.",
            ["Nothing to do. Keep .env in .gitignore and rotate a key if a file is ever shared."]))
    if not any(f.severity != "info" for f in res.findings):
        res.passed.append("Secrets: no exposed secrets found")
    return res
