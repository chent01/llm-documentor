"""
Unit tests for LLM backend abstraction.

Tests the abstract interface contracts, error handling, and configuration system
for local LLM backends.
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch

from medical_analyzer.llm.backend import (
    LLMBackend, FallbackLLMBackend, LLMError, ModelInfo, ModelType
)
from medical_analyzer.llm.config import LLMConfig, BackendConfig


class MockLLMBackend(LLMBackend):
    """Mock LLM backend for testing."""
    
    def __init__(self, config, available=True, model_info=None):
        super().__init__(config)
        self._available = available
        self._model_info = model_info or ModelInfo(
            name="mock-model",
            type=ModelType.CHAT,
            context_length=4096,
            backend_name="MockLLMBackend"
        )
    
    def generate(self, prompt, context_chunks=None, temperature=0.1, 
                max_tokens=None, system_prompt=None):
        if not self._available:
            raise LLMError("Backend not available", recoverable=False)
        return f"Generated response for: {prompt[:50]}..."
    
    def is_available(self):
        return self._available
    
    def get_model_info(self):
        if not self._available:
            raise LLMError("Model info not available")
        return self._model_info
    
    def get_required_config_keys(self):
        return ["model_path", "api_key"]


class TestLLMBackend:
    """Test cases for LLM backend abstract interface."""
    
    def test_backend_initialization(self):
        """Test backend initialization with config."""
        config = {"model_path": "/path/to/model", "api_key": "test"}
        backend = MockLLMBackend(config)
        assert backend.config == config
    
    def test_generate_method(self):
        """Test text generation method."""
        config = {"model_path": "/path/to/model", "api_key": "test"}
        backend = MockLLMBackend(config)
        
        result = backend.generate("Test prompt")
        assert "Generated response for: Test prompt" in result
    
    def test_generate_with_context(self):
        """Test generation with context chunks."""
        config = {"model_path": "/path/to/model", "api_key": "test"}
        backend = MockLLMBackend(config)
        
        context = ["chunk1", "chunk2"]
        result = backend.generate("Test prompt", context_chunks=context)
        assert "Generated response for: Test prompt" in result
    
    def test_is_available(self):
        """Test availability check."""
        config = {"model_path": "/path/to/model", "api_key": "test"}
        
        # Available backend
        backend = MockLLMBackend(config, available=True)
        assert backend.is_available() is True
        
        # Unavailable backend
        backend = MockLLMBackend(config, available=False)
        assert backend.is_available() is False
    
    def test_get_model_info(self):
        """Test model info retrieval."""
        config = {"model_path": "/path/to/model", "api_key": "test"}
        model_info = ModelInfo(
            name="test-model",
            type=ModelType.COMPLETION,
            context_length=2048,
            backend_name="TestBackend"
        )
        
        backend = MockLLMBackend(config, model_info=model_info)
        info = backend.get_model_info()
        
        assert info.name == "test-model"
        assert info.type == ModelType.COMPLETION
        assert info.context_length == 2048
        assert info.backend_name == "TestBackend"
    
    def test_chunk_content_small(self):
        """Test content chunking for small content."""
        config = {"model_path": "/path/to/model", "api_key": "test"}
        backend = MockLLMBackend(config)
        
        content = "This is a small piece of content."
        chunks = backend.chunk_content(content, max_chunk_size=1000)
        
        assert len(chunks) == 1
        assert chunks[0] == content
    
    def test_chunk_content_large(self):
        """Test content chunking for large content."""
        config = {"model_path": "/path/to/model", "api_key": "test"}
        backend = MockLLMBackend(config)
        
        # Create content larger than chunk size
        content = "This is a sentence. " * 100  # ~2000 characters
        chunks = backend.chunk_content(content, max_chunk_size=500)
        
        assert len(chunks) > 1
        # Verify all content is preserved
        reconstructed = "".join(chunks)
        assert reconstructed == content
    
    def test_chunk_content_with_newlines(self):
        """Test content chunking respects newline boundaries."""
        config = {"model_path": "/path/to/model", "api_key": "test"}
        backend = MockLLMBackend(config)
        
        content = "Line 1\nLine 2\nLine 3\n" * 50
        chunks = backend.chunk_content(content, max_chunk_size=200)
        
        # Most chunks should end with newlines (natural boundaries)
        newline_endings = sum(1 for chunk in chunks[:-1] if chunk.endswith('\n'))
        assert newline_endings > 0
    
    def test_validate_config_valid(self):
        """Test configuration validation with valid config."""
        config = {"model_path": "/path/to/model", "api_key": "test"}
        backend = MockLLMBackend(config)
        
        assert backend.validate_config() is True
    
    def test_validate_config_missing_keys(self):
        """Test configuration validation with missing keys."""
        config = {"model_path": "/path/to/model"}  # Missing api_key
        backend = MockLLMBackend(config)
        
        with pytest.raises(LLMError) as exc_info:
            backend.validate_config()
        
        assert "Missing required configuration keys" in str(exc_info.value)
        assert "api_key" in str(exc_info.value)
    
    def test_health_check_healthy(self):
        """Test health check for healthy backend."""
        config = {"model_path": "/path/to/model", "api_key": "test"}
        backend = MockLLMBackend(config, available=True)
        
        health = backend.health_check()
        
        assert health["available"] is True
        assert health["backend"] == "MockLLMBackend"
        assert health["model_info"] is not None
        assert health["config_valid"] is True
        assert health["error"] is None
    
    def test_health_check_unhealthy(self):
        """Test health check for unhealthy backend."""
        config = {"model_path": "/path/to/model"}  # Missing required key
        backend = MockLLMBackend(config, available=False)
        
        health = backend.health_check()
        
        assert health["available"] is False
        assert health["backend"] == "MockLLMBackend"
        assert health["config_valid"] is False
        assert health["error"] is not None


class TestFallbackLLMBackend:
    """Test cases for fallback LLM backend."""
    
    def test_fallback_initialization(self):
        """Test fallback backend initialization."""
        config = {}
        backend = FallbackLLMBackend(config)
        
        assert backend.is_available() is True
        model_info = backend.get_model_info()
        assert model_info.name == "fallback-template"
        assert model_info.type == ModelType.COMPLETION
    
    def test_fallback_generate_feature_extraction(self):
        """Test fallback generation for feature extraction."""
        config = {}
        backend = FallbackLLMBackend(config)
        
        result = backend.generate("Extract features from this code")
        assert "Feature extraction requires a local LLM backend" in result
    
    def test_fallback_generate_requirements(self):
        """Test fallback generation for requirements."""
        config = {}
        backend = FallbackLLMBackend(config)
        
        result = backend.generate("Generate requirements for this feature")
        assert "Requirement generation requires a local LLM backend" in result
    
    def test_fallback_generate_risk_analysis(self):
        """Test fallback generation for risk analysis."""
        config = {}
        backend = FallbackLLMBackend(config)
        
        result = backend.generate("Perform risk analysis on this code")
        assert "Risk analysis requires a local LLM backend" in result
    
    def test_fallback_generate_generic(self):
        """Test fallback generation for generic prompts."""
        config = {}
        backend = FallbackLLMBackend(config)
        
        result = backend.generate("Some other analysis task")
        assert "This analysis requires a local LLM backend" in result
    
    def test_fallback_no_required_config(self):
        """Test fallback backend requires no configuration."""
        config = {}
        backend = FallbackLLMBackend(config)
        
        assert backend.get_required_config_keys() == []
        assert backend.validate_config() is True


class TestLLMError:
    """Test cases for LLM error handling."""
    
    def test_llm_error_basic(self):
        """Test basic LLM error creation."""
        error = LLMError("Test error message")
        
        assert str(error) == "Test error message"
        assert error.recoverable is True
        assert error.backend is None
    
    def test_llm_error_with_backend(self):
        """Test LLM error with backend information."""
        error = LLMError("Test error", recoverable=False, backend="TestBackend")
        
        assert error.recoverable is False
        assert error.backend == "TestBackend"
    
    def test_llm_error_inheritance(self):
        """Test LLM error inherits from Exception."""
        error = LLMError("Test error")
        assert isinstance(error, Exception)


class TestModelInfo:
    """Test cases for ModelInfo dataclass."""
    
    def test_model_info_basic(self):
        """Test basic ModelInfo creation."""
        info = ModelInfo(
            name="test-model",
            type=ModelType.CHAT,
            context_length=4096
        )
        
        assert info.name == "test-model"
        assert info.type == ModelType.CHAT
        assert info.context_length == 4096
        assert info.supports_system_prompt is True
        assert info.max_tokens == int(4096 * 0.8)  # 80% of context length
    
    def test_model_info_with_max_tokens(self):
        """Test ModelInfo with explicit max_tokens."""
        info = ModelInfo(
            name="test-model",
            type=ModelType.COMPLETION,
            context_length=2048,
            max_tokens=1000
        )
        
        assert info.max_tokens == 1000
    
    def test_model_info_no_system_prompt(self):
        """Test ModelInfo without system prompt support."""
        info = ModelInfo(
            name="test-model",
            type=ModelType.COMPLETION,
            context_length=2048,
            supports_system_prompt=False
        )
        
        assert info.supports_system_prompt is False


if __name__ == "__main__":
    pytest.main([__file__])