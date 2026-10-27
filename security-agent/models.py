"""Shared value types. Plain dataclasses, no behaviour."""
from dataclasses import dataclass, field
from typing import Literal

Severity = Literal["high", "medium", "low", "info"]
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


@dataclass(frozen=True)
class Finding:
    key: str          # stable across scans, e.g. "port:5000:python"
    category: str     # performance | ports | secrets | basics | malware
    severity: Severity
    title: str        # never holds paths or secret material (it goes to Solaris)
    evidence: str     # already redacted
    explanation: str
    fix: list[str]


@dataclass
class CheckResult:
    category: str
    findings: list[Finding] = field(default_factory=list)
    passed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CmdResult:
    ok: bool
    stdout: str
    stderr: str
    error: str | None
