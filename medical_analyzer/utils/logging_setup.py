"""
Logging setup utilities for the Medical Software Analysis Tool.

This module provides logging configuration and setup functions
for consistent logging across the application.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
import os


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    format_string: Optional[str] = None,
    console_enabled: bool = True,
    file_enabled: bool = True
) -> None:
    """
    Setup logging configuration for the application.
    
    Args:
        level: Logging level
        log_file: Path to log file (optional)
        max_file_size: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
        format_string: Custom format string for log messages
        console_enabled: Whether to enable console logging
        file_enabled: Whether to enable file logging
    """
    # Default format string
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Create formatter
    formatter = logging.Formatter(format_string)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    if console_enabled:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if file_enabled and log_file:
        try:
            # Create log directory if it doesn't exist
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
        except Exception as e:
            # Fallback to basic file handler if rotating handler fails
            try:
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setLevel(level)
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
            except Exception as e2:
                print(f"Warning: Could not setup file logging: {e2}")
    
    # Set specific logger levels
    logging.getLogger('medical_analyzer').setLevel(level)
    
    # Reduce noise from third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('PyQt6').setLevel(logging.WARNING)


def setup_development_logging(
    log_dir: Optional[str] = None,
    level: int = logging.DEBUG
) -> None:
    """
    Setup logging for development environment.
    
    Args:
        log_dir: Directory for log files
        level: Logging level
    """
    if log_dir is None:
        log_dir = Path.home() / ".medical_analyzer" / "logs"
    
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "medical_analyzer_dev.log"
    
    setup_logging(
        level=level,
        log_file=str(log_file),
        max_file_size=5 * 1024 * 1024,  # 5MB for development
        backup_count=3,
        format_string="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        console_enabled=True,
        file_enabled=True
    )


def setup_production_logging(
    log_dir: Optional[str] = None,
    level: int = logging.INFO
) -> None:
    """
    Setup logging for production environment.
    
    Args:
        log_dir: Directory for log files
        level: Logging level
    """
    if log_dir is None:
        log_dir = Path.home() / ".medical_analyzer" / "logs"
    
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "medical_analyzer.log"
    
    setup_logging(
        level=level,
        log_file=str(log_file),
        max_file_size=10 * 1024 * 1024,  # 10MB for production
        backup_count=5,
        format_string="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        console_enabled=False,  # No console output in production
        file_enabled=True
    )


def setup_test_logging(
    level: int = logging.WARNING,
    log_file: Optional[str] = None
) -> None:
    """
    Setup logging for testing environment.
    
    Args:
        level: Logging level
        log_file: Path to log file (optional)
    """
    setup_logging(
        level=level,
        log_file=log_file,
        max_file_size=1 * 1024 * 1024,  # 1MB for tests
        backup_count=1,
        format_string="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        console_enabled=False,  # No console output during tests
        file_enabled=log_file is not None
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(f"medical_analyzer.{name}")


def log_system_info() -> None:
    """Log system information for debugging purposes."""
    logger = get_logger("system")
    
    import platform
    import sys
    
    logger.info("System Information:")
    logger.info(f"  Platform: {platform.platform()}")
    logger.info(f"  Python Version: {sys.version}")
    logger.info(f"  Architecture: {platform.architecture()}")
    logger.info(f"  Machine: {platform.machine()}")
    logger.info(f"  Processor: {platform.processor()}")
    
    # Log environment variables (excluding sensitive ones)
    sensitive_vars = {'API_KEY', 'PASSWORD', 'SECRET', 'TOKEN'}
    for key, value in os.environ.items():
        if not any(sensitive in key.upper() for sensitive in sensitive_vars):
            logger.debug(f"  {key}: {value}")


def log_application_startup() -> None:
    """Log application startup information."""
    logger = get_logger("startup")
    
    logger.info("=" * 60)
    logger.info("Medical Software Analysis Tool Starting")
    logger.info("=" * 60)
    
    # Log system information
    log_system_info()
    
    # Log application version
    try:
        from medical_analyzer import __version__
        logger.info(f"Application Version: {__version__}")
    except ImportError:
        logger.info("Application Version: Unknown")
    
    logger.info("=" * 60)


def log_application_shutdown() -> None:
    """Log application shutdown information."""
    logger = get_logger("shutdown")
    
    logger.info("=" * 60)
    logger.info("Medical Software Analysis Tool Shutting Down")
    logger.info("=" * 60)


def configure_logging_from_config(logging_config: dict) -> None:
    """
    Configure logging from a configuration dictionary.
    
    Args:
        logging_config: Dictionary containing logging configuration
    """
    level_name = logging_config.get('level', 'INFO')
    level = getattr(logging, level_name.upper(), logging.INFO)
    
    log_file = logging_config.get('log_file')
    max_file_size = logging_config.get('max_file_size', 10 * 1024 * 1024)
    backup_count = logging_config.get('backup_count', 5)
    format_string = logging_config.get('format_string')
    console_enabled = logging_config.get('console_enabled', True)
    file_enabled = logging_config.get('file_enabled', True)
    
    setup_logging(
        level=level,
        log_file=log_file,
        max_file_size=max_file_size,
        backup_count=backup_count,
        format_string=format_string,
        console_enabled=console_enabled,
        file_enabled=file_enabled
    )


class LoggingContext:
    """Context manager for temporary logging configuration."""
    
    def __init__(self, level: int, logger_name: str):
        """
        Initialize logging context.
        
        Args:
            level: Logging level to set
            logger_name: Name of logger to configure
        """
        self.level = level
        self.logger_name = logger_name
        self.original_level = None
        self.logger = None
    
    def __enter__(self):
        """Enter logging context."""
        self.logger = logging.getLogger(self.logger_name)
        self.original_level = self.logger.level
        self.logger.setLevel(self.level)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit logging context."""
        if self.logger:
            self.logger.setLevel(self.original_level)


def create_log_rotation_schedule() -> dict:
    """
    Create a log rotation schedule configuration.
    
    Returns:
        Dictionary with log rotation schedule
    """
    return {
        'daily': {
            'when': 'midnight',
            'interval': 1,
            'backup_count': 7
        },
        'weekly': {
            'when': 'W0',  # Monday
            'interval': 1,
            'backup_count': 4
        },
        'monthly': {
            'when': 'M0',  # First day of month
            'interval': 1,
            'backup_count': 12
        }
    }


def setup_advanced_logging(
    log_dir: str,
    app_name: str = "medical_analyzer",
    level: int = logging.INFO,
    rotation_schedule: str = "daily"
) -> None:
    """
    Setup advanced logging with rotation schedules.
    
    Args:
        log_dir: Directory for log files
        app_name: Application name for log files
        level: Logging level
        rotation_schedule: Rotation schedule ('daily', 'weekly', 'monthly')
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Get rotation schedule
    schedules = create_log_rotation_schedule()
    schedule = schedules.get(rotation_schedule, schedules['daily'])
    
    # Create log file path
    log_file = log_dir / f"{app_name}.log"
    
    # Setup formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create timed rotating file handler
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when=schedule['when'],
        interval=schedule['interval'],
        backupCount=schedule['backup_count'],
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Console handler for development
    if os.getenv('MEDICAL_ANALYZER_DEV', 'false').lower() == 'true':
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
