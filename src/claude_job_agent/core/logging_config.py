"""
Claude Job Agent - Centralized Logging Configuration
===================================================

Centralized logging configuration that can be used across all modules.
Provides consistent logging setup with environment-based configuration.

Features:
- Environment-based log level configuration
- Multiple output handlers (console, file, rotating files)
- Component-specific loggers
- Performance and error tracking
- JSON logging option for structured logs
- Log rotation and clean-up
- Development vs production configurations

Usage:
    from claude_job_agent.core.logging_config import setup_logging, get_logger

    # Initialize logging (call once at application startup)
    setup_logging()

    # Get logger for specific component
    logger = get_logger('api.adzuna')
    logger.info("Starting API call")
"""

import json
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Any

from .coloured_formatter import ColouredFormatter
from .json_formatter import JSONFormatter


class LoggingConfig:
    """Centralized logging configuration."""

    def __init__(self):
        # Environment-based configuration
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_format = os.getenv("LOG_FORMAT", "detailed")  # simple, detailed, json
        self.log_dir = Path(os.getenv("LOG_DIR", "logs"))
        self.enable_console = os.getenv("LOG_CONSOLE", "true").lower() == "true"
        self.enable_file = os.getenv("LOG_FILE", "true").lower() == "true"
        self.enable_colors = os.getenv("LOG_COLORS", "true").lower() == "true"

        # File rotation settings
        self.max_file_size = int(os.getenv("LOG_FILE_MAX_SIZE", str(10 * 1024 * 1024)))  # 10MB
        self.backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))

        # Performance settings
        self.enable_performance_logging = os.getenv("LOG_PERFORMANCE", "true").lower() == "true"
        self.enable_api_logging = os.getenv("LOG_API", "true").lower() == "true"

        # Create log directory
        self.log_dir.mkdir(exist_ok=True)

        # Track configured loggers to avoid duplicate setup
        self._configured_loggers: set = set()

    def get_formatter(self, formatter_type: str = None) -> logging.Formatter:
        """Get appropriate formatter based on configuration."""
        if formatter_type is None:
            formatter_type = self.log_format

        if formatter_type == "json":
            return JSONFormatter()
        elif formatter_type == "simple":
            return logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        elif formatter_type == "colored":
            return ColouredFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        else:  # detailed
            return logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s'
            )

    def create_console_handler(self) -> logging.Handler:
        """Create console handler with appropriate formatting."""
        handler = logging.StreamHandler(sys.stdout)

        if self.enable_colors:
            handler.setFormatter(self.get_formatter("colored"))
        else:
            handler.setFormatter(self.get_formatter("simple"))

        handler.setLevel(logging.INFO)  # Console shows INFO and above
        return handler

    def create_file_handler(self, filename: str, level: int = None) -> logging.Handler:
        """Create rotating file handler."""
        if level is None:
            level = getattr(logging, self.log_level, logging.INFO)

        handler = logging.handlers.RotatingFileHandler(
            self.log_dir / filename,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )

        handler.setFormatter(self.get_formatter())
        handler.setLevel(level)
        return handler

    def create_error_handler(self) -> logging.Handler:
        """Create handler specifically for errors."""
        handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "errors.log",
            maxBytes=self.max_file_size // 2,  # Smaller error log
            backupCount=self.backup_count,
            encoding='utf-8'
        )

        handler.setFormatter(self.get_formatter())
        handler.setLevel(logging.ERROR)
        return handler

    def setup_root_logger(self) -> logging.Logger:
        """Set up the root application logger."""
        root_logger = logging.getLogger('claude_job_agent')

        if root_logger.name in self._configured_loggers:
            return root_logger

        root_logger.setLevel(getattr(logging, self.log_level, logging.INFO))

        # Clear any existing handlers
        root_logger.handlers.clear()

        # Console handler
        if self.enable_console:
            root_logger.addHandler(self.create_console_handler())

        # Main application file handler
        if self.enable_file:
            root_logger.addHandler(self.create_file_handler("claude_job_agent.log"))

        # Error file handler
        root_logger.addHandler(self.create_error_handler())

        # Prevent propagation to Python's root logger
        root_logger.propagate = False

        self._configured_loggers.add(root_logger.name)
        return root_logger

    def setup_component_logger(self, component: str) -> logging.Logger:
        """Set up logger for specific component."""
        logger_name = f'claude_job_agent.{component}'
        logger = logging.getLogger(logger_name)

        if logger_name in self._configured_loggers:
            return logger

        # Component loggers inherit from root but can have additional handlers
        logger.setLevel(logging.DEBUG)  # Allow all messages through

        # Component-specific file handler (optional)
        if component in {'api', 'database', 'monitoring'} and self.enable_file:
            component_handler = self.create_file_handler(f"{component}.log")
            logger.addHandler(component_handler)

        self._configured_loggers.add(logger_name)
        return logger

    def setup_performance_logger(self) -> logging.Logger:
        """Set up logger specifically for performance metrics."""
        if not self.enable_performance_logging:
            return logging.getLogger('claude_job_agent.performance.disabled')

        perf_logger = logging.getLogger('claude_job_agent.performance')

        if perf_logger.name in self._configured_loggers:
            return perf_logger

        perf_logger.setLevel(logging.DEBUG)

        if self.enable_file:
            # Performance metrics in JSON format for analysis
            perf_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / "performance.log",
                maxBytes=self.max_file_size,
                backupCount=self.backup_count * 2,  # Keep more performance data
                encoding='utf-8'
            )
            perf_handler.setFormatter(JSONFormatter())
            perf_handler.setLevel(logging.DEBUG)
            perf_logger.addHandler(perf_handler)

        perf_logger.propagate = False
        self._configured_loggers.add(perf_logger.name)
        return perf_logger

    def setup_api_logger(self) -> logging.Logger:
        """Set up logger specifically for API calls."""
        if not self.enable_api_logging:
            return logging.getLogger('claude_job_agent.api.disabled')

        _api_logger = logging.getLogger('claude_job_agent.api')

        if _api_logger.name in self._configured_loggers:
            return _api_logger

        _api_logger.setLevel(logging.DEBUG)

        if self.enable_file:
            # API calls in structured format
            api_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / "api_calls.log",
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            api_handler.setFormatter(JSONFormatter())
            api_handler.setLevel(logging.DEBUG)
            _api_logger.addHandler(api_handler)

        _api_logger.propagate = False
        self._configured_loggers.add(_api_logger.name)
        return _api_logger


# Global configuration instance
_config: LoggingConfig | None = None
_initialized: bool = False


def setup_logging(force_reinit: bool = False) -> None:
    """
    Initialize application-wide logging.

    Args:
        force_reinit: Force reinitialization even if already set up
    """
    global _config, _initialized

    if _initialized and not force_reinit:
        return

    _config = LoggingConfig()

    # Set up all loggers
    _config.setup_root_logger()
    _config.setup_component_logger('startup')
    _config.setup_component_logger('database')
    _config.setup_component_logger('api')
    _config.setup_component_logger('mcp')
    _config.setup_component_logger('monitoring')
    _config.setup_performance_logger()
    _config.setup_api_logger()

    _initialized = True

    # Log initialization
    logger = get_logger('startup')
    logger.info("Logging system initialized")
    logger.info("Log level: %s", _config.log_level)
    logger.info("Log directory: %s", _config.log_dir)
    logger.info("Console logging: %s", _config.enable_console)
    logger.info("File logging: %s", _config.enable_file)
    logger.debug("Logging configuration: %s", {
        'format': _config.log_format,
        'max_file_size': _config.max_file_size,
        'backup_count': _config.backup_count,
        'performance_logging': _config.enable_performance_logging,
        'api_logging': _config.enable_api_logging,
    })


def get_logger(component: str = '') -> logging.Logger:
    """
    Get logger for specific component.

    Args:
        component: Component name (e.g., 'api.adzuna', 'database.jobs')

    Returns:
        Configured logger instance
    """
    global _config, _initialized

    if not _initialized:
        setup_logging()

    if component:
        logger_name = f'claude_job_agent.{component}'
    else:
        logger_name = 'claude_job_agent'

    return logging.getLogger(logger_name)


def log_performance(operation: str, duration: float, **kwargs) -> None:
    """
    Log performance metrics in structured format.

    Args:
        operation: Name of the operation
        duration: Duration in seconds
        **kwargs: Additional context data
    """
    perf_logger = get_logger('performance')

    extra_data = {
        'operation': operation,
        'duration': duration,
        **kwargs
    }

    perf_logger.info("Performance metric", extra=extra_data)


def log_api_call(api_name: str, endpoint: str, method: str, status_code: int,
                response_time: float, **kwargs) -> None:
    """
    Log API call in structured format.

    Args:
        api_name: Name of the API (e.g., 'adzuna')
        endpoint: API endpoint
        method: HTTP method
        status_code: Response status code
        response_time: Response time in seconds
        **kwargs: Additional context data
    """
    api_logger = get_logger('api')

    extra_data = {
        'api_name': api_name,
        'endpoint': endpoint,
        'method': method,
        'status_code': status_code,
        'response_time': response_time,
        **kwargs
    }

    api_logger.info("API call", extra=extra_data)


def configure_external_loggers() -> None:
    """Configure logging for external libraries."""
    # Reduce noise from external libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    # Set specific levels for other libraries as needed
    external_config = {
        'aiohttp': logging.WARNING,
        'asyncio': logging.WARNING,
        'sqlite3': logging.WARNING,
    }

    for lib_name, level in external_config.items():
        logging.getLogger(lib_name).setLevel(level)


def get_log_stats() -> dict[str, Any]:
    """Get statistics about current logging configuration."""
    global _config, _initialized

    if not _initialized:
        return {"error": "Logging not initialized"}

    log_files = []
    total_size = 0

    if _config.log_dir.exists():
        for log_file in _config.log_dir.glob("*.log"):
            size = log_file.stat().st_size
            log_files.append({
                "name": log_file.name,
                "size": size,
                "size_mb": round(size / (1024 * 1024), 2)
            })
            total_size += size

    return {
        "initialized": _initialized,
        "log_level": _config.log_level if _config else None,
        "log_dir": str(_config.log_dir) if _config else None,
        "log_files": log_files,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "configured_loggers": len(_config._configured_loggers) if _config else 0
    }


# Example usage and testing
if __name__ == "__main__":
    # Test the logging configuration
    setup_logging()

    # Test different loggers
    main_logger = get_logger()
    api_logger = get_logger('api.test')
    db_logger = get_logger('database.test')

    # Test different log levels
    main_logger.debug("This is a debug message")
    main_logger.info("This is an info message")
    main_logger.warning("This is a warning message")
    main_logger.error("This is an error message")

    # Test component-specific logging
    api_logger.info("Testing API logger")
    db_logger.info("Testing database logger")

    # Test performance logging
    log_performance("test_operation", 1.23, extra_info="test")

    # Test API logging
    log_api_call("test_api", "/test", "GET", 200, 0.456, request_id="test-123")

    # Print stats
    stats = get_log_stats()
    print("Logging statistics:", json.dumps(stats, indent=2))

    print("Logging test completed - check logs/ directory")
