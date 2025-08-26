"""
Abstract LLM backend interface and base classes.

This module defines the contract for local LLM backends and provides
error handling and graceful degradation capabilities.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum
from ..error_handling.error_handler import (
    ErrorCategory, ErrorSeverity, handle_error, 
    get_error_handler, AnalysisError
)


class LLMError(Exception):
    """Base exception for LLM-related errors."""
    
    def __init__(self, message: str, recoverable: bool = True, backend: Optional[str] = None, 
                 error_type: str = "general", context: Optional[Dict[str, Any]] = None):
        self.message = message
        self.recoverable = recoverable
        self.backend = backend
        self.error_type = error_type
        self.context = context or {}
        super().__init__(message)


class ModelType(Enum):
    """Types of LLM models supported."""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"


@dataclass
class ModelInfo:
    """Information about an LLM model."""
    name: str
    type: ModelType
    context_length: int
    supports_system_prompt: bool = True
    max_tokens: Optional[int] = None
    backend_name: str = ""
    
    def __post_init__(self):
        if self.max_tokens is None:
            # Default to 80% of context length for generation
            self.max_tokens = int(self.context_length * 0.8)


class LLMBackend(ABC):
    """
    Abstract base class for local LLM backends.
    
    This interface ensures all LLM backends provide consistent functionality
    for local medical software analysis without cloud dependencies.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the LLM backend with configuration.
        
        Args:
            config: Backend-specific configuration dictionary
        """
        self.config = config
        self._model_info: Optional[ModelInfo] = None
        
        # Circuit breaker state
        self._failure_count = 0
        self._last_failure_time = None
        self._circuit_open = False
        self._circuit_timeout = 60  # seconds
        self._max_failures = 3
        
        # Error handler
        self._error_handler = get_error_handler()
    
    @abstractmethod
    def generate(
        self, 
        prompt: str, 
        context_chunks: Optional[List[str]] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate text using the local LLM.
        
        Args:
            prompt: The main prompt for generation
            context_chunks: Optional list of context chunks for RAG
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt for instruction
            
        Returns:
            Generated text response
            
        Raises:
            LLMError: If generation fails
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the LLM backend is available and ready.
        
        Returns:
            True if backend is available, False otherwise
        """
        pass
    
    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker is open.
        
        Returns:
            True if circuit is closed (can proceed), False if open
        """
        if not self._circuit_open:
            return True
        
        # Check if timeout has passed
        if self._last_failure_time:
            import time
            if time.time() - self._last_failure_time > self._circuit_timeout:
                self._circuit_open = False
                self._failure_count = 0
                return True
        
        return False
    
    def _record_failure(self):
        """Record a failure and potentially open the circuit breaker."""
        import time
        
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._failure_count >= self._max_failures:
            self._circuit_open = True
            self._error_handler.handle_error(
                category=ErrorCategory.LLM_SERVICE,
                message="Circuit breaker opened due to repeated failures",
                details=f"Failed {self._failure_count} times in {self._circuit_timeout} seconds",
                severity=ErrorSeverity.HIGH,
                recoverable=True,
                stage="llm_generation",
                context={"backend": self.__class__.__name__}
            )
    
    def _record_success(self):
        """Record a successful operation and reset failure count."""
        self._failure_count = 0
        self._circuit_open = False
    
    def _handle_generation_error(self, error: Exception, context: Dict[str, Any]) -> str:
        """Handle generation errors with fallback strategies.
        
        Args:
            error: The original error
            context: Context information about the generation request
            
        Returns:
            Fallback response or raises the error
        """
        # Record the failure
        self._record_failure()
        
        # Log the error
        error_details = {
            "prompt_length": len(context.get("prompt", "")),
            "temperature": context.get("temperature", 0.1),
            "max_tokens": context.get("max_tokens"),
            "backend": self.__class__.__name__
        }
        
        analysis_error = self._error_handler.handle_error(
            category=ErrorCategory.LLM_SERVICE,
            message=f"LLM generation failed: {str(error)}",
            details=f"Context: {error_details}",
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            stage="llm_generation",
            context=error_details,
            exception=error
        )
        
        # Check if we have a fallback handler
        operation = context.get("operation", "text_generation")
        if operation in self._error_handler.fallback_handlers:
            try:
                fallback_result = self._error_handler.fallback_handlers[operation](context)
                return fallback_result
            except Exception as fallback_error:
                self._error_handler.handle_error(
                    category=ErrorCategory.LLM_SERVICE,
                    message="Fallback handler also failed",
                    details=str(fallback_error),
                    severity=ErrorSeverity.HIGH,
                    recoverable=False,
                    stage="llm_fallback",
                    exception=fallback_error
                )
        
        # If no fallback, raise the original error
        raise error
    
    @abstractmethod
    def get_model_info(self) -> ModelInfo:
        """
        Get information about the loaded model.
        
        Returns:
            ModelInfo object with model details
            
        Raises:
            LLMError: If model info cannot be retrieved
        """
        pass
    
    def chunk_content(self, content: str, max_chunk_size: Optional[int] = None) -> List[str]:
        """
        Chunk content to fit within model token limits.
        
        Args:
            content: Content to chunk
            max_chunk_size: Maximum chunk size in characters (estimated)
            
        Returns:
            List of content chunks
        """
        if max_chunk_size is None:
            model_info = self.get_model_info()
            # Rough estimate: 4 characters per token
            max_chunk_size = int(model_info.context_length * 0.6 * 4)
        
        if len(content) <= max_chunk_size:
            return [content]
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(content):
            end_pos = min(current_pos + max_chunk_size, len(content))
            
            # Try to break at natural boundaries (newlines, sentences)
            if end_pos < len(content):
                # Look for newline within last 200 characters
                newline_pos = content.rfind('\n', current_pos, end_pos)
                if newline_pos > current_pos + max_chunk_size * 0.8:
                    end_pos = newline_pos + 1
                else:
                    # Look for sentence end
                    sentence_pos = content.rfind('.', current_pos, end_pos)
                    if sentence_pos > current_pos + max_chunk_size * 0.8:
                        end_pos = sentence_pos + 1
            
            chunks.append(content[current_pos:end_pos])
            current_pos = end_pos
        
        return chunks
    
    def validate_config(self) -> bool:
        """
        Validate the backend configuration.
        
        Returns:
            True if configuration is valid
            
        Raises:
            LLMError: If configuration is invalid
        """
        required_keys = self.get_required_config_keys()
        missing_keys = [key for key in required_keys if key not in self.config]
        
        if missing_keys:
            raise LLMError(
                f"Missing required configuration keys: {missing_keys}",
                recoverable=False,
                backend=self.__class__.__name__
            )
        
        return True
    
    @abstractmethod
    def get_required_config_keys(self) -> List[str]:
        """
        Get list of required configuration keys for this backend.
        
        Returns:
            List of required configuration key names
        """
        pass
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check of the backend.
        
        Returns:
            Dictionary with health check results
        """
        try:
            available = self.is_available()
            model_info = self.get_model_info() if available else None
            
            return {
                "available": available,
                "backend": self.__class__.__name__,
                "model_info": model_info.__dict__ if model_info else None,
                "config_valid": self.validate_config(),
                "error": None
            }
        except Exception as e:
            return {
                "available": False,
                "backend": self.__class__.__name__,
                "model_info": None,
                "config_valid": False,
                "error": str(e)
            }


class FallbackLLMBackend(LLMBackend):
    """
    Fallback LLM backend that provides template-based responses.
    
    This backend is used when no local LLM is available, providing
    graceful degradation with template-based analysis.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._model_info = ModelInfo(
            name="fallback-template",
            type=ModelType.COMPLETION,
            context_length=4096,
            supports_system_prompt=False,
            backend_name="FallbackLLMBackend"
        )
    
    def generate(
        self, 
        prompt: str, 
        context_chunks: Optional[List[str]] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate template-based response.
        
        This provides basic template responses for common analysis tasks
        when no LLM is available.
        """
        # Simple template-based responses for common prompts
        if "extract features" in prompt.lower():
            return "Feature extraction requires a local LLM backend. Please configure a local model."
        elif "generate requirements" in prompt.lower():
            return "Requirement generation requires a local LLM backend. Please configure a local model."
        elif "risk analysis" in prompt.lower():
            return "Risk analysis requires a local LLM backend. Please configure a local model."
        else:
            return "This analysis requires a local LLM backend. Please configure a local model to proceed."
    
    def is_available(self) -> bool:
        """Fallback backend is always available."""
        return True
    
    def get_model_info(self) -> ModelInfo:
        """Return fallback model info."""
        return self._model_info
    
    def get_required_config_keys(self) -> List[str]:
        """Fallback backend requires no configuration."""
        return []