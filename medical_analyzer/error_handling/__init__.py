"""
Error handling and management for the Medical Software Analysis Tool.

This module provides centralized error handling, error categorization,
and error recovery mechanisms for the application.
"""

from .error_handler import ErrorHandler, AnalysisError, ErrorCategory, ErrorSeverity

__all__ = ['ErrorHandler', 'AnalysisError', 'ErrorCategory', 'ErrorSeverity']
