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
    
    # Validation and error tracking
    _validation_errors: list[str] = field(default_factory=list, init=False, repr=False)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_settings()
        if self._validation_errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in self._validation_errors)
            raise ValueError(error_msg)
    
    def _validate_settings(self):
        """Validate all settings and collect errors."""
        # Validate URLs
        if not self.turbo_host.startswith(('http://', 'https://')):
            self._validation_errors.append(f"Invalid turbo_host URL: {self.turbo_host}")
        if not self.local_host.startswith(('http://', 'https://')):
            self._validation_errors.append(f"Invalid local_host URL: {self.local_host}")
        
        # Validate numeric values
        if self.max_steps <= 0:
            self._validation_errors.append(f"max_steps must be positive, got: {self.max_steps}")
        if self.request_timeout_s <= 0:
            self._validation_errors.append(f"request_timeout_s must be positive, got: {self.request_timeout_s}")
        
        # Validate required fields
        if not self.planner_model.strip():
            self._validation_errors.append("planner_model cannot be empty")
        if not self.coder_model.strip():
            self._validation_errors.append("coder_model cannot be empty")
        
        # Validate API key format (basic check)
        if self.api_key and len(self.api_key) < 10:
            self._validation_errors.append("api_key appears to be too short")
    
    def with_overrides(self, **kwargs) -> 'Settings':
        """Create a new Settings instance with specified overrides."""
        current_values = {
            'turbo_host': self.turbo_host,
            'local_host': self.local_host,
            'planner_model': self.planner_model,
            'coder_model': self.coder_model,
            'api_key': self.api_key,
            'max_steps': self.max_steps,
            'request_timeout_s': self.request_timeout_s,
            'dry_run': self.dry_run,
        }
        current_values.update({k: v for k, v in kwargs.items() if v is not None})
        return Settings(**current_values)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary for logging/debugging."""
        return {
            'turbo_host': self.turbo_host,
            'local_host': self.local_host,
            'planner_model': self.planner_model,
            'coder_model': self.coder_model,
            'api_key': '***' if self.api_key else '',
            'max_steps': self.max_steps,
            'request_timeout_s': self.request_timeout_s,
            'dry_run': self.dry_run,
        }


# ConfigurationError now imported from errors module


def _load_env_file(env_path: Path) -> Dict[str, str]:
    """Load environment variables from .env file with error handling."""
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
            key, val = key.strip(), val.strip()
            
            if not key:
                logging.warning(f"Empty key on line {line_num} in {env_path}")
                continue
            
            env_vars[key] = val
            # Only set in os.environ if not already present
            os.environ.setdefault(key, val)
        
        logging.info(f"Loaded {len(env_vars)} environment variables from {env_path}")
        return env_vars
        
    except Exception as e:
        logging.error(f"Failed to load {env_path}: {e}")
        return env_vars


def _parse_int_with_validation(value: str, name: str, min_value: int = 1) -> int:
    """Parse integer with validation and helpful error messages."""
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
    """Parse boolean from string with multiple accepted formats."""
    return value.lower() in {"1", "true", "yes", "on", "enabled"}


def load_settings(config_path: Optional[Path] = None) -> Settings:
    """Load settings from environment and optional .env file with robust error handling."""
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Load .env file
    env_path = config_path or Path(".env")
    env_vars = _load_env_file(env_path)
    
    try:
        # Parse with validation
        turbo_host = os.getenv("TURBO_HOST", "https://ollama.com")
        local_host = os.getenv("OLLAMA_LOCAL", "http://127.0.0.1:11434")
        planner_model = os.getenv("PLANNER_MODEL", "deepseek-v3.1:671b")
        coder_model = os.getenv("CODER_MODEL", "qwen2.5-coder:latest")
        api_key = os.getenv("OLLAMA_API_KEY", "")
        
        max_steps = _parse_int_with_validation(os.getenv("MAX_STEPS", "25"), "MAX_STEPS")
        timeout = _parse_int_with_validation(os.getenv("REQUEST_TIMEOUT_S", "120"), "REQUEST_TIMEOUT_S")
        dry_run = _parse_bool(os.getenv("DRY_RUN", "0"))
        
        settings = Settings(
            turbo_host=turbo_host,
            local_host=local_host,
            planner_model=planner_model,
            coder_model=coder_model,
            api_key=api_key,
            max_steps=max_steps,
            request_timeout_s=timeout,
            dry_run=dry_run,
        )
        
        logging.info("Configuration loaded successfully")
        logging.debug(f"Configuration: {settings.to_dict()}")
        return settings
        
    except Exception as e:
        raise ConfigurationError(f"Failed to load configuration: {e}") from e


def compact_json(obj: object) -> str:
    """Return compact JSON for logging."""
    try:
        return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
    except (TypeError, ValueError) as e:
        logging.warning(f"Failed to serialize object to JSON: {e}")
        return str(obj)


def validate_configuration() -> bool:
    """Validate current configuration and return True if valid."""
    try:
        load_settings()
        return True
    except ConfigurationError as e:
        logging.error(f"Configuration validation failed: {e}")
        return False
