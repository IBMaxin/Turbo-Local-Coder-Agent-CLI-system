from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class FSResult:
    ok: bool
    detail: str


def _safe_path(path: str) -> Path:
    """Resolve path and ensure it stays within the CWD sandbox."""
    base = Path.cwd().resolve()
    p = Path(path)
    if p.is_absolute():
        p = p.relative_to("/")
    full = (base / p).resolve()
    if base not in full.parents and full != base:
        raise ValueError("path escapes sandbox")
    return full


def fs_read(path: str) -> FSResult:
    f = _safe_path(path)
    if not f.exists():
        return FSResult(False, f"read: not found: {path}")
    return FSResult(True, f.read_text(encoding="utf-8"))


def fs_write(path: str, content: str) -> FSResult:
    f = _safe_path(path)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")
    size = f.stat().st_size
    lines = content.count("\n") + (0 if content.endswith("\n") else 1)
    return FSResult(True, f"wrote {path} ({lines} lines, {size} bytes)")


def fs_list(path: str) -> FSResult:
    d = _safe_path(path)
    if not d.exists():
        return FSResult(False, f"list: not found: {path}")
    if not d.is_dir():
        return FSResult(False, f"list: not a directory: {path}")
    items = [p.name + ("/" if p.is_dir() else "") for p in d.iterdir()]
    return FSResult(True, "\n".join(sorted(items)))
