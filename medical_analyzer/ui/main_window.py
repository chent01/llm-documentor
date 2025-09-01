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
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from .file_tree_widget import FileTreeWidget
from .progress_widget import AnalysisProgressWidget, AnalysisStage, StageStatus
from .results_tab_widget import ResultsTabWidget
from .requirements_tab_widget import RequirementsTabWidget
from .traceability_matrix_widget import TraceabilityMatrixWidget
from .test_case_export_widget import CaseModelExportWidget
from .soup_widget import SOUPWidget
from ..database.schema import DatabaseManager
from ..services.soup_service import SOUPService
from ..services.export_service import ExportService
from ..services.test_case_generator import CaseGenerator
from ..services.traceability_service import TraceabilityService
from ..llm.backend import LLMBackend


class MainWindow(QMainWindow):
    """Main application window for the Medical Software Analysis Tool."""
    
    # Signals
    project_selected = pyqtSignal(str)
    analysis_requested = pyqtSignal(str, str, list)
    analysis_cancelled = pyqtSignal()
    
    def __init__(self, config_manager=None, app_settings=None, llm_backend=None):
        super().__init__()
        self.selected_project_path: Optional[str] = None
        self.config_manager = config_manager
        self.app_settings = app_settings
        self.llm_backend = llm_backend
        
        # Initialize services
        self.db_manager = DatabaseManager()
        self.soup_service = SOUPService(self.db_manager)
        self.export_service = ExportService(self.soup_service)
        self.traceability_service = TraceabilityService(self.db_manager)
        
        # Initialize enhanced UI components
        self.requirements_tab_widget: Optional[RequirementsTabWidget] = None
        self.traceability_matrix_widget: Optional[TraceabilityMatrixWidget] = None
        self.test_case_export_widget: Optional[CaseModelExportWidget] = None
        self.enhanced_soup_widget: Optional[SOUPWidget] = None
        
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
        
        # Results section with enhanced components
        self.results_widget = ResultsTabWidget(self.soup_service)
        
        # Initialize enhanced UI components
        self.requirements_tab_widget = RequirementsTabWidget()
        self.traceability_matrix_widget = TraceabilityMatrixWidget()
        
        # Initialize test case export widget with generator
        if self.llm_backend:
            test_generator = CaseGenerator(self.llm_backend)
            self.test_case_export_widget = CaseModelExportWidget()
            self.test_case_export_widget.set_generator(test_generator)
        else:
            self.test_case_export_widget = CaseModelExportWidget()
        
        # Initialize enhanced SOUP widget
        self.enhanced_soup_widget = SOUPWidget(self.soup_service)
        
        # Add enhanced components to results widget
        self.results_widget.add_enhanced_tab("Requirements", self.requirements_tab_widget)
        self.results_widget.add_enhanced_tab("Traceability Matrix", self.traceability_matrix_widget)
        self.results_widget.add_enhanced_tab("Test Cases", self.test_case_export_widget)
        self.results_widget.add_enhanced_tab("SOUP Inventory", self.enhanced_soup_widget)
        
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
        
        # Enhanced component signal connections
        self.setup_enhanced_component_connections()
        
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
                
            supported_extensions = {'.c', '.h', '.js', '.ts', '.jsx', '.tsx', '.json'}
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
        self.analysis_requested.emit(self.selected_project_path, description, selected_files)
        
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
            # Also update enhanced components
            self.update_enhanced_components_with_results(results)
        
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
    
    def setup_enhanced_component_connections(self):
        """Set up comprehensive signal connections between enhanced components."""
        # Requirements Tab Widget connections
        if self.requirements_tab_widget:
            # Connect requirements updates to traceability matrix refresh
            self.requirements_tab_widget.requirements_updated.connect(self.on_requirements_updated)
            self.requirements_tab_widget.traceability_update_requested.connect(self.on_traceability_update_requested)
            
            # Connect requirements updates to test case regeneration triggers
            self.requirements_tab_widget.requirements_updated.connect(self.on_requirements_changed_for_tests)
        
        # Traceability Matrix Widget connections
        if self.traceability_matrix_widget:
            # Connect export signals to file operations
            self.traceability_matrix_widget.export_requested.connect(self.on_traceability_export_requested)
            self.traceability_matrix_widget.gap_selected.connect(self.on_gap_selected)
            
            # Connect cell details requests for cross-component navigation
            if hasattr(self.traceability_matrix_widget, 'cell_details_requested'):
                self.traceability_matrix_widget.cell_details_requested.connect(self.on_traceability_cell_details)
        
        # Test Case Export Widget connections
        if self.test_case_export_widget:
            # Connect test case generation completion
            self.test_case_export_widget.test_cases_generated.connect(self.on_test_cases_generated)
            self.test_case_export_widget.export_completed.connect(self.on_test_export_completed)
        
        # Enhanced SOUP Widget connections
        if self.enhanced_soup_widget:
            # Connect SOUP component changes to requirement impact analysis
            self.enhanced_soup_widget.component_added.connect(self.on_soup_component_added)
            self.enhanced_soup_widget.component_updated.connect(self.on_soup_component_updated)
            self.enhanced_soup_widget.component_deleted.connect(self.on_soup_component_deleted)
            
            # Connect SOUP changes to requirements impact analysis
            self.enhanced_soup_widget.component_added.connect(self.analyze_soup_impact_on_requirements)
            self.enhanced_soup_widget.component_updated.connect(self.analyze_soup_impact_on_requirements)
            self.enhanced_soup_widget.component_deleted.connect(self.analyze_soup_impact_on_requirements)
        
        # Cross-component validation and consistency checking
        self.setup_cross_component_validation()
    
    def setup_cross_component_validation(self):
        """Set up cross-component validation and consistency checking."""
        # Create a timer for periodic validation checks
        self.validation_timer = QTimer()
        self.validation_timer.timeout.connect(self.perform_cross_component_validation)
        self.validation_timer.setSingleShot(True)  # Only run once per trigger
        
        # Connect all component update signals to trigger validation
        if self.requirements_tab_widget:
            self.requirements_tab_widget.requirements_updated.connect(self.trigger_validation_check)
        
        if self.enhanced_soup_widget:
            self.enhanced_soup_widget.component_updated.connect(self.trigger_validation_check)
    
    def trigger_validation_check(self):
        """Trigger a delayed validation check to avoid excessive validation calls."""
        # Restart the timer to delay validation until updates settle
        self.validation_timer.stop()
        self.validation_timer.start(2000)  # 2 second delay
    
    def perform_cross_component_validation(self):
        """Perform cross-component validation and consistency checking."""
        validation_issues = []
        
        # Check requirements consistency
        if self.requirements_tab_widget:
            req_validation = self.validate_requirements_consistency()
            validation_issues.extend(req_validation)
        
        # Check SOUP-requirements consistency
        if self.enhanced_soup_widget and self.requirements_tab_widget:
            soup_req_validation = self.validate_soup_requirements_consistency()
            validation_issues.extend(soup_req_validation)
        
        # Check traceability completeness
        if self.traceability_matrix_widget:
            trace_validation = self.validate_traceability_completeness()
            validation_issues.extend(trace_validation)
        
        # Update validation status in UI
        self.update_validation_status(validation_issues)
    
    def validate_requirements_consistency(self) -> List[str]:
        """Validate requirements for internal consistency."""
        issues = []
        
        if not self.requirements_tab_widget:
            return issues
        
        user_reqs = self.requirements_tab_widget.user_requirements
        software_reqs = self.requirements_tab_widget.software_requirements
        
        # Check for duplicate IDs
        all_ids = [req.get('id', '') for req in user_reqs + software_reqs]
        duplicate_ids = [id for id in set(all_ids) if all_ids.count(id) > 1 and id]
        if duplicate_ids:
            issues.append(f"Duplicate requirement IDs found: {', '.join(duplicate_ids)}")
        
        # Check for orphaned software requirements (derived_from references non-existent URs)
        user_req_ids = {req.get('id', '') for req in user_reqs}
        for sr in software_reqs:
            derived_from = sr.get('derived_from', [])
            if isinstance(derived_from, list):
                for parent_id in derived_from:
                    if parent_id and parent_id not in user_req_ids:
                        issues.append(f"Software requirement {sr.get('id', 'Unknown')} references non-existent user requirement {parent_id}")
        
        return issues
    
    def validate_soup_requirements_consistency(self) -> List[str]:
        """Validate consistency between SOUP components and requirements."""
        issues = []
        
        # This would check if SOUP components are properly referenced in requirements
        # and if safety-critical SOUP components have appropriate requirements
        
        return issues
    
    def validate_traceability_completeness(self) -> List[str]:
        """Validate traceability matrix completeness."""
        issues = []
        
        # This would check for missing traceability links and incomplete chains
        
        return issues
    
    def update_validation_status(self, issues: List[str]):
        """Update the UI with validation status."""
        if issues:
            print(f"Validation issues found: {len(issues)}")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("Cross-component validation passed")
    
    # Enhanced component signal handlers
    def on_requirements_updated(self, requirements_data: dict):
        """Handle requirements updates from enhanced requirements widget."""
        print(f"Requirements updated: UR={len(requirements_data.get('user_requirements', []))}, SR={len(requirements_data.get('software_requirements', []))}")
        
        # Update traceability matrix if available
        if self.traceability_matrix_widget and hasattr(self, 'traceability_service'):
            # Trigger traceability matrix refresh
            self.refresh_traceability_matrix()
    
    def on_traceability_update_requested(self):
        """Handle traceability update requests."""
        self.refresh_traceability_matrix()
    
    def on_traceability_export_requested(self, export_format: str, filename: str):
        """Handle traceability matrix export requests."""
        print(f"Traceability export requested: {export_format} -> {filename}")
        # The export is handled by the widget itself
    
    def on_gap_selected(self, gap_details: dict):
        """Handle gap selection from traceability matrix."""
        print(f"Gap selected: {gap_details}")
        # Could be used to highlight related requirements or show gap details
    
    def on_test_cases_generated(self, test_outline):
        """Handle test case generation completion."""
        print(f"Test cases generated: {len(test_outline.test_cases)} test cases")
        # Update test case widget with requirements if needed
        if self.test_case_export_widget and self.requirements_tab_widget:
            requirements = []
            # Convert requirements to the format expected by test generator
            for req_data in self.requirements_tab_widget.user_requirements:
                # This would need proper Requirement object creation
                pass
            for req_data in self.requirements_tab_widget.software_requirements:
                # This would need proper Requirement object creation
                pass
    
    def on_test_export_completed(self, export_format: str, filepath: str):
        """Handle test case export completion."""
        print(f"Test cases exported: {export_format} -> {filepath}")
        self.show_info("Export Complete", f"Test cases exported to {filepath}")
    
    def on_soup_component_added(self, component):
        """Handle SOUP component addition."""
        print(f"SOUP component added: {component.name} v{component.version}")
    
    def on_soup_component_updated(self, component):
        """Handle SOUP component update."""
        print(f"SOUP component updated: {component.name} v{component.version}")
    
    def on_soup_component_deleted(self, component_id: str):
        """Handle SOUP component deletion."""
        print(f"SOUP component deleted: {component_id}")
    
    def refresh_traceability_matrix(self):
        """Refresh the traceability matrix with current data."""
        if not self.traceability_matrix_widget:
            return
        
        try:
            # Get current requirements data
            requirements_data = {}
            if self.requirements_tab_widget:
                requirements_data = {
                    'user_requirements': self.requirements_tab_widget.user_requirements,
                    'software_requirements': self.requirements_tab_widget.software_requirements
                }
            
            # Generate traceability matrix using the service
            if hasattr(self, 'traceability_service') and requirements_data:
                matrix_data = self.traceability_service.generate_matrix(requirements_data)
                table_rows = self.traceability_service.generate_table_rows(matrix_data)
                gaps = self.traceability_service.analyze_gaps(matrix_data)
                
                # Update the traceability matrix widget
                self.traceability_matrix_widget.update_matrix(matrix_data, table_rows, gaps)
                
        except Exception as e:
            print(f"Error refreshing traceability matrix: {str(e)}")
    
    def update_enhanced_components_with_results(self, results: dict):
        """Update enhanced components with analysis results."""
        # Update requirements widget
        if self.requirements_tab_widget and 'requirements' in results:
            req_data = results['requirements']
            self.requirements_tab_widget.update_requirements(
                req_data.get('user_requirements', []),
                req_data.get('software_requirements', [])
            )
        
        # Update traceability matrix widget
        if self.traceability_matrix_widget and 'traceability' in results:
            traceability_data = results['traceability']
            if hasattr(traceability_data, 'matrix_data'):
                self.traceability_matrix_widget.update_matrix(
                    traceability_data.matrix_data,
                    traceability_data.table_rows,
                    traceability_data.gaps
                )
        
        # Update test case widget with requirements
        if self.test_case_export_widget and 'requirements' in results:
            req_data = results['requirements']
            # Convert to Requirement objects if needed
            requirements = []
            # This would need proper conversion logic
            self.test_case_export_widget.set_requirements(requirements)
    
    def on_requirements_changed_for_tests(self, requirements_data: dict):
        """Handle requirements changes that should trigger test case regeneration."""
        if self.test_case_export_widget:
            # Clear existing test cases to indicate they may be outdated
            self.test_case_export_widget.clear_all()
            
            # Update the test case widget with new requirements
            requirements = []
            # Convert requirements data to Requirement objects
            # This would need proper implementation based on the Requirement model
            self.test_case_export_widget.set_requirements(requirements)
    
    def on_traceability_cell_details(self, row: int, column: int):
        """Handle traceability matrix cell details requests."""
        print(f"Traceability cell details requested: row {row}, column {column}")
        # Could be used to show detailed information about the traceability link
    
    def analyze_soup_impact_on_requirements(self, component=None):
        """Analyze the impact of SOUP component changes on requirements."""
        if not self.requirements_tab_widget or not self.enhanced_soup_widget:
            return
        
        print("Analyzing SOUP component impact on requirements...")
        
        # This would analyze if SOUP component changes affect any requirements
        # For example, if a safety-critical SOUP component is updated,
        # it might require updates to related safety requirements
        
        # Get all SOUP components
        soup_components = []  # Would get from enhanced_soup_widget
        
        # Get all requirements
        user_reqs = self.requirements_tab_widget.user_requirements
        software_reqs = self.requirements_tab_widget.software_requirements
        
        # Analyze impact (simplified implementation)
        impact_found = False
        
        if impact_found:
            # Notify user of potential impact
            self.show_info(
                "SOUP Impact Analysis",
                "SOUP component changes may affect existing requirements. "
                "Please review requirements for consistency."
            )