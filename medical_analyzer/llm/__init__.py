"""
LLM integration layer for the Medical Software Analyzer.

This module provides local LLM backend abstractions and implementations
for analyzing medical device software without cloud dependencies.
"""

from .backend import LLMBackend, ModelInfo, LLMError, FallbackLLMBackend
from .config import LLMConfig
from .llama_cpp_backend import LlamaCppBackend
from .local_server_backend import LocalServerBackend
from .embedding_service import EmbeddingService, EmbeddingResult

__all__ = [
    'LLMBackend', 'ModelInfo', 'LLMError', 'LLMConfig',
    'FallbackLLMBackend', 'LlamaCppBackend', 'LocalServerBackend',
    'EmbeddingService', 'EmbeddingResult'
]