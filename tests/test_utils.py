"""
Common test utilities and fixtures for the medical analyzer test suite.

This module provides standardized test infrastructure to ensure:
- Consistent import handling
- Proper mock configurations
- Deterministic test behavior
- UI component test utilities
"""

import sys
import os
import pytest
import importlib
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from PyQt6.QtWidgets import QApplication, QWidget, QTableWidgetItem, QMessageBox, QDialog
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtTest import QTest
from typing import Optional, Any, Dict, List, Union, Callable


class TestApplicationManager:
    """Manages QApplication instance for tests to ensure proper cleanup and isolation."""
    
    _instance: Optional[QApplication] = None
    
    @classmethod
    def get_application(cls) -> QApplication:
        """Get or create QApplication instance for testing."""
        if cls._instance is None or not QApplication.instance():
            # Ensure clean argv for test environment
            test_argv = ['test']
            cls._instance = QApplication(test_argv)
            cls._instance.setQuitOnLastWindowClosed(False)
        return cls._instance
    
    @classmethod
    def cleanup(cls):
        """Clean up application instance."""
        if cls._instance:
            cls._instance.quit()
            cls._instance = None


class MockConfigurationManager:
    """Provides standardized mock configurations for consistent test behavior."""
    
    @staticmethod
    def create_llm_backend_mock(backend_type: str = 'openai') -> Mock:
        """Create a standardized LLM backend mock with consistent behavior."""
        mock_backend = Mock()
        mock_backend.is_available.return_value = True
        mock_backend.generate.return_value = "Mock response"
        mock_backend.get_model_info.return_value = {
            'name': 'test-model',
            'type': backend_type,
            'max_tokens': 4096
        }
        mock_backend.backend_type = backend_type
        mock_backend.validate_config.return_value = True
        mock_backend.health_check.return_value = True
        return mock_backend
    
    @staticmethod
    def create_service_mock(service_class: type) -> Mock:
        """Create a standardized service mock with proper spec and common methods."""
        # Create mock without spec first to allow adding any attributes
        mock_service = Mock()
        mock_service._spec_class = service_class  # Store for validation
        
        # Add common service methods that all services should have
        # Only add if they exist in the real class
        if hasattr(service_class, 'initialize'):
            mock_service.initialize.return_value = True
        if hasattr(service_class, 'is_ready'):
            mock_service.is_ready.return_value = True
        if hasattr(service_class, 'cleanup'):
            mock_service.cleanup.return_value = None
        
        # Add service-specific default behaviors based on actual methods
        service_name = service_class.__name__.lower()
        if 'soup' in service_name:
            if hasattr(service_class, 'get_all_components'):
                mock_service.get_all_components.return_value = []
            if hasattr(service_class, 'add_component'):
                mock_service.add_component.return_value = True
            if hasattr(service_class, 'delete_component'):
                mock_service.delete_component.return_value = True
            if hasattr(service_class, 'validate_component'):
                mock_service.validate_component.return_value = True
        elif 'parser' in service_name:
            if hasattr(service_class, 'parse_file'):
                mock_service.parse_file.return_value = Mock()
            if hasattr(service_class, 'parse_project'):
                mock_service.parse_project.return_value = []
        elif 'risk' in service_name:
            if hasattr(service_class, 'get_all_risks'):
                mock_service.get_all_risks.return_value = []
            if hasattr(service_class, 'add_risk'):
                mock_service.add_risk.return_value = True
            if hasattr(service_class, 'update_risk'):
                mock_service.update_risk.return_value = True
            
        return mock_service
    
    @staticmethod
    def create_config_mock(backend_type: str = 'openai') -> Dict[str, Any]:
        """Create a standardized configuration mock with consistent backend types."""
        return {
            'llm': {
                'backend_type': backend_type,
                'model': 'gpt-3.5-turbo' if backend_type == 'openai' else 'claude-3-sonnet',
                'api_key': 'test-key',
                'max_tokens': 4096,
                'temperature': 0.7
            },
            'analysis': {
                'max_file_size': 1048576,
                'supported_extensions': ['.c', '.h', '.js', '.py'],
                'timeout': 300
            },
            'ui': {
                'theme': 'light',
                'auto_save': True,
                'show_progress': True
            }
        }
    
    @staticmethod
    def create_widget_mock(widget_class: type) -> Mock:
        """Create a standardized widget mock with common UI properties."""
        mock_widget = Mock(spec=widget_class)
        mock_widget.isVisible.return_value = True
        mock_widget.isEnabled.return_value = True
        mock_widget.text.return_value = ""
        mock_widget.setVisible = Mock()
        mock_widget.setEnabled = Mock()
        mock_widget.setText = Mock()
        return mock_widget


class UITestHelper:
    """Helper utilities for UI component testing with improved reliability."""
    
    @staticmethod
    def wait_for_signal(signal, timeout: int = 1000) -> bool:
        """Wait for a signal to be emitted within timeout with proper cleanup."""
        loop = QApplication.instance().processEvents
        timer = QTimer()
        timer.setSingleShot(True)
        
        signal_received = [False]
        
        def on_signal(*args):
            signal_received[0] = True
            timer.stop()
            
        def on_timeout():
            signal_received[0] = False
            
        signal.connect(on_signal)
        timer.timeout.connect(on_timeout)
        timer.start(timeout)
        
        while timer.isActive() and not signal_received[0]:
            loop()
            
        # Cleanup
        try:
            signal.disconnect(on_signal)
        except (TypeError, RuntimeError):
            pass  # Signal may already be disconnected
            
        return signal_received[0]
    
    @staticmethod
    def process_events(iterations: int = 10):
        """Process pending Qt events to ensure UI updates."""
        app = QApplication.instance()
        if app:
            for _ in range(iterations):
                app.processEvents()
                
    @staticmethod
    def process_events_until_idle(max_iterations: int = 100):
        """Process events until the event queue is idle."""
        app = QApplication.instance()
        if not app:
            return
            
        # Process events multiple times to ensure all pending events are handled
        for _ in range(max_iterations):
            app.processEvents()
            # In PyQt6, we don't have hasPendingEvents, so we just process a few times
            if _ > 5:  # Process at least 5 times, then break
                break
    
    @staticmethod
    def verify_widget_visibility(widget: QWidget, should_be_visible: bool = True):
        """Verify widget visibility with proper event processing."""
        UITestHelper.process_events_until_idle()
        if should_be_visible:
            assert widget.isVisible(), f"Widget {widget.__class__.__name__} should be visible"
        else:
            assert not widget.isVisible(), f"Widget {widget.__class__.__name__} should not be visible"
    
    @staticmethod
    def verify_widget_enabled(widget: QWidget, should_be_enabled: bool = True):
        """Verify widget enabled state with proper event processing."""
        UITestHelper.process_events_until_idle()
        if should_be_enabled:
            assert widget.isEnabled(), f"Widget {widget.__class__.__name__} should be enabled"
        else:
            assert not widget.isEnabled(), f"Widget {widget.__class__.__name__} should be disabled"
    
    @staticmethod
    def verify_table_item_text(table_widget, row: int, col: int, expected_text: str):
        """Verify table widget item text with proper null checking."""
        UITestHelper.process_events_until_idle()
        item = table_widget.item(row, col)
        assert item is not None, f"Table item at ({row}, {col}) should not be None"
        assert item.text() == expected_text, f"Expected '{expected_text}', got '{item.text()}'"
    
    @staticmethod
    def count_signal_emissions(signal, action_func: Callable, timeout: int = 1000) -> int:
        """Count the number of times a signal is emitted during an action."""
        emission_count = [0]
        
        def on_signal(*args):
            emission_count[0] += 1
            
        signal.connect(on_signal)
        
        try:
            action_func()
            UITestHelper.process_events_until_idle()
        finally:
            try:
                signal.disconnect(on_signal)
            except (TypeError, RuntimeError):
                pass
                
        return emission_count[0]


class DeterministicTestMixin:
    """Mixin class to ensure deterministic test behavior and proper isolation."""
    
    def setup_method(self):
        """Set up deterministic test environment with complete isolation."""
        # Store original state
        self._original_argv = sys.argv.copy()
        self._original_env = os.environ.copy()
        
        # Set deterministic test state
        sys.argv = ['test']
        os.environ['PYTHONHASHSEED'] = '0'
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        
        # Ensure clean application state
        TestApplicationManager.get_application()
        
        # Clear any cached modules that might affect test behavior
        self._clear_module_caches()
    
    def teardown_method(self):
        """Clean up after test to prevent state leakage."""
        # Process any pending events first
        UITestHelper.process_events_until_idle()
        
        # Restore original state
        sys.argv = self._original_argv
        os.environ.clear()
        os.environ.update(self._original_env)
        
        # Clear any test-specific module state
        self._clear_module_caches()
    
    def _clear_module_caches(self):
        """Clear module-level caches that might affect test determinism."""
        # Clear importlib caches
        importlib.invalidate_caches()
        
        # Clear any module-level state in our application modules
        modules_to_clear = [
            'medical_analyzer.config',
            'medical_analyzer.services',
            'medical_analyzer.ui'
        ]
        
        for module_name in modules_to_clear:
            if module_name in sys.modules:
                module = sys.modules[module_name]
                # Clear any module-level caches or state
                if hasattr(module, '_cache'):
                    module._cache.clear()
                if hasattr(module, '_instances'):
                    module._instances.clear()


# Common fixtures
@pytest.fixture(scope="session")
def qapp():
    """Session-scoped QApplication fixture."""
    app = TestApplicationManager.get_application()
    yield app
    TestApplicationManager.cleanup()


@pytest.fixture
def mock_config():
    """Provide standardized mock configuration."""
    return MockConfigurationManager.create_config_mock()


@pytest.fixture
def mock_llm_backend():
    """Provide standardized LLM backend mock."""
    return MockConfigurationManager.create_llm_backend_mock()


# Import validation utilities
def validate_required_imports(module_name: str, required_imports: List[str]) -> List[str]:
    """Validate that all required imports are available in a module."""
    missing_imports = []
    
    try:
        module = __import__(module_name, fromlist=[''])
        for import_name in required_imports:
            if '.' in import_name:
                # Handle nested attributes like 'QtWidgets.QTableWidgetItem'
                parts = import_name.split('.')
                current = module
                for part in parts:
                    if not hasattr(current, part):
                        missing_imports.append(f"{module_name}.{import_name}")
                        break
                    current = getattr(current, part)
            else:
                if not hasattr(module, import_name):
                    missing_imports.append(f"{module_name}.{import_name}")
    except ImportError as e:
        missing_imports.append(f"{module_name}: {str(e)}")
    
    return missing_imports


def ensure_required_imports(test_module_path: str) -> None:
    """Ensure all required imports are available for a test module."""
    # Skip validation for framework validation module to avoid circular dependency
    if 'test_framework_validation' in test_module_path:
        return
    
    try:
        # Try to import the module to check if basic imports work
        module = __import__(test_module_path, fromlist=[''])
        
        # Check for basic pytest availability
        if not hasattr(module, 'pytest') and 'pytest' not in str(module):
            # Try importing pytest directly
            import pytest as _pytest
            
        # For UI test modules, check Qt availability
        if any(ui_keyword in test_module_path.lower() for ui_keyword in ['widget', 'ui', 'main_window']):
            try:
                from PyQt6.QtWidgets import QApplication
                from PyQt6.QtCore import Qt
            except ImportError as e:
                raise ImportError(f"Qt imports not available in {test_module_path}: {e}")
                
    except ImportError as e:
        # Only raise if it's a critical import issue
        if 'No module named' in str(e):
            raise ImportError(f"Module import failed for {test_module_path}: {e}")


# Mock behavior validation
def validate_mock_behavior(mock_obj: Mock, expected_methods: List[str]) -> List[str]:
    """Validate that a mock object has all expected methods configured."""
    missing_methods = []
    
    for method_name in expected_methods:
        if not hasattr(mock_obj, method_name):
            missing_methods.append(method_name)
        elif not callable(getattr(mock_obj, method_name)):
            missing_methods.append(f"{method_name} (not callable)")
    
    return missing_methods


def validate_mock_consistency(mock_obj: Mock, real_class: type) -> List[str]:
    """Validate that a mock object is consistent with the real class interface."""
    inconsistencies = []
    
    # Check that mock has spec if it should
    if not hasattr(mock_obj, '_spec_class') or mock_obj._spec_class != real_class:
        inconsistencies.append(f"Mock should have spec={real_class.__name__}")
    
    # Check common methods exist
    real_methods = [method for method in dir(real_class) if not method.startswith('_')]
    mock_methods = [method for method in dir(mock_obj) if not method.startswith('_')]
    
    for method in real_methods:
        if method not in mock_methods and not method.startswith('_'):
            inconsistencies.append(f"Missing method: {method}")
    
    return inconsistencies


# Test determinism utilities
class TestStateManager:
    """Manages test state to ensure deterministic behavior."""
    
    @staticmethod
    def reset_global_state():
        """Reset any global state that might affect test determinism."""
        # Clear Qt application state
        app = QApplication.instance()
        if app:
            app.closeAllWindows()
            UITestHelper.process_events(10)  # Use simpler event processing
        
        # Reset environment variables that affect behavior
        test_env_vars = {
            'QT_QPA_PLATFORM': 'offscreen',
            'PYTHONHASHSEED': '0',
            'TESTING': '1'
        }
        
        for key, value in test_env_vars.items():
            os.environ[key] = value
    
    @staticmethod
    def isolate_test_environment():
        """Create an isolated test environment."""
        # Store original state
        original_argv = sys.argv.copy()
        original_cwd = os.getcwd()
        
        # Set test state
        sys.argv = ['test']
        
        return {
            'original_argv': original_argv,
            'original_cwd': original_cwd
        }
    
    @staticmethod
    def restore_test_environment(state: Dict[str, Any]):
        """Restore the test environment from saved state."""
        sys.argv = state['original_argv']
        os.chdir(state['original_cwd'])