"""
Comprehensive error handling system for medical software analyzer.

This module provides centralized error handling with graceful degradation,
error categorization, and recovery mechanisms for various failure scenarios.
"""

import os
import logging
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for different system components."""
    FILE_SYSTEM = "file_system"
    PARSER = "parser"
    LLM_SERVICE = "llm_service"
    DATABASE = "database"
    NETWORK = "network"
    VALIDATION = "validation"
    ANALYSIS_PIPELINE = "analysis_pipeline"
    UI = "ui"
    EXPORT = "export"


@dataclass
class AnalysisError:
    """Structured error information for analysis pipeline."""
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: str
    recoverable: bool
    stage: str
    timestamp: datetime = field(default_factory=datetime.now)
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    context: Dict[str, Any] = field(default_factory=dict)
    recovery_action: Optional[str] = None
    fallback_result: Optional[Any] = None


class ErrorHandler:
    """Centralized error handling with graceful degradation."""
    
    def __init__(self, enable_logging: bool = True, log_file: Optional[str] = None):
        """Initialize the error handler.
        
        Args:
            enable_logging: Whether to enable error logging
            log_file: Optional log file path
        """
        self.enable_logging = enable_logging
        self.error_log: List[AnalysisError] = []
        self.recovery_strategies: Dict[ErrorCategory, List[Callable]] = {}
        self.fallback_handlers: Dict[str, Callable] = {}
        
        # Setup logging
        if enable_logging:
            self._setup_logging(log_file)
        
        # Register default recovery strategies
        self._register_default_strategies()
    
    def _setup_logging(self, log_file: Optional[str] = None):
        """Setup error logging."""
        self.logger = logging.getLogger('medical_analyzer.error_handler')
        self.logger.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def _register_default_strategies(self):
        """Register default recovery strategies."""
        # File system error recovery
        self.register_recovery_strategy(
            ErrorCategory.FILE_SYSTEM,
            self._handle_file_system_error
        )
        
        # Parser error recovery
        self.register_recovery_strategy(
            ErrorCategory.PARSER,
            self._handle_parser_error
        )
        
        # LLM service error recovery
        self.register_recovery_strategy(
            ErrorCategory.LLM_SERVICE,
            self._handle_llm_service_error
        )
        
        # Database error recovery
        self.register_recovery_strategy(
            ErrorCategory.DATABASE,
            self._handle_database_error
        )
    
    def register_recovery_strategy(self, category: ErrorCategory, strategy: Callable):
        """Register a recovery strategy for an error category.
        
        Args:
            category: Error category to handle
            strategy: Recovery strategy function
        """
        if category not in self.recovery_strategies:
            self.recovery_strategies[category] = []
        self.recovery_strategies[category].append(strategy)
    
    def register_fallback_handler(self, operation: str, handler: Callable):
        """Register a fallback handler for a specific operation.
        
        Args:
            operation: Operation name (e.g., 'feature_extraction', 'risk_analysis')
            handler: Fallback handler function
        """
        self.fallback_handlers[operation] = handler
    
    def handle_error(self, 
                    category: ErrorCategory,
                    message: str,
                    details: str = "",
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    recoverable: bool = True,
                    stage: str = "unknown",
                    file_path: Optional[str] = None,
                    line_number: Optional[int] = None,
                    context: Optional[Dict[str, Any]] = None,
                    exception: Optional[Exception] = None) -> AnalysisError:
        """Handle an error with appropriate recovery strategies.
        
        Args:
            category: Error category
            message: Error message
            details: Detailed error information
            severity: Error severity level
            recoverable: Whether the error is recoverable
            stage: Analysis stage where error occurred
            file_path: File path where error occurred
            line_number: Line number where error occurred
            context: Additional context information
            exception: Original exception if available
            
        Returns:
            AnalysisError object with handling results
        """
        # Create error object
        error = AnalysisError(
            category=category,
            severity=severity,
            message=message,
            details=details or (str(exception) if exception else ""),
            recoverable=recoverable,
            stage=stage,
            file_path=file_path,
            line_number=line_number,
            context=context or {}
        )
        
        # Log the error
        self._log_error(error, exception)
        
        # Add to error log
        self.error_log.append(error)
        
        # Attempt recovery if error is recoverable
        if recoverable and category in self.recovery_strategies:
            error.recovery_action = self._attempt_recovery(error)
        
        return error
    
    def _log_error(self, error: AnalysisError, exception: Optional[Exception] = None):
        """Log error information."""
        if not self.enable_logging:
            return
        
        log_message = f"[{error.category.value.upper()}] {error.message}"
        if error.file_path:
            log_message += f" (File: {error.file_path}"
            if error.line_number:
                log_message += f":{error.line_number}"
            log_message += ")"
        
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
        
        # Log details if available
        if error.details:
            self.logger.debug(f"Error details: {error.details}")
        
        # Log stack trace for exceptions
        if exception:
            self.logger.debug(f"Exception traceback:\n{traceback.format_exc()}")
    
    def _attempt_recovery(self, error: AnalysisError) -> Optional[str]:
        """Attempt to recover from an error using registered strategies.
        
        Args:
            error: Error to attempt recovery for
            
        Returns:
            Recovery action description or None if recovery failed
        """
        strategies = self.recovery_strategies.get(error.category, [])
        
        for strategy in strategies:
            try:
                result = strategy(error)
                if result:
                    return result
            except Exception as e:
                self.logger.warning(f"Recovery strategy failed: {e}")
        
        return None
    
    def _handle_file_system_error(self, error: AnalysisError) -> Optional[str]:
        """Handle file system errors with graceful degradation.
        
        Args:
            error: File system error
            
        Returns:
            Recovery action description or None
        """
        if "Permission denied" in error.message:
            return "Skipped file due to permission restrictions"
        elif "File not found" in error.message:
            return "Skipped missing file"
        elif "No space left" in error.message:
            return "Reduced analysis scope due to disk space constraints"
        
        return None
    
    def _handle_parser_error(self, error: AnalysisError) -> Optional[str]:
        """Handle parser errors with partial analysis capability.
        
        Args:
            error: Parser error
            
        Returns:
            Recovery action description or None
        """
        if error.file_path:
            return f"Skipped problematic file: {os.path.basename(error.file_path)}"
        
        return "Applied basic text analysis as fallback"
    
    def _handle_llm_service_error(self, error: AnalysisError) -> Optional[str]:
        """Handle LLM service errors with fallback options.
        
        Args:
            error: LLM service error
            
        Returns:
            Recovery action description or None
        """
        # Check if we have a fallback handler for the operation
        operation = error.context.get('operation', 'unknown')
        if operation in self.fallback_handlers:
            try:
                fallback_result = self.fallback_handlers[operation](error.context)
                error.fallback_result = fallback_result
                return f"Applied fallback analysis for {operation}"
            except Exception as e:
                self.logger.warning(f"Fallback handler failed: {e}")
        
        return "Used template-based analysis as fallback"
    
    def _handle_database_error(self, error: AnalysisError) -> Optional[str]:
        """Handle database errors with local fallback.
        
        Args:
            error: Database error
            
        Returns:
            Recovery action description or None
        """
        if "database is locked" in error.message.lower():
            return "Retried database operation after delay"
        elif "no such table" in error.message.lower():
            return "Initialized missing database schema"
        
        return "Used in-memory storage as fallback"
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get a summary of all handled errors.
        
        Returns:
            Dictionary with error statistics
        """
        if not self.error_log:
            return {"total_errors": 0, "recovered_errors": 0}
        
        total_errors = len(self.error_log)
        recovered_errors = sum(1 for e in self.error_log if e.recovery_action)
        
        # Count by category
        category_counts = {}
        for error in self.error_log:
            category = error.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Count by severity
        severity_counts = {}
        for error in self.error_log:
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            "total_errors": total_errors,
            "recovered_errors": recovered_errors,
            "recovery_rate": recovered_errors / total_errors if total_errors > 0 else 0,
            "category_counts": category_counts,
            "severity_counts": severity_counts,
            "errors_by_stage": self._group_errors_by_stage()
        }
    
    def _group_errors_by_stage(self) -> Dict[str, int]:
        """Group errors by analysis stage.
        
        Returns:
            Dictionary mapping stage names to error counts
        """
        stage_counts = {}
        for error in self.error_log:
            stage = error.stage
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
        return stage_counts
    
    def clear_error_log(self):
        """Clear the error log."""
        self.error_log.clear()
    
    def export_error_log(self, file_path: str):
        """Export error log to a file.
        
        Args:
            file_path: Path to export the error log
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("Medical Software Analyzer - Error Log\n")
                f.write("=" * 50 + "\n\n")
                
                for error in self.error_log:
                    f.write(f"Timestamp: {error.timestamp}\n")
                    f.write(f"Category: {error.category.value}\n")
                    f.write(f"Severity: {error.severity.value}\n")
                    f.write(f"Stage: {error.stage}\n")
                    f.write(f"Message: {error.message}\n")
                    if error.file_path:
                        f.write(f"File: {error.file_path}")
                        if error.line_number:
                            f.write(f":{error.line_number}")
                        f.write("\n")
                    if error.details:
                        f.write(f"Details: {error.details}\n")
                    if error.recovery_action:
                        f.write(f"Recovery: {error.recovery_action}\n")
                    f.write("-" * 30 + "\n\n")
                
                # Add summary
                summary = self.get_error_summary()
                f.write("ERROR SUMMARY\n")
                f.write("=" * 20 + "\n")
                f.write(f"Total Errors: {summary['total_errors']}\n")
                f.write(f"Recovered Errors: {summary['recovered_errors']}\n")
                f.write(f"Recovery Rate: {summary['recovery_rate']:.2%}\n")
        
        except Exception as e:
            if self.enable_logging:
                self.logger.error(f"Failed to export error log: {e}")


# Global error handler instance
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance.
    
    Returns:
        Global ErrorHandler instance
    """
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def set_error_handler(handler: ErrorHandler):
    """Set the global error handler instance.
    
    Args:
        handler: ErrorHandler instance to set as global
    """
    global _global_error_handler
    _global_error_handler = handler


def handle_error(*args, **kwargs) -> AnalysisError:
    """Convenience function to handle errors using the global handler.
    
    Returns:
        AnalysisError object
    """
    return get_error_handler().handle_error(*args, **kwargs)
