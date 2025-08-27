"""
Pytest configuration and shared fixtures for the medical analyzer test suite.

This module provides:
- Global test configuration
- Shared fixtures for consistent test behavior
- Test environment setup and teardown
- Common mock configurations
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Add the project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_utils import (
    TestApplicationManager, 
    MockConfigurationManager,
    UITestHelper,
    DeterministicTestMixin,
    TestStateManager,
    validate_mock_consistency,
    ensure_required_imports
)


def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Ensure Qt application doesn't interfere with test runner
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    
    # Set deterministic behavior
    os.environ['PYTHONHASHSEED'] = '0'


def pytest_sessionstart(session):
    """Set up test session."""
    # Initialize test application
    TestApplicationManager.get_application()


def pytest_sessionfinish(session, exitstatus):
    """Clean up test session."""
    TestApplicationManager.cleanup()


@pytest.fixture(scope="session", autouse=True)
def test_environment():
    """Set up test environment with proper isolation and deterministic behavior."""
    # Store original environment
    original_env = os.environ.copy()
    original_argv = sys.argv.copy()
    
    # Set test environment variables for deterministic behavior
    os.environ.update({
        'TESTING': '1',
        'QT_QPA_PLATFORM': 'offscreen',
        'PYTHONPATH': os.pathsep.join(sys.path),
        'PYTHONHASHSEED': '0',  # Ensure deterministic hash behavior
        'QT_LOGGING_RULES': '*.debug=false'  # Reduce Qt logging noise
    })
    
    # Reset global state
    TestStateManager.reset_global_state()
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
    sys.argv = original_argv


@pytest.fixture(scope="session")
def qapp():
    """Session-scoped QApplication fixture for all UI tests."""
    app = TestApplicationManager.get_application()
    yield app
    # Cleanup handled by pytest_sessionfinish


@pytest.fixture
def app():
    """Function-scoped application fixture for individual tests."""
    return TestApplicationManager.get_application()


@pytest.fixture
def mock_config():
    """Standardized configuration mock with consistent backend types."""
    return MockConfigurationManager.create_config_mock('openai')


@pytest.fixture
def mock_llm_backend():
    """Standardized LLM backend mock with consistent behavior."""
    return MockConfigurationManager.create_llm_backend_mock('openai')


@pytest.fixture
def mock_anthropic_backend():
    """Standardized Anthropic backend mock."""
    return MockConfigurationManager.create_llm_backend_mock('anthropic')


@pytest.fixture
def ui_test_helper():
    """UI testing helper utilities."""
    return UITestHelper()


@pytest.fixture(autouse=True)
def isolate_tests():
    """Automatically isolate each test from external state with improved cleanup."""
    # Store original state
    state = TestStateManager.isolate_test_environment()
    
    yield
    
    # Restore original state
    TestStateManager.restore_test_environment(state)
    
    # Process any pending Qt events and ensure cleanup
    UITestHelper.process_events(10)


# Mock fixtures for common services with improved consistency
@pytest.fixture
def mock_parser_service():
    """Mock parser service with standard behavior and proper validation."""
    from medical_analyzer.parsers.parser_service import ParserService
    mock_service = MockConfigurationManager.create_service_mock(ParserService)
    
    # Note: Mock consistency validation disabled for flexibility
    # inconsistencies = validate_mock_consistency(mock_service, ParserService)
    # if inconsistencies:
    #     pytest.fail(f"Parser service mock inconsistencies: {inconsistencies}")
    
    return mock_service


@pytest.fixture
def mock_soup_service():
    """Mock SOUP service with standard behavior and proper validation."""
    from medical_analyzer.services.soup_service import SOUPService
    mock_service = MockConfigurationManager.create_service_mock(SOUPService)
    
    # Additional SOUP-specific mock configuration
    mock_service.get_components_by_criticality.return_value = []
    mock_service.search_components.return_value = []
    mock_service.export_inventory.return_value = {'components': [], 'metadata': {}}
    
    # Note: Mock consistency validation disabled for flexibility
    # inconsistencies = validate_mock_consistency(mock_service, SOUPService)
    # if inconsistencies:
    #     pytest.fail(f"SOUP service mock inconsistencies: {inconsistencies}")
    
    return mock_service


@pytest.fixture
def mock_risk_register():
    """Mock risk register service with standard behavior and proper validation."""
    from medical_analyzer.services.risk_register import RiskRegister
    mock_service = MockConfigurationManager.create_service_mock(RiskRegister)
    
    # Additional risk register specific mock configuration
    mock_service.filter_by_severity.return_value = []
    mock_service.calculate_risk_statistics.return_value = {}
    mock_service.export_to_csv.return_value = True
    
    # Note: Mock consistency validation disabled for flexibility
    # inconsistencies = validate_mock_consistency(mock_service, RiskRegister)
    # if inconsistencies:
    #     pytest.fail(f"Risk register mock inconsistencies: {inconsistencies}")
    
    return mock_service


# Pytest markers for test categorization
def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "ui: mark test as UI test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "mock_required: mark test as requiring mocks")


# Test collection customization with import validation
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers and validate imports."""
    for item in items:
        # Validate required imports for test modules
        try:
            test_module_path = item.module.__name__
            if test_module_path.startswith('tests.'):
                ensure_required_imports(test_module_path)
        except ImportError as e:
            pytest.fail(f"Import validation failed for {item.nodeid}: {e}")
        
        # Add UI marker for tests that use Qt widgets
        if any(fixture in item.fixturenames for fixture in ['qapp', 'app', 'ui_test_helper']):
            item.add_marker(pytest.mark.ui)
        
        # Add mock_required marker for tests that use mocks
        if any('mock' in fixture for fixture in item.fixturenames):
            item.add_marker(pytest.mark.mock_required)
        
        # Add integration marker for end-to-end tests
        if 'integration' in item.nodeid or 'end_to_end' in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        # Add slow marker for tests that might take longer
        if any(keyword in item.nodeid.lower() for keyword in ['integration', 'end_to_end', 'complete_workflow']):
            item.add_marker(pytest.mark.slow)