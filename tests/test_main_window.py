"""
Unit tests for the MainWindow class.
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from medical_analyzer.ui import MainWindow


@pytest.fixture
def app():
    """Provide QApplication instance."""
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Don't quit the app as it might be used by other tests


@pytest.fixture
def main_window(app):
    """Create MainWindow instance for testing."""
    window = MainWindow()
    window.show()  # Show the window for proper widget visibility testing
    app.processEvents()  # Process any pending events
    return window


@pytest.fixture
def temp_project_dir():
    """Create a temporary directory with sample project files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create some C files
        (temp_path / "main.c").write_text("int main() { return 0; }")
        (temp_path / "utils.h").write_text("#ifndef UTILS_H\\n#define UTILS_H\\n#endif")
        
        # Create some JavaScript files
        (temp_path / "app.js").write_text("console.log('Hello World');")
        (temp_path / "config.ts").write_text("export const config = {};")
        
        # Create a subdirectory with more files
        sub_dir = temp_path / "src"
        sub_dir.mkdir()
        (sub_dir / "module.c").write_text("void function() {}")
        (sub_dir / "component.jsx").write_text("export default function Component() {}")
        
        yield str(temp_path)


@pytest.fixture
def empty_project_dir():
    """Create a temporary directory with no supported files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create some unsupported files
        (temp_path / "README.md").write_text("# Project")
        (temp_path / "config.ini").write_text("[settings]")
        
        yield str(temp_dir)


class TestMainWindow:
    """Test cases for MainWindow class."""
    
    def test_window_initialization(self, main_window):
        """Test that the main window initializes correctly."""
        assert main_window.windowTitle() == "Medical Software Analysis Tool"
        assert main_window.selected_project_path is None
        assert not main_window.analyze_button.isEnabled()
        assert not main_window.description_text.isEnabled()
        assert not main_window.progress_group.isVisible()
        
    def test_window_geometry(self, main_window):
        """Test window geometry settings."""
        geometry = main_window.geometry()
        assert geometry.width() >= 600
        assert geometry.height() >= 400
        
    def test_ui_components_exist(self, main_window):
        """Test that all required UI components exist."""
        # Check main components exist
        assert hasattr(main_window, 'project_path_label')
        assert hasattr(main_window, 'select_folder_button')
        assert hasattr(main_window, 'validation_label')
        assert hasattr(main_window, 'description_text')
        assert hasattr(main_window, 'analyze_button')
        assert hasattr(main_window, 'progress_group')
        assert hasattr(main_window, 'progress_label')
        assert hasattr(main_window, 'progress_bar')
        
    def test_project_path_validation_valid_project(self, main_window, temp_project_dir):
        """Test project validation with a valid project."""
        result = main_window.validate_project_structure(temp_project_dir)
        
        assert result["valid"] is True
        assert "Found" in result["message"]
        assert "supported files" in result["message"]
        
    def test_project_path_validation_empty_project(self, main_window, empty_project_dir):
        """Test project validation with no supported files."""
        result = main_window.validate_project_structure(empty_project_dir)
        
        assert result["valid"] is False
        assert "No supported files found" in result["message"]
        
    def test_project_path_validation_nonexistent_path(self, main_window):
        """Test project validation with nonexistent path."""
        result = main_window.validate_project_structure("/nonexistent/path")
        
        assert result["valid"] is False
        assert "Error scanning project" in result["message"]
        
    def test_validate_project_structure_finds_files(self, main_window, temp_project_dir):
        """Test that project validation finds supported files."""
        result = main_window.validate_project_structure(temp_project_dir)
        
        assert result["valid"] is True
        # Should find at least the files we created (main.c, utils.h, app.js, config.ts, module.c, component.jsx)
        assert "6 supported files" in result["message"]
        
    def test_validate_project_structure_excludes_hidden_dirs(self, main_window, temp_project_dir):
        """Test that hidden directories and common build dirs are excluded."""
        temp_path = Path(temp_project_dir)
        
        # Create files in directories that should be excluded
        (temp_path / ".git").mkdir()
        (temp_path / ".git" / "config.js").write_text("// git config")
        
        (temp_path / "node_modules").mkdir()
        (temp_path / "node_modules" / "package.js").write_text("// package")
        
        result = main_window.validate_project_structure(temp_project_dir)
        
        # Should still only find the original 6 files, not the excluded ones
        assert result["valid"] is True
        assert "6 supported files" in result["message"]
            
    def test_set_project_folder_valid(self, main_window, temp_project_dir):
        """Test setting a valid project path."""
        main_window.set_project_folder(temp_project_dir)
        
        assert main_window.selected_project_path == temp_project_dir
        assert main_window.project_path_label.text() == temp_project_dir
        assert "Found" in main_window.validation_label.text()
        assert "supported files" in main_window.validation_label.text()
        # Analyze button should be disabled until files are selected
        assert not main_window.analyze_button.isEnabled()
        
        # Select files to enable analyze button
        main_window.file_tree_widget.select_all_files()
        assert main_window.analyze_button.isEnabled()
        
    def test_set_project_folder_invalid(self, main_window, empty_project_dir):
        """Test setting an invalid project path."""
        main_window.set_project_folder(empty_project_dir)
        
        assert main_window.selected_project_path == empty_project_dir
        assert main_window.project_path_label.text() == empty_project_dir
        assert "No supported files found" in main_window.validation_label.text()
        assert not main_window.analyze_button.isEnabled()
        
    def test_initial_ui_state_no_project(self, main_window):
        """Test UI state with no project selected."""
        assert not main_window.analyze_button.isEnabled()
        
    def test_ui_state_valid_project(self, main_window, temp_project_dir):
        """Test UI state with valid project selected."""
        main_window.set_project_folder(temp_project_dir)
        # Analyze button should be disabled until files are selected
        assert not main_window.analyze_button.isEnabled()
        
        # Select files to enable analyze button
        main_window.file_tree_widget.select_all_files()
        assert main_window.analyze_button.isEnabled()
        
    def test_get_selected_project_path(self, main_window, temp_project_dir):
        """Test getting selected project path."""
        assert main_window.get_selected_project_path() is None
        
        main_window.selected_project_path = temp_project_dir
        assert main_window.get_selected_project_path() == temp_project_dir
        
    def test_get_project_description(self, main_window):
        """Test getting project description."""
        assert main_window.get_project_description() == ""
        
        test_description = "Test medical device project"
        main_window.description_text.setPlainText(test_description)
        assert main_window.get_project_description() == test_description
        
    def test_get_project_description_strips_whitespace(self, main_window):
        """Test that project description strips whitespace."""
        test_description = "  Test description  \n\n  "
        main_window.description_text.setPlainText(test_description)
        assert main_window.get_project_description() == "Test description"
        
    @patch('PyQt6.QtWidgets.QFileDialog.getExistingDirectory')
    def test_select_project_folder_dialog(self, mock_dialog, main_window, temp_project_dir):
        """Test project folder selection dialog."""
        mock_dialog.return_value = temp_project_dir
        
        main_window.select_project_folder()
        
        mock_dialog.assert_called_once()
        assert main_window.selected_project_path == temp_project_dir
        
    @patch('PyQt6.QtWidgets.QFileDialog.getExistingDirectory')
    def test_select_project_folder_dialog_cancelled(self, mock_dialog, main_window):
        """Test project folder selection dialog when cancelled."""
        mock_dialog.return_value = ""  # User cancelled
        
        original_path = main_window.selected_project_path
        main_window.select_project_folder()
        
        mock_dialog.assert_called_once()
        assert main_window.selected_project_path == original_path
        
    def test_start_analysis_no_project(self, main_window):
        """Test starting analysis with no project selected."""
        with patch('PyQt6.QtWidgets.QMessageBox.critical') as mock_error:
            main_window.start_analysis()
            mock_error.assert_called_once()
            
    def test_start_analysis_with_description(self, main_window, temp_project_dir):
        """Test starting analysis with project and description."""
        main_window.set_project_folder(temp_project_dir)
        main_window.file_tree_widget.select_all_files()  # Select files first
        main_window.description_text.setPlainText("Test description")
        
        # Connect signal to capture emission
        signal_emitted = []
        main_window.analysis_requested.connect(
            lambda path, desc: signal_emitted.append((path, desc))
        )
        
        main_window.start_analysis()
        
        # Process any pending UI events
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        # Check that signal was emitted with correct parameters
        assert len(signal_emitted) == 1
        assert signal_emitted[0][0] == temp_project_dir
        assert signal_emitted[0][1] == "Test description"
        
        # Check UI state during analysis
        assert main_window.progress_group.isVisible()
        assert not main_window.select_folder_button.isEnabled()
        assert not main_window.description_text.isEnabled()
        assert not main_window.analyze_button.isEnabled()
        
    @patch('PyQt6.QtWidgets.QMessageBox.question')
    def test_start_analysis_no_description_continue(self, mock_question, main_window, temp_project_dir):
        """Test starting analysis with no description but user continues."""
        from PyQt6.QtWidgets import QMessageBox
        mock_question.return_value = QMessageBox.StandardButton.Yes
        
        main_window.set_project_folder(temp_project_dir)
        main_window.file_tree_widget.select_all_files()  # Select files first
        # Don't set description
        
        signal_emitted = []
        main_window.analysis_requested.connect(
            lambda path, desc: signal_emitted.append((path, desc))
        )
        
        main_window.start_analysis()
        
        mock_question.assert_called_once()
        assert len(signal_emitted) == 1
        assert signal_emitted[0][0] == temp_project_dir
        assert signal_emitted[0][1] == ""
        
    @patch('PyQt6.QtWidgets.QMessageBox.question')
    def test_start_analysis_no_description_cancel(self, mock_question, main_window, temp_project_dir):
        """Test starting analysis with no description and user cancels."""
        from PyQt6.QtWidgets import QMessageBox
        mock_question.return_value = QMessageBox.StandardButton.No
        
        main_window.set_project_folder(temp_project_dir)
        main_window.file_tree_widget.select_all_files()  # Select files first
        # Don't set description
        
        signal_emitted = []
        main_window.analysis_requested.connect(
            lambda path, desc: signal_emitted.append((path, desc))
        )
        
        main_window.start_analysis()
        
        mock_question.assert_called_once()
        assert len(signal_emitted) == 0  # Signal should not be emitted
        
    def test_update_progress(self, main_window):
        """Test progress update functionality."""
        main_window.update_progress("Parsing files", 25)
        
        assert "Parsing files" in main_window.progress_label.text()
        assert main_window.progress_bar.value() == 25
        
    def test_analysis_completed_success(self, main_window, temp_project_dir):
        """Test analysis completion with success."""
        # Set up initial state (analysis in progress)
        main_window.set_project_folder(temp_project_dir)
        main_window.description_text.setPlainText("Test description")  # Add description to avoid dialog
        main_window.start_analysis()
        
        # Complete analysis successfully
        main_window.analysis_completed()
        
        assert "completed successfully" in main_window.progress_label.text()
        assert main_window.progress_bar.value() == 100
        assert main_window.select_folder_button.isEnabled()
        assert main_window.description_text.isEnabled()
        assert main_window.analyze_button.isEnabled()
        
    def test_analysis_completed_failure(self, main_window, temp_project_dir):
        """Test analysis completion with failure."""
        # Set up initial state (analysis in progress)
        main_window.set_project_folder(temp_project_dir)
        main_window.description_text.setPlainText("Test description")  # Add description to avoid dialog
        main_window.start_analysis()
        
        # Complete analysis with failure
        error_message = "Parser error"
        main_window.analysis_failed(error_message)
        
        assert "Analysis failed" in main_window.progress_label.text()
        assert error_message in main_window.progress_label.text()
        assert main_window.select_folder_button.isEnabled()
        assert main_window.description_text.isEnabled()
        assert main_window.analyze_button.isEnabled()
        
    def test_signals_exist(self, main_window):
        """Test that required signals exist."""
        assert hasattr(main_window, 'project_selected')
        assert hasattr(main_window, 'analysis_requested')
        
    def test_project_selected_signal_emission(self, main_window, temp_project_dir):
        """Test that project_selected signal is emitted correctly."""
        signal_emitted = []
        main_window.project_selected.connect(lambda path: signal_emitted.append(path))
        
        main_window.set_project_folder(temp_project_dir)
        
        assert len(signal_emitted) == 1
        assert signal_emitted[0] == temp_project_dir
        
    def test_project_selected_signal_emitted_even_invalid(self, main_window, empty_project_dir):
        """Test that project_selected signal is emitted even for invalid projects."""
        signal_emitted = []
        main_window.project_selected.connect(lambda path: signal_emitted.append(path))
        
        main_window.set_project_folder(empty_project_dir)
        
        # Signal should still be emitted, even if project is invalid
        assert len(signal_emitted) == 1
        assert signal_emitted[0] == empty_project_dir


class TestMainWindowIntegration:
    """Integration tests for MainWindow."""
    
    def test_complete_workflow(self, main_window, temp_project_dir):
        """Test complete workflow from project selection to analysis start."""
        # Initially, analyze button should be disabled
        assert not main_window.analyze_button.isEnabled()
        
        # Select project
        main_window.set_project_folder(temp_project_dir)
        
        # Analyze button should still be disabled until files are selected
        assert not main_window.analyze_button.isEnabled()
        
        # Select files
        main_window.file_tree_widget.select_all_files()
        
        # Now analyze button should be enabled
        assert main_window.analyze_button.isEnabled()
        
        # Add description
        description = "Medical monitoring device software"
        main_window.description_text.setPlainText(description)
        
        # Set up signal capture
        analysis_requests = []
        main_window.analysis_requested.connect(
            lambda path, desc: analysis_requests.append((path, desc))
        )
        
        # Start analysis
        main_window.start_analysis()
        
        # Process any pending UI events
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        # Verify signal was emitted correctly
        assert len(analysis_requests) == 1
        assert analysis_requests[0][0] == temp_project_dir
        assert analysis_requests[0][1] == description
        
        # Verify UI state during analysis
        assert main_window.progress_group.isVisible()
        assert not main_window.analyze_button.isEnabled()
        
        # Test file selection methods
        selected_files = main_window.get_selected_files()
        assert len(selected_files) > 0
        
        # Test setting files
        main_window.set_selected_files(selected_files[:1])  # Select only first file
        assert len(main_window.get_selected_files()) == 1
        
        # Simulate analysis completion
        main_window.analysis_completed()
        
        # Verify UI state after completion
        assert main_window.analyze_button.isEnabled()
        assert main_window.progress_bar.value() == 100


if __name__ == "__main__":
    pytest.main([__file__])


class TestMainWindowEnhancedProgress:
    """Test cases for enhanced progress functionality."""
    
    def test_progress_widget_initialization(self, main_window):
        """Test that progress widget is properly initialized."""
        assert hasattr(main_window, 'progress_widget')
        assert not main_window.progress_widget.isVisible()
        
    def test_results_widget_initialization(self, main_window):
        """Test that results widget is properly initialized."""
        assert hasattr(main_window, 'results_widget')
        assert not main_window.results_widget.isEnabled()
        assert main_window.results_widget.count() == 5  # 5 tabs
        
    def test_update_stage_progress(self, main_window):
        """Test stage progress update functionality."""
        from medical_analyzer.ui.progress_widget import AnalysisStage, StageStatus
        
        # Start analysis to initialize progress widget
        main_window.progress_widget.start_analysis()
        
        # Test updating stage progress
        main_window.update_stage_progress(
            "code_parsing", 50, "in_progress", "Parsing C files"
        )
        
        # Check that progress widget was updated
        stage_widget = main_window.progress_widget.stage_widgets[AnalysisStage.CODE_PARSING]
        assert stage_widget.progress == 50
        assert stage_widget.status == StageStatus.IN_PROGRESS
        
    def test_update_stage_progress_with_error(self, main_window):
        """Test stage progress update with error."""
        from medical_analyzer.ui.progress_widget import AnalysisStage, StageStatus
        
        main_window.progress_widget.start_analysis()
        
        main_window.update_stage_progress(
            "feature_extraction", 25, "failed", 
            error_message="Feature extraction failed"
        )
        
        stage_widget = main_window.progress_widget.stage_widgets[AnalysisStage.FEATURE_EXTRACTION]
        assert stage_widget.status == StageStatus.FAILED
        assert stage_widget.error_message == "Feature extraction failed"
        
    def test_analysis_completed_with_results(self, main_window):
        """Test analysis completion with results."""
        # Start analysis first to disable UI
        main_window.select_folder_button.setEnabled(False)
        main_window.analyze_button.setEnabled(False)
        main_window.description_text.setEnabled(False)
        main_window.file_tree_widget.setEnabled(False)
        
        # Mock results data
        results = {
            'summary': {'project_path': '/test/path', 'files_analyzed': 5},
            'requirements': {'user_requirements': [], 'software_requirements': []},
            'risks': []
        }
        
        # Complete analysis
        main_window.analysis_completed(results)
        
        # UI should be re-enabled
        assert main_window.select_folder_button.isEnabled()
        assert main_window.analyze_button.isEnabled()
        assert main_window.description_text.isEnabled()
        assert main_window.file_tree_widget.isEnabled()
        
        # Results should be updated
        assert main_window.results_widget.isEnabled()
        
    def test_analysis_failed_with_partial_results(self, main_window):
        """Test analysis failure with partial results."""
        # Start analysis first to disable UI
        main_window.select_folder_button.setEnabled(False)
        main_window.analyze_button.setEnabled(False)
        main_window.description_text.setEnabled(False)
        main_window.file_tree_widget.setEnabled(False)
        
        # Mock partial results
        partial_results = {
            'summary': {'project_path': '/test/path'},
            'requirements': {'user_requirements': []}
        }
        
        with patch('PyQt6.QtWidgets.QMessageBox.critical') as mock_error:
            main_window.analysis_failed("Test error message", partial_results)
            
            # UI should be re-enabled
            assert main_window.select_folder_button.isEnabled()
            assert main_window.analyze_button.isEnabled()
            assert main_window.description_text.isEnabled()
            assert main_window.file_tree_widget.isEnabled()
            
            # Error should be shown
            mock_error.assert_called_once()
            
    def test_cancel_analysis(self, main_window):
        """Test analysis cancellation."""
        # Start analysis first
        main_window.select_folder_button.setEnabled(False)
        main_window.analyze_button.setEnabled(False)
        main_window.description_text.setEnabled(False)
        main_window.file_tree_widget.setEnabled(False)
        
        # Mock the analysis_cancelled signal
        signal_emitted = False
        def on_analysis_cancelled():
            nonlocal signal_emitted
            signal_emitted = True
            
        main_window.analysis_cancelled.connect(on_analysis_cancelled)
        
        main_window.cancel_analysis()
        
        # UI should be re-enabled
        assert main_window.select_folder_button.isEnabled()
        assert main_window.analyze_button.isEnabled()
        assert main_window.description_text.isEnabled()
        assert main_window.file_tree_widget.isEnabled()
        
        # Signal should be emitted
        assert signal_emitted
        
    def test_progress_widget_signals(self, main_window):
        """Test progress widget signal connections."""
        # Test cancel signal
        cancel_signal_received = False
        def on_cancel():
            nonlocal cancel_signal_received
            cancel_signal_received = True
            
        main_window.analysis_cancelled.connect(on_cancel)
        
        # Simulate cancel button click
        main_window.progress_widget.cancel_requested.emit()
        
        assert cancel_signal_received
        
        # Test stage completed signal
        stage_completed_received = False
        def on_stage_completed(stage_name):
            nonlocal stage_completed_received
            stage_completed_received = True
            
        main_window.progress_widget.stage_completed.connect(on_stage_completed)
        main_window.progress_widget.stage_completed.emit("test_stage")
        
        # The main window should receive the signal
        assert stage_completed_received
        
    def test_results_widget_signals(self, main_window):
        """Test results widget signal connections."""
        # Test export signal
        with patch.object(main_window, 'show_info') as mock_info:
            main_window.results_widget.export_requested.emit("requirements", "csv")
            mock_info.assert_called_once_with("Export", "Export requirements as csv requested")
            
        # Test refresh signal
        with patch.object(main_window, 'show_info') as mock_info:
            main_window.results_widget.refresh_requested.emit("risks")
            mock_info.assert_called_once_with("Refresh", "Refresh risks requested")
            
    def test_stage_name_mapping(self, main_window):
        """Test stage name mapping in update_stage_progress."""
        from medical_analyzer.ui.progress_widget import AnalysisStage, StageStatus
        
        main_window.progress_widget.start_analysis()
        
        # Test all stage mappings
        stage_mappings = {
            "initialization": AnalysisStage.INITIALIZATION,
            "file_scanning": AnalysisStage.FILE_SCANNING,
            "code_parsing": AnalysisStage.CODE_PARSING,
            "feature_extraction": AnalysisStage.FEATURE_EXTRACTION,
            "requirements_generation": AnalysisStage.REQUIREMENTS_GENERATION,
            "risk_analysis": AnalysisStage.RISK_ANALYSIS,
            "traceability_mapping": AnalysisStage.TRACEABILITY_MAPPING,
            "test_generation": AnalysisStage.TEST_GENERATION,
            "finalization": AnalysisStage.FINALIZATION
        }
        
        for stage_name, expected_stage in stage_mappings.items():
            main_window.update_stage_progress(stage_name, 50, "in_progress")
            stage_widget = main_window.progress_widget.stage_widgets[expected_stage]
            assert stage_widget.status == StageStatus.IN_PROGRESS
            
    def test_invalid_stage_name(self, main_window):
        """Test handling of invalid stage name."""
        from medical_analyzer.ui.progress_widget import StageStatus
        
        main_window.progress_widget.start_analysis()
        
        # Should not crash with invalid stage name
        main_window.update_stage_progress("invalid_stage", 50, "in_progress")
        
        # No stage should be updated
        for stage_widget in main_window.progress_widget.stage_widgets.values():
            assert stage_widget.status == StageStatus.PENDING
            
    def test_clear_project_clears_progress_and_results(self, main_window, temp_project_dir):
        """Test that clearing project also clears progress and results."""
        # First set a project and start analysis
        main_window.set_project_folder(temp_project_dir)
        main_window.file_tree_widget.select_all_files()
        main_window.description_text.setPlainText("Test description")
        main_window.start_analysis()
        
        # Verify progress is visible
        assert main_window.progress_widget.isVisible()
        
        # Clear project
        main_window.clear_project()
        
        # Check that progress and results are cleared
        assert not main_window.progress_widget.isVisible()
        assert not main_window.results_widget.isEnabled()
        
    def test_start_analysis_clears_previous_results(self, main_window, temp_project_dir):
        """Test that starting analysis clears previous results."""
        # Enable results widget to simulate previous analysis
        main_window.results_widget.setEnabled(True)
        
        # Set up for new analysis
        main_window.set_project_folder(temp_project_dir)
        main_window.file_tree_widget.select_all_files()
        main_window.description_text.setPlainText("Test description")
        
        # Start analysis
        main_window.start_analysis()
        
        # Results should be cleared (disabled)
        assert not main_window.results_widget.isEnabled()
        
    def test_on_export_requested(self, main_window):
        """Test export request handling."""
        with patch.object(main_window, 'show_info') as mock_info:
            main_window.on_export_requested("requirements", "csv")
            mock_info.assert_called_once_with("Export", "Export requirements as csv requested")
            
    def test_on_refresh_requested(self, main_window):
        """Test refresh request handling."""
        with patch.object(main_window, 'show_info') as mock_info:
            main_window.on_refresh_requested("risks")
            mock_info.assert_called_once_with("Refresh", "Refresh risks requested")
            
    def test_on_stage_completed(self, main_window):
        """Test stage completed handling."""
        # This method currently does nothing, but should not crash
        main_window.on_stage_completed("test_stage")
        # No assertion needed, just verify it doesn't crash