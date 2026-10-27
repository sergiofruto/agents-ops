import pytest

from checks.redact import SecretHit, find_secrets
from checks.secrets import classify, scan_secrets
from conftest import ANTH, PLANTED, commit_all

BASE = dict(tracked=False, in_history=False, other_readable=False, in_project=True, shell_history=False)


def test_find_secrets_reports_kind_and_line_only():
    hits = find_secrets(f"A=1\nPOLY_PRIVATE_KEY={PLANTED}\nANTHROPIC_API_KEY={ANTH}\n")
    assert hits == [SecretHit("wallet_private_key", 2), SecretHit("anthropic_key", 3)]


def test_placeholders_are_not_secrets():
    assert find_secrets("API_KEY=\nTOKEN=changeme\nSECRET=your_secret_here\nKEY=<key>\n") == []


@pytest.mark.parametrize("kw,expected", [
    (dict(tracked=True), "high"), (dict(in_history=True), "high"),
    (dict(other_readable=True), "medium"), (dict(in_project=False), "medium"),
    (dict(shell_history=True, in_project=False), "medium"), ({}, "info"),
])
def test_classify(kw, expected):
    assert classify([SecretHit("generic_secret", 1)], **{**BASE, **kw}) == expected


def test_wallet_key_in_ignored_env_is_medium():
    assert classify([SecretHit("wallet_private_key", 1)], **BASE) == "medium"


def test_scan_groups_info_and_never_leaks_values(tmp_path, git_repo):
    proj = git_repo
    (proj / ".env").write_text(f"ANTHROPIC_API_KEY={ANTH}\n")
    (proj / ".env").chmod(0o600)
    other = proj / "sub"
    other.mkdir()
    (other / ".env").write_text(f"POLY_PRIVATE_KEY={PLANTED}\n")
    (other / ".env").chmod(0o600)
    res = scan_secrets(tmp_path / "Projects", home=tmp_path)
    keys = {f.key: f for f in res.findings}
    assert "secrets:ignored-env" in keys and keys["secrets:ignored-env"].severity == "info"
    wallet = [f for f in res.findings if f.severity == "medium"]
    assert len(wallet) == 1 and "line 1" in wallet[0].evidence and "/" not in wallet[0].title
    dump = repr(res)
    assert PLANTED not in dump and ANTH not in dump and "ab" * 32 not in dump


def test_committed_secret_is_high(tmp_path, git_repo):
    (git_repo / "config.env").write_text(f"ANTHROPIC_API_KEY={ANTH}\n")
    commit_all(git_repo)
    res = scan_secrets(tmp_path / "Projects", home=tmp_path)
    assert any(f.severity == "high" for f in res.findings)


def test_large_binary_and_unreadable_files_are_skipped(tmp_path, git_repo):
    (git_repo / ".env.big").write_text("KEY=" + "x" * 2_000_000)
    (git_repo / ".env.bin").write_bytes(b"\xff\xfe\x00" * 100)
    locked = git_repo / ".env.locked"
    locked.write_text(f"ANTHROPIC_API_KEY={ANTH}\n")
    locked.chmod(0)
    try:
        res = scan_secrets(tmp_path / "Projects", home=tmp_path)  # must not raise
    finally:
        locked.chmod(0o600)
    assert all(".env.big" not in f.evidence and ".env.bin" not in f.evidence for f in res.findings)


def test_shell_history_secret_is_medium(tmp_path):
    (tmp_path / "Projects").mkdir()
    (tmp_path / ".zsh_history").write_text(f": 1:0;export ANTHROPIC_API_KEY={ANTH}\n")
    (tmp_path / ".zsh_history").chmod(0o600)
    res = scan_secrets(tmp_path / "Projects", home=tmp_path)
    f = next(f for f in res.findings if f.key == "secrets:.zsh_history")
    assert f.severity == "medium" and f.title == "Secret in shell history"


def test_ssh_key_readable_by_others(tmp_path):
    (tmp_path / "Projects").mkdir()
    ssh = tmp_path / ".ssh"
    ssh.mkdir()
    (ssh / "id_ed25519").write_text("-----BEGIN OPENSSH PRIVATE KEY-----\nabc\n")
    (ssh / "id_ed25519").chmod(0o644)
    (ssh / "id_ed25519.pub").write_text("ssh-ed25519 AAAA")
    res = scan_secrets(tmp_path / "Projects", home=tmp_path)
    titles = [f.title for f in res.findings]
    assert titles.count("SSH private key readable by other users") == 1
