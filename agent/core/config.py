from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    turbo_host: str
    local_host: str
    planner_model: str
    coder_model: str
    api_key: str
    max_steps: int
    request_timeout_s: int
    dry_run: bool


def load_settings() -> Settings:
    """Load settings from env and optional .env file."""
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

    turbo_host = os.getenv("TURBO_HOST", "https://ollama.com")
    local_host = os.getenv("OLLAMA_LOCAL", "http://127.0.0.1:11434")
    planner_model = os.getenv("PLANNER_MODEL", "gpt-oss:20b")
    coder_model = os.getenv("CODER_MODEL", "qwen2.5-coder:latest")
    api_key = os.getenv("OLLAMA_API_KEY", "")
    max_steps = int(os.getenv("MAX_STEPS", "25"))
    timeout = int(os.getenv("REQUEST_TIMEOUT_S", "120"))
    dry_run = os.getenv("DRY_RUN", "0") in {"1", "true", "True"}

    return Settings(
        turbo_host=turbo_host,
        local_host=local_host,
        planner_model=planner_model,
        coder_model=coder_model,
        api_key=api_key,
        max_steps=max_steps,
        request_timeout_s=timeout,
        dry_run=dry_run,
    )


def compact_json(obj: object) -> str:
    """Return compact JSON for logging."""
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
