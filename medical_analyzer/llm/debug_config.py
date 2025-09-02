"""
Debug configuration and logging setup for LLM backends.

This module provides utilities for configuring detailed logging and debugging
for local LLM backends, especially useful for troubleshooting connection issues
and performance problems.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class LLMDebugConfig:
    """Configuration manager for LLM debugging and logging."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize debug configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.log_dir = Path(self.config.get('log_dir', Path.home() / '.medical_analyzer' / 'logs'))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Debug levels
        self.debug_level = self.config.get('debug_level', 'INFO')
        self.enable_file_logging = self.config.get('enable_file_logging', True)
        self.enable_console_logging = self.config.get('enable_console_logging', True)
        
        # Specialized logging options
        self.log_requests = self.config.get('log_requests', False)
        self.log_responses = self.config.get('log_responses', False)
        self.log_connections = self.config.get('log_connections', True)
        self.log_performance = self.config.get('log_performance', True)
        self.log_model_operations = self.config.get('log_model_operations', True)
        self.log_errors = self.config.get('log_errors', True)
        
        # File rotation settings
        self.max_log_size = self.config.get('max_log_size', 10 * 1024 * 1024)  # 10MB
        self.backup_count = self.config.get('backup_count', 5)
        
        # Performance settings
        self.log_slow_requests = self.config.get('log_slow_requests', True)
        self.slow_request_threshold = self.config.get('slow_request_threshold', 5.0)  # seconds
        
        self._loggers_configured = False
    
    def setup_llm_logging(self) -> None:
        """Set up comprehensive logging for LLM backends."""
        if self._loggers_configured:
            return
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Set up main LLM logger
        self._setup_logger('medical_analyzer.llm', 'llm_main.log', detailed_formatter)
        
        # Set up specialized loggers
        if self.log_connections:
            self._setup_logger('medical_analyzer.llm.local_server_backend.connection', 
                             'llm_connections.log', detailed_formatter)
            self._setup_logger('medical_analyzer.llm.llama_cpp_backend.model', 
                             'llm_model.log', detailed_formatter)
        
        if self.log_performance:
            self._setup_logger('medical_analyzer.llm.local_server_backend.performance', 
                             'llm_performance.log', simple_formatter)
            self._setup_logger('medical_analyzer.llm.llama_cpp_backend.performance', 
                             'llm_performance.log', simple_formatter)
        
        if self.log_requests:
            self._setup_logger('medical_analyzer.llm.local_server_backend.requests', 
                             'llm_requests.log', detailed_formatter)
        
        if self.log_responses:
            self._setup_logger('medical_analyzer.llm.local_server_backend.responses', 
                             'llm_responses.log', detailed_formatter)
        
        if self.log_model_operations:
            self._setup_logger('medical_analyzer.llm.llama_cpp_backend.generation', 
                             'llm_generation.log', detailed_formatter)
        
        if self.log_errors:
            self._setup_logger('medical_analyzer.llm.local_server_backend.errors', 
                             'llm_errors.log', detailed_formatter)
            self._setup_logger('medical_analyzer.llm.llama_cpp_backend.errors', 
                             'llm_errors.log', detailed_formatter)
        
        # Set up debug loggers
        self._setup_logger('medical_analyzer.llm.local_server_backend.debug', 
                         'llm_debug.log', detailed_formatter)
        self._setup_logger('medical_analyzer.llm.llama_cpp_backend.debug', 
                         'llm_debug.log', detailed_formatter)
        
        self._loggers_configured = True
        
        # Log configuration summary
        main_logger = logging.getLogger('medical_analyzer.llm')
        main_logger.info("LLM debugging configured")
        main_logger.info(f"Log directory: {self.log_dir}")
        main_logger.info(f"Debug level: {self.debug_level}")
        main_logger.info(f"Specialized logging: connections={self.log_connections}, "
                        f"performance={self.log_performance}, requests={self.log_requests}, "
                        f"responses={self.log_responses}")
    
    def _setup_logger(self, logger_name: str, log_file: str, formatter: logging.Formatter) -> None:
        """Set up a specific logger with file and console handlers."""
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, self.debug_level.upper()))
        
        # Clear existing handlers to avoid duplicates
        logger.handlers.clear()
        
        # File handler with rotation
        if self.enable_file_logging:
            log_path = self.log_dir / log_file
            file_handler = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=self.max_log_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        # Console handler
        if self.enable_console_logging:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            
            # Only show INFO and above on console for specialized loggers
            if 'connection' in logger_name or 'performance' in logger_name:
                console_handler.setLevel(logging.INFO)
            elif 'requests' in logger_name or 'responses' in logger_name:
                console_handler.setLevel(logging.WARNING)  # Reduce console noise
            else:
                console_handler.setLevel(getattr(logging, self.debug_level.upper()))
            
            logger.addHandler(console_handler)
        
        # Prevent propagation to avoid duplicate messages
        logger.propagate = False
    
    def enable_verbose_debugging(self) -> None:
        """Enable maximum verbosity for debugging."""
        self.debug_level = 'DEBUG'
        self.log_requests = True
        self.log_responses = True
        self.log_connections = True
        self.log_performance = True
        self.log_model_operations = True
        self.log_errors = True
        
        # Reconfigure loggers
        self._loggers_configured = False
        self.setup_llm_logging()
        
        logger = logging.getLogger('medical_analyzer.llm')
        logger.info("Verbose debugging enabled - all LLM operations will be logged")
    
    def enable_performance_only(self) -> None:
        """Enable only performance and error logging."""
        self.debug_level = 'INFO'
        self.log_requests = False
        self.log_responses = False
        self.log_connections = True
        self.log_performance = True
        self.log_model_operations = False
        self.log_errors = True
        
        # Reconfigure loggers
        self._loggers_configured = False
        self.setup_llm_logging()
        
        logger = logging.getLogger('medical_analyzer.llm')
        logger.info("Performance-only logging enabled")
    
    def disable_debug_logging(self) -> None:
        """Disable debug logging, keep only warnings and errors."""
        self.debug_level = 'WARNING'
        self.log_requests = False
        self.log_responses = False
        self.log_connections = False
        self.log_performance = False
        self.log_model_operations = False
        self.log_errors = True
        
        # Reconfigure loggers
        self._loggers_configured = False
        self.setup_llm_logging()
        
        logger = logging.getLogger('medical_analyzer.llm')
        logger.warning("Debug logging disabled - only warnings and errors will be logged")
    
    def create_debug_session(self, session_name: str) -> str:
        """
        Create a new debug session with timestamped logs.
        
        Args:
            session_name: Name for the debug session
            
        Returns:
            Path to the session log directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = self.log_dir / f"debug_session_{session_name}_{timestamp}"
        session_dir.mkdir(exist_ok=True)
        
        # Update log directory for this session
        old_log_dir = self.log_dir
        self.log_dir = session_dir
        
        # Reconfigure loggers for the session
        self._loggers_configured = False
        self.enable_verbose_debugging()
        
        logger = logging.getLogger('medical_analyzer.llm')
        logger.info(f"Debug session '{session_name}' started")
        logger.info(f"Session logs: {session_dir}")
        
        return str(session_dir)
    
    def get_log_summary(self) -> Dict[str, Any]:
        """Get summary of current logging configuration."""
        return {
            'log_directory': str(self.log_dir),
            'debug_level': self.debug_level,
            'file_logging': self.enable_file_logging,
            'console_logging': self.enable_console_logging,
            'specialized_logging': {
                'requests': self.log_requests,
                'responses': self.log_responses,
                'connections': self.log_connections,
                'performance': self.log_performance,
                'model_operations': self.log_model_operations,
                'errors': self.log_errors
            },
            'performance_settings': {
                'log_slow_requests': self.log_slow_requests,
                'slow_request_threshold': self.slow_request_threshold
            },
            'file_settings': {
                'max_log_size': self.max_log_size,
                'backup_count': self.backup_count
            }
        }


def setup_llm_debugging(config: Optional[Dict[str, Any]] = None) -> LLMDebugConfig:
    """
    Set up LLM debugging with the specified configuration.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        LLMDebugConfig instance
    """
    debug_config = LLMDebugConfig(config)
    debug_config.setup_llm_logging()
    return debug_config


def enable_verbose_llm_debugging() -> LLMDebugConfig:
    """
    Enable verbose debugging for all LLM operations.
    
    Returns:
        LLMDebugConfig instance with verbose debugging enabled
    """
    debug_config = LLMDebugConfig()
    debug_config.enable_verbose_debugging()
    return debug_config


def create_llm_debug_session(session_name: str) -> str:
    """
    Create a new LLM debug session with comprehensive logging.
    
    Args:
        session_name: Name for the debug session
        
    Returns:
        Path to the session log directory
    """
    debug_config = LLMDebugConfig()
    return debug_config.create_debug_session(session_name)


# Convenience function for quick debugging setup
def quick_debug_setup(level: str = "DEBUG") -> None:
    """
    Quick setup for LLM debugging.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    config = {
        'debug_level': level,
        'log_connections': True,
        'log_performance': True,
        'log_errors': True,
        'log_requests': level == "DEBUG",
        'log_responses': level == "DEBUG"
    }
    
    debug_config = LLMDebugConfig(config)
    debug_config.setup_llm_logging()
    
    logger = logging.getLogger('medical_analyzer.llm')
    logger.info(f"Quick debug setup completed with level: {level}")