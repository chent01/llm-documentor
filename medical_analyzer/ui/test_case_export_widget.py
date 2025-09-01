"""
Test Case Export Widget for Medical Software Analysis.

This widget provides a comprehensive interface for generating, previewing,
and exporting test case outlines in multiple formats.
"""

from typing import Dict, List, Optional, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QGroupBox, QComboBox, QTextEdit, QPlainTextEdit,
    QMessageBox, QHeaderView, QSplitter, QProgressBar, QCheckBox,
    QFileDialog, QTabWidget, QTreeWidget, QTreeWidgetItem, QSpinBox,
    QFormLayout, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QFont, QColor, QSyntaxHighlighter, QTextCharFormat, QTextDocument
import json
import os
from datetime import datetime

from ..models.core import Requirement
from ..services.test_case_generator import CaseGenerator
from ..models.test_models import CaseOutline, CaseModel, CasePriority, CaseCategory


class CaseModelSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for test case preview."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_highlighting_rules()
    
    def setup_highlighting_rules(self):
        """Set up syntax highlighting rules for test cases."""
        # Test case headers
        self.header_format = QTextCharFormat()
        self.header_format.setForeground(QColor(0, 0, 255))
        self.header_format.setFontWeight(QFont.Weight.Bold)
        
        # Step numbers
        self.step_format = QTextCharFormat()
        self.step_format.setForeground(QColor(255, 0, 0))
        self.step_format.setFontWeight(QFont.Weight.Bold)
        
        # Expected results
        self.expected_format = QTextCharFormat()
        self.expected_format.setForeground(QColor(0, 128, 0))
        
        # Keywords
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor(128, 0, 128))
        self.keyword_format.setFontWeight(QFont.Weight.Bold)
    
    def highlightBlock(self, text):
        """Apply syntax highlighting to a block of text."""
        # Highlight test case headers
        if text.startswith("Test Case") or text.startswith("="):
            self.setFormat(0, len(text), self.header_format)
        
        # Highlight step numbers
        if text.strip().startswith(tuple(f"{i}." for i in range(1, 20))):
            end_pos = text.find('.') + 1
            self.setFormat(0, end_pos, self.step_format)
        
        # Highlight expected results
        if "Expected:" in text:
            start = text.find("Expected:")
            self.setFormat(start, len("Expected:"), self.expected_format)
        
        # Highlight keywords
        keywords = ["Preconditions:", "Description:", "Priority:", "Category:", "Duration:"]
        for keyword in keywords:
            if keyword in text:
                start = text.find(keyword)
                self.setFormat(start, len(keyword), self.keyword_format)


class TestGenerationWorker(QThread):
    """Worker thread for test case generation."""
    
    progress_updated = pyqtSignal(int)
    generation_completed = pyqtSignal(object)  # CaseOutline
    error_occurred = pyqtSignal(str)
    
    def __init__(self, requirements: List[Requirement], generator: CaseGenerator):
        super().__init__()
        self.requirements = requirements
        self.generator = generator
    
    def run(self):
        """Run test case generation in background thread."""
        try:
            self.progress_updated.emit(10)
            
            # Generate test cases
            test_outline = self.generator.generate_test_cases(self.requirements)
            self.progress_updated.emit(80)
            
            # Generate coverage report
            coverage_report = self.generator.generate_coverage_report(test_outline, self.requirements)
            test_outline.coverage_summary.update(coverage_report)
            self.progress_updated.emit(100)
            
            self.generation_completed.emit(test_outline)
            
        except Exception as e:
            self.error_occurred.emit(str(e))


class CaseModelExportWidget(QWidget):
    """Widget for test case generation, preview, and export."""
    
    # Signals
    test_cases_generated = pyqtSignal(object)  # CaseOutline
    export_completed = pyqtSignal(str, str)  # format, filepath
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.test_outline: Optional[CaseOutline] = None
        self.generator: Optional[CaseGenerator] = None
        self.requirements: List[Requirement] = []
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Initialize the test case export widget UI."""
        layout = QVBoxLayout(self)
        
        # Main toolbar
        toolbar_layout = QHBoxLayout()
        
        self.generate_button = QPushButton("Generate Test Cases")
        self.generate_button.setStyleSheet("font-weight: bold; background-color: #2196F3; color: white;")
        
        self.export_button = QPushButton("Export Test Cases")
        self.export_button.setEnabled(False)
        
        self.clear_button = QPushButton("Clear")
        
        toolbar_layout.addWidget(self.generate_button)
        toolbar_layout.addWidget(self.export_button)
        toolbar_layout.addWidget(self.clear_button)
        toolbar_layout.addStretch()
        
        layout.addLayout(toolbar_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Main content area with tabs
        self.tab_widget = QTabWidget()
        
        # Configuration tab
        self.config_tab = self.create_configuration_tab()
        self.tab_widget.addTab(self.config_tab, "Configuration")
        
        # Preview tab
        self.preview_tab = self.create_preview_tab()
        self.tab_widget.addTab(self.preview_tab, "Preview")
        
        # Coverage tab
        self.coverage_tab = self.create_coverage_tab()
        self.tab_widget.addTab(self.coverage_tab, "Coverage Analysis")
        
        # Export tab
        self.export_tab = self.create_export_tab()
        self.tab_widget.addTab(self.export_tab, "Export Options")
        
        layout.addWidget(self.tab_widget)
        
        # Status bar
        self.status_label = QLabel("Ready to generate test cases")
        self.status_label.setStyleSheet("padding: 5px; background-color: #f0f0f0;")
        layout.addWidget(self.status_label)
    
    def create_configuration_tab(self) -> QWidget:
        """Create the configuration tab for test generation settings."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Requirements selection
        req_group = QGroupBox("Requirements Selection")
        req_layout = QVBoxLayout(req_group)
        
        self.requirements_table = QTableWidget()
        self.requirements_table.setColumnCount(4)
        self.requirements_table.setHorizontalHeaderLabels(["Select", "ID", "Type", "Description"])
        self.requirements_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        req_layout.addWidget(self.requirements_table)
        
        # Select all/none buttons
        select_layout = QHBoxLayout()
        self.select_all_button = QPushButton("Select All")
        self.select_none_button = QPushButton("Select None")
        select_layout.addWidget(self.select_all_button)
        select_layout.addWidget(self.select_none_button)
        select_layout.addStretch()
        req_layout.addLayout(select_layout)
        
        layout.addWidget(req_group)
        
        # Generation options
        options_group = QGroupBox("Generation Options")
        options_layout = QFormLayout(options_group)
        
        self.include_edge_cases = QCheckBox("Include edge case tests")
        self.include_edge_cases.setChecked(True)
        
        self.include_negative_tests = QCheckBox("Include negative tests for safety requirements")
        self.include_negative_tests.setChecked(True)
        
        self.use_llm_enhancement = QCheckBox("Use LLM for enhanced test generation")
        self.use_llm_enhancement.setChecked(True)
        
        self.max_steps_per_test = QSpinBox()
        self.max_steps_per_test.setRange(3, 20)
        self.max_steps_per_test.setValue(8)
        
        options_layout.addRow("Include Edge Cases:", self.include_edge_cases)
        options_layout.addRow("Include Negative Tests:", self.include_negative_tests)
        options_layout.addRow("LLM Enhancement:", self.use_llm_enhancement)
        options_layout.addRow("Max Steps per Test:", self.max_steps_per_test)
        
        layout.addWidget(options_group)
        
        layout.addStretch()
        return tab
    
    def create_preview_tab(self) -> QWidget:
        """Create the preview tab for test case display."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Preview controls
        controls_layout = QHBoxLayout()
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Text", "JSON", "XML"])
        self.format_combo.setCurrentText("Text")
        
        self.refresh_preview_button = QPushButton("Refresh Preview")
        
        controls_layout.addWidget(QLabel("Preview Format:"))
        controls_layout.addWidget(self.format_combo)
        controls_layout.addWidget(self.refresh_preview_button)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Preview area with syntax highlighting
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFont(QFont("Consolas", 10))
        
        # Apply syntax highlighter for text format
        self.syntax_highlighter = CaseModelSyntaxHighlighter(self.preview_text.document())
        
        layout.addWidget(self.preview_text)
        
        return tab
    
    def create_coverage_tab(self) -> QWidget:
        """Create the coverage analysis tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Coverage summary
        summary_group = QGroupBox("Coverage Summary")
        summary_layout = QVBoxLayout(summary_group)
        
        self.coverage_summary_text = QTextEdit()
        self.coverage_summary_text.setReadOnly(True)
        self.coverage_summary_text.setMaximumHeight(150)
        summary_layout.addWidget(self.coverage_summary_text)
        
        layout.addWidget(summary_group)
        
        # Coverage details
        details_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Requirements coverage tree
        req_coverage_group = QGroupBox("Requirements Coverage")
        req_coverage_layout = QVBoxLayout(req_coverage_group)
        
        self.requirements_coverage_tree = QTreeWidget()
        self.requirements_coverage_tree.setHeaderLabels(["Requirement", "Test Cases", "Coverage"])
        req_coverage_layout.addWidget(self.requirements_coverage_tree)
        
        details_splitter.addWidget(req_coverage_group)
        
        # Gap analysis
        gaps_group = QGroupBox("Coverage Gaps")
        gaps_layout = QVBoxLayout(gaps_group)
        
        self.gaps_table = QTableWidget()
        self.gaps_table.setColumnCount(4)
        self.gaps_table.setHorizontalHeaderLabels(["Requirement ID", "Type", "Severity", "Recommendation"])
        gaps_layout.addWidget(self.gaps_table)
        
        details_splitter.addWidget(gaps_group)
        
        layout.addWidget(details_splitter)
        
        return tab
    
    def create_export_tab(self) -> QWidget:
        """Create the export options tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Export format selection
        format_group = QGroupBox("Export Format")
        format_layout = QVBoxLayout(format_group)
        
        self.export_formats = {
            "text": QCheckBox("Plain Text (.txt)"),
            "json": QCheckBox("JSON (.json)"),
            "xml": QCheckBox("XML (.xml)"),
            "csv": QCheckBox("CSV (.csv)")
        }
        
        for format_name, checkbox in self.export_formats.items():
            checkbox.setChecked(True)
            format_layout.addWidget(checkbox)
        
        layout.addWidget(format_group)
        
        # Export options
        options_group = QGroupBox("Export Options")
        options_layout = QFormLayout(options_group)
        
        self.include_coverage_report = QCheckBox("Include coverage report")
        self.include_coverage_report.setChecked(True)
        
        self.include_metadata = QCheckBox("Include generation metadata")
        self.include_metadata.setChecked(True)
        
        self.group_by_requirement = QCheckBox("Group test cases by requirement")
        self.group_by_requirement.setChecked(False)
        
        options_layout.addRow("Coverage Report:", self.include_coverage_report)
        options_layout.addRow("Metadata:", self.include_metadata)
        options_layout.addRow("Group by Requirement:", self.group_by_requirement)
        
        layout.addWidget(options_group)
        
        # Export destination
        dest_group = QGroupBox("Export Destination")
        dest_layout = QVBoxLayout(dest_group)
        
        dest_controls_layout = QHBoxLayout()
        self.export_path_label = QLabel("No destination selected")
        self.browse_button = QPushButton("Browse...")
        
        dest_controls_layout.addWidget(self.export_path_label)
        dest_controls_layout.addWidget(self.browse_button)
        
        dest_layout.addLayout(dest_controls_layout)
        layout.addWidget(dest_group)
        
        # Batch export button
        self.batch_export_button = QPushButton("Export All Selected Formats")
        self.batch_export_button.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
        self.batch_export_button.setEnabled(False)
        layout.addWidget(self.batch_export_button)
        
        layout.addStretch()
        return tab
    
    def setup_connections(self):
        """Set up signal connections."""
        # Main buttons
        self.generate_button.clicked.connect(self.generate_test_cases)
        self.export_button.clicked.connect(self.export_current_format)
        self.clear_button.clicked.connect(self.clear_all)
        
        # Configuration tab
        self.select_all_button.clicked.connect(self.select_all_requirements)
        self.select_none_button.clicked.connect(self.select_no_requirements)
        
        # Preview tab
        self.format_combo.currentTextChanged.connect(self.update_preview)
        self.refresh_preview_button.clicked.connect(self.update_preview)
        
        # Export tab
        self.browse_button.clicked.connect(self.browse_export_destination)
        self.batch_export_button.clicked.connect(self.batch_export)
    
    def set_generator(self, generator: CaseGenerator):
        """Set the test case generator instance."""
        self.generator = generator
        self.use_llm_enhancement.setEnabled(generator.llm_backend is not None)
    
    def set_requirements(self, requirements: List[Requirement]):
        """Set the requirements list for test generation."""
        self.requirements = requirements
        self.populate_requirements_table()
    
    def populate_requirements_table(self):
        """Populate the requirements selection table."""
        self.requirements_table.setRowCount(len(self.requirements))
        
        for row, requirement in enumerate(self.requirements):
            # Checkbox for selection
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            self.requirements_table.setCellWidget(row, 0, checkbox)
            
            # Requirement details
            self.requirements_table.setItem(row, 1, QTableWidgetItem(requirement.id))
            self.requirements_table.setItem(row, 2, QTableWidgetItem(requirement.type.value))
            self.requirements_table.setItem(row, 3, QTableWidgetItem(requirement.text[:100] + "..."))
        
        self.requirements_table.resizeColumnsToContents()
    
    def get_selected_requirements(self) -> List[Requirement]:
        """Get the list of selected requirements."""
        selected = []
        for row in range(self.requirements_table.rowCount()):
            checkbox = self.requirements_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                selected.append(self.requirements[row])
        return selected
    
    def select_all_requirements(self):
        """Select all requirements in the table."""
        for row in range(self.requirements_table.rowCount()):
            checkbox = self.requirements_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)
    
    def select_no_requirements(self):
        """Deselect all requirements in the table."""
        for row in range(self.requirements_table.rowCount()):
            checkbox = self.requirements_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
    
    def generate_test_cases(self):
        """Generate test cases for selected requirements."""
        if not self.generator:
            QMessageBox.warning(self, "Warning", "No test case generator available.")
            return
        
        selected_requirements = self.get_selected_requirements()
        if not selected_requirements:
            QMessageBox.warning(self, "Warning", "Please select at least one requirement.")
            return
        
        # Show progress and disable UI
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.generate_button.setEnabled(False)
        self.status_label.setText("Generating test cases...")
        
        # Start generation in worker thread
        self.generation_worker = TestGenerationWorker(selected_requirements, self.generator)
        self.generation_worker.progress_updated.connect(self.progress_bar.setValue)
        self.generation_worker.generation_completed.connect(self.on_generation_completed)
        self.generation_worker.error_occurred.connect(self.on_generation_error)
        self.generation_worker.start()
    
    def on_generation_completed(self, test_outline: CaseOutline):
        """Handle completion of test case generation."""
        self.test_outline = test_outline
        
        # Update UI
        self.progress_bar.setVisible(False)
        self.generate_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.batch_export_button.setEnabled(True)
        
        # Update preview and coverage
        self.update_preview()
        self.update_coverage_analysis()
        
        # Switch to preview tab
        self.tab_widget.setCurrentIndex(1)
        
        self.status_label.setText(f"Generated {len(test_outline.test_cases)} test cases successfully")
        self.test_cases_generated.emit(test_outline)
    
    def on_generation_error(self, error_message: str):
        """Handle test case generation error."""
        self.progress_bar.setVisible(False)
        self.generate_button.setEnabled(True)
        self.status_label.setText("Test case generation failed")
        
        QMessageBox.critical(self, "Generation Error", f"Failed to generate test cases:\n{error_message}")
    
    def update_preview(self):
        """Update the test case preview."""
        if not self.test_outline:
            self.preview_text.setPlainText("No test cases generated yet.")
            return
        
        format_type = self.format_combo.currentText().lower()
        
        try:
            if format_type == "text":
                content = self.generator.export_test_cases(self.test_outline, "text")
                self.preview_text.setPlainText(content)
            elif format_type == "json":
                content = self.generator.export_test_cases(self.test_outline, "json")
                self.preview_text.setPlainText(content)
            elif format_type == "xml":
                content = self.generator.export_test_cases(self.test_outline, "xml")
                self.preview_text.setPlainText(content)
        except Exception as e:
            self.preview_text.setPlainText(f"Error generating preview: {str(e)}")
    
    def update_coverage_analysis(self):
        """Update the coverage analysis display."""
        if not self.test_outline:
            return
        
        # Update coverage summary
        summary = self.test_outline.coverage_summary
        summary_text = f"""
Test Cases Generated: {len(self.test_outline.test_cases)}
Requirements Covered: {summary.get('covered_requirements', 0)}
Total Requirements: {summary.get('total_requirements', 0)}
Coverage Percentage: {summary.get('coverage_percentage', 0):.1f}%

Category Distribution:
{self._format_distribution(summary.get('category_distribution', {}))}

Priority Distribution:
{self._format_distribution(summary.get('priority_distribution', {}))}
        """.strip()
        
        self.coverage_summary_text.setPlainText(summary_text)
        
        # Update requirements coverage tree
        self.requirements_coverage_tree.clear()
        req_coverage = self.test_outline.get_coverage_by_requirement()
        
        for requirement in self.requirements:
            item = QTreeWidgetItem(self.requirements_coverage_tree)
            item.setText(0, f"{requirement.id}: {requirement.text[:50]}...")
            
            test_cases = req_coverage.get(requirement.id, [])
            item.setText(1, str(len(test_cases)))
            item.setText(2, "Covered" if test_cases else "Not Covered")
            
            # Color coding
            if test_cases:
                item.setBackground(2, QColor(200, 255, 200))  # Light green
            else:
                item.setBackground(2, QColor(255, 200, 200))  # Light red
        
        self.requirements_coverage_tree.expandAll()
        
        # Update gaps table
        gaps = summary.get('gaps', [])
        self.gaps_table.setRowCount(len(gaps))
        
        for row, gap in enumerate(gaps):
            self.gaps_table.setItem(row, 0, QTableWidgetItem(gap.get('requirement_id', '')))
            self.gaps_table.setItem(row, 1, QTableWidgetItem(gap.get('gap_type', '')))
            self.gaps_table.setItem(row, 2, QTableWidgetItem(gap.get('severity', '')))
            self.gaps_table.setItem(row, 3, QTableWidgetItem("Add test case coverage"))
        
        self.gaps_table.resizeColumnsToContents()
    
    def _format_distribution(self, distribution: Dict[str, int]) -> str:
        """Format distribution dictionary for display."""
        if not distribution:
            return "No data"
        
        lines = []
        for key, value in distribution.items():
            lines.append(f"  {key}: {value}")
        return "\n".join(lines)
    
    def browse_export_destination(self):
        """Browse for export destination directory."""
        directory = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if directory:
            self.export_path_label.setText(directory)
    
    def export_current_format(self):
        """Export test cases in the currently selected preview format."""
        if not self.test_outline:
            QMessageBox.warning(self, "Warning", "No test cases to export.")
            return
        
        format_type = self.format_combo.currentText().lower()
        self._export_single_format(format_type)
    
    def batch_export(self):
        """Export test cases in all selected formats."""
        if not self.test_outline:
            QMessageBox.warning(self, "Warning", "No test cases to export.")
            return
        
        export_dir = self.export_path_label.text()
        if export_dir == "No destination selected":
            QMessageBox.warning(self, "Warning", "Please select an export destination.")
            return
        
        exported_files = []
        
        for format_name, checkbox in self.export_formats.items():
            if checkbox.isChecked():
                try:
                    filename = self._export_single_format(format_name, export_dir)
                    if filename:
                        exported_files.append(filename)
                except Exception as e:
                    QMessageBox.warning(self, "Export Error", f"Failed to export {format_name}: {str(e)}")
        
        if exported_files:
            QMessageBox.information(
                self, "Export Complete", 
                f"Successfully exported {len(exported_files)} files:\n" + "\n".join(exported_files)
            )
            self.export_completed.emit("batch", export_dir)
    
    def _export_single_format(self, format_type: str, export_dir: Optional[str] = None) -> Optional[str]:
        """Export test cases in a single format."""
        if not export_dir:
            extensions = {"text": "txt", "json": "json", "xml": "xml", "csv": "csv"}
            ext = extensions.get(format_type, "txt")
            
            filename, _ = QFileDialog.getSaveFileName(
                self, f"Export Test Cases ({format_type.upper()})",
                f"test_cases.{ext}",
                f"{format_type.upper()} Files (*.{ext})"
            )
            
            if not filename:
                return None
        else:
            extensions = {"text": "txt", "json": "json", "xml": "xml", "csv": "csv"}
            ext = extensions.get(format_type, "txt")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(export_dir, f"test_cases_{timestamp}.{ext}")
        
        try:
            content = self.generator.export_test_cases(self.test_outline, format_type)
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.status_label.setText(f"Exported to {filename}")
            return filename
            
        except Exception as e:
            raise Exception(f"Failed to export {format_type}: {str(e)}")
    
    def clear_all(self):
        """Clear all generated test cases and reset the widget."""
        self.test_outline = None
        self.preview_text.clear()
        self.coverage_summary_text.clear()
        self.requirements_coverage_tree.clear()
        self.gaps_table.setRowCount(0)
        
        self.export_button.setEnabled(False)
        self.batch_export_button.setEnabled(False)
        
        self.status_label.setText("Ready to generate test cases")
        
        # Reset to configuration tab
        self.tab_widget.setCurrentIndex(0)
