"""
Enhanced traceability matrix widget with proper tabular format and gap highlighting.

This widget provides a comprehensive view of traceability relationships between
code, features, requirements, and risks with interactive gap analysis and export capabilities.
"""

from typing import Dict, List, Optional, Any, Tuple
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
    QLabel, QPushButton, QComboBox, QLineEdit, QCheckBox, QGroupBox,
    QHeaderView, QMessageBox, QFileDialog, QDialog, QDialogButtonBox,
    QTextBrowser, QSplitter, QFrame, QProgressBar, QMenu, QToolTip,
    QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QColor, QFont, QAction, QCursor
import csv
import json
import os
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from ..services.traceability_service import (
    TraceabilityMatrix, TraceabilityGap, TraceabilityTableRow
)


class GapSeverity(Enum):
    """Gap severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TraceabilityMatrixWidget(QWidget):
    """Enhanced traceability matrix widget with gap analysis and export capabilities."""
    
    # Signals
    export_requested = pyqtSignal(str, str)  # format, filename
    gap_selected = pyqtSignal(dict)  # gap details
    cell_details_requested = pyqtSignal(int, int)  # row, column
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.matrix_data: Optional[TraceabilityMatrix] = None
        self.table_rows: List[TraceabilityTableRow] = []
        self.gaps: List[TraceabilityGap] = []
        self.filtered_rows: List[TraceabilityTableRow] = []
        self.current_view = "full_matrix"
        
        self.setup_ui()
        self.setup_connections()
        self.setup_styling()
        
    def setup_ui(self):
        """Initialize the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Create main splitter for matrix and gap analysis
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(self.main_splitter)
        
        # Matrix section
        matrix_widget = QWidget()
        matrix_layout = QVBoxLayout(matrix_widget)
        
        # Controls section
        self.setup_controls(matrix_layout)
        
        # Statistics section
        self.setup_statistics(matrix_layout)
        
        # Matrix table
        self.setup_matrix_table(matrix_layout)
        
        # Action buttons
        self.setup_action_buttons(matrix_layout)
        
        self.main_splitter.addWidget(matrix_widget)
        
        # Gap analysis section
        self.setup_gap_analysis()
        
        # Set initial splitter sizes (80% matrix, 20% gaps)
        self.main_splitter.setSizes([800, 200])
        
    def setup_controls(self, layout: QVBoxLayout):
        """Setup the control panel."""
        controls_group = QGroupBox("Matrix View Controls")
        controls_layout = QHBoxLayout(controls_group)
        
        # View selector
        controls_layout.addWidget(QLabel("View:"))
        self.view_combo = QComboBox()
        self.view_combo.addItems([
            "Full Matrix",
            "Code → Requirements", 
            "Requirements → Risks",
            "Gap Analysis Only",
            "High Confidence Only"
        ])
        controls_layout.addWidget(self.view_combo)
        
        # Filter controls
        controls_layout.addWidget(QLabel("Filter:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter by file, requirement, risk, or function...")
        controls_layout.addWidget(self.filter_edit)
        
        # Gap filter
        self.show_gaps_only = QCheckBox("Show Gaps Only")
        controls_layout.addWidget(self.show_gaps_only)
        
        # Confidence threshold
        controls_layout.addWidget(QLabel("Min Confidence:"))
        self.confidence_combo = QComboBox()
        self.confidence_combo.addItems(["0.0", "0.3", "0.5", "0.7", "0.9"])
        self.confidence_combo.setCurrentText("0.0")
        controls_layout.addWidget(self.confidence_combo)
        
        # Clear filters button
        self.clear_filters_btn = QPushButton("Clear Filters")
        controls_layout.addWidget(self.clear_filters_btn)
        
        controls_layout.addStretch()
        layout.addWidget(controls_group)
        
    def setup_statistics(self, layout: QVBoxLayout):
        """Setup the statistics panel."""
        stats_group = QGroupBox("Traceability Statistics")
        stats_layout = QHBoxLayout(stats_group)
        
        # Statistics labels
        self.total_rows_label = QLabel("Total Rows: 0")
        self.complete_chains_label = QLabel("Complete Chains: 0")
        self.gaps_count_label = QLabel("Gaps: 0")
        self.avg_confidence_label = QLabel("Avg Confidence: 0.0")
        self.coverage_label = QLabel("Coverage: 0%")
        
        stats_layout.addWidget(self.total_rows_label)
        stats_layout.addWidget(self.complete_chains_label)
        stats_layout.addWidget(self.gaps_count_label)
        stats_layout.addWidget(self.avg_confidence_label)
        stats_layout.addWidget(self.coverage_label)
        stats_layout.addStretch()
        
        layout.addWidget(stats_group)
        
    def setup_matrix_table(self, layout: QVBoxLayout):
        """Setup the main traceability matrix table."""
        self.matrix_table = QTableWidget()
        self.matrix_table.setColumnCount(11)
        self.matrix_table.setHorizontalHeaderLabels([
            "Code Reference",
            "File Path", 
            "Function",
            "Feature ID",
            "Feature Description",
            "User Req ID",
            "User Requirement",
            "Software Req ID", 
            "Software Requirement",
            "Risk ID",
            "Confidence"
        ])
        
        # Configure table properties
        self.matrix_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.matrix_table.setAlternatingRowColors(True)
        self.matrix_table.setSortingEnabled(True)
        self.matrix_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        # Set column widths
        header = self.matrix_table.horizontalHeader()
        header.resizeSection(0, 150)  # Code Reference
        header.resizeSection(1, 200)  # File Path
        header.resizeSection(2, 120)  # Function
        header.resizeSection(3, 100)  # Feature ID
        header.resizeSection(4, 200)  # Feature Description
        header.resizeSection(5, 100)  # User Req ID
        header.resizeSection(6, 200)  # User Requirement
        header.resizeSection(7, 100)  # Software Req ID
        header.resizeSection(8, 200)  # Software Requirement
        header.resizeSection(9, 100)  # Risk ID
        header.resizeSection(10, 80)  # Confidence
        
        # Enable tooltips and context menu
        self.matrix_table.setMouseTracking(True)
        self.matrix_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        layout.addWidget(self.matrix_table)
        
    def setup_action_buttons(self, layout: QVBoxLayout):
        """Setup action buttons."""
        button_layout = QHBoxLayout()
        
        # Export buttons
        self.export_csv_btn = QPushButton("Export CSV")
        self.export_excel_btn = QPushButton("Export Excel") 
        self.export_pdf_btn = QPushButton("Export PDF")
        self.export_gaps_btn = QPushButton("Export Gap Report")
        
        # Utility buttons
        self.refresh_btn = QPushButton("Refresh")
        self.validate_btn = QPushButton("Validate Matrix")
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.validate_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.export_gaps_btn)
        button_layout.addWidget(self.export_csv_btn)
        button_layout.addWidget(self.export_excel_btn)
        button_layout.addWidget(self.export_pdf_btn)
        
        layout.addLayout(button_layout)
        
    def setup_gap_analysis(self):
        """Setup the gap analysis panel."""
        gap_widget = QWidget()
        gap_layout = QVBoxLayout(gap_widget)
        
        # Gap analysis header
        gap_header = QHBoxLayout()
        gap_title = QLabel("Gap Analysis")
        gap_title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        gap_header.addWidget(gap_title)
        
        self.toggle_gaps_btn = QPushButton("Hide Gaps")
        gap_header.addWidget(self.toggle_gaps_btn)
        gap_header.addStretch()
        
        gap_layout.addLayout(gap_header)
        
        # Gap analysis content
        self.gaps_browser = QTextBrowser()
        self.gaps_browser.setMaximumHeight(200)
        gap_layout.addWidget(self.gaps_browser)
        
        self.main_splitter.addWidget(gap_widget)
        
    def setup_connections(self):
        """Setup signal connections."""
        # Control connections
        self.view_combo.currentTextChanged.connect(self.on_view_changed)
        self.filter_edit.textChanged.connect(self.apply_filters)
        self.show_gaps_only.toggled.connect(self.apply_filters)
        self.confidence_combo.currentTextChanged.connect(self.apply_filters)
        self.clear_filters_btn.clicked.connect(self.clear_filters)
        
        # Table connections
        self.matrix_table.cellClicked.connect(self.on_cell_clicked)
        self.matrix_table.cellEntered.connect(self.on_cell_entered)
        self.matrix_table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Button connections
        self.export_csv_btn.clicked.connect(lambda: self.export_matrix("csv"))
        self.export_excel_btn.clicked.connect(lambda: self.export_matrix("excel"))
        self.export_pdf_btn.clicked.connect(lambda: self.export_matrix("pdf"))
        self.export_gaps_btn.clicked.connect(lambda: self.export_matrix("gaps"))
        self.refresh_btn.clicked.connect(self.refresh_matrix)
        self.validate_btn.clicked.connect(self.validate_matrix)
        self.toggle_gaps_btn.clicked.connect(self.toggle_gap_panel)
        
    def setup_styling(self):
        """Setup widget styling."""
        # Gap severity colors
        self.gap_colors = {
            GapSeverity.HIGH: QColor(255, 200, 200),      # Light red
            GapSeverity.MEDIUM: QColor(255, 255, 200),    # Light yellow  
            GapSeverity.LOW: QColor(200, 255, 200)        # Light green
        }
        
        # Confidence colors
        self.confidence_colors = {
            "high": QColor(200, 255, 200),    # Green for high confidence
            "medium": QColor(255, 255, 200),  # Yellow for medium confidence
            "low": QColor(255, 200, 200)      # Red for low confidence
        }
        
    def update_matrix(self, matrix_data: TraceabilityMatrix, table_rows: List[TraceabilityTableRow], gaps: List[TraceabilityGap]):
        """Update the matrix display with new data."""
        self.matrix_data = matrix_data
        self.table_rows = table_rows
        self.gaps = gaps
        
        # Update statistics
        self.update_statistics()
        
        # Apply current filters and view
        self.apply_filters()
        
        # Update gap analysis
        self.update_gap_analysis()
        
    def update_statistics(self):
        """Update the statistics display."""
        if not self.matrix_data or not self.table_rows:
            self.total_rows_label.setText("Total Rows: 0")
            self.complete_chains_label.setText("Complete Chains: 0")
            self.gaps_count_label.setText("Gaps: 0")
            self.avg_confidence_label.setText("Avg Confidence: 0.0")
            self.coverage_label.setText("Coverage: 0%")
            return
            
        total_rows = len(self.table_rows)
        
        # Count complete chains (rows with all fields populated)
        complete_chains = sum(1 for row in self.table_rows 
                            if all([row.code_reference, row.user_requirement_id, 
                                   row.software_requirement_id, row.risk_id]))
        
        # Calculate average confidence
        confidences = [row.confidence for row in self.table_rows if row.confidence > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Calculate coverage percentage
        coverage = (complete_chains / total_rows * 100) if total_rows > 0 else 0
        
        # Update labels
        self.total_rows_label.setText(f"Total Rows: {total_rows}")
        self.complete_chains_label.setText(f"Complete Chains: {complete_chains}")
        self.gaps_count_label.setText(f"Gaps: {len(self.gaps)}")
        self.avg_confidence_label.setText(f"Avg Confidence: {avg_confidence:.2f}")
        self.coverage_label.setText(f"Coverage: {coverage:.1f}%")
        
        # Color-code gaps count based on severity
        high_gaps = sum(1 for gap in self.gaps if gap.severity == "high")
        if high_gaps > 0:
            self.gaps_count_label.setStyleSheet("color: red; font-weight: bold;")
        elif len(self.gaps) > 0:
            self.gaps_count_label.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self.gaps_count_label.setStyleSheet("color: green; font-weight: bold;")
            
    def apply_filters(self):
        """Apply all active filters to the matrix display."""
        if not self.table_rows:
            self.populate_table([])
            return
            
        filtered_rows = self.table_rows.copy()
        
        # Apply view filter
        view_type = self.view_combo.currentText()
        filtered_rows = self.filter_by_view(filtered_rows, view_type)
        
        # Apply text filter
        filter_text = self.filter_edit.text().lower().strip()
        if filter_text:
            filtered_rows = self.filter_by_text(filtered_rows, filter_text)
            
        # Apply confidence filter
        min_confidence = float(self.confidence_combo.currentText())
        filtered_rows = [row for row in filtered_rows if row.confidence >= min_confidence]
        
        # Apply gaps filter
        if self.show_gaps_only.isChecked():
            filtered_rows = self.filter_by_gaps(filtered_rows)
            
        self.filtered_rows = filtered_rows
        self.populate_table(filtered_rows)
        
    def filter_by_view(self, rows: List[TraceabilityTableRow], view_type: str) -> List[TraceabilityTableRow]:
        """Filter rows based on selected view type."""
        if view_type == "Full Matrix":
            return rows
        elif view_type == "Code → Requirements":
            return [row for row in rows if row.code_reference and row.software_requirement_id]
        elif view_type == "Requirements → Risks":
            return [row for row in rows if row.software_requirement_id and row.risk_id]
        elif view_type == "Gap Analysis Only":
            return self.filter_by_gaps(rows)
        elif view_type == "High Confidence Only":
            return [row for row in rows if row.confidence >= 0.8]
        else:
            return rows
            
    def filter_by_text(self, rows: List[TraceabilityTableRow], filter_text: str) -> List[TraceabilityTableRow]:
        """Filter rows by text search."""
        filtered = []
        for row in rows:
            # Search in all text fields
            searchable_text = " ".join([
                row.file_path.lower(),
                row.function_name.lower(),
                row.feature_description.lower(),
                row.user_requirement_text.lower(),
                row.software_requirement_text.lower(),
                row.risk_hazard.lower(),
                row.code_reference.lower(),
                row.feature_id.lower(),
                row.user_requirement_id.lower(),
                row.software_requirement_id.lower(),
                row.risk_id.lower()
            ])
            
            if filter_text in searchable_text:
                filtered.append(row)
                
        return filtered
        
    def filter_by_gaps(self, rows: List[TraceabilityTableRow]) -> List[TraceabilityTableRow]:
        """Filter rows to show only those with gaps."""
        gap_rows = []
        for row in rows:
            has_gap = (
                not row.user_requirement_id or
                not row.software_requirement_id or 
                not row.risk_id or
                row.confidence < 0.5
            )
            if has_gap:
                gap_rows.append(row)
        return gap_rows
        
    def populate_table(self, rows: List[TraceabilityTableRow]):
        """Populate the matrix table with filtered rows."""
        self.matrix_table.setRowCount(len(rows))
        
        if not rows:
            self.show_empty_message()
            return
            
        for i, row in enumerate(rows):
            # Populate row data
            self.matrix_table.setItem(i, 0, QTableWidgetItem(row.code_reference))
            self.matrix_table.setItem(i, 1, QTableWidgetItem(row.file_path))
            self.matrix_table.setItem(i, 2, QTableWidgetItem(row.function_name))
            self.matrix_table.setItem(i, 3, QTableWidgetItem(row.feature_id))
            self.matrix_table.setItem(i, 4, QTableWidgetItem(row.feature_description))
            self.matrix_table.setItem(i, 5, QTableWidgetItem(row.user_requirement_id))
            self.matrix_table.setItem(i, 6, QTableWidgetItem(row.user_requirement_text))
            self.matrix_table.setItem(i, 7, QTableWidgetItem(row.software_requirement_id))
            self.matrix_table.setItem(i, 8, QTableWidgetItem(row.software_requirement_text))
            self.matrix_table.setItem(i, 9, QTableWidgetItem(row.risk_id))
            
            # Confidence with color coding
            confidence_item = QTableWidgetItem(f"{row.confidence:.2f}")
            confidence_color = self.get_confidence_color(row.confidence)
            confidence_item.setBackground(confidence_color)
            self.matrix_table.setItem(i, 10, confidence_item)
            
            # Highlight gaps with colors
            self.highlight_row_gaps(i, row)
            
    def highlight_row_gaps(self, row_index: int, row: TraceabilityTableRow):
        """Highlight gaps in a table row with appropriate colors."""
        # Check for missing links and apply gap highlighting
        if not row.user_requirement_id:
            self.highlight_cell(row_index, 5, GapSeverity.HIGH, "Missing User Requirement")
            self.highlight_cell(row_index, 6, GapSeverity.HIGH, "Missing User Requirement")
            
        if not row.software_requirement_id:
            self.highlight_cell(row_index, 7, GapSeverity.HIGH, "Missing Software Requirement")
            self.highlight_cell(row_index, 8, GapSeverity.HIGH, "Missing Software Requirement")
            
        if not row.risk_id:
            self.highlight_cell(row_index, 9, GapSeverity.MEDIUM, "Missing Risk Link")
            
        # Highlight low confidence
        if row.confidence < 0.5:
            for col in range(11):
                item = self.matrix_table.item(row_index, col)
                if item:
                    current_color = item.background().color()
                    if current_color == QColor():  # No existing color
                        self.highlight_cell(row_index, col, GapSeverity.LOW, f"Low Confidence: {row.confidence:.2f}")
                        
    def highlight_cell(self, row: int, col: int, severity: GapSeverity, tooltip: str):
        """Highlight a cell with gap color and tooltip."""
        item = self.matrix_table.item(row, col)
        if item:
            item.setBackground(self.gap_colors[severity])
            item.setToolTip(tooltip)
            
    def get_confidence_color(self, confidence: float) -> QColor:
        """Get color for confidence level."""
        if confidence >= 0.8:
            return self.confidence_colors["high"]
        elif confidence >= 0.5:
            return self.confidence_colors["medium"]
        else:
            return self.confidence_colors["low"]
            
    def show_empty_message(self):
        """Show message when no data is available."""
        self.matrix_table.setRowCount(1)
        message = QTableWidgetItem(
            "No traceability data available.\n\n"
            "This may be because:\n"
            "• No analysis has been run yet\n"
            "• Analysis failed to generate traceability links\n"
            "• Current filters exclude all data\n\n"
            "Try running an analysis or adjusting the filters."
        )
        message.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self.matrix_table.setItem(0, 0, message)
        self.matrix_table.setSpan(0, 0, 1, 11)
        
    def update_gap_analysis(self):
        """Update the gap analysis display."""
        if not self.gaps:
            self.gaps_browser.setHtml(
                "<h3>No Gaps Detected</h3>"
                "<p>The traceability matrix appears to be complete with no significant gaps.</p>"
            )
            return
            
        # Generate gap report HTML
        html_report = self.generate_gap_html_report()
        self.gaps_browser.setHtml(html_report)
        
    def generate_gap_html_report(self) -> str:
        """Generate HTML formatted gap analysis report."""
        if not self.gaps:
            return "<h3>No Gaps Detected</h3><p>Traceability matrix is complete.</p>"
            
        # Group gaps by severity
        high_gaps = [g for g in self.gaps if g.severity == "high"]
        medium_gaps = [g for g in self.gaps if g.severity == "medium"] 
        low_gaps = [g for g in self.gaps if g.severity == "low"]
        
        html = ["<h3>Traceability Gap Analysis</h3>"]
        
        # Summary
        html.append(f"<p><strong>Total Gaps:</strong> {len(self.gaps)}</p>")
        html.append(f"<p><span style='color: red;'>High Severity:</span> {len(high_gaps)} | ")
        html.append(f"<span style='color: orange;'>Medium Severity:</span> {len(medium_gaps)} | ")
        html.append(f"<span style='color: green;'>Low Severity:</span> {len(low_gaps)}</p>")
        
        # High severity gaps
        if high_gaps:
            html.append("<h4 style='color: red;'>High Severity Gaps</h4>")
            html.append("<ul>")
            for gap in high_gaps[:10]:  # Limit to first 10
                html.append(f"<li><strong>{gap.gap_type.replace('_', ' ').title()}:</strong> {gap.description}</li>")
            if len(high_gaps) > 10:
                html.append(f"<li><em>... and {len(high_gaps) - 10} more high severity gaps</em></li>")
            html.append("</ul>")
            
        # Medium severity gaps
        if medium_gaps:
            html.append("<h4 style='color: orange;'>Medium Severity Gaps</h4>")
            html.append("<ul>")
            for gap in medium_gaps[:5]:  # Limit to first 5
                html.append(f"<li><strong>{gap.gap_type.replace('_', ' ').title()}:</strong> {gap.description}</li>")
            if len(medium_gaps) > 5:
                html.append(f"<li><em>... and {len(medium_gaps) - 5} more medium severity gaps</em></li>")
            html.append("</ul>")
            
        return "".join(html)
        
    # Event handlers
    def on_view_changed(self, view_type: str):
        """Handle view type change."""
        self.current_view = view_type.lower().replace(" ", "_").replace("→", "to")
        self.apply_filters()
        
    def on_cell_clicked(self, row: int, column: int):
        """Handle cell click to show details."""
        if row < len(self.filtered_rows):
            self.cell_details_requested.emit(row, column)
            
    def on_cell_entered(self, row: int, column: int):
        """Handle mouse enter on cell for tooltips."""
        if row < len(self.filtered_rows):
            table_row = self.filtered_rows[row]
            tooltip = self.generate_cell_tooltip(table_row, column)
            
            item = self.matrix_table.item(row, column)
            if item and not item.toolTip():
                item.setToolTip(tooltip)
                
    def generate_cell_tooltip(self, row: TraceabilityTableRow, column: int) -> str:
        """Generate tooltip for a cell."""
        tooltips = {
            0: f"Code Reference: {row.code_reference}",
            1: f"File: {row.file_path}",
            2: f"Function: {row.function_name}",
            3: f"Feature ID: {row.feature_id}",
            4: f"Feature: {row.feature_description}",
            5: f"User Requirement: {row.user_requirement_id}",
            6: f"UR Text: {row.user_requirement_text[:100]}...",
            7: f"Software Requirement: {row.software_requirement_id}",
            8: f"SR Text: {row.software_requirement_text[:100]}...",
            9: f"Risk: {row.risk_id}",
            10: f"Confidence: {row.confidence:.2f}"
        }
        return tooltips.get(column, "")
        
    def show_context_menu(self, position: QPoint):
        """Show context menu for table."""
        item = self.matrix_table.itemAt(position)
        if not item:
            return
            
        menu = QMenu(self)
        
        # Add context menu actions
        copy_action = QAction("Copy Cell", self)
        copy_action.triggered.connect(lambda: self.copy_cell_content(item))
        menu.addAction(copy_action)
        
        copy_row_action = QAction("Copy Row", self)
        copy_row_action.triggered.connect(lambda: self.copy_row_content(item.row()))
        menu.addAction(copy_row_action)
        
        menu.addSeparator()
        
        show_details_action = QAction("Show Details", self)
        show_details_action.triggered.connect(lambda: self.show_row_details(item.row()))
        menu.addAction(show_details_action)
        
        menu.exec(self.matrix_table.mapToGlobal(position))
        
    def copy_cell_content(self, item: QTableWidgetItem):
        """Copy cell content to clipboard."""
        QApplication.clipboard().setText(item.text())
        
    def copy_row_content(self, row: int):
        """Copy entire row content to clipboard."""
        if row < len(self.filtered_rows):
            table_row = self.filtered_rows[row]
            row_data = [
                table_row.code_reference,
                table_row.file_path,
                table_row.function_name,
                table_row.feature_id,
                table_row.feature_description,
                table_row.user_requirement_id,
                table_row.user_requirement_text,
                table_row.software_requirement_id,
                table_row.software_requirement_text,
                table_row.risk_id,
                str(table_row.confidence)
            ]
            QApplication.clipboard().setText("\t".join(row_data))
            
    def show_row_details(self, row: int):
        """Show detailed information for a row."""
        if row < len(self.filtered_rows):
            table_row = self.filtered_rows[row]
            details = {
                "code_reference": table_row.code_reference,
                "file_path": table_row.file_path,
                "function_name": table_row.function_name,
                "feature_id": table_row.feature_id,
                "feature_description": table_row.feature_description,
                "user_requirement_id": table_row.user_requirement_id,
                "user_requirement_text": table_row.user_requirement_text,
                "software_requirement_id": table_row.software_requirement_id,
                "software_requirement_text": table_row.software_requirement_text,
                "risk_id": table_row.risk_id,
                "risk_hazard": table_row.risk_hazard,
                "confidence": table_row.confidence
            }
            
            # Create details dialog
            dialog = TraceabilityDetailsDialog(details, self)
            dialog.exec()
            
    def clear_filters(self):
        """Clear all filters."""
        self.view_combo.setCurrentText("Full Matrix")
        self.filter_edit.clear()
        self.show_gaps_only.setChecked(False)
        self.confidence_combo.setCurrentText("0.0")
        
    def refresh_matrix(self):
        """Refresh the matrix display."""
        self.apply_filters()
        self.update_gap_analysis()
        
    def validate_matrix(self):
        """Validate the traceability matrix."""
        if not self.matrix_data:
            QMessageBox.information(self, "Validation", "No matrix data to validate.")
            return
            
        # Perform validation (this would call the traceability service)
        issues = []
        
        # Check for completeness
        incomplete_rows = sum(1 for row in self.table_rows 
                            if not all([row.user_requirement_id, row.software_requirement_id]))
        if incomplete_rows > 0:
            issues.append(f"{incomplete_rows} incomplete traceability chains")
            
        # Check for low confidence links
        low_confidence = sum(1 for row in self.table_rows if row.confidence < 0.5)
        if low_confidence > 0:
            issues.append(f"{low_confidence} low confidence links")
            
        # Show validation results
        if issues:
            message = "Validation Issues Found:\n\n" + "\n".join(f"• {issue}" for issue in issues)
            QMessageBox.warning(self, "Validation Results", message)
        else:
            QMessageBox.information(self, "Validation Results", "Matrix validation passed successfully!")
            
    def toggle_gap_panel(self):
        """Toggle the gap analysis panel visibility."""
        gap_widget = self.main_splitter.widget(1)
        if gap_widget.isVisible():
            gap_widget.setVisible(False)
            self.toggle_gaps_btn.setText("Show Gaps")
        else:
            gap_widget.setVisible(True)
            self.toggle_gaps_btn.setText("Hide Gaps")
            
    def export_matrix(self, format_type: str):
        """Export the matrix in the specified format."""
        if not self.filtered_rows and format_type != "gaps":
            QMessageBox.warning(self, "Export Error", "No data to export.")
            return
            
        # Get filename from user
        filters = {
            "csv": "CSV Files (*.csv)",
            "excel": "Excel Files (*.xlsx)",
            "pdf": "PDF Files (*.pdf)",
            "gaps": "Text Files (*.txt)"
        }
        
        filename, _ = QFileDialog.getSaveFileName(
            self, f"Export {format_type.upper()}", 
            f"traceability_matrix.{format_type if format_type != 'gaps' else 'txt'}", 
            filters.get(format_type, "All Files (*)")
        )
        
        if filename:
            self.export_requested.emit(format_type, filename)


class TraceabilityDetailsDialog(QDialog):
    """Dialog for showing detailed traceability information."""
    
    def __init__(self, details: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.details = details
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle("Traceability Details")
        self.setModal(True)
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Create details browser
        browser = QTextBrowser()
        html_content = self.generate_details_html()
        browser.setHtml(html_content)
        layout.addWidget(browser)
        
        # Add close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def generate_details_html(self) -> str:
        """Generate HTML content for details display."""
        html = ["<h3>Traceability Chain Details</h3>"]
        
        sections = [
            ("Code Information", [
                ("Code Reference", self.details.get("code_reference", "N/A")),
                ("File Path", self.details.get("file_path", "N/A")),
                ("Function Name", self.details.get("function_name", "N/A"))
            ]),
            ("Feature Information", [
                ("Feature ID", self.details.get("feature_id", "N/A")),
                ("Description", self.details.get("feature_description", "N/A"))
            ]),
            ("Requirements Information", [
                ("User Requirement ID", self.details.get("user_requirement_id", "N/A")),
                ("User Requirement", self.details.get("user_requirement_text", "N/A")),
                ("Software Requirement ID", self.details.get("software_requirement_id", "N/A")),
                ("Software Requirement", self.details.get("software_requirement_text", "N/A"))
            ]),
            ("Risk Information", [
                ("Risk ID", self.details.get("risk_id", "N/A")),
                ("Risk Hazard", self.details.get("risk_hazard", "N/A"))
            ]),
            ("Traceability Metrics", [
                ("Confidence Score", f"{self.details.get('confidence', 0):.2f}")
            ])
        ]
        
        for section_title, fields in sections:
            html.append(f"<h4>{section_title}</h4>")
            html.append("<table border='1' cellpadding='5' cellspacing='0' width='100%'>")
            for field_name, field_value in fields:
                html.append(f"<tr><td><strong>{field_name}:</strong></td><td>{field_value}</td></tr>")
            html.append("</table><br>")
            
        return "".join(html)