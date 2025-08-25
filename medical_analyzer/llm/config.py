"""
Configuration system for LLM backends.

This module provides configuration management for different local LLM backends,
supporting multiple backend types with validation and defaults.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from pathlib import Path


@dataclass
class BackendConfig:
    """Configuration for a specific LLM backend."""
    name: str
    backend_type: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1  # Higher priority backends are tried first


@dataclass
class LLMConfig:
    """
    Main configuration class for LLM backends.
    
    Manages multiple backend configurations with fallback support
    and graceful degradation when backends are unavailable.
    """
    backends: List[BackendConfig] = field(default_factory=list)
    default_temperature: float = 0.1
    default_max_tokens: int = 2048
    enable_fallback: bool = True
    chunk_overlap: int = 200  # Characters of overlap between chunks
    
    @classmethod
    def load_from_file(cls, config_path: str) -> 'LLMConfig':
        """
        Load configuration from a JSON file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            LLMConfig instance
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is invalid
        """
        if not os.path.exists(config_path):
            # Return default configuration if file doesn't exist
            return cls.get_default_config()
        
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            
            backends = []
            for backend_data in data.get('backends', []):
                backends.append(BackendConfig(
                    name=backend_data['name'],
                    backend_type=backend_data['backend_type'],
                    enabled=backend_data.get('enabled', True),
                    config=backend_data.get('config', {}),
                    priority=backend_data.get('priority', 1)
                ))
            
            return cls(
                backends=backends,
                default_temperature=data.get('default_temperature', 0.1),
                default_max_tokens=data.get('default_max_tokens', 2048),
                enable_fallback=data.get('enable_fallback', True),
                chunk_overlap=data.get('chunk_overlap', 200)
            )
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid configuration file: {e}")
    
    def save_to_file(self, config_path: str) -> None:
        """
        Save configuration to a JSON file.
        
        Args:
            config_path: Path where to save the configuration
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        data = {
            'backends': [
                {
                    'name': backend.name,
                    'backend_type': backend.backend_type,
                    'enabled': backend.enabled,
                    'config': backend.config,
                    'priority': backend.priority
                }
                for backend in self.backends
            ],
            'default_temperature': self.default_temperature,
            'default_max_tokens': self.default_max_tokens,
            'enable_fallback': self.enable_fallback,
            'chunk_overlap': self.chunk_overlap
        }
        
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def get_default_config(cls) -> 'LLMConfig':
        """
        Get default configuration with common local LLM backends.
        
        Returns:
            Default LLMConfig instance
        """
        backends = [
            BackendConfig(
                name="llama-cpp",
                backend_type="LlamaCppBackend",
                enabled=True,
                priority=3,
                config={
                    "model_path": "",
                    "n_ctx": 4096,
                    "n_threads": -1,
                    "verbose": False
                }
            ),
            BackendConfig(
                name="local-server",
                backend_type="LocalServerBackend",
                enabled=True,
                priority=2,
                config={
                    "base_url": "http://localhost:8080",
                    "api_key": "",
                    "timeout": 30
                }
            ),
            BackendConfig(
                name="fallback",
                backend_type="FallbackLLMBackend",
                enabled=True,
                priority=1,
                config={}
            )
        ]
        
        return cls(backends=backends)
    
    def get_enabled_backends(self) -> List[BackendConfig]:
        """
        Get list of enabled backends sorted by priority (highest first).
        
        Returns:
            List of enabled BackendConfig instances
        """
        enabled = [backend for backend in self.backends if backend.enabled]
        return sorted(enabled, key=lambda x: x.priority, reverse=True)
    
    def get_backend_config(self, name: str) -> Optional[BackendConfig]:
        """
        Get configuration for a specific backend by name.
        
        Args:
            name: Backend name
            
        Returns:
            BackendConfig if found, None otherwise
        """
        for backend in self.backends:
            if backend.name == name:
                return backend
        return None
    
    def add_backend(self, backend_config: BackendConfig) -> None:
        """
        Add a new backend configuration.
        
        Args:
            backend_config: Backend configuration to add
        """
        # Remove existing backend with same name
        self.backends = [b for b in self.backends if b.name != backend_config.name]
        self.backends.append(backend_config)
    
    def remove_backend(self, name: str) -> bool:
        """
        Remove a backend configuration by name.
        
        Args:
            name: Backend name to remove
            
        Returns:
            True if backend was removed, False if not found
        """
        original_count = len(self.backends)
        self.backends = [b for b in self.backends if b.name != name]
        return len(self.backends) < original_count
    
    def validate(self) -> List[str]:
        """
        Validate the configuration.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not self.backends:
            errors.append("No backends configured")
        
        if self.default_temperature < 0 or self.default_temperature > 1:
            errors.append("default_temperature must be between 0 and 1")
        
        if self.default_max_tokens <= 0:
            errors.append("default_max_tokens must be positive")
        
        if self.chunk_overlap < 0:
            errors.append("chunk_overlap must be non-negative")
        
        # Check for duplicate backend names
        names = [backend.name for backend in self.backends]
        if len(names) != len(set(names)):
            errors.append("Duplicate backend names found")
        
        # Validate individual backend configs
        for backend in self.backends:
            if not backend.name:
                errors.append("Backend name cannot be empty")
            if not backend.backend_type:
                errors.append(f"Backend type cannot be empty for {backend.name}")
            if backend.priority < 1:
                errors.append(f"Backend priority must be >= 1 for {backend.name}")
        
        return errors


def get_config_path() -> str:
    """
    Get the default configuration file path.
    
    Returns:
        Path to the LLM configuration file
    """
    # Use user's home directory for config
    home_dir = Path.home()
    config_dir = home_dir / ".medical_analyzer"
    config_dir.mkdir(exist_ok=True)
    return str(config_dir / "llm_config.json")


def load_config() -> LLMConfig:
    """
    Load LLM configuration from the default location.
    
    Returns:
        LLMConfig instance
    """
    config_path = get_config_path()
    return LLMConfig.load_from_file(config_path)


def save_config(config: LLMConfig) -> None:
    """
    Save LLM configuration to the default location.
    
    Args:
        config: LLMConfig instance to save
    """
    config_path = get_config_path()
    config.save_to_file(config_path)