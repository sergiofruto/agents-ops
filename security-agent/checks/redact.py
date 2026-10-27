"""Find secrets in text and keep only what kind they are and where.

This is the redaction boundary: a matched value is tested and dropped right
here. Nothing returned from this module can carry a secret value.
"""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SecretHit:
    kind: str
    line: int


# Most specific first: one hit per line, the first kind that matches wins.
SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("wallet_private_key", re.compile(
        r"(?i)[A-Z0-9_]*(PRIVATE_KEY|WALLET)[A-Z0-9_]*\s*[=:]\s*['\"]?(0x)?[0-9a-f]{64}\b")),
    ("anthropic_key", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("openai_key", re.compile(r"sk-(proj-)?[A-Za-z0-9]{20,}")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
]

_GENERIC = re.compile(
    r"(?i)^\s*(export\s+)?[A-Z0-9_.-]*(KEY|SECRET|TOKEN|PASSWORD|PASSPHRASE)[A-Z0-9_.-]*"
    r"\s*[=:]\s*['\"]?([^'\"\s#]*)")
_PLACEHOLDER = re.compile(
    r"(?i)^(|changeme|change_me|none|null|true|false|x+|\*+|your[_-].*|<.*>|\$\{.*\}|\$[A-Z_]+|\.\.\.)$")


def _generic(line: str) -> bool:
    m = _GENERIC.match(line)
    if not m:
        return False
    value = m.group(3)
    return len(value) >= 8 and not _PLACEHOLDER.match(value)


def find_secrets(text: str) -> list[SecretHit]:
    hits = []
    for n, line in enumerate(text.splitlines(), start=1):
        kind = next((k for k, p in SECRET_PATTERNS if p.search(line)), None)
        if kind is None and _generic(line):
            kind = "generic_secret"
        if kind:
            hits.append(SecretHit(kind, n))
    return hits
