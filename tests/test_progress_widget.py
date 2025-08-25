"""
Tests for the AnalysisProgressWidget.
"""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtTest import QTest
import sys

from medical_analyzer.ui.progress_widget import (
    AnalysisProgressWidget, StageProgressWidget, 
    AnalysisStage, StageStatus
)


@pytest.fixture
def app():
    """Create QApplication instance for testing."""
    if not QApplication.instance():
        return QApplication(sys.argv)
    return QApplication.instance()


@pytest.fixture
def progress_widget(app):
    """Create AnalysisProgressWidget instance for testing."""
    widget = AnalysisProgressWidget()
    return widget


@pytest.fixture
def stage_widget(app):
    """Create StageProgressWidget instance for testing."""
    widget = StageProgressWidget(AnalysisStage.CODE_PARSING)
    return widget


class TestStageProgressWidget:
    """Test cases for StageProgressWidget."""
    
    def test_initialization(self, stage_widget):
        """Test stage widget initialization."""
        assert stage_widget.stage == AnalysisStage.CODE_PARSING
        assert stage_widget.status == StageStatus.PENDING
        assert stage_widget.progress == 0
        assert stage_widget.start_time is None
        assert stage_widget.end_time is None
        assert stage_widget.error_message is None
        
    def test_update_progress(self, stage_widget):
        """Test progress update functionality."""
        # Test progress update
        stage_widget.update_progress(50)
        assert stage_widget.progress == 50
        assert stage_widget.progress_bar.value() == 50
        
        # Test status update
        stage_widget.update_progress(75, StageStatus.IN_PROGRESS)
        assert stage_widget.status == StageStatus.IN_PROGRESS
        assert stage_widget.progress == 75
        assert stage_widget.start_time is not None
        
        # Test completion
        stage_widget.update_progress(100, StageStatus.COMPLETED)
        assert stage_widget.status == StageStatus.COMPLETED
        assert stage_widget.end_time is not None
        
    def test_error_handling(self, stage_widget):
        """Test error handling in stage widget."""
        error_msg = "Test error message"
        stage_widget.update_progress(25, StageStatus.FAILED, error_msg)
        
        assert stage_widget.status == StageStatus.FAILED
        assert stage_widget.error_message == error_msg
        assert stage_widget.error_label.isVisible()
        
    def test_appearance_updates(self, stage_widget):
        """Test visual appearance updates."""
        # Test pending state
        stage_widget.update_progress(0, StageStatus.PENDING)
        assert "color: #666666" in stage_widget.status_label.styleSheet()
        
        # Test in progress state
        stage_widget.update_progress(50, StageStatus.IN_PROGRESS)
        assert "color: #2196F3" in stage_widget.status_label.styleSheet()
        
        # Test completed state
        stage_widget.update_progress(100, StageStatus.COMPLETED)
        assert "color: #4CAF50" in stage_widget.status_label.styleSheet()
        
        # Test failed state
        stage_widget.update_progress(25, StageStatus.FAILED)
        assert "color: #f44336" in stage_widget.status_label.styleSheet()


class TestAnalysisProgressWidget:
    """Test cases for AnalysisProgressWidget."""
    
    def test_initialization(self, progress_widget):
        """Test progress widget initialization."""
        assert len(progress_widget.stage_widgets) == len(AnalysisStage)
        assert progress_widget.current_stage is None
        assert progress_widget.completed_stages == 0
        assert progress_widget.start_time is None
        assert not progress_widget.isVisible()
        
    def test_start_analysis(self, progress_widget):
        """Test analysis start functionality."""
        progress_widget.start_analysis()
        
        assert progress_widget.start_time is not None
        assert progress_widget.completed_stages == 0
        assert progress_widget.isVisible()
        assert progress_widget.cancel_button.isEnabled()
        assert progress_widget.timer.isActive()
        
        # Check that all stages are reset to pending
        for stage_widget in progress_widget.stage_widgets.values():
            assert stage_widget.status == StageStatus.PENDING
            
    def test_update_stage_progress(self, progress_widget):
        """Test stage progress update functionality."""
        progress_widget.start_analysis()
        
        # Test starting a stage
        stage = AnalysisStage.CODE_PARSING
        progress_widget.update_stage_progress(
            stage, 25, StageStatus.IN_PROGRESS, "Starting code parsing"
        )
        
        assert progress_widget.current_stage == stage
        assert progress_widget.stage_widgets[stage].status == StageStatus.IN_PROGRESS
        assert progress_widget.stage_widgets[stage].progress == 25
        
        # Test completing a stage
        progress_widget.update_stage_progress(
            stage, 100, StageStatus.COMPLETED, "Code parsing completed"
        )
        
        assert progress_widget.completed_stages == 1
        assert progress_widget.stage_widgets[stage].status == StageStatus.COMPLETED
        
        # Check overall progress update
        expected_overall = int((1 / len(AnalysisStage)) * 100)
        assert progress_widget.overall_progress_bar.value() == expected_overall
        
    def test_stage_failure(self, progress_widget):
        """Test stage failure handling."""
        progress_widget.start_analysis()
        
        stage = AnalysisStage.FEATURE_EXTRACTION
        error_msg = "Feature extraction failed"
        
        progress_widget.update_stage_progress(
            stage, 50, StageStatus.FAILED, error_message=error_msg
        )
        
        assert progress_widget.stage_widgets[stage].status == StageStatus.FAILED
        assert progress_widget.stage_widgets[stage].error_message == error_msg
        assert "Failed at" in progress_widget.current_stage_label.text()
        
    def test_complete_analysis(self, progress_widget):
        """Test analysis completion."""
        progress_widget.start_analysis()
        
        # Test successful completion
        progress_widget.complete_analysis(success=True)
        
        assert not progress_widget.timer.isActive()
        assert not progress_widget.cancel_button.isEnabled()
        assert progress_widget.overall_progress_bar.value() == 100
        assert "completed successfully" in progress_widget.current_stage_label.text()
        
        # Test failed completion
        progress_widget.start_analysis()
        progress_widget.complete_analysis(success=False)
        
        assert "failed" in progress_widget.current_stage_label.text()
        
    def test_cancel_analysis(self, progress_widget):
        """Test analysis cancellation."""
        progress_widget.start_analysis()
        progress_widget.cancel_analysis()
        
        assert not progress_widget.timer.isActive()
        assert not progress_widget.cancel_button.isEnabled()
        assert "cancelled" in progress_widget.current_stage_label.text()
        
    def test_log_functionality(self, progress_widget):
        """Test log functionality."""
        progress_widget.start_analysis()
        
        # Test adding log entries
        progress_widget.add_log_entry("Test log message")
        log_content = progress_widget.log_text.toPlainText()
        assert "Test log message" in log_content
        
        # Test log visibility toggle
        initial_visibility = progress_widget.log_text.isVisible()
        progress_widget.toggle_log_visibility()
        assert progress_widget.log_text.isVisible() != initial_visibility
        
        # Test log clearing
        progress_widget.log_text.clear()
        assert progress_widget.log_text.toPlainText() == ""
        
    def test_time_estimation(self, progress_widget):
        """Test time estimation functionality."""
        with patch('medical_analyzer.ui.progress_widget.datetime') as mock_datetime:
            from datetime import datetime, timedelta
            
            # Mock start time
            start_time = datetime(2023, 1, 1, 12, 0, 0)
            current_time = start_time + timedelta(seconds=60)  # 1 minute elapsed
            
            mock_datetime.now.return_value = current_time
            progress_widget.start_time = start_time
            progress_widget.completed_stages = 2  # 2 out of 9 stages completed
            
            progress_widget.update_elapsed_time()
            
            assert "01:00" in progress_widget.elapsed_time_label.text()
            # Should show estimated time based on current progress
            assert "Estimated:" in progress_widget.estimated_time_label.text()
            
    def test_signal_emissions(self, progress_widget):
        """Test signal emissions."""
        # Test cancel signal
        cancel_signal_received = False
        
        def on_cancel():
            nonlocal cancel_signal_received
            cancel_signal_received = True
            
        progress_widget.cancel_requested.connect(on_cancel)
        progress_widget.cancel_button.click()
        
        assert cancel_signal_received
        
        # Test stage completed signal
        stage_completed_signal = None
        
        def on_stage_completed(stage_name):
            nonlocal stage_completed_signal
            stage_completed_signal = stage_name
            
        progress_widget.stage_completed.connect(on_stage_completed)
        progress_widget.start_analysis()
        
        # Complete a stage
        stage = AnalysisStage.INITIALIZATION
        progress_widget.update_stage_progress(
            stage, 100, StageStatus.COMPLETED
        )
        
        assert stage_completed_signal == stage.value
        
    def test_get_failed_stages(self, progress_widget):
        """Test getting failed stages."""
        progress_widget.start_analysis()
        
        # Fail a couple of stages
        progress_widget.update_stage_progress(
            AnalysisStage.CODE_PARSING, 50, StageStatus.FAILED
        )
        progress_widget.update_stage_progress(
            AnalysisStage.RISK_ANALYSIS, 25, StageStatus.FAILED
        )
        
        failed_stages = progress_widget.get_failed_stages()
        assert len(failed_stages) == 2
        assert AnalysisStage.CODE_PARSING in failed_stages
        assert AnalysisStage.RISK_ANALYSIS in failed_stages
        
    def test_hide_progress(self, progress_widget):
        """Test hiding progress widget."""
        progress_widget.start_analysis()
        assert progress_widget.isVisible()
        
        progress_widget.hide_progress()
        assert not progress_widget.isVisible()
        assert not progress_widget.timer.isActive()


if __name__ == '__main__':
    pytest.main([__file__])