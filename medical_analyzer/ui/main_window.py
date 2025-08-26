"""
Main window implementation for the Medical Software Analysis Tool.
"""

import os
from pathlib import Path
from typing import Optional, List
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QTextEdit, 
    QFileDialog, QMessageBox, QProgressBar, QGroupBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from .file_tree_widget import FileTreeWidget
from .progress_widget import AnalysisProgressWidget, AnalysisStage, StageStatus
from .results_tab_widget import ResultsTabWidget
from ..database.schema import DatabaseManager
from ..services.soup_service import SOUPService
from ..services.export_service import ExportService


class MainWindow(QMainWindow):
    """Main application window for the Medical Software Analysis Tool."""
    
    # Signals
    project_selected = pyqtSignal(str)
    analysis_requested = pyqtSignal(str, str)
    analysis_cancelled = pyqtSignal()
    
    def __init__(self, config_manager=None, app_settings=None):
        super().__init__()
        self.selected_project_path: Optional[str] = None
        self.config_manager = config_manager
        self.app_settings = app_settings
        
        # Initialize services
        self.db_manager = DatabaseManager()
        self.soup_service = SOUPService(self.db_manager)
        self.export_service = ExportService(self.soup_service)
        
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Initialize the user interface components."""
        self.setWindowTitle("Medical Software Analysis Tool")
        self.setMinimumSize(800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Project selection
        project_group = QGroupBox("Project Selection")
        project_layout = QVBoxLayout(project_group)
        
        path_layout = QHBoxLayout()
        self.project_path_label = QLabel("No project selected")
        self.select_folder_button = QPushButton("Select Project Folder")
        path_layout.addWidget(QLabel("Project Root:"))
        path_layout.addWidget(self.project_path_label, 1)
        path_layout.addWidget(self.select_folder_button)
        
        self.validation_label = QLabel("")
        
        project_layout.addLayout(path_layout)
        project_layout.addWidget(self.validation_label)
        layout.addWidget(project_group)
        
        # File selection tree
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout(file_group)
        self.file_tree_widget = FileTreeWidget()
        file_layout.addWidget(self.file_tree_widget)
        layout.addWidget(file_group)
        
        # Project description
        desc_group = QGroupBox("Project Context")
        desc_layout = QVBoxLayout(desc_group)
        desc_layout.addWidget(QLabel("Project Description:"))
        self.description_text = QTextEdit()
        self.description_text.setMinimumHeight(120)
        self.description_text.setEnabled(False)  # Initially disabled until project is selected
        desc_layout.addWidget(self.description_text)
        layout.addWidget(desc_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        self.clear_button = QPushButton("Clear")
        self.analyze_button = QPushButton("Start Analysis")
        self.analyze_button.setEnabled(False)
        self.export_button = QPushButton("Export Bundle")
        self.export_button.setEnabled(False)
        button_layout.addStretch()
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.analyze_button)
        button_layout.addWidget(self.export_button)
        
        # Create main splitter for analysis and results
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Top section with project setup
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.addWidget(project_group)
        top_layout.addWidget(file_group)
        top_layout.addWidget(desc_group)
        top_layout.addLayout(button_layout)
        
        # Enhanced progress widget
        self.progress_widget = AnalysisProgressWidget()
        top_layout.addWidget(self.progress_widget)
        
        main_splitter.addWidget(top_widget)
        
        # Results section
        self.results_widget = ResultsTabWidget(self.soup_service)
        main_splitter.addWidget(self.results_widget)
        
        # Set initial splitter sizes (70% top, 30% bottom)
        main_splitter.setSizes([700, 300])
        
        # Add splitter to main layout
        layout.addWidget(main_splitter)
        
    def setup_connections(self):
        """Set up signal-slot connections."""
        self.select_folder_button.clicked.connect(self.select_project_folder)
        self.analyze_button.clicked.connect(self.start_analysis)
        self.clear_button.clicked.connect(self.clear_project)
        self.export_button.clicked.connect(self.export_bundle)
        self.file_tree_widget.selection_changed.connect(self.on_file_selection_changed)
        
        # Progress widget connections
        self.progress_widget.cancel_requested.connect(self.cancel_analysis)
        self.progress_widget.stage_completed.connect(self.on_stage_completed)
        
        # Results widget connections
        self.results_widget.export_requested.connect(self.on_export_requested)
        self.results_widget.refresh_requested.connect(self.on_refresh_requested)
        
    def select_project_folder(self):
        """Open folder selection dialog."""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Project Root Folder", ""
        )
        if folder_path:
            self.set_project_folder(folder_path)
            
    def set_project_folder(self, folder_path: str):
        """Set and validate the project folder."""
        if not os.path.exists(folder_path):
            self.show_error("Invalid folder", "The selected folder does not exist.")
            return
            
        self.selected_project_path = folder_path
        self.project_path_label.setText(folder_path)
        
        # Load file tree
        self.file_tree_widget.load_directory_structure(folder_path)
        
        # Validate project structure
        validation_result = self.validate_project_structure(folder_path)
        self.validation_label.setText(validation_result["message"])
        
        if validation_result["valid"]:
            self.validation_label.setStyleSheet("color: #4CAF50;")
            self.description_text.setEnabled(True)
            # Enable analyze button only if files are selected
            self._update_analyze_button_state()
        else:
            self.validation_label.setStyleSheet("color: #f44336;")
            self.analyze_button.setEnabled(False)
            self.description_text.setEnabled(False)
            
        self.project_selected.emit(folder_path)
        
    def validate_project_structure(self, folder_path: str) -> dict:
        """Validate the project structure and look for supported files."""
        try:
            # Check if path exists first
            if not os.path.exists(folder_path):
                return {
                    "valid": False,
                    "message": "Error scanning project: path does not exist"
                }
                
            supported_extensions = {'.c', '.h', '.js', '.ts', '.jsx', '.tsx'}
            supported_files = []
            
            for root, dirs, files in os.walk(folder_path):
                dirs[:] = [d for d in dirs if not d.startswith('.') and 
                          d not in ['node_modules', '__pycache__', 'build', 'dist']]
                
                for file in files:
                    file_path = Path(root) / file
                    if file_path.suffix.lower() in supported_extensions:
                        supported_files.append(str(file_path))
                        
            if not supported_files:
                return {
                    "valid": False,
                    "message": "No supported files found (C, JavaScript, TypeScript files)"
                }
            else:
                return {
                    "valid": True,
                    "message": f"Found {len(supported_files)} supported files for analysis"
                }
                
        except Exception as e:
            return {
                "valid": False,
                "message": f"Error scanning project: {str(e)}"
            }
            
    def start_analysis(self):
        """Start the analysis process."""
        if not self.selected_project_path:
            self.show_error("No project selected", "Please select a project folder first.")
            return
            
        # Validate file selection
        file_validation = self.file_tree_widget.validate_selection()
        if not file_validation["valid"]:
            self.show_error("No files selected", file_validation["message"])
            return
            
        description = self.description_text.toPlainText().strip()
        if not description:
            reply = QMessageBox.question(
                self, "No Description",
                "No project description provided. Continue without description?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
                
        # Start enhanced progress tracking
        self.progress_widget.start_analysis()
        
        # Disable UI elements during analysis
        self.select_folder_button.setEnabled(False)
        self.analyze_button.setEnabled(False)
        self.description_text.setEnabled(False)
        self.file_tree_widget.setEnabled(False)
        
        # Clear previous results
        self.results_widget.clear_results()
        
        # Emit analysis requested signal with selected files
        selected_files = self.file_tree_widget.get_selected_files()
        self.analysis_requested.emit(self.selected_project_path, description)
        
    def clear_project(self):
        """Clear the current project selection."""
        self.selected_project_path = None
        self.project_path_label.setText("No project selected")
        self.validation_label.setText("")
        self.description_text.clear()
        self.analyze_button.setEnabled(False)
        self.export_button.setEnabled(False)
        
        # Hide progress and clear results
        self.progress_widget.hide_progress()
        self.results_widget.clear_results()
        
        # Clear file tree
        self.file_tree_widget.tree_widget.clear()
        
        # Re-enable UI elements
        self.select_folder_button.setEnabled(True)
        self.file_tree_widget.setEnabled(True)
        # Only enable description if we have a valid project
        if self.selected_project_path:
            validation_result = self.validate_project_structure(self.selected_project_path)
            if validation_result["valid"]:
                self.description_text.setEnabled(True)
                
    def on_file_selection_changed(self, selected_files: List[str]):
        """Handle file selection changes from the file tree widget."""
        self._update_analyze_button_state()
        
    def _update_analyze_button_state(self):
        """Update the analyze button enabled state based on project and file selection."""
        if not self.selected_project_path:
            self.analyze_button.setEnabled(False)
            return
            
        # Check if project structure is valid
        validation_result = self.validate_project_structure(self.selected_project_path)
        if not validation_result["valid"]:
            self.analyze_button.setEnabled(False)
            return
            
        # Check if files are selected
        file_validation = self.file_tree_widget.validate_selection()
        self.analyze_button.setEnabled(file_validation["valid"])
        
    def update_stage_progress(self, stage_name: str, progress: int, 
                            status: str = None, message: str = None,
                            error_message: str = None):
        """Update progress for a specific analysis stage."""
        # Map stage name to AnalysisStage enum
        stage_mapping = {
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
        
        stage = stage_mapping.get(stage_name.lower())
        if stage:
            # Map status string to StageStatus enum
            status_mapping = {
                "pending": StageStatus.PENDING,
                "in_progress": StageStatus.IN_PROGRESS,
                "completed": StageStatus.COMPLETED,
                "failed": StageStatus.FAILED,
                "skipped": StageStatus.SKIPPED
            }
            
            stage_status = status_mapping.get(status.lower()) if status else None
            self.progress_widget.update_stage_progress(
                stage, progress, stage_status, message, error_message
            )
        
    def analysis_completed(self, results: dict = None):
        """Handle analysis completion."""
        self.progress_widget.complete_analysis(success=True)
        
        # Update results if provided
        if results:
            self.results_widget.update_results(results)
        
        # Re-enable UI elements
        self.select_folder_button.setEnabled(True)
        self.analyze_button.setEnabled(True)
        self.description_text.setEnabled(True)
        self.file_tree_widget.setEnabled(True)
        
        # Enable export button if we have results
        if results:
            self.export_button.setEnabled(True)
        
    def analysis_failed(self, error_message: str, partial_results: dict = None):
        """Handle analysis failure."""
        self.progress_widget.complete_analysis(success=False)
        
        # Show partial results if available
        if partial_results:
            failed_stages = self.progress_widget.get_failed_stages()
            error_list = [f"Failed at stage: {stage.value}" for stage in failed_stages]
            if error_message:
                error_list.append(error_message)
            self.results_widget.show_partial_results(partial_results, error_list)
        
        # Re-enable UI elements
        self.select_folder_button.setEnabled(True)
        self.analyze_button.setEnabled(True)
        self.description_text.setEnabled(True)
        self.file_tree_widget.setEnabled(True)
        
        self.show_error("Analysis Failed", error_message)
        
    def cancel_analysis(self):
        """Handle analysis cancellation."""
        self.progress_widget.cancel_analysis()
        self.analysis_cancelled.emit()
        
        # Re-enable UI elements
        self.select_folder_button.setEnabled(True)
        self.analyze_button.setEnabled(True)
        self.description_text.setEnabled(True)
        self.file_tree_widget.setEnabled(True)
        
    def on_stage_completed(self, stage_name: str):
        """Handle completion of an analysis stage."""
        # This can be used for additional processing when stages complete
        pass
        
    def on_export_requested(self, tab_name: str, export_type: str):
        """Handle export request from results tabs."""
        # This would typically open a file dialog and export the data
        self.show_info("Export", f"Export {tab_name} as {export_type} requested")
        
    def on_refresh_requested(self, tab_name: str):
        """Handle refresh request from results tabs."""
        # This would typically re-run analysis for specific components
        self.show_info("Refresh", f"Refresh {tab_name} requested")
    
    def export_bundle(self):
        """Create and export a comprehensive analysis bundle."""
        if not self.selected_project_path:
            self.show_error("Export Error", "No project selected for export.")
            return
        
        # Get project name from path
        project_name = os.path.basename(self.selected_project_path)
        if not project_name:
            project_name = "medical_software_project"
        
        # Get analysis results from results widget
        analysis_results = self.results_widget.analysis_results
        if not analysis_results:
            self.show_error("Export Error", "No analysis results available for export.")
            return
        
        # Ask user for export location
        export_dir = QFileDialog.getExistingDirectory(
            self, "Select Export Directory", "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not export_dir:
            return  # User cancelled
        
        try:
            # Log export start
            self.export_service.log_action(
                "export_initiated", 
                f"User initiated export for project: {project_name}",
                user="user"
            )
            
            # Create the export bundle
            bundle_path = self.export_service.create_comprehensive_export(
                analysis_results=analysis_results,
                project_name=project_name,
                project_path=self.selected_project_path,
                output_dir=export_dir
            )
            
            # Show success message
            self.show_info(
                "Export Successful", 
                f"Analysis bundle exported successfully to:\n{bundle_path}\n\n"
                "The bundle contains all analysis artifacts including requirements, "
                "risk register, traceability matrix, test results, and SOUP inventory."
            )
            
        except Exception as e:
            self.show_error("Export Failed", f"Failed to create export bundle:\n{str(e)}")
            
            # Log export failure
            self.export_service.log_action(
                "export_failed", 
                f"Export failed with error: {str(e)}",
                user="user"
            )
        
    def show_error(self, title: str, message: str):
        """Show an error message dialog."""
        QMessageBox.critical(self, title, message)
        
    def show_info(self, title: str, message: str):
        """Show an information message dialog."""
        QMessageBox.information(self, title, message)
        
    def get_selected_project_path(self) -> Optional[str]:
        """Get the currently selected project path."""
        return self.selected_project_path
        
    def get_project_description(self) -> str:
        """Get the project description text."""
        return self.description_text.toPlainText().strip()
        
    def get_selected_files(self) -> List[str]:
        """Get the list of selected files from the file tree widget."""
        return self.file_tree_widget.get_selected_files()
        
    def set_selected_files(self, file_paths: List[str]):
        """Set the selected files in the file tree widget."""
        self.file_tree_widget.set_selected_files(file_paths)