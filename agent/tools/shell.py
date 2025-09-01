from __future__ import annotations

import logging
import shlex
import subprocess
from dataclasses import dataclass

WHITELIST: set[str] = {
    "python", "pytest", "pip", "ls", "cat", "echo",
    "mkdir", "rm", "touch", "git",
}


@dataclass
class ShellResult:
    ok: bool
    stdout: str
    stderr: str
    code: int


def _allowed(cmd: str) -> bool:
    parts = shlex.split(cmd)
    return bool(parts) and parts[0] in WHITELIST


def shell_run(cmd: str, timeout_s: int = 60) -> ShellResult:
    """Run a safe command with timeout."""
    if not _allowed(cmd):
        return ShellResult(False, "", f"blocked: {cmd}", 126)
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return ShellResult(
            proc.returncode == 0,
            proc.stdout.strip(),
            proc.stderr.strip(),
            proc.returncode,
        )
    except subprocess.TimeoutExpired as exc:  # pragma: no cover
        logger = logging.getLogger(__name__)
        stdout = exc.stdout
        if isinstance(stdout, memoryview):
            stdout = stdout.tobytes().decode('utf-8', errors='replace')
        elif isinstance(stdout, (bytes, bytearray)):
            stdout = stdout.decode('utf-8', errors='replace')
        elif stdout is None:
            stdout = ""
        logger.warning(f"Timeout running command: {cmd} (timeout={timeout_s}s)")
        logger.info(f"Partial stdout: {stdout[:120] if stdout else '<empty>'}")
        return ShellResult(False, stdout or "", "timeout", 124)
