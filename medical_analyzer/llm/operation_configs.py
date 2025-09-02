"""
Centralized LLM operation configurations.

This module provides operation-specific LLM parameter configurations to eliminate
scattered hardcoded values and ensure consistency across the application.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Any
import json
from pathlib import Path


@dataclass
class OperationConfig:
    """Configuration for a specific LLM operation."""
    temperature: float
    max_tokens: int
    system_prompt: Optional[str] = None
    operation_name: str = ""
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'system_prompt': self.system_prompt,
            'operation_name': self.operation_name,
            'description': self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OperationConfig':
        """Create from dictionary."""
        return cls(
            temperature=data['temperature'],
            max_tokens=data['max_tokens'],
            system_prompt=data.get('system_prompt'),
            operation_name=data.get('operation_name', ''),
            description=data.get('description', '')
        )


class LLMOperationConfigs:
    """Centralized configuration manager for LLM operations."""
    
    # Default configurations for all operations
    DEFAULT_CONFIGS = {
        # Requirements generation - higher creativity needed
        "user_requirements_generation": OperationConfig(
            temperature=0.7,
            max_tokens=4000,
            operation_name="user_requirements_generation",
            description="Generate user requirements from features - needs creativity"
        ),
        
        "software_requirements_generation": OperationConfig(
            temperature=0.6,
            max_tokens=4000,
            operation_name="software_requirements_generation", 
            description="Generate software requirements - moderate creativity"
        ),
        
        # Classification tasks - low temperature for consistency
        "soup_classification": OperationConfig(
            temperature=0.1,
            max_tokens=1500,
            operation_name="soup_classification",
            description="SOUP classification - needs consistency"
        ),
        
        "soup_risk_assessment": OperationConfig(
            temperature=0.2,
            max_tokens=1000,
            operation_name="soup_risk_assessment",
            description="SOUP risk assessment - low creativity"
        ),
        
        # Test generation - very low temperature for precision
        "test_case_generation": OperationConfig(
            temperature=0.1,
            max_tokens=1000,
            operation_name="test_case_generation",
            description="Test case generation - needs precision"
        ),
        
        # Analysis tasks - balanced approach
        "hazard_identification": OperationConfig(
            temperature=0.1,
            max_tokens=2000,
            operation_name="hazard_identification",
            description="Hazard identification - needs precision"
        ),
        
        "feature_extraction": OperationConfig(
            temperature=0.5,
            max_tokens=4000,
            operation_name="feature_extraction",
            description="Feature extraction - moderate creativity"
        ),
        
        # Diagnostic operations - minimal creativity
        "diagnostic_test": OperationConfig(
            temperature=0.1,
            max_tokens=50,
            operation_name="diagnostic_test",
            description="LLM diagnostic tests - minimal output"
        ),
        
        # Generic fallback
        "default": OperationConfig(
            temperature=0.3,
            max_tokens=2000,
            operation_name="default",
            description="Default configuration for unspecified operations"
        )
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize operation configs.
        
        Args:
            config_file: Optional path to custom config file
        """
        self._configs = self.DEFAULT_CONFIGS.copy()
        self._config_file = config_file
        
        if config_file and Path(config_file).exists():
            self.load_from_file(config_file)
    
    def get_config(self, operation: str) -> OperationConfig:
        """
        Get configuration for an operation.
        
        Args:
            operation: Operation name
            
        Returns:
            OperationConfig for the operation, or default if not found
        """
        return self._configs.get(operation, self._configs["default"])
    
    def set_config(self, operation: str, config: OperationConfig) -> None:
        """
        Set configuration for an operation.
        
        Args:
            operation: Operation name
            config: OperationConfig to set
        """
        self._configs[operation] = config
    
    def get_all_operations(self) -> Dict[str, OperationConfig]:
        """Get all operation configurations."""
        return self._configs.copy()
    
    def load_from_file(self, config_file: str) -> None:
        """
        Load configurations from JSON file.
        
        Args:
            config_file: Path to configuration file
        """
        try:
            with open(config_file, 'r') as f:
                data = json.load(f)
            
            for operation, config_data in data.items():
                self._configs[operation] = OperationConfig.from_dict(config_data)
                
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            # Fall back to defaults if loading fails
            print(f"Warning: Could not load operation configs from {config_file}: {e}")
    
    def save_to_file(self, config_file: str) -> None:
        """
        Save configurations to JSON file.
        
        Args:
            config_file: Path to save configuration file
        """
        # Ensure directory exists
        Path(config_file).parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            operation: config.to_dict() 
            for operation, config in self._configs.items()
        }
        
        with open(config_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_generation_params(self, operation: str) -> Dict[str, Any]:
        """
        Get generation parameters for an operation.
        
        Args:
            operation: Operation name
            
        Returns:
            Dictionary with temperature and max_tokens
        """
        config = self.get_config(operation)
        return {
            'temperature': config.temperature,
            'max_tokens': config.max_tokens
        }
    
    def update_operation_temperature(self, operation: str, temperature: float) -> None:
        """
        Update temperature for a specific operation.
        
        Args:
            operation: Operation name
            temperature: New temperature value (0.0 to 1.0)
        """
        if operation not in self._configs:
            self._configs[operation] = self._configs["default"]
        
        # Create new config with updated temperature
        old_config = self._configs[operation]
        self._configs[operation] = OperationConfig(
            temperature=temperature,
            max_tokens=old_config.max_tokens,
            system_prompt=old_config.system_prompt,
            operation_name=old_config.operation_name,
            description=old_config.description
        )
    
    def update_operation_max_tokens(self, operation: str, max_tokens: int) -> None:
        """
        Update max_tokens for a specific operation.
        
        Args:
            operation: Operation name
            max_tokens: New max_tokens value
        """
        if operation not in self._configs:
            self._configs[operation] = self._configs["default"]
        
        # Create new config with updated max_tokens
        old_config = self._configs[operation]
        self._configs[operation] = OperationConfig(
            temperature=old_config.temperature,
            max_tokens=max_tokens,
            system_prompt=old_config.system_prompt,
            operation_name=old_config.operation_name,
            description=old_config.description
        )


# Global instance for easy access
_global_configs = None

def get_operation_configs(config_file: Optional[str] = None) -> LLMOperationConfigs:
    """
    Get global operation configurations instance.
    
    Args:
        config_file: Optional path to custom config file
        
    Returns:
        LLMOperationConfigs instance
    """
    global _global_configs
    if _global_configs is None:
        _global_configs = LLMOperationConfigs(config_file)
    return _global_configs


def get_operation_params(operation: str) -> Dict[str, Any]:
    """
    Convenience function to get operation parameters.
    
    Args:
        operation: Operation name
        
    Returns:
        Dictionary with temperature and max_tokens
    """
    return get_operation_configs().get_generation_params(operation)


def get_operation_config(operation: str) -> OperationConfig:
    """
    Convenience function to get operation configuration.
    
    Args:
        operation: Operation name
        
    Returns:
        OperationConfig for the operation
    """
    return get_operation_configs().get_config(operation)