"""
Error handling utilities for the Medical Software Analysis Tool.
"""

import logging
import traceback
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime


class ErrorCategory(Enum):
    """Categories of errors that can occur in the application."""
    FILE_SYSTEM = "file_system"
    PARSING = "parsing"
    LLM_SERVICE = "llm_service"
    DATABASE = "database"
    UI = "ui"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Information about an error that occurred."""
    category: ErrorCategory
    message: str
    details: Optional[str] = None
    timestamp: Optional[datetime] = None
    context: Optional[Dict[str, Any]] = None
    traceback_info: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ErrorHandler:
    """Centralized error handling and logging."""
    
    def __init__(self, logger_name: str = __name__):
        """Initialize error handler with logger."""
        self.logger = logging.getLogger(logger_name)
        self.error_history: List[ErrorInfo] = []
        self.max_history_size = 1000
    
    def handle_error(self, 
                    category: ErrorCategory,
                    message: str,
                    exception: Optional[Exception] = None,
                    context: Optional[Dict[str, Any]] = None,
                    log_level: int = logging.ERROR) -> ErrorInfo:
        """
        Handle an error by logging it and storing error information.
        
        Args:
            category: Category of the error
            message: Human-readable error message
            exception: Optional exception that caused the error
            context: Optional context information
            log_level: Logging level to use
            
        Returns:
            ErrorInfo object containing error details
        """
        # Get traceback if exception provided
        traceback_info = None
        details = None
        
        if exception:
            traceback_info = traceback.format_exc()
            details = str(exception)
        
        # Create error info
        error_info = ErrorInfo(
            category=category,
            message=message,
            details=details,
            context=context,
            traceback_info=traceback_info
        )
        
        # Log the error
        log_message = f"[{category.value.upper()}] {message}"
        if details:
            log_message += f" - {details}"
        
        self.logger.log(log_level, log_message)
        
        if traceback_info and log_level >= logging.ERROR:
            self.logger.debug(f"Traceback:\n{traceback_info}")
        
        # Store in history
        self._add_to_history(error_info)
        
        return error_info
    
    def handle_file_error(self, 
                         message: str, 
                         file_path: Optional[str] = None,
                         exception: Optional[Exception] = None) -> ErrorInfo:
        """Handle file system related errors."""
        context = {"file_path": file_path} if file_path else None
        return self.handle_error(
            ErrorCategory.FILE_SYSTEM,
            message,
            exception,
            context
        )
    
    def handle_parsing_error(self,
                           message: str,
                           file_path: Optional[str] = None,
                           line_number: Optional[int] = None,
                           exception: Optional[Exception] = None) -> ErrorInfo:
        """Handle parsing related errors."""
        context = {}
        if file_path:
            context["file_path"] = file_path
        if line_number:
            context["line_number"] = line_number
        
        return self.handle_error(
            ErrorCategory.PARSING,
            message,
            exception,
            context if context else None
        )
    
    def handle_llm_error(self,
                        message: str,
                        backend_type: Optional[str] = None,
                        exception: Optional[Exception] = None) -> ErrorInfo:
        """Handle LLM service related errors."""
        context = {"backend_type": backend_type} if backend_type else None
        return self.handle_error(
            ErrorCategory.LLM_SERVICE,
            message,
            exception,
            context
        )
    
    def handle_database_error(self,
                            message: str,
                            operation: Optional[str] = None,
                            exception: Optional[Exception] = None) -> ErrorInfo:
        """Handle database related errors."""
        context = {"operation": operation} if operation else None
        return self.handle_error(
            ErrorCategory.DATABASE,
            message,
            exception,
            context
        )
    
    def handle_ui_error(self,
                       message: str,
                       widget_name: Optional[str] = None,
                       exception: Optional[Exception] = None) -> ErrorInfo:
        """Handle UI related errors."""
        context = {"widget_name": widget_name} if widget_name else None
        return self.handle_error(
            ErrorCategory.UI,
            message,
            exception,
            context,
            log_level=logging.WARNING  # UI errors are often less critical
        )
    
    def handle_validation_error(self,
                              message: str,
                              field_name: Optional[str] = None,
                              value: Optional[Any] = None,
                              exception: Optional[Exception] = None) -> ErrorInfo:
        """Handle validation related errors."""
        context = {}
        if field_name:
            context["field_name"] = field_name
        if value is not None:
            context["value"] = str(value)
        
        return self.handle_error(
            ErrorCategory.VALIDATION,
            message,
            exception,
            context if context else None,
            log_level=logging.WARNING
        )
    
    def _add_to_history(self, error_info: ErrorInfo):
        """Add error to history, maintaining size limit."""
        self.error_history.append(error_info)
        
        # Trim history if too large
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]
    
    def get_recent_errors(self, 
                         count: int = 10,
                         category: Optional[ErrorCategory] = None) -> List[ErrorInfo]:
        """Get recent errors, optionally filtered by category."""
        errors = self.error_history
        
        if category:
            errors = [e for e in errors if e.category == category]
        
        return errors[-count:] if count > 0 else errors
    
    def clear_history(self):
        """Clear error history."""
        self.error_history.clear()
        self.logger.info("Error history cleared")
    
    def get_error_summary(self) -> Dict[str, int]:
        """Get summary of errors by category."""
        summary = {}
        for error in self.error_history:
            category_name = error.category.value
            summary[category_name] = summary.get(category_name, 0) + 1
        
        return summary
    
    def has_critical_errors(self) -> bool:
        """Check if there are any critical errors in recent history."""
        critical_categories = {
            ErrorCategory.DATABASE,
            ErrorCategory.CONFIGURATION,
            ErrorCategory.LLM_SERVICE
        }
        
        return any(
            error.category in critical_categories 
            for error in self.error_history[-50:]  # Check last 50 errors
        )


# Global error handler instance
_global_error_handler = None


def get_error_handler(logger_name: str = __name__) -> ErrorHandler:
    """Get global error handler instance."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler(logger_name)
    return _global_error_handler


def handle_error(category: ErrorCategory,
                message: str,
                exception: Optional[Exception] = None,
                context: Optional[Dict[str, Any]] = None) -> ErrorInfo:
    """Convenience function to handle errors using global handler."""
    return get_error_handler().handle_error(category, message, exception, context)