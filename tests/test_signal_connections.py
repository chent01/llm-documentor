"""
Tests for signal connections in the main application.

This test module verifies that all required signals are properly connected
and that the analysis_requested signal issue is resolved.
"""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from medical_analyzer.ui.main_window import MainWindow
from medical_analyzer.services.analysis_orchestrator import AnalysisOrchestrator
from medical_analyzer.config.config_manager import ConfigManager
from medical_analyzer.config.app_settings import AppSettings
from tests.test_utils import DeterministicTestMixin, UITestHelper


class TestSignalConnections(DeterministicTestMixin):
    """Test signal connections between UI components and services."""
    
    @pytest.fixture
    def config_manager(self):
        """Create a mock configuration manager."""
        config_manager = Mock(spec=ConfigManager)
        config_manager.load_default_config.return_value = None
        config_manager.get_llm_config.return_value = {}
        return config_manager
    
    @pytest.fixture
    def app_settings(self, config_manager):
        """Create mock application settings."""
        app_settings = Mock(spec=AppSettings)
        return app_settings
    
    @pytest.fixture
    def main_window(self, app, config_manager, app_settings):
        """Create MainWindow instance for testing."""
        return MainWindow(config_manager, app_settings)
    
    @pytest.fixture
    def analysis_orchestrator(self, config_manager, app_settings):
        """Create AnalysisOrchestrator instance for testing."""
        with patch('medical_analyzer.services.analysis_orchestrator.DatabaseManager'):
            with patch('medical_analyzer.services.analysis_orchestrator.LLMBackend'):
                return AnalysisOrchestrator(config_manager, app_settings)
    
    def test_analysis_requested_signal_exists(self, main_window):
        """Test that the analysis_requested signal exists on MainWindow."""
        assert hasattr(main_window, 'analysis_requested')
        assert hasattr(main_window.analysis_requested, 'connect')
        assert hasattr(main_window.analysis_requested, 'emit')
    
    def test_orchestrator_start_analysis_method_exists(self, analysis_orchestrator):
        """Test that the orchestrator has a start_analysis method."""
        assert hasattr(analysis_orchestrator, 'start_analysis')
        assert callable(analysis_orchestrator.start_analysis)
    
    def test_signal_connection_successful(self, main_window, analysis_orchestrator):
        """Test that analysis_requested signal can be connected to orchestrator."""
        # This should not raise any exceptions
        main_window.analysis_requested.connect(analysis_orchestrator.start_analysis)
        
        # Verify connection by checking signal emission
        analysis_calls = []
        
        def capture_analysis_call(project_path, description, selected_files):
            analysis_calls.append((project_path, description, selected_files))
        
        # Connect our capture function
        main_window.analysis_requested.connect(capture_analysis_call)
        
        # Emit the signal
        main_window.analysis_requested.emit("/test/path", "test description", [])
        
        # Process events to ensure signal is handled
        UITestHelper.process_events()
        
        # Verify the signal was received
        assert len(analysis_calls) == 1
        assert analysis_calls[0] == ("/test/path", "test description", [])
    
    def test_orchestrator_signals_exist(self, analysis_orchestrator):
        """Test that the orchestrator has all required signals."""
        required_signals = [
            'analysis_started',
            'stage_started', 
            'stage_completed',
            'stage_failed',
            'analysis_completed',
            'analysis_failed',
            'progress_updated'
        ]
        
        for signal_name in required_signals:
            assert hasattr(analysis_orchestrator, signal_name), f"Missing signal: {signal_name}"
            signal = getattr(analysis_orchestrator, signal_name)
            assert hasattr(signal, 'connect'), f"Signal {signal_name} is not connectable"
            assert hasattr(signal, 'emit'), f"Signal {signal_name} is not emittable"
    
    def test_main_window_progress_methods_exist(self, main_window):
        """Test that MainWindow has methods to handle progress updates."""
        required_methods = [
            'update_stage_progress',
            'analysis_completed',
            'analysis_failed'
        ]
        
        for method_name in required_methods:
            assert hasattr(main_window, method_name), f"Missing method: {method_name}"
            assert callable(getattr(main_window, method_name)), f"Method {method_name} is not callable"
    
    def test_full_signal_chain_connection(self, main_window, analysis_orchestrator):
        """Test that the full signal chain can be connected without errors."""
        # Connect main signal
        main_window.analysis_requested.connect(analysis_orchestrator.start_analysis)
        
        # Connect progress signals
        analysis_orchestrator.analysis_completed.connect(main_window.analysis_completed)
        analysis_orchestrator.analysis_failed.connect(main_window.analysis_failed)
        
        # Connect progress update with lambda (as done in main app)
        analysis_orchestrator.progress_updated.connect(
            lambda percentage: main_window.update_stage_progress("Analysis", percentage, "in_progress")
        )
        
        # Connect stage signals
        analysis_orchestrator.stage_started.connect(
            lambda stage: main_window.update_stage_progress(stage, 0, "in_progress")
        )
        analysis_orchestrator.stage_completed.connect(
            lambda stage, results: main_window.update_stage_progress(stage, 100, "completed")
        )
        analysis_orchestrator.stage_failed.connect(
            lambda stage, error: main_window.update_stage_progress(stage, 0, "failed", error_message=error)
        )
        
        # Connect cancellation
        main_window.analysis_cancelled.connect(analysis_orchestrator.cancel_analysis)
        
        # If we get here without exceptions, all connections are valid
        assert True, "All signal connections established successfully"
    
    def test_signal_emission_with_mock_orchestrator(self, main_window):
        """Test signal emission with a mock orchestrator to verify the fix."""
        # Create a mock orchestrator
        mock_orchestrator = Mock()
        
        # Connect the signal
        main_window.analysis_requested.connect(mock_orchestrator.start_analysis)
        
        # Emit the signal
        test_path = "/test/project/path"
        test_description = "Test project description"
        main_window.analysis_requested.emit(test_path, test_description, [])
        
        # Process events
        UITestHelper.process_events()
        
        # Verify the mock was called
        mock_orchestrator.start_analysis.assert_called_once_with(test_path, test_description, [])
    
    def test_orchestrator_initialization_with_config(self, config_manager, app_settings):
        """Test that orchestrator initializes properly with configuration."""
        with patch('medical_analyzer.services.analysis_orchestrator.DatabaseManager'):
            with patch('medical_analyzer.services.analysis_orchestrator.LLMBackend') as mock_llm:
                # Mock LLM backend creation to avoid initialization issues
                mock_llm.create_from_config.return_value = Mock()
                
                orchestrator = AnalysisOrchestrator(config_manager, app_settings)
                
                assert orchestrator.config_manager == config_manager
                assert orchestrator.app_settings == app_settings
                assert not orchestrator.is_running
                assert orchestrator.current_analysis is None
    
    def test_orchestrator_service_initialization(self, config_manager, app_settings):
        """Test that orchestrator initializes all required services."""
        with patch('medical_analyzer.services.analysis_orchestrator.DatabaseManager'):
            with patch('medical_analyzer.services.analysis_orchestrator.LLMBackend'):
                with patch('medical_analyzer.services.analysis_orchestrator.IngestionService'):
                    with patch('medical_analyzer.services.analysis_orchestrator.ParserService'):
                        with patch('medical_analyzer.services.analysis_orchestrator.SOUPService'):
                            orchestrator = AnalysisOrchestrator(config_manager, app_settings)
                            
                            # Verify services are initialized
                            assert hasattr(orchestrator, 'ingestion_service')
                            assert hasattr(orchestrator, 'parser_service')
                            assert hasattr(orchestrator, 'soup_service')
                            assert hasattr(orchestrator, 'export_service')
                            assert hasattr(orchestrator, 'traceability_service')
                            assert hasattr(orchestrator, 'risk_register')
                            assert hasattr(orchestrator, 'test_generator')
    
    def test_file_type_summary_method(self, config_manager, app_settings):
        """Test the _get_file_type_summary method works correctly."""
        with patch('medical_analyzer.services.analysis_orchestrator.DatabaseManager'):
            with patch('medical_analyzer.services.analysis_orchestrator.LLMBackend'):
                orchestrator = AnalysisOrchestrator(config_manager, app_settings)
                
                # Test with various file types
                test_files = [
                    'main.py',
                    'utils.py', 
                    'config.json',
                    'README.md',
                    'script.js',
                    'style.css',
                    'test.c',
                    'header.h',
                    'no_extension_file'
                ]
                
                result = orchestrator._get_file_type_summary(test_files)
                
                # Verify the summary is correct
                expected = {
                    '.py': 2,
                    '.json': 1,
                    '.md': 1,
                    '.js': 1,
                    '.css': 1,
                    '.c': 1,
                    '.h': 1,
                    'no_extension': 1
                }
                
                assert result == expected
    
    def test_project_ingestion_stage_no_attribute_error(self, config_manager, app_settings):
        """Test that project ingestion stage doesn't raise AttributeError for get_file_type_summary."""
        from medical_analyzer.models.core import ProjectStructure
        
        with patch('medical_analyzer.services.analysis_orchestrator.DatabaseManager'):
            with patch('medical_analyzer.services.analysis_orchestrator.LLMBackend'):
                orchestrator = AnalysisOrchestrator(config_manager, app_settings)
                
                # Create a mock project structure
                mock_project_structure = ProjectStructure(
                    root_path='/test/path',
                    selected_files=['test.py', 'main.c', 'script.js'],
                    description='Test project'
                )
                
                # Mock the ingestion service
                orchestrator.ingestion_service = Mock()
                orchestrator.ingestion_service.scan_project.return_value = mock_project_structure
                
                # Set up current analysis
                orchestrator.current_analysis = {
                    'project_path': '/test/path',
                    'description': 'Test project',
                    'selected_files': None,
                    'results': {}
                }
                
                # This should not raise AttributeError
                result = orchestrator._stage_project_ingestion()
                
                # Verify the result structure
                assert 'project_structure' in result
                assert 'total_files' in result
                assert 'file_types' in result
                assert result['total_files'] == 3
                assert result['file_types'] == {'.py': 1, '.c': 1, '.js': 1}
    
    def test_hazard_identification_stage_no_attribute_error(self, config_manager, app_settings):
        """Test that hazard identification stage doesn't raise AttributeError for hazards attribute."""
        from medical_analyzer.models.result_models import HazardIdentificationResult
        
        with patch('medical_analyzer.services.analysis_orchestrator.DatabaseManager'):
            with patch('medical_analyzer.services.analysis_orchestrator.LLMBackend'):
                orchestrator = AnalysisOrchestrator(config_manager, app_settings)
                
                # Create a mock hazard identification result
                mock_hazard_result = HazardIdentificationResult(
                    risk_items=[],
                    confidence_score=0.8,
                    processing_time=1.5,
                    requirements_processed=0,
                    errors=[],
                    metadata={'method': 'test', 'llm_used': False}
                )
                
                # Mock the hazard identifier
                orchestrator.hazard_identifier = Mock()
                orchestrator.hazard_identifier.identify_hazards.return_value = mock_hazard_result
                
                # Set up current analysis
                orchestrator.current_analysis = {
                    'project_path': '/test/path',
                    'description': 'Test medical device project',
                    'results': {}
                }
                
                # This should not raise AttributeError
                result = orchestrator._stage_hazard_identification()
                
                # Verify the result structure
                assert 'hazards' in result
                assert 'total_hazards' in result
                assert 'identification_metadata' in result
                assert result['total_hazards'] == 0
                assert result['hazards'] == []
                assert result['identification_metadata']['method'] == 'test'
                
                # Verify the hazard identifier was called with correct parameters
                orchestrator.hazard_identifier.identify_hazards.assert_called_once_with(
                    [], 'Test medical device project'
                )


class TestSignalConnectionIntegration:
    """Integration tests for signal connections in the full application context."""
    
    def test_main_application_signal_setup(self):
        """Test that the main application sets up signals correctly."""
        # This test verifies that the fix in __main__.py works correctly
        from medical_analyzer.__main__ import run_gui_mode
        from medical_analyzer.config.config_manager import ConfigManager
        from medical_analyzer.config.app_settings import AppSettings
        
        # Mock the QApplication and main window to avoid GUI creation
        with patch('medical_analyzer.__main__.QApplication') as mock_app:
            with patch('medical_analyzer.__main__.MainWindow') as mock_main_window:
                with patch('medical_analyzer.services.analysis_orchestrator.AnalysisOrchestrator') as mock_orchestrator:
                    
                    # Create mock instances
                    mock_app_instance = Mock()
                    mock_app.return_value = mock_app_instance
                    mock_app_instance.exec.return_value = 0
                    
                    mock_window_instance = Mock()
                    mock_main_window.return_value = mock_window_instance
                    
                    mock_orchestrator_instance = Mock()
                    mock_orchestrator.return_value = mock_orchestrator_instance
                    
                    # Create config
                    config_manager = Mock(spec=ConfigManager)
                    app_settings = Mock(spec=AppSettings)
                    
                    # Run the GUI mode setup
                    result = run_gui_mode(config_manager, app_settings)
                    
                    # Verify orchestrator was created
                    mock_orchestrator.assert_called_once_with(config_manager, app_settings)
                    
                    # Verify main window was created
                    mock_main_window.assert_called_once_with(config_manager, app_settings)
                    
                    # Verify signal connections were made
                    mock_window_instance.analysis_requested.connect.assert_called()
                    
                    # Verify the application ran successfully
                    assert result == 0