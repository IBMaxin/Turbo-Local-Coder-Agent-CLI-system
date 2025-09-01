from __future__ import annotations

import subprocess
import sys
import tempfile
from dataclasses import dataclass


@dataclass
class PyRunResult:
    ok: bool
    stdout: str
    stderr: str
    code: int


def python_run(mode: str, code: str | None = None) -> PyRunResult:
    """Run pytest or a small Python snippet."""
    try:
        if mode == "pytest":
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q"],
                capture_output=True,
                text=True,
            )
            return PyRunResult(
                proc.returncode == 0, proc.stdout, proc.stderr,
                proc.returncode,
            )
        if mode == "snippet":
            if not code:
                return PyRunResult(False, "", "no code provided", 2)
            with tempfile.NamedTemporaryFile(
                "w", suffix=".py", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(code)
                tmp.flush()
                path = tmp.name
            proc = subprocess.run(
                [sys.executable, path],
                capture_output=True,
                text=True,
            )
            return PyRunResult(
                proc.returncode == 0, proc.stdout, proc.stderr,
                proc.returncode,
            )
        return PyRunResult(False, "", f"unknown mode: {mode}", 2)
    except Exception as exc:  # pragma: no cover
        return PyRunResult(False, "", f"error: {exc}", 1)
