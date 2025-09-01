"""
Centralized error handling and recovery system for Turbo Local Coder Agent.

Provides consistent error types, logging, and recovery strategies across all modules.
"""

from __future__ import annotations

import logging
import traceback
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path


class ErrorSeverity(Enum):
    """Error severity levels for consistent handling."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification and handling."""
    CONFIGURATION = "configuration"
    NETWORK = "network"
    MODEL = "model"
    TOOL = "tool"
    VALIDATION = "validation"
    FILESYSTEM = "filesystem"
    PARSING = "parsing"
    AUTHENTICATION = "authentication"


@dataclass
class ErrorContext:
    """Context information for error tracking and debugging."""
    component: str
    operation: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    user_input: Optional[str] = None
    stack_trace: Optional[str] = None
    timestamp: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            import time
            self.timestamp = time.time()


class TurboError(Exception):
    """Base exception class for all Turbo Local Coder Agent errors."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: Optional[ErrorContext] = None,
        recoverable: bool = True,
        recovery_suggestion: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context
        self.recoverable = recoverable
        self.recovery_suggestion = recovery_suggestion
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging and debugging."""
        return {
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "recoverable": self.recoverable,
            "recovery_suggestion": self.recovery_suggestion,
            "context": {
                "component": self.context.component,
                "operation": self.context.operation,
                "parameters": self.context.parameters,
                "timestamp": self.context.timestamp
            } if self.context else None
        }


class ConfigurationError(TurboError):
    """Configuration-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.CONFIGURATION,
            recovery_suggestion="Check your .env file and environment variables",
            **kwargs
        )


class ModelError(TurboError):
    """Model-related errors (API calls, responses, etc.)."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.MODEL,
            recovery_suggestion="Check model availability and API credentials",
            **kwargs
        )


class ToolError(TurboError):
    """Tool execution errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.TOOL,
            recovery_suggestion="Verify tool parameters and system state",
            **kwargs
        )


class ParsingError(TurboError):
    """Data parsing and format errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.PARSING,
            recovery_suggestion="Check data format and parsing logic",
            **kwargs
        )


class ErrorHandler:
    """Centralized error handling with logging and recovery."""
    
    def __init__(self, log_level: int = logging.INFO):
        self.logger = logging.getLogger("turbo_agent")
        self.logger.setLevel(log_level)
        self.error_history: List[TurboError] = []
        self.recovery_strategies: Dict[ErrorCategory, List[Callable]] = {}
        
        # Setup default logging if no handlers exist
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def handle_error(self, error: TurboError, context: Optional[ErrorContext] = None) -> Optional[Any]:
        """Handle error with appropriate logging and recovery attempts."""
        
        if context:
            error.context = context
        
        # Log error based on severity
        error_dict = error.to_dict()
        log_message = f"{error.category.value.upper()}: {error.message}"
        
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, extra={"error_data": error_dict})
        elif error.severity == ErrorSeverity.ERROR:
            self.logger.error(log_message, extra={"error_data": error_dict})
        elif error.severity == ErrorSeverity.WARNING:
            self.logger.warning(log_message, extra={"error_data": error_dict})
        else:
            self.logger.info(log_message, extra={"error_data": error_dict})
        
        # Store in error history
        self.error_history.append(error)
        
        # Attempt recovery if error is recoverable
        if error.recoverable:
            return self._attempt_recovery(error)
        
        return None
    
    def _attempt_recovery(self, error: TurboError) -> Optional[Any]:
        """Attempt to recover from error using registered strategies."""
        
        strategies = self.recovery_strategies.get(error.category, [])
        for strategy in strategies:
            try:
                result = strategy(error)
                if result is not None:
                    self.logger.info(f"Successfully recovered from {error.category.value} error")
                    return result
            except Exception as e:
                self.logger.warning(f"Recovery strategy failed: {e}")
        
        self.logger.warning(f"No recovery possible for {error.category.value} error")
        return None
    
    def register_recovery_strategy(self, category: ErrorCategory, strategy: Callable):
        """Register a recovery strategy for a specific error category."""
        if category not in self.recovery_strategies:
            self.recovery_strategies[category] = []
        self.recovery_strategies[category].append(strategy)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get statistics about handled errors."""
        if not self.error_history:
            return {"total_errors": 0, "categories": {}, "severities": {}}
        
        categories = {}
        severities = {}
        
        for error in self.error_history:
            # Count by category
            cat = error.category.value
            categories[cat] = categories.get(cat, 0) + 1
            
            # Count by severity
            sev = error.severity.value
            severities[sev] = severities.get(sev, 0) + 1
        
        return {
            "total_errors": len(self.error_history),
            "categories": categories,
            "severities": severities,
            "last_error": self.error_history[-1].to_dict() if self.error_history else None
        }


# Global error handler instance
_error_handler = ErrorHandler()


def handle_error(error: TurboError, context: Optional[ErrorContext] = None) -> Optional[Any]:
    """Global error handling function."""
    return _error_handler.handle_error(error, context)


def create_error_context(component: str, operation: str, **kwargs) -> ErrorContext:
    """Helper function to create error context."""
    return ErrorContext(
        component=component,
        operation=operation,
        parameters=kwargs.get("parameters", {}),
        user_input=kwargs.get("user_input"),
        stack_trace=traceback.format_exc() if kwargs.get("include_trace", True) else None
    )


def safe_execute(operation: Callable, context: ErrorContext, 
                default_return=None) -> Any:
    """Safely execute an operation with error handling."""
    try:
        return operation()
    except TurboError as e:
        return handle_error(e, context) or default_return
    except Exception as e:
        # Convert generic exceptions to TurboError
        turbo_error = TurboError(
            message=f"Unexpected error: {str(e)}",
            category=ErrorCategory.VALIDATION,
            context=context,
            recovery_suggestion="Check the operation parameters and try again"
        )
        return handle_error(turbo_error, context) or default_return


# Recovery strategy decorators
def recovery_strategy(category: ErrorCategory):
    """Decorator to register recovery strategies."""
    def decorator(func: Callable):
        _error_handler.register_recovery_strategy(category, func)
        return func
    return decorator


# Built-in recovery strategies
@recovery_strategy(ErrorCategory.CONFIGURATION)
def recover_from_config_error(error: ConfigurationError) -> Optional[Any]:
    """Attempt to recover from configuration errors."""
    # Try to reload configuration with defaults
    try:
        from .config import load_settings
        return load_settings()
    except Exception:
        return None


@recovery_strategy(ErrorCategory.NETWORK)
def recover_from_network_error(error: TurboError) -> Optional[Any]:
    """Attempt to recover from network errors with retry."""
    # Simple retry mechanism could be implemented here
    return None