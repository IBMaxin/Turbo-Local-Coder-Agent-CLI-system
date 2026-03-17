from __future__ import annotations

import json
import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any

from .errors import ConfigurationError, ErrorContext, create_error_context, safe_execute


@dataclass
class Settings:
    turbo_host: str
    local_host: str
    planner_model: str
    coder_model: str
    api_key: str
    max_steps: int
    request_timeout_s: int
    dry_run: bool

    # Backend selection: "lmstudio", "ollama", or "llamacpp"
    backend: str = "lmstudio"

    # LM Studio settings
    lmstudio_host: str = "http://localhost:1234"

    # llama.cpp specific settings
    llamacpp_model_path: str = "./models/phi-4-mini-Q4_K_M.gguf"
    llamacpp_port: int = 8080
    llamacpp_use_vulkan: bool = True
    llamacpp_n_gpu_layers: int = 32
    llamacpp_context_size: int = 4096

    # Validation and error tracking
    _validation_errors: list[str] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        self._validate_settings()
        if self._validation_errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in self._validation_errors)
            raise ValueError(error_msg)

    def _validate_settings(self):
        if not self.turbo_host.startswith(('http://', 'https://')):
            self._validation_errors.append(f"Invalid turbo_host URL: {self.turbo_host}")
        if not self.local_host.startswith(('http://', 'https://')):
            self._validation_errors.append(f"Invalid local_host URL: {self.local_host}")
        if not self.lmstudio_host.startswith(('http://', 'https://')):
            self._validation_errors.append(f"Invalid lmstudio_host URL: {self.lmstudio_host}")

        if self.max_steps <= 0:
            self._validation_errors.append(f"max_steps must be positive, got: {self.max_steps}")
        if self.request_timeout_s <= 0:
            self._validation_errors.append(f"request_timeout_s must be positive, got: {self.request_timeout_s}")
        if not self.planner_model.strip():
            self._validation_errors.append("planner_model cannot be empty")
        if not self.coder_model.strip():
            self._validation_errors.append("coder_model cannot be empty")
        if self.api_key and len(self.api_key) < 10:
            self._validation_errors.append("api_key appears to be too short")

        if self.backend.lower() not in ["lmstudio", "ollama", "llamacpp"]:
            self._validation_errors.append(f"backend must be 'lmstudio', 'ollama', or 'llamacpp', got: {self.backend}")

        if self.llamacpp_port < 1 or self.llamacpp_port > 65535:
            self._validation_errors.append(f"llamacpp_port must be 1-65535, got: {self.llamacpp_port}")
        if self.llamacpp_n_gpu_layers < 0:
            self._validation_errors.append(f"llamacpp_n_gpu_layers must be >= 0, got: {self.llamacpp_n_gpu_layers}")
        if self.llamacpp_context_size < 512:
            self._validation_errors.append(f"llamacpp_context_size must be >= 512, got: {self.llamacpp_context_size}")

    def with_overrides(self, **kwargs) -> 'Settings':
        current_values = {
            'turbo_host': self.turbo_host,
            'local_host': self.local_host,
            'planner_model': self.planner_model,
            'coder_model': self.coder_model,
            'api_key': self.api_key,
            'max_steps': self.max_steps,
            'request_timeout_s': self.request_timeout_s,
            'dry_run': self.dry_run,
            'backend': self.backend,
            'lmstudio_host': self.lmstudio_host,
            'llamacpp_model_path': self.llamacpp_model_path,
            'llamacpp_port': self.llamacpp_port,
            'llamacpp_use_vulkan': self.llamacpp_use_vulkan,
            'llamacpp_n_gpu_layers': self.llamacpp_n_gpu_layers,
            'llamacpp_context_size': self.llamacpp_context_size,
        }
        current_values.update({k: v for k, v in kwargs.items() if v is not None})
        return Settings(**current_values)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'turbo_host': self.turbo_host,
            'local_host': self.local_host,
            'planner_model': self.planner_model,
            'coder_model': self.coder_model,
            'api_key': '***' if self.api_key else '',
            'max_steps': self.max_steps,
            'request_timeout_s': self.request_timeout_s,
            'dry_run': self.dry_run,
            'backend': self.backend,
            'lmstudio_host': self.lmstudio_host,
            'llamacpp_model_path': self.llamacpp_model_path,
            'llamacpp_port': self.llamacpp_port,
            'llamacpp_use_vulkan': self.llamacpp_use_vulkan,
            'llamacpp_n_gpu_layers': self.llamacpp_n_gpu_layers,
            'llamacpp_context_size': self.llamacpp_context_size,
        }


def _strip_inline_comment(value: str) -> str:
    if '#' in value:
        value = value.split('#', 1)[0]
    return value.strip()


def _load_env_file(env_path: Path) -> Dict[str, str]:
    env_vars = {}
    if not env_path.exists():
        return env_vars

    try:
        content = env_path.read_text(encoding="utf-8")
        for line_num, line in enumerate(content.splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                logging.warning(f"Skipping malformed line {line_num} in {env_path}: {line}")
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = _strip_inline_comment(val)
            if not key:
                logging.warning(f"Empty key on line {line_num} in {env_path}")
                continue
            env_vars[key] = val
            os.environ.setdefault(key, val)

        logging.info(f"Loaded {len(env_vars)} environment variables from {env_path}")
        return env_vars

    except Exception as e:
        logging.error(f"Failed to load {env_path}: {e}")
        return env_vars


def _parse_int_with_validation(value: str, name: str, min_value: int = 1) -> int:
    try:
        parsed = int(value)
        if parsed < min_value:
            raise ValueError(f"{name} must be >= {min_value}, got: {parsed}")
        return parsed
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ConfigurationError(f"Invalid {name}: '{value}' is not a valid integer")
        raise ConfigurationError(str(e))


def _parse_bool(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "on", "enabled"}


def load_settings(config_path: Optional[Path] = None) -> Settings:
    """Load settings from environment and optional .env file."""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    env_path = config_path or Path(".env")
    _load_env_file(env_path)

    try:
        # General
        turbo_host = os.getenv("TURBO_HOST", "http://localhost:1234")  # fallback to LM Studio
        local_host = os.getenv("OLLAMA_LOCAL", "http://127.0.0.1:11434")
        api_key = os.getenv("OLLAMA_API_KEY", "")
        max_steps = _parse_int_with_validation(os.getenv("MAX_STEPS", "25"), "MAX_STEPS")
        timeout = _parse_int_with_validation(os.getenv("REQUEST_TIMEOUT_S", "120"), "REQUEST_TIMEOUT_S")
        dry_run = _parse_bool(os.getenv("DRY_RUN", "0"))

        # Backend
        backend = os.getenv("BACKEND", "lmstudio")

        # Model selection — defaults to your Qwen3 stack
        planner_model = os.getenv("PLANNER_MODEL", "qwen3-8b")
        coder_model = os.getenv("CODER_MODEL", "qwen3-4b")

        # LM Studio
        lmstudio_host = os.getenv("LMSTUDIO_HOST", "http://localhost:1234")

        # llama.cpp
        llamacpp_model_path = os.getenv("LLAMACPP_MODEL_PATH", "./models/phi-4-mini-Q4_K_M.gguf")
        llamacpp_port = _parse_int_with_validation(os.getenv("LLAMACPP_PORT", "8080"), "LLAMACPP_PORT", 1)
        llamacpp_use_vulkan = _parse_bool(os.getenv("LLAMACPP_USE_VULKAN", "1"))
        llamacpp_n_gpu_layers = _parse_int_with_validation(os.getenv("LLAMACPP_N_GPU_LAYERS", "32"), "LLAMACPP_N_GPU_LAYERS", 0)
        llamacpp_context_size = _parse_int_with_validation(os.getenv("LLAMACPP_CONTEXT_SIZE", "4096"), "LLAMACPP_CONTEXT_SIZE", 512)

        settings = Settings(
            turbo_host=turbo_host,
            local_host=local_host,
            planner_model=planner_model,
            coder_model=coder_model,
            api_key=api_key,
            max_steps=max_steps,
            request_timeout_s=timeout,
            dry_run=dry_run,
            backend=backend,
            lmstudio_host=lmstudio_host,
            llamacpp_model_path=llamacpp_model_path,
            llamacpp_port=llamacpp_port,
            llamacpp_use_vulkan=llamacpp_use_vulkan,
            llamacpp_n_gpu_layers=llamacpp_n_gpu_layers,
            llamacpp_context_size=llamacpp_context_size,
        )

        logging.info("Configuration loaded successfully")
        logging.debug(f"Configuration: {settings.to_dict()}")
        return settings

    except Exception as e:
        raise ConfigurationError(f"Failed to load configuration: {e}") from e


def compact_json(obj: object) -> str:
    try:
        return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
    except (TypeError, ValueError) as e:
        logging.warning(f"Failed to serialize object to JSON: {e}")
        return str(obj)


def validate_configuration() -> bool:
    try:
        load_settings()
        return True
    except ConfigurationError as e:
        logging.error(f"Configuration validation failed: {e}")
        return False
