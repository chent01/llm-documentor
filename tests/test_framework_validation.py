"""
Test framework validation utilities.

This module provides tests to validate that the test framework infrastructure
is working correctly and consistently across all test modules.
"""

import pytest
import sys
import os
import importlib
from pathlib import Path
from unittest.mock import Mock
from PyQt6.QtWidgets import QApplication, QWidget, QTableWidgetItem

from tests.test_utils import (
    MockConfigurationManager,
    UITestHelper,
    TestStateManager,
    validate_required_imports,
    validate_mock_consistency
)


class TestFrameworkInfrastructure:
    """Test the test framework infrastructure itself."""
    
    def test_required_imports_available(self):
        """Test that critical imports are available in test modules."""
        # Test that we can import pytest and basic modules
        try:
            import pytest
            import sys
            import os
            from unittest.mock import Mock, patch
        except ImportError as e:
            pytest.fail(f"Critical imports not available: {e}")
        
        # Test that PyQt imports work for UI tests
        try:
            from PyQt6.QtWidgets import QApplication, QWidget
            from PyQt6.QtCore import Qt
        except ImportError as e:
            pytest.fail(f"PyQt imports not available: {e}")
        
        # Test that our test utilities can be imported
        try:
            from tests.test_utils import MockConfigurationManager, UITestHelper
        except ImportError as e:
            pytest.fail(f"Test utilities not available: {e}")
    
    def test_mock_configuration_consistency(self):
        """Test that mock configurations are consistent with real implementations."""
        # Test LLM backend mock
        mock_backend = MockConfigurationManager.create_llm_backend_mock()
        assert hasattr(mock_backend, 'is_available')
        assert hasattr(mock_backend, 'generate')
        assert hasattr(mock_backend, 'get_model_info')
        assert hasattr(mock_backend, 'backend_type')
        
        # Test service mock creation
        from medical_analyzer.parsers.parser_service import ParserService
        mock_service = MockConfigurationManager.create_service_mock(ParserService)
        assert hasattr(mock_service, 'initialize')
        assert hasattr(mock_service, 'is_ready')
        assert hasattr(mock_service, 'parse_file')
    
    def test_ui_test_helper_functionality(self):
        """Test that UI test helper functions work correctly."""
        # Test event processing
        UITestHelper.process_events()
        UITestHelper.process_events_until_idle()
        
        # Test with QApplication
        app = QApplication.instance()
        assert app is not None, "QApplication should be available in tests"
    
    def test_deterministic_test_environment(self):
        """Test that the test environment is deterministic."""
        # Check environment variables
        assert os.environ.get('PYTHONHASHSEED') == '0'
        assert os.environ.get('QT_QPA_PLATFORM') == 'offscreen'
        assert os.environ.get('TESTING') == '1'
        
        # Check sys.argv isolation
        assert sys.argv == ['test']
    
    def test_test_state_manager(self):
        """Test that TestStateManager properly isolates test state."""
        original_argv = sys.argv.copy()
        
        # Test isolation
        state = TestStateManager.isolate_test_environment()
        assert 'original_argv' in state
        assert 'original_cwd' in state
        
        # Modify state
        sys.argv.append('--test-flag')
        
        # Restore state
        TestStateManager.restore_test_environment(state)
        assert sys.argv == original_argv
    
    def test_widget_mock_creation(self):
        """Test that widget mocks are created with proper attributes."""
        from PyQt6.QtWidgets import QLabel
        mock_widget = MockConfigurationManager.create_widget_mock(QLabel)
        
        # Check common widget methods
        assert hasattr(mock_widget, 'isVisible')
        assert hasattr(mock_widget, 'isEnabled')
        assert hasattr(mock_widget, 'text')
        assert hasattr(mock_widget, 'setVisible')
        assert hasattr(mock_widget, 'setEnabled')
        assert hasattr(mock_widget, 'setText')
        
        # Test default return values
        assert mock_widget.isVisible() is True
        assert mock_widget.isEnabled() is True
        assert mock_widget.text() == ""


class TestImportConsistency:
    """Test that imports are consistent across test modules."""
    
    def test_pyqt_imports_available(self):
        """Test that PyQt imports are available where needed."""
        # Simply test that we can import PyQt components
        try:
            from PyQt6.QtWidgets import QApplication, QWidget, QTableWidgetItem, QMessageBox
            from PyQt6.QtCore import Qt, pyqtSignal
            from PyQt6.QtTest import QTest
        except ImportError as e:
            pytest.fail(f"PyQt imports not available: {e}")
        
        # Test that UI test modules can be imported
        ui_test_modules = [
            'tests.test_main_window',
            'tests.test_progress_widget',
            'tests.test_results_tab_widget',
            'tests.test_soup_widget'
        ]
        
        for module_name in ui_test_modules:
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                pytest.fail(f"Could not import UI test module {module_name}: {e}")
    
    def test_mock_imports_available(self):
        """Test that mock imports are available in test modules."""
        # Simply test that we can import mock components
        try:
            from unittest.mock import Mock, patch, MagicMock
        except ImportError as e:
            pytest.fail(f"Mock imports not available: {e}")
        
        # Test that test modules can be imported
        test_modules = [
            'tests.test_soup_service',
            'tests.test_risk_register',
            'tests.test_parser_service'
        ]
        
        for module_name in test_modules:
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                pytest.fail(f"Could not import test module {module_name}: {e}")


class TestMockBehaviorConsistency:
    """Test that mocks behave consistently with real implementations."""
    
    def test_soup_service_mock_consistency(self, mock_soup_service):
        """Test that SOUP service mock is consistent with real implementation."""
        # Test that mock has expected methods
        assert hasattr(mock_soup_service, 'get_all_components')
        assert hasattr(mock_soup_service, 'add_component')
        assert hasattr(mock_soup_service, 'delete_component')
        assert hasattr(mock_soup_service, 'validate_component')
        
        # Test that methods return expected types
        components = mock_soup_service.get_all_components()
        assert isinstance(components, list)
        
        result = mock_soup_service.add_component(Mock())
        assert isinstance(result, bool)
    
    def test_parser_service_mock_consistency(self, mock_parser_service):
        """Test that parser service mock is consistent with real implementation."""
        # Test that mock has expected methods
        assert hasattr(mock_parser_service, 'parse_file')
        assert hasattr(mock_parser_service, 'parse_project')
        assert hasattr(mock_parser_service, 'initialize')
        
        # Test that methods can be called
        mock_parser_service.parse_file('test.c')
        mock_parser_service.parse_project('/test/path')
    
    def test_llm_backend_mock_consistency(self, mock_llm_backend):
        """Test that LLM backend mock is consistent with real implementation."""
        # Test that mock has expected attributes
        assert hasattr(mock_llm_backend, 'backend_type')
        assert hasattr(mock_llm_backend, 'is_available')
        assert hasattr(mock_llm_backend, 'generate')
        assert hasattr(mock_llm_backend, 'get_model_info')
        
        # Test that methods return expected types
        assert isinstance(mock_llm_backend.is_available(), bool)
        assert isinstance(mock_llm_backend.generate('test'), str)
        assert isinstance(mock_llm_backend.get_model_info(), dict)


class TestUIComponentAssertions:
    """Test that UI component assertions work correctly."""
    
    def test_table_widget_item_assertions(self, qapp):
        """Test table widget item assertion helpers."""
        from PyQt6.QtWidgets import QTableWidget
        
        table = QTableWidget(2, 2)
        table.setItem(0, 0, QTableWidgetItem("Test Text"))
        table.setItem(0, 1, QTableWidgetItem("Another Text"))
        
        # Test the helper function
        UITestHelper.verify_table_item_text(table, 0, 0, "Test Text")
        UITestHelper.verify_table_item_text(table, 0, 1, "Another Text")
        
        # Test that assertion fails for wrong text
        with pytest.raises(AssertionError):
            UITestHelper.verify_table_item_text(table, 0, 0, "Wrong Text")
    
    def test_widget_visibility_assertions(self, qapp):
        """Test widget visibility assertion helpers."""
        from PyQt6.QtWidgets import QLabel
        
        widget = QLabel("Test")
        widget.show()
        UITestHelper.process_events_until_idle()
        
        # Test visibility verification
        UITestHelper.verify_widget_visibility(widget, True)
        
        widget.hide()
        UITestHelper.process_events_until_idle()
        
        UITestHelper.verify_widget_visibility(widget, False)
    
    def test_signal_emission_counting(self, qapp):
        """Test signal emission counting functionality."""
        from PyQt6.QtWidgets import QPushButton
        from PyQt6.QtCore import pyqtSignal, QObject
        
        class TestObject(QObject):
            test_signal = pyqtSignal()
        
        test_obj = TestObject()
        
        def emit_signal():
            test_obj.test_signal.emit()
            test_obj.test_signal.emit()
        
        count = UITestHelper.count_signal_emissions(test_obj.test_signal, emit_signal)
        assert count == 2