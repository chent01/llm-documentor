"""Tests for application packaging and deployment."""

import os
import sys
import json
import shutil
import tempfile
import subprocess
from pathlib import Path

import pytest

from medical_analyzer import __version__
from medical_analyzer.config.config_manager import ConfigManager


@pytest.fixture
def temp_install_dir():
    """Create a temporary directory for installation testing."""
    temp_dir = tempfile.mkdtemp(prefix="medical_analyzer_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for configuration testing."""
    temp_dir = tempfile.mkdtemp(prefix="medical_analyzer_config_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_package_version():
    """Test that the package version is correctly set."""
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__.split(".")) >= 2


def test_entry_point_script():
    """Test that the entry point script is correctly installed."""
    # This test assumes the package is installed in development mode
    # using pip install -e .
    result = subprocess.run(
        [sys.executable, "-m", "medical_analyzer", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert __version__ in result.stdout


def test_config_template_exists():
    """Test that the default configuration template exists."""
    # Get the package directory
    import medical_analyzer
    package_dir = Path(medical_analyzer.__file__).parent
    template_path = package_dir / "config" / "templates" / "default_config.json"
    
    assert template_path.exists(), "Default configuration template not found"
    
    # Test that the template is valid JSON
    with open(template_path, "r") as f:
        config_data = json.load(f)
    
    # Check for required sections
    assert "llm" in config_data
    assert "database" in config_data
    assert "export" in config_data
    assert "ui" in config_data
    assert "analysis" in config_data
    assert "logging" in config_data


def test_config_manager_initialization():
    """Test that the ConfigManager initializes correctly."""
    config_manager = ConfigManager()
    
    # Test that default configurations are loaded
    assert config_manager.llm_config is not None
    assert config_manager.database_config is not None
    assert config_manager.export_config is not None
    assert config_manager.ui_config is not None
    assert config_manager.analysis_config is not None
    assert config_manager.logging_config is not None


def test_config_manager_custom_path(temp_config_dir):
    """Test that the ConfigManager can load from a custom path."""
    config_path = os.path.join(temp_config_dir, "test_config.json")
    
    # Create a test configuration
    test_config = {
        "llm": {
            "backend_type": "openai",
            "model_name": "gpt-4",
            "api_key": "test_key",
            "max_tokens": 2000,
            "temperature": 0.2,
            "timeout": 60,
            "retry_attempts": 2,
            "batch_size": 16,
            "context_window": 8192,
            "embedding_model": "text-embedding-ada-002"
        },
        "database": {
            "db_path": "test.db",
            "backup_enabled": False
        },
        "export": {
            "default_format": "json",
            "include_audit_log": False
        },
        "ui": {
            "theme": "dark",
            "window_width": 1400,
            "window_height": 900
        },
        "analysis": {
            "max_chunk_size": 2000,
            "min_confidence": 0.7
        },
        "logging": {
            "level": "DEBUG",
            "file_enabled": False
        }
    }
    
    # Write the test configuration to file
    with open(config_path, "w") as f:
        json.dump(test_config, f)
    
    # Initialize ConfigManager with the test configuration
    config_manager = ConfigManager(config_path=config_path)
    
    # Test that the configuration was loaded correctly
    assert config_manager.llm_config.backend_type == "openai"
    assert config_manager.llm_config.model_name == "gpt-4"
    assert config_manager.llm_config.api_key == "test_key"
    assert config_manager.llm_config.max_tokens == 2000
    assert config_manager.llm_config.temperature == 0.2
    assert config_manager.llm_config.batch_size == 16
    assert config_manager.llm_config.context_window == 8192
    assert config_manager.llm_config.embedding_model == "text-embedding-ada-002"
    
    assert config_manager.database_config.db_path == "test.db"
    assert config_manager.database_config.backup_enabled is False
    
    assert config_manager.export_config.default_format == "json"
    assert config_manager.export_config.include_audit_log is False
    
    assert config_manager.ui_config.theme == "dark"
    assert config_manager.ui_config.window_width == 1400
    assert config_manager.ui_config.window_height == 900
    
    assert config_manager.analysis_config.max_chunk_size == 2000
    assert config_manager.analysis_config.min_confidence == 0.7
    
    assert config_manager.logging_config.level == "DEBUG"
    assert config_manager.logging_config.file_enabled is False


def test_config_save_and_load(temp_config_dir):
    """Test saving and loading configurations."""
    config_path = os.path.join(temp_config_dir, "save_test_config.json")
    
    # Create a config manager with default settings
    config_manager = ConfigManager()
    
    # Modify some settings
    config_manager.llm_config.backend_type = "anthropic"
    config_manager.llm_config.model_name = "claude-2"
    config_manager.ui_config.theme = "light"
    config_manager.logging_config.level = "WARNING"
    
    # Save the configuration
    config_manager.save_config(config_path)
    
    # Create a new config manager and load the saved configuration
    new_config_manager = ConfigManager(config_path=config_path)
    
    # Test that the configuration was loaded correctly
    assert new_config_manager.llm_config.backend_type == "anthropic"
    assert new_config_manager.llm_config.model_name == "claude-2"
    assert new_config_manager.ui_config.theme == "light"
    assert new_config_manager.logging_config.level == "WARNING"


def test_headless_mode():
    """Test that the application can run in headless mode."""
    # Run the application with the --headless flag and a simple task
    result = subprocess.run(
        [sys.executable, "-m", "medical_analyzer", "--headless", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()


def test_config_validation():
    """Test that the LLM configuration validation works correctly."""
    config_manager = ConfigManager()
    
    # Test valid OpenAI configuration
    config_manager.llm_config.backend_type = "openai"
    config_manager.llm_config.api_key = "test_key"
    config_manager.llm_config.model_name = "gpt-4"
    assert config_manager.llm_config.validate() is True
    
    # Test invalid OpenAI configuration (missing API key)
    config_manager.llm_config.api_key = None
    assert config_manager.llm_config.validate() is False
    
    # Test valid Anthropic configuration
    config_manager.llm_config.backend_type = "anthropic"
    config_manager.llm_config.api_key = "test_key"
    config_manager.llm_config.model_name = "claude-2"
    assert config_manager.llm_config.validate() is True
    
    # Test valid local model configuration
    config_manager.llm_config.backend_type = "local"
    config_manager.llm_config.model_path = "/path/to/model"
    assert config_manager.llm_config.validate() is True
    
    # Test invalid local model configuration (missing model path)
    config_manager.llm_config.model_path = None
    assert config_manager.llm_config.validate() is False
    
    # Test valid mock configuration (for testing)
    config_manager.llm_config.backend_type = "mock"
    assert config_manager.llm_config.validate() is True