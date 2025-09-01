"""
Enhanced Requirements Tab Widget for displaying and editing requirements.
Implements dual-pane layout for URs and SRs with advanced editing capabilities.
"""

from typing import Dict, List, Optional, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
    QLabel, QPushButton, QGroupBox, QLineEdit, QComboBox, 
    QMessageBox, QHeaderView, QSplitter, QPlainTextEdit, 
    QDialog, QDialogButtonBox, QFormLayout, QFileDialog,
    QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
import csv
import json
import os
from datetime import datetime


class RequirementsTabWidget(QWidget):
    """Enhanced requirements tab widget with dual-pane layout for URs and SRs."""
    
    # Signals
    requirements_updated = pyqtSignal(dict)
    traceability_update_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_requirements: List[Dict] = []
        self.software_requirements: List[Dict] = []
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Initialize the requirements tab UI with dual-pane layout."""
        layout = QVBoxLayout(self)
        
        # Main toolbar
        toolbar_layout = QHBoxLayout()
        
        self.save_all_button = QPushButton("Save All Changes")
        self.save_all_button.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
        
        self.export_button = QPushButton("Export Requirements")
        self.import_button = QPushButton("Import Requirements")
        self.validate_button = QPushButton("Validate All")
        
        toolbar_layout.addWidget(self.save_all_button)
        toolbar_layout.addWidget(self.export_button)
        toolbar_layout.addWidget(self.import_button)
        toolbar_layout.addWidget(self.validate_button)
        toolbar_layout.addStretch()
        
        # Search functionality
        toolbar_layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search requirements...")
        self.search_edit.setMaximumWidth(200)
        toolbar_layout.addWidget(self.search_edit)
        
        layout.addLayout(toolbar_layout)
        
        # Create horizontal splitter for dual-pane layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # User Requirements pane
        ur_group = QGroupBox("User Requirements (URs)")
        ur_layout = QVBoxLayout(ur_group)
        
        # UR toolbar
        ur_toolbar = QHBoxLayout()
        self.add_ur_button = QPushButton("Add UR")
        self.edit_ur_button = QPushButton("Edit UR")
        self.delete_ur_button = QPushButton("Delete UR")
        
        ur_toolbar.addWidget(self.add_ur_button)
        ur_toolbar.addWidget(self.edit_ur_button)
        ur_toolbar.addWidget(self.delete_ur_button)
        ur_toolbar.addStretch()
        
        self.ur_count_label = QLabel("Count: 0")
        ur_toolbar.addWidget(self.ur_count_label)
        
        ur_layout.addLayout(ur_toolbar)
        
        # UR table
        self.ur_table = QTableWidget()
        self.ur_table.setColumnCount(5)
        self.ur_table.setHorizontalHeaderLabels([
            "ID", "Description", "Priority", "Status", "Acceptance Criteria"
        ])
        
        header = self.ur_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        
        self.ur_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.ur_table.setAlternatingRowColors(True)
        self.ur_table.setSortingEnabled(True)
        ur_layout.addWidget(self.ur_table)
        
        splitter.addWidget(ur_group)
        
        # Software Requirements pane
        sr_group = QGroupBox("Software Requirements (SRs)")
        sr_layout = QVBoxLayout(sr_group)
        
        # SR toolbar
        sr_toolbar = QHBoxLayout()
        self.add_sr_button = QPushButton("Add SR")
        self.edit_sr_button = QPushButton("Edit SR")
        self.delete_sr_button = QPushButton("Delete SR")
        
        sr_toolbar.addWidget(self.add_sr_button)
        sr_toolbar.addWidget(self.edit_sr_button)
        sr_toolbar.addWidget(self.delete_sr_button)
        sr_toolbar.addStretch()
        
        self.sr_count_label = QLabel("Count: 0")
        sr_toolbar.addWidget(self.sr_count_label)
        
        sr_layout.addLayout(sr_toolbar)
        
        # SR table
        self.sr_table = QTableWidget()
        self.sr_table.setColumnCount(6)
        self.sr_table.setHorizontalHeaderLabels([
            "ID", "Description", "Priority", "Status", "Derived From", "Code Refs"
        ])
        
        header = self.sr_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.sr_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.sr_table.setAlternatingRowColors(True)
        self.sr_table.setSortingEnabled(True)
        sr_layout.addWidget(self.sr_table)
        
        splitter.addWidget(sr_group)
        
        # Set equal sizes for both panes
        splitter.setSizes([400, 400])
        layout.addWidget(splitter)
        
        # Status bar
        status_layout = QHBoxLayout()
        
        self.total_requirements_label = QLabel("Total Requirements: 0")
        self.validation_status_label = QLabel("Validation: Not checked")
        self.last_saved_label = QLabel("Last saved: Never")
        
        status_layout.addWidget(self.total_requirements_label)
        status_layout.addWidget(QLabel("|"))
        status_layout.addWidget(self.validation_status_label)
        status_layout.addWidget(QLabel("|"))
        status_layout.addWidget(self.last_saved_label)
        status_layout.addStretch()
        
        layout.addLayout(status_layout)
        
    def setup_connections(self):
        """Set up signal connections for all UI elements."""
        # Main toolbar connections
        self.save_all_button.clicked.connect(self.save_all_changes)
        self.export_button.clicked.connect(self.export_requirements)
        self.import_button.clicked.connect(self.import_requirements)
        self.validate_button.clicked.connect(self.validate_all_requirements)
        self.search_edit.textChanged.connect(self.filter_requirements)
        
        # UR connections
        self.add_ur_button.clicked.connect(self.add_user_requirement)
        self.edit_ur_button.clicked.connect(self.edit_user_requirement)
        self.delete_ur_button.clicked.connect(self.delete_user_requirement)
        self.ur_table.doubleClicked.connect(self.edit_user_requirement)
        
        # SR connections
        self.add_sr_button.clicked.connect(self.add_software_requirement)
        self.edit_sr_button.clicked.connect(self.edit_software_requirement)
        self.delete_sr_button.clicked.connect(self.delete_software_requirement)
        self.sr_table.doubleClicked.connect(self.edit_software_requirement)
        
    def update_requirements(self, user_requirements: List[Dict], software_requirements: List[Dict]):
        """Update the requirements display with new data."""
        self.user_requirements = user_requirements.copy() if user_requirements else []
        self.software_requirements = software_requirements.copy() if software_requirements else []
        
        self.refresh_ur_table()
        self.refresh_sr_table()
        self.update_statistics()
        self.update_validation_display()
        
        # Emit update signal for integration with results system
        # Use QTimer to ensure signal is processed after UI updates
        QTimer.singleShot(50, self.emit_requirements_updated)
        
    def refresh_ur_table(self):
        """Refresh the user requirements table."""
        self.ur_table.setRowCount(len(self.user_requirements))
        for i, req in enumerate(self.user_requirements):
            validation_errors = self._validate_requirement(req, "user")
            has_errors = len(validation_errors) > 0
            
            # ID
            id_item = QTableWidgetItem(req.get('id', ''))
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if has_errors:
                id_item.setBackground(QColor(255, 220, 220))
                id_item.setToolTip(f"Validation errors:\\n" + "\\n".join(validation_errors))
            self.ur_table.setItem(i, 0, id_item)
            
            # Description
            desc_item = QTableWidgetItem(req.get('description', ''))
            if has_errors:
                desc_item.setBackground(QColor(255, 220, 220))
            self.ur_table.setItem(i, 1, desc_item)
            
            # Priority
            priority_item = QTableWidgetItem(req.get('priority', 'Medium'))
            self.set_priority_color(priority_item, req.get('priority', 'Medium'))
            if has_errors:
                priority_item.setBackground(QColor(255, 220, 220))
            self.ur_table.setItem(i, 2, priority_item)
            
            # Status
            status_item = QTableWidgetItem(req.get('status', 'Draft'))
            self.set_status_color(status_item, req.get('status', 'Draft'))
            if has_errors:
                status_item.setBackground(QColor(255, 220, 220))
            self.ur_table.setItem(i, 3, status_item)
            
            # Acceptance Criteria
            criteria = req.get('acceptance_criteria', [])
            criteria_text = f"{len(criteria)} criteria" if isinstance(criteria, list) else str(criteria)
            criteria_item = QTableWidgetItem(criteria_text)
            if has_errors:
                criteria_item.setBackground(QColor(255, 220, 220))
            self.ur_table.setItem(i, 4, criteria_item)
            
    def refresh_sr_table(self):
        """Refresh the software requirements table."""
        self.sr_table.setRowCount(len(self.software_requirements))
        for i, req in enumerate(self.software_requirements):
            validation_errors = self._validate_requirement(req, "software")
            has_errors = len(validation_errors) > 0
            
            # ID
            id_item = QTableWidgetItem(req.get('id', ''))
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if has_errors:
                id_item.setBackground(QColor(255, 220, 220))
                id_item.setToolTip(f"Validation errors:\\n" + "\\n".join(validation_errors))
            self.sr_table.setItem(i, 0, id_item)
            
            # Description
            desc_item = QTableWidgetItem(req.get('description', ''))
            if has_errors:
                desc_item.setBackground(QColor(255, 220, 220))
            self.sr_table.setItem(i, 1, desc_item)
            
            # Priority
            priority_item = QTableWidgetItem(req.get('priority', 'Medium'))
            self.set_priority_color(priority_item, req.get('priority', 'Medium'))
            if has_errors:
                priority_item.setBackground(QColor(255, 220, 220))
            self.sr_table.setItem(i, 2, priority_item)
            
            # Status
            status_item = QTableWidgetItem(req.get('status', 'Draft'))
            self.set_status_color(status_item, req.get('status', 'Draft'))
            if has_errors:
                status_item.setBackground(QColor(255, 220, 220))
            self.sr_table.setItem(i, 3, status_item)
            
            # Derived From
            derived_from = req.get('derived_from', [])
            derived_text = ', '.join(derived_from) if isinstance(derived_from, list) else str(derived_from)
            derived_item = QTableWidgetItem(derived_text)
            if has_errors:
                derived_item.setBackground(QColor(255, 220, 220))
            self.sr_table.setItem(i, 4, derived_item)
            
            # Code References
            code_refs = req.get('code_references', [])
            code_count = len(code_refs) if isinstance(code_refs, list) else 0
            code_item = QTableWidgetItem(str(code_count))
            if has_errors:
                code_item.setBackground(QColor(255, 220, 220))
            self.sr_table.setItem(i, 5, code_item)
            
    def set_priority_color(self, item: QTableWidgetItem, priority: str):
        """Set background color based on priority."""
        colors = {
            'Critical': QColor(255, 200, 200),
            'High': QColor(255, 230, 200),
            'Medium': QColor(255, 255, 200),
            'Low': QColor(200, 255, 200)
        }
        if priority in colors:
            item.setBackground(colors[priority])
            
    def set_status_color(self, item: QTableWidgetItem, status: str):
        """Set text color based on status."""
        colors = {
            'Draft': QColor(128, 128, 128),
            'Under Review': QColor(255, 165, 0),
            'Approved': QColor(0, 128, 0),
            'Implemented': QColor(0, 0, 255),
            'Verified': QColor(128, 0, 128)
        }
        if status in colors:
            item.setForeground(colors[status])
            
    def update_statistics(self):
        """Update the statistics labels."""
        ur_count = len(self.user_requirements)
        sr_count = len(self.software_requirements)
        total_count = ur_count + sr_count
        
        self.ur_count_label.setText(f"Count: {ur_count}")
        self.sr_count_label.setText(f"Count: {sr_count}")
        self.total_requirements_label.setText(f"Total Requirements: {total_count}")
        
    def emit_requirements_updated(self):
        """Emit signal that requirements have been updated."""
        self.update_validation_display()
        
        self.requirements_updated.emit({
            'user_requirements': self.user_requirements,
            'software_requirements': self.software_requirements
        })
        
        # Automatically trigger traceability matrix refresh
        self.traceability_update_requested.emit()
        
    def save_all_changes(self):
        """Save all changes to requirements."""
        self.emit_requirements_updated()
        self.last_saved_label.setText(f"Last saved: {datetime.now().strftime('%H:%M:%S')}")
        QMessageBox.information(self, "Saved", "All requirements changes have been saved.")
        
    def export_requirements(self):
        """Export requirements in multiple formats."""
        if not self.user_requirements and not self.software_requirements:
            QMessageBox.information(self, "No Data", "No requirements to export.")
            return
        
        # Format selection dialog
        from PyQt6.QtWidgets import QInputDialog
        
        formats = ["CSV", "JSON", "Excel (CSV)", "PDF (Text)"]
        format_choice, ok = QInputDialog.getItem(
            self, "Export Format", "Select export format:", formats, 0, False
        )
        
        if not ok:
            return
            
        # File extension mapping
        extensions = {
            "CSV": ".csv",
            "JSON": ".json", 
            "Excel (CSV)": ".csv",
            "PDF (Text)": ".txt"
        }
        
        file_filter_map = {
            "CSV": "CSV files (*.csv)",
            "JSON": "JSON files (*.json)",
            "Excel (CSV)": "CSV files (*.csv)",
            "PDF (Text)": "Text files (*.txt)"
        }
        
        default_name = f"requirements_export{extensions[format_choice]}"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Requirements", default_name, 
            f"{file_filter_map[format_choice]};;All files (*.*)"
        )
        
        if file_path:
            try:
                if format_choice == "JSON":
                    self._export_json(file_path)
                elif format_choice == "Excel (CSV)":
                    self._export_excel_csv(file_path)
                elif format_choice == "PDF (Text)":
                    self._export_pdf_text(file_path)
                else:  # CSV
                    self._export_csv(file_path)
                    
                QMessageBox.information(self, "Export Complete", f"Requirements exported to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export requirements: {str(e)}")
                
    def _export_csv(self, file_path: str):
        """Export to CSV format."""
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Type', 'ID', 'Description', 'Priority', 'Status', 'Acceptance Criteria', 'Derived From', 'Code References'])
            
            for req in self.user_requirements:
                criteria = '; '.join(req.get('acceptance_criteria', []))
                writer.writerow(['User', req.get('id', ''), req.get('description', ''), 
                               req.get('priority', ''), req.get('status', ''), criteria, '', ''])
                               
            for req in self.software_requirements:
                criteria = '; '.join(req.get('acceptance_criteria', []))
                derived_from = ', '.join(req.get('derived_from', []))
                code_refs = '; '.join(req.get('code_references', []))
                writer.writerow(['Software', req.get('id', ''), req.get('description', ''), 
                               req.get('priority', ''), req.get('status', ''), criteria, derived_from, code_refs])
                               
    def _export_json(self, file_path: str):
        """Export to JSON format."""
        data = {
            'user_requirements': self.user_requirements,
            'software_requirements': self.software_requirements,
            'metadata': {
                'export_timestamp': datetime.now().isoformat(),
                'total_user_requirements': len(self.user_requirements),
                'total_software_requirements': len(self.software_requirements)
            }
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _export_excel_csv(self, file_path: str):
        """Export to Excel-compatible CSV format with enhanced formatting."""
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write metadata header
            writer.writerow(['Requirements Export Report'])
            writer.writerow(['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
            writer.writerow(['Total User Requirements:', len(self.user_requirements)])
            writer.writerow(['Total Software Requirements:', len(self.software_requirements)])
            writer.writerow([])  # Empty row
            
            # Write detailed header
            writer.writerow(['Type', 'ID', 'Description', 'Priority', 'Status', 'Acceptance Criteria', 'Derived From', 'Code References', 'Validation Status'])
            
            # Write user requirements with validation
            for req in self.user_requirements:
                criteria = '; '.join(req.get('acceptance_criteria', []))
                validation_errors = self._validate_requirement(req, "user")
                validation_status = "Valid" if not validation_errors else f"Errors: {'; '.join(validation_errors)}"
                
                writer.writerow([
                    'User', req.get('id', ''), req.get('description', ''),
                    req.get('priority', ''), req.get('status', ''), criteria, '', '', validation_status
                ])
                
            # Write software requirements with validation
            for req in self.software_requirements:
                criteria = '; '.join(req.get('acceptance_criteria', []))
                derived_from = '; '.join(req.get('derived_from', []))
                code_refs = '; '.join(req.get('code_references', []))
                validation_errors = self._validate_requirement(req, "software")
                validation_status = "Valid" if not validation_errors else f"Errors: {'; '.join(validation_errors)}"
                
                writer.writerow([
                    'Software', req.get('id', ''), req.get('description', ''),
                    req.get('priority', ''), req.get('status', ''), criteria, derived_from, code_refs, validation_status
                ])
    
    def _export_pdf_text(self, file_path: str):
        """Export to PDF-style text format."""
        lines = []
        lines.append("REQUIREMENTS SPECIFICATION DOCUMENT")
        lines.append("=" * 50)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Summary
        ur_count = len(self.user_requirements)
        sr_count = len(self.software_requirements)
        validation_passed = self.validate_all_requirements()
        
        lines.append("DOCUMENT SUMMARY")
        lines.append("-" * 20)
        lines.append(f"Total User Requirements: {ur_count}")
        lines.append(f"Total Software Requirements: {sr_count}")
        lines.append(f"Validation Status: {'PASSED' if validation_passed else 'FAILED'}")
        lines.append("")
        
        # User Requirements
        if self.user_requirements:
            lines.append("USER REQUIREMENTS")
            lines.append("-" * 20)
            for i, req in enumerate(self.user_requirements, 1):
                lines.append(f"{i}. {req.get('id', 'N/A')}: {req.get('description', 'No description')}")
                lines.append(f"   Priority: {req.get('priority', 'N/A')}")
                lines.append(f"   Status: {req.get('status', 'N/A')}")
                
                criteria = req.get('acceptance_criteria', [])
                if criteria:
                    lines.append("   Acceptance Criteria:")
                    for j, criterion in enumerate(criteria, 1):
                        lines.append(f"     {j}. {criterion}")
                
                validation_errors = self._validate_requirement(req, "user")
                if validation_errors:
                    lines.append(f"   ⚠ Validation Issues: {'; '.join(validation_errors)}")
                
                lines.append("")
        
        # Software Requirements
        if self.software_requirements:
            lines.append("SOFTWARE REQUIREMENTS")
            lines.append("-" * 25)
            for i, req in enumerate(self.software_requirements, 1):
                lines.append(f"{i}. {req.get('id', 'N/A')}: {req.get('description', 'No description')}")
                lines.append(f"   Priority: {req.get('priority', 'N/A')}")
                lines.append(f"   Status: {req.get('status', 'N/A')}")
                
                derived_from = req.get('derived_from', [])
                if derived_from:
                    lines.append(f"   Derived From: {', '.join(derived_from)}")
                
                code_refs = req.get('code_references', [])
                if code_refs:
                    lines.append(f"   Code References: {', '.join(code_refs)}")
                
                criteria = req.get('acceptance_criteria', [])
                if criteria:
                    lines.append("   Acceptance Criteria:")
                    for j, criterion in enumerate(criteria, 1):
                        lines.append(f"     {j}. {criterion}")
                
                validation_errors = self._validate_requirement(req, "software")
                if validation_errors:
                    lines.append(f"   ⚠ Validation Issues: {'; '.join(validation_errors)}")
                
                lines.append("")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
            
    def import_requirements(self):
        """Import requirements from file."""
        QMessageBox.information(self, "Import", "Import functionality not yet implemented.")
        
    def validate_all_requirements(self):
        """Validate all requirements and update status indicators."""
        ur_errors = []
        sr_errors = []
        
        for i, req in enumerate(self.user_requirements):
            errors = self._validate_requirement(req, "user")
            if errors:
                ur_errors.extend([f"UR {i+1}: {error}" for error in errors])
                
        for i, req in enumerate(self.software_requirements):
            errors = self._validate_requirement(req, "software")
            if errors:
                sr_errors.extend([f"SR {i+1}: {error}" for error in errors])
                
        total_errors = len(ur_errors) + len(sr_errors)
        if total_errors == 0:
            self.validation_status_label.setText("Validation: ✓ All requirements valid")
            self.validation_status_label.setStyleSheet("color: green;")
            QMessageBox.information(self, "Validation Complete", "All requirements are valid!")
        else:
            self.validation_status_label.setText(f"Validation: ⚠ {total_errors} error(s)")
            self.validation_status_label.setStyleSheet("color: red;")
            
            all_errors = ur_errors + sr_errors
            QMessageBox.warning(self, "Validation Errors", 
                              "Found the following validation errors:\\n\\n" + 
                              "\\n".join(all_errors[:10]) + 
                              (f"\\n... and {len(all_errors) - 10} more" if len(all_errors) > 10 else ""))
                
        # Refresh the display to show validation indicators
        self.refresh_ur_table()
        self.refresh_sr_table()
        
        return total_errors == 0
        
    def _get_req_attr(self, requirement, attr_name: str, default=None):
        """Helper to get attribute from requirement (dict or object)."""
        if hasattr(requirement, 'get'):
            return requirement.get(attr_name, default)
        else:
            return getattr(requirement, attr_name, default)
    
    def _validate_requirement(self, requirement: Dict, req_type: str) -> List[str]:
        """Validate a single requirement and return list of errors."""
        errors = []
        
        # Handle both dict and Requirement object
        if hasattr(requirement, 'get'):
            # Dictionary-like object
            req_id = requirement.get('id')
            req_desc = requirement.get('description')
        else:
            # Requirement object
            req_id = getattr(requirement, 'id', None)
            req_desc = getattr(requirement, 'description', None)
        
        if not req_id:
            errors.append("Missing ID")
        elif req_type == "user" and not req_id.startswith('UR-'):
            errors.append("User requirement ID must start with 'UR-'")
        elif req_type == "software" and not req_id.startswith('SR-'):
            errors.append("Software requirement ID must start with 'SR-'")
            
        if not req_desc:
            errors.append("Missing description")
        
        # Get acceptance criteria
        if hasattr(requirement, 'get'):
            acceptance_criteria = requirement.get('acceptance_criteria')
            priority = requirement.get('priority')
        else:
            acceptance_criteria = getattr(requirement, 'acceptance_criteria', None)
            priority = getattr(requirement, 'priority', None)
            
        if not acceptance_criteria:
            errors.append("Missing acceptance criteria")
        elif isinstance(acceptance_criteria, list) and len(acceptance_criteria) == 0:
            errors.append("At least one acceptance criterion required")
            
        valid_priorities = ['Low', 'Medium', 'High', 'Critical']
        if priority not in valid_priorities:
            errors.append(f"Invalid priority. Must be one of: {', '.join(valid_priorities)}")
            
        # Get status
        if hasattr(requirement, 'get'):
            status = requirement.get('status')
        else:
            status = getattr(requirement, 'status', None)
            
        valid_statuses = ['Draft', 'Under Review', 'Approved', 'Implemented', 'Verified']
        if status not in valid_statuses:
            errors.append(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
            
        return errors
        
    def update_validation_display(self):
        """Update the validation status display without showing dialogs."""
        ur_errors = []
        sr_errors = []
        
        for i, req in enumerate(self.user_requirements):
            errors = self._validate_requirement(req, "user")
            if errors:
                ur_errors.extend([f"UR {i+1}: {error}" for error in errors])
                
        for i, req in enumerate(self.software_requirements):
            errors = self._validate_requirement(req, "software")
            if errors:
                sr_errors.extend([f"SR {i+1}: {error}" for error in errors])
                
        total_errors = len(ur_errors) + len(sr_errors)
        
        if total_errors == 0:
            self.validation_status_label.setText("Validation: ✓ All requirements valid")
            self.validation_status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.validation_status_label.setText(f"Validation: ⚠ {total_errors} error(s)")
            self.validation_status_label.setStyleSheet("color: red; font-weight: bold;")
            
        # Update button states based on validation
        self.save_all_button.setEnabled(True)  # Always allow saving
        if total_errors == 0:
            self.save_all_button.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
        else:
            self.save_all_button.setStyleSheet("font-weight: bold; background-color: #FF9800; color: white;")
            
    def filter_requirements(self):
        """Filter requirements based on search text."""
        # Simple implementation - just refresh tables for now
        self.refresh_ur_table()
        self.refresh_sr_table()
        
    def add_user_requirement(self):
        """Add a new user requirement."""
        QMessageBox.information(self, "Add UR", "Add user requirement functionality not yet implemented.")
        
    def edit_user_requirement(self):
        """Edit selected user requirement."""
        QMessageBox.information(self, "Edit UR", "Edit user requirement functionality not yet implemented.")
        
    def delete_user_requirement(self):
        """Delete selected user requirement."""
        QMessageBox.information(self, "Delete UR", "Delete user requirement functionality not yet implemented.")
        
    def add_software_requirement(self):
        """Add a new software requirement."""
        QMessageBox.information(self, "Add SR", "Add software requirement functionality not yet implemented.")
        
    def edit_software_requirement(self):
        """Edit selected software requirement."""
        QMessageBox.information(self, "Edit SR", "Edit software requirement functionality not yet implemented.")
        
    def delete_software_requirement(self):
        """Delete selected software requirement."""
        QMessageBox.information(self, "Delete SR", "Delete software requirement functionality not yet implemented.")
        
    def get_requirements_data(self) -> Dict:
        """Get current requirements data."""
        return {
            'user_requirements': self.user_requirements,
            'software_requirements': self.software_requirements
        }