"""
Unit tests for LLM configuration system.

Tests configuration loading, saving, validation, and backend management
for the local LLM integration layer.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from medical_analyzer.llm.config import (
    LLMConfig, BackendConfig, get_config_path, load_config, save_config
)


class TestBackendConfig:
    """Test cases for BackendConfig dataclass."""
    
    def test_backend_config_creation(self):
        """Test basic BackendConfig creation."""
        config = BackendConfig(
            name="test-backend",
            backend_type="TestBackend",
            enabled=True,
            config={"key": "value"},
            priority=2
        )
        
        assert config.name == "test-backend"
        assert config.backend_type == "TestBackend"
        assert config.enabled is True
        assert config.config == {"key": "value"}
        assert config.priority == 2
    
    def test_backend_config_defaults(self):
        """Test BackendConfig with default values."""
        config = BackendConfig(
            name="test-backend",
            backend_type="TestBackend"
        )
        
        assert config.enabled is True
        assert config.config == {}
        assert config.priority == 1


class TestLLMConfig:
    """Test cases for LLMConfig class."""
    
    def test_llm_config_creation(self):
        """Test basic LLMConfig creation."""
        backend = BackendConfig("test", "TestBackend")
        config = LLMConfig(
            backends=[backend],
            default_temperature=0.2,
            default_max_tokens=1024,
            enable_fallback=False,
            chunk_overlap=100
        )
        
        assert len(config.backends) == 1
        assert config.default_temperature == 0.2
        assert config.default_max_tokens == 1024
        assert config.enable_fallback is False
        assert config.chunk_overlap == 100
    
    def test_llm_config_defaults(self):
        """Test LLMConfig with default values."""
        config = LLMConfig()
        
        assert config.backends == []
        assert config.default_temperature == 0.1
        assert config.default_max_tokens == 2048
        assert config.enable_fallback is True
        assert config.chunk_overlap == 200
    
    def test_get_default_config(self):
        """Test getting default configuration."""
        config = LLMConfig.get_default_config()
        
        assert len(config.backends) == 3  # llama-cpp, local-server, fallback
        
        # Check backend names
        backend_names = [b.name for b in config.backends]
        assert "llama-cpp" in backend_names
        assert "local-server" in backend_names
        assert "fallback" in backend_names
        
        # Check priorities
        llama_cpp = next(b for b in config.backends if b.name == "llama-cpp")
        local_server = next(b for b in config.backends if b.name == "local-server")
        fallback = next(b for b in config.backends if b.name == "fallback")
        
        assert llama_cpp.priority == 3
        assert local_server.priority == 2
        assert fallback.priority == 1
    
    def test_get_enabled_backends(self):
        """Test getting enabled backends sorted by priority."""
        backends = [
            BackendConfig("backend1", "Type1", enabled=True, priority=1),
            BackendConfig("backend2", "Type2", enabled=False, priority=3),
            BackendConfig("backend3", "Type3", enabled=True, priority=2)
        ]
        config = LLMConfig(backends=backends)
        
        enabled = config.get_enabled_backends()
        
        assert len(enabled) == 2
        assert enabled[0].name == "backend3"  # Priority 2
        assert enabled[1].name == "backend1"  # Priority 1
    
    def test_get_backend_config(self):
        """Test getting backend config by name."""
        backend = BackendConfig("test-backend", "TestBackend")
        config = LLMConfig(backends=[backend])
        
        found = config.get_backend_config("test-backend")
        assert found is not None
        assert found.name == "test-backend"
        
        not_found = config.get_backend_config("nonexistent")
        assert not_found is None
    
    def test_add_backend(self):
        """Test adding a backend configuration."""
        config = LLMConfig()
        backend = BackendConfig("new-backend", "NewBackend")
        
        config.add_backend(backend)
        
        assert len(config.backends) == 1
        assert config.backends[0].name == "new-backend"
    
    def test_add_backend_replace_existing(self):
        """Test adding backend replaces existing with same name."""
        existing = BackendConfig("test-backend", "OldBackend")
        config = LLMConfig(backends=[existing])
        
        new_backend = BackendConfig("test-backend", "NewBackend")
        config.add_backend(new_backend)
        
        assert len(config.backends) == 1
        assert config.backends[0].backend_type == "NewBackend"
    
    def test_remove_backend(self):
        """Test removing a backend configuration."""
        backend = BackendConfig("test-backend", "TestBackend")
        config = LLMConfig(backends=[backend])
        
        removed = config.remove_backend("test-backend")
        assert removed is True
        assert len(config.backends) == 0
        
        not_removed = config.remove_backend("nonexistent")
        assert not_removed is False
    
    def test_validate_valid_config(self):
        """Test validation of valid configuration."""
        backend = BackendConfig("test", "TestBackend", priority=2)
        config = LLMConfig(
            backends=[backend],
            default_temperature=0.5,
            default_max_tokens=1024,
            chunk_overlap=100
        )
        
        errors = config.validate()
        assert errors == []
    
    def test_validate_no_backends(self):
        """Test validation with no backends."""
        config = LLMConfig()
        
        errors = config.validate()
        assert "No backends configured" in errors
    
    def test_validate_invalid_temperature(self):
        """Test validation with invalid temperature."""
        backend = BackendConfig("test", "TestBackend")
        config = LLMConfig(backends=[backend], default_temperature=1.5)
        
        errors = config.validate()
        assert any("temperature must be between 0 and 1" in error for error in errors)
    
    def test_validate_invalid_max_tokens(self):
        """Test validation with invalid max_tokens."""
        backend = BackendConfig("test", "TestBackend")
        config = LLMConfig(backends=[backend], default_max_tokens=-100)
        
        errors = config.validate()
        assert any("max_tokens must be positive" in error for error in errors)
    
    def test_validate_negative_chunk_overlap(self):
        """Test validation with negative chunk overlap."""
        backend = BackendConfig("test", "TestBackend")
        config = LLMConfig(backends=[backend], chunk_overlap=-50)
        
        errors = config.validate()
        assert any("chunk_overlap must be non-negative" in error for error in errors)
    
    def test_validate_duplicate_backend_names(self):
        """Test validation with duplicate backend names."""
        backends = [
            BackendConfig("duplicate", "Type1"),
            BackendConfig("duplicate", "Type2")
        ]
        config = LLMConfig(backends=backends)
        
        errors = config.validate()
        assert any("Duplicate backend names" in error for error in errors)
    
    def test_validate_empty_backend_name(self):
        """Test validation with empty backend name."""
        backend = BackendConfig("", "TestBackend")
        config = LLMConfig(backends=[backend])
        
        errors = config.validate()
        assert any("Backend name cannot be empty" in error for error in errors)
    
    def test_validate_empty_backend_type(self):
        """Test validation with empty backend type."""
        backend = BackendConfig("test", "")
        config = LLMConfig(backends=[backend])
        
        errors = config.validate()
        assert any("Backend type cannot be empty" in error for error in errors)
    
    def test_validate_invalid_priority(self):
        """Test validation with invalid priority."""
        backend = BackendConfig("test", "TestBackend", priority=0)
        config = LLMConfig(backends=[backend])
        
        errors = config.validate()
        assert any("Backend priority must be >= 1" in error for error in errors)


class TestLLMConfigFileOperations:
    """Test cases for LLM config file operations."""
    
    def test_save_and_load_config(self):
        """Test saving and loading configuration to/from file."""
        backend = BackendConfig(
            name="test-backend",
            backend_type="TestBackend",
            enabled=True,
            config={"key": "value"},
            priority=2
        )
        original_config = LLMConfig(
            backends=[backend],
            default_temperature=0.3,
            default_max_tokens=1500,
            enable_fallback=False,
            chunk_overlap=150
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = f.name
        
        try:
            # Save config
            original_config.save_to_file(config_path)
            
            # Load config
            loaded_config = LLMConfig.load_from_file(config_path)
            
            # Verify loaded config matches original
            assert len(loaded_config.backends) == 1
            assert loaded_config.backends[0].name == "test-backend"
            assert loaded_config.backends[0].backend_type == "TestBackend"
            assert loaded_config.backends[0].enabled is True
            assert loaded_config.backends[0].config == {"key": "value"}
            assert loaded_config.backends[0].priority == 2
            
            assert loaded_config.default_temperature == 0.3
            assert loaded_config.default_max_tokens == 1500
            assert loaded_config.enable_fallback is False
            assert loaded_config.chunk_overlap == 150
            
        finally:
            os.unlink(config_path)
    
    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file returns default config."""
        config = LLMConfig.load_from_file("/nonexistent/path/config.json")
        
        # Should return default config
        assert len(config.backends) == 3  # Default has 3 backends
        assert config.default_temperature == 0.1
        assert config.enable_fallback is True
    
    def test_load_invalid_json(self):
        """Test loading invalid JSON file raises ValueError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            config_path = f.name
        
        try:
            with pytest.raises(ValueError) as exc_info:
                LLMConfig.load_from_file(config_path)
            
            assert "Invalid configuration file" in str(exc_info.value)
            
        finally:
            os.unlink(config_path)
    
    def test_save_creates_directory(self):
        """Test saving config creates directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "subdir", "config.json")
            config = LLMConfig.get_default_config()
            
            # Directory doesn't exist yet
            assert not os.path.exists(os.path.dirname(config_path))
            
            config.save_to_file(config_path)
            
            # Directory should be created and file should exist
            assert os.path.exists(config_path)
            assert os.path.isfile(config_path)


class TestConfigUtilityFunctions:
    """Test cases for configuration utility functions."""
    
    def test_get_config_path(self):
        """Test getting default config path."""
        config_path = get_config_path()
        
        assert config_path.endswith("llm_config.json")
        assert ".medical_analyzer" in config_path
    
    @patch('medical_analyzer.llm.config.get_config_path')
    def test_load_config_function(self, mock_get_path):
        """Test load_config utility function."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = f.name
            # Write minimal valid config
            json.dump({
                "backends": [],
                "default_temperature": 0.2
            }, f)
        
        mock_get_path.return_value = config_path
        
        try:
            config = load_config()
            assert config.default_temperature == 0.2
            
        finally:
            os.unlink(config_path)
    
    @patch('medical_analyzer.llm.config.get_config_path')
    def test_save_config_function(self, mock_get_path):
        """Test save_config utility function."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = f.name
        
        mock_get_path.return_value = config_path
        
        try:
            config = LLMConfig(default_temperature=0.7)
            save_config(config)
            
            # Verify file was written
            with open(config_path, 'r') as f:
                data = json.load(f)
            
            assert data["default_temperature"] == 0.7
            
        finally:
            os.unlink(config_path)


if __name__ == "__main__":
    pytest.main([__file__])