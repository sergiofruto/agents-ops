"""The only way checks run commands: argument list, timeout, never raises."""
import subprocess

from models import CmdResult


def run(cmd: list[str], timeout: float = 30) -> CmdResult:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return CmdResult(False, "", "", "not found")
    except subprocess.TimeoutExpired:
        return CmdResult(False, "", "", "timeout")
    except (PermissionError, OSError) as exc:
        return CmdResult(False, "", str(exc), type(exc).__name__)
    return CmdResult(p.returncode == 0, p.stdout, p.stderr, None)
