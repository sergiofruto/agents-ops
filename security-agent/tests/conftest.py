import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import database  # noqa: E402
from models import CmdResult, Finding  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"

# Planted secrets: tests assert these never show up anywhere they shouldn't.
PLANTED = "0x" + "ab" * 32
ANTH = "sk-ant-api03-" + "Z" * 40


@pytest.fixture
def db():
    conn = database.connect(":memory:")
    database.init_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def fixture():
    return lambda name: (FIXTURES / name).read_text()


def F(key, sev="medium", title="t", evidence="e", fix=None, category="ports"):
    return Finding(key, category, sev, title, evidence, "x", fix or ["f"])


def fake_run(outputs: dict):
    """A shell.run stand-in keyed by the command's basename.

    Values are stdout strings (ok) or full CmdResult objects. Unknown commands
    behave like a missing binary.
    """
    def run(cmd, timeout=30):
        out = outputs.get(os.path.basename(cmd[0]))
        if out is None:
            return CmdResult(False, "", "", "not found")
        if isinstance(out, CmdResult):
            return out
        return CmdResult(True, out, "", None)
    return run


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def git_repo(tmp_path):
    repo = tmp_path / "Projects" / "proj"
    repo.mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / ".gitignore").write_text(".env\n.env.*\n")
    return repo


def commit_all(repo):
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "c")
