"""
Enhanced progress widget for displaying detailed analysis progress.
"""

from typing import Dict, List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, 
    QGroupBox, QFrame, QScrollArea, QTextEdit, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette
from enum import Enum
from datetime import datetime


class AnalysisStage(Enum):
    """Enumeration of analysis stages."""
    INITIALIZATION = "Initialization"
    FILE_SCANNING = "File Scanning"
    CODE_PARSING = "Code Parsing"
    FEATURE_EXTRACTION = "Feature Extraction"
    REQUIREMENTS_GENERATION = "Requirements Generation"
    RISK_ANALYSIS = "Risk Analysis"
    TRACEABILITY_MAPPING = "Traceability Mapping"
    TEST_GENERATION = "Test Generation"
    FINALIZATION = "Finalization"


class StageStatus(Enum):
    """Enumeration of stage statuses."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StageProgressWidget(QWidget):
    """Widget for displaying progress of a single analysis stage."""
    
    def __init__(self, stage: AnalysisStage):
        super().__init__()
        self.stage = stage
        self.status = StageStatus.PENDING
        self.progress = 0
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize the stage progress UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Stage name label
        self.stage_label = QLabel(self.stage.value)
        self.stage_label.setMinimumWidth(150)
        font = QFont()
        font.setBold(True)
        self.stage_label.setFont(font)
        layout.addWidget(self.stage_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumWidth(200)
        self.progress_bar.setMaximumHeight(20)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Pending")
        self.status_label.setMinimumWidth(80)
        layout.addWidget(self.status_label)
        
        # Time label
        self.time_label = QLabel("")
        self.time_label.setMinimumWidth(100)
        layout.addWidget(self.time_label)
        
        # Error indicator (initially hidden)
        self.error_label = QLabel("❌")
        self.error_label.setVisible(False)
        self.error_label.setToolTip("Click to view error details")
        self.error_label.mousePressEvent = self.show_error_details
        layout.addWidget(self.error_label)
        
        layout.addStretch()
        self.update_appearance()
        
    def update_progress(self, progress: int, status: StageStatus = None, 
                       error_message: str = None):
        """Update the progress and status of this stage."""
        self.progress = progress
        self.progress_bar.setValue(progress)
        
        if status:
            old_status = self.status
            self.status = status
            
            # Update timing
            if status == StageStatus.IN_PROGRESS and old_status == StageStatus.PENDING:
                self.start_time = datetime.now()
            elif status in [StageStatus.COMPLETED, StageStatus.FAILED, StageStatus.SKIPPED]:
                self.end_time = datetime.now()
                
        if error_message:
            self.error_message = error_message
            
        self.update_appearance()
        
    def update_appearance(self):
        """Update the visual appearance based on current status."""
        # Update status label
        self.status_label.setText(self.status.value.replace('_', ' ').title())
        
        # Update colors based on status
        if self.status == StageStatus.PENDING:
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #e0e0e0; }")
            self.status_label.setStyleSheet("color: #666666;")
        elif self.status == StageStatus.IN_PROGRESS:
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #2196F3; }")
            self.status_label.setStyleSheet("color: #2196F3; font-weight: bold;")
        elif self.status == StageStatus.COMPLETED:
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        elif self.status == StageStatus.FAILED:
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #f44336; }")
            self.status_label.setStyleSheet("color: #f44336; font-weight: bold;")
            if self.error_message:
                self.error_label.setVisible(True)
        elif self.status == StageStatus.SKIPPED:
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #FF9800; }")
            self.status_label.setStyleSheet("color: #FF9800; font-weight: bold;")
            
        # Update time label
        if self.start_time:
            if self.end_time:
                duration = self.end_time - self.start_time
                self.time_label.setText(f"{duration.total_seconds():.1f}s")
            else:
                duration = datetime.now() - self.start_time
                self.time_label.setText(f"{duration.total_seconds():.1f}s")
        else:
            self.time_label.setText("")
            
    def show_error_details(self, event):
        """Show error details when error indicator is clicked."""
        if self.error_message:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self, f"Error in {self.stage.value}",
                self.error_message
            )


class AnalysisProgressWidget(QWidget):
    """Enhanced progress widget for displaying detailed analysis progress."""
    
    # Signals
    cancel_requested = pyqtSignal()
    stage_completed = pyqtSignal(str)  # stage_name
    
    def __init__(self):
        super().__init__()
        self.stage_widgets: Dict[AnalysisStage, StageProgressWidget] = {}
        self.current_stage: Optional[AnalysisStage] = None
        self.total_stages = len(AnalysisStage)
        self.completed_stages = 0
        self.start_time: Optional[datetime] = None
        self.setup_ui()
        self.setup_timer()
        
    def setup_ui(self):
        """Initialize the progress widget UI."""
        layout = QVBoxLayout(self)
        
        # Overall progress section
        overall_group = QGroupBox("Overall Progress")
        overall_layout = QVBoxLayout(overall_group)
        
        # Overall progress bar
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("Total Progress:"))
        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setMinimumHeight(25)
        progress_layout.addWidget(self.overall_progress_bar)
        
        self.overall_percentage_label = QLabel("0%")
        self.overall_percentage_label.setMinimumWidth(40)
        progress_layout.addWidget(self.overall_percentage_label)
        overall_layout.addLayout(progress_layout)
        
        # Time and status info
        info_layout = QHBoxLayout()
        self.elapsed_time_label = QLabel("Elapsed: 0s")
        self.estimated_time_label = QLabel("Estimated: --")
        self.current_stage_label = QLabel("Status: Ready")
        
        info_layout.addWidget(self.elapsed_time_label)
        info_layout.addWidget(self.estimated_time_label)
        info_layout.addWidget(self.current_stage_label)
        info_layout.addStretch()
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel Analysis")
        self.cancel_button.clicked.connect(self.cancel_requested.emit)
        self.cancel_button.setEnabled(False)
        info_layout.addWidget(self.cancel_button)
        
        overall_layout.addLayout(info_layout)
        layout.addWidget(overall_group)
        
        # Stage details section
        stages_group = QGroupBox("Stage Details")
        stages_layout = QVBoxLayout(stages_group)
        
        # Create scroll area for stages
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Create stage widgets
        for stage in AnalysisStage:
            stage_widget = StageProgressWidget(stage)
            self.stage_widgets[stage] = stage_widget
            scroll_layout.addWidget(stage_widget)
            
            # Add separator line (except for last item)
            if stage != list(AnalysisStage)[-1]:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setFrameShadow(QFrame.Shadow.Sunken)
                scroll_layout.addWidget(line)
                
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(300)
        
        stages_layout.addWidget(scroll_area)
        layout.addWidget(stages_group)
        
        # Log section (collapsible)
        self.log_group = QGroupBox("Analysis Log")
        log_layout = QVBoxLayout(self.log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        
        # Log controls
        log_controls = QHBoxLayout()
        self.clear_log_button = QPushButton("Clear Log")
        self.clear_log_button.clicked.connect(self.log_text.clear)
        self.show_log_button = QPushButton("Hide Log")
        self.show_log_button.clicked.connect(self.toggle_log_visibility)
        
        log_controls.addStretch()
        log_controls.addWidget(self.clear_log_button)
        log_controls.addWidget(self.show_log_button)
        log_layout.addLayout(log_controls)
        
        layout.addWidget(self.log_group)
        
        # Initially hide the widget
        self.setVisible(False)
        
    def setup_timer(self):
        """Set up timer for updating elapsed time."""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_elapsed_time)
        
    def start_analysis(self):
        """Start the analysis progress tracking."""
        self.start_time = datetime.now()
        self.completed_stages = 0
        self.current_stage = None
        
        # Reset all stages
        for stage_widget in self.stage_widgets.values():
            stage_widget.update_progress(0, StageStatus.PENDING)
            
        # Reset overall progress
        self.overall_progress_bar.setValue(0)
        self.overall_percentage_label.setText("0%")
        self.current_stage_label.setText("Status: Starting analysis...")
        
        # Clear log
        self.log_text.clear()
        self.add_log_entry("Analysis started")
        
        # Show widget and enable cancel
        self.setVisible(True)
        self.cancel_button.setEnabled(True)
        
        # Start timer
        self.timer.start(1000)  # Update every second
        
    def update_stage_progress(self, stage: AnalysisStage, progress: int, 
                            status: StageStatus = None, message: str = None,
                            error_message: str = None):
        """Update progress for a specific stage."""
        if stage in self.stage_widgets:
            # Update stage widget
            self.stage_widgets[stage].update_progress(progress, status, error_message)
            
            # Update current stage tracking
            if status == StageStatus.IN_PROGRESS:
                self.current_stage = stage
                self.current_stage_label.setText(f"Status: {stage.value}")
                
            elif status == StageStatus.COMPLETED:
                if stage == self.current_stage:
                    self.completed_stages += 1
                    self.stage_completed.emit(stage.value)
                    
            elif status == StageStatus.FAILED:
                self.current_stage_label.setText(f"Status: Failed at {stage.value}")
                    
            # Update overall progress
            overall_progress = int((self.completed_stages / self.total_stages) * 100)
            self.overall_progress_bar.setValue(overall_progress)
            self.overall_percentage_label.setText(f"{overall_progress}%")
            
            # Add log entry
            if message:
                self.add_log_entry(f"[{stage.value}] {message}")
            if error_message:
                self.add_log_entry(f"[{stage.value}] ERROR: {error_message}")
                
    def complete_analysis(self, success: bool = True):
        """Complete the analysis progress tracking."""
        self.timer.stop()
        self.cancel_button.setEnabled(False)
        
        if success:
            self.overall_progress_bar.setValue(100)
            self.overall_percentage_label.setText("100%")
            self.current_stage_label.setText("Status: Analysis completed successfully")
            self.add_log_entry("Analysis completed successfully")
        else:
            self.current_stage_label.setText("Status: Analysis failed")
            self.add_log_entry("Analysis failed")
            
    def cancel_analysis(self):
        """Cancel the analysis progress tracking."""
        self.timer.stop()
        self.cancel_button.setEnabled(False)
        self.current_stage_label.setText("Status: Analysis cancelled")
        self.add_log_entry("Analysis cancelled by user")
        
    def hide_progress(self):
        """Hide the progress widget."""
        self.setVisible(False)
        self.timer.stop()
        
    def add_log_entry(self, message: str):
        """Add an entry to the analysis log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.log_text.append(log_entry)
        
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def update_elapsed_time(self):
        """Update the elapsed time display."""
        if self.start_time:
            elapsed = datetime.now() - self.start_time
            elapsed_seconds = int(elapsed.total_seconds())
            
            hours = elapsed_seconds // 3600
            minutes = (elapsed_seconds % 3600) // 60
            seconds = elapsed_seconds % 60
            
            if hours > 0:
                time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                time_str = f"{minutes:02d}:{seconds:02d}"
                
            self.elapsed_time_label.setText(f"Elapsed: {time_str}")
            
            # Estimate remaining time based on current progress
            if self.completed_stages > 0:
                avg_time_per_stage = elapsed.total_seconds() / self.completed_stages
                remaining_stages = self.total_stages - self.completed_stages
                estimated_remaining = int(avg_time_per_stage * remaining_stages)
                
                if estimated_remaining > 0:
                    est_minutes = estimated_remaining // 60
                    est_seconds = estimated_remaining % 60
                    self.estimated_time_label.setText(f"Estimated: {est_minutes:02d}:{est_seconds:02d}")
                else:
                    self.estimated_time_label.setText("Estimated: <1min")
            else:
                self.estimated_time_label.setText("Estimated: --")
                
    def toggle_log_visibility(self):
        """Toggle the visibility of the log section."""
        if self.log_text.isVisible():
            self.log_text.setVisible(False)
            self.clear_log_button.setVisible(False)
            self.show_log_button.setText("Show Log")
        else:
            self.log_text.setVisible(True)
            self.clear_log_button.setVisible(True)
            self.show_log_button.setText("Hide Log")
            
    def get_stage_status(self, stage: AnalysisStage) -> StageStatus:
        """Get the current status of a specific stage."""
        if stage in self.stage_widgets:
            return self.stage_widgets[stage].status
        return StageStatus.PENDING
        
    def get_failed_stages(self) -> List[AnalysisStage]:
        """Get list of stages that failed."""
        failed_stages = []
        for stage, widget in self.stage_widgets.items():
            if widget.status == StageStatus.FAILED:
                failed_stages.append(stage)
        return failed_stages