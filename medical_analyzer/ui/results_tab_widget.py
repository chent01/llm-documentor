"""
Results tab widget for displaying analysis results in organized tabs.
"""

from typing import Dict, List, Optional, Any
from PyQt6.QtWidgets import (
    QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QTableWidget, QTableWidgetItem, QLabel, QPushButton, 
    QScrollArea, QGroupBox, QLineEdit, QComboBox, QMessageBox,
    QHeaderView, QSplitter, QFrame, QPlainTextEdit, QCheckBox,
    QSpinBox, QProgressBar, QFileDialog, QDialog, QDialogButtonBox,
    QFormLayout, QTextBrowser
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QAction
import csv
import json
import os
import io
from datetime import datetime

from ..services.soup_service import SOUPService
from .soup_widget import SOUPWidget
import csv
import json
import os
import io
from datetime import datetime


class RequirementEditDialog(QDialog):
    """Dialog for editing individual requirements."""
    
    def __init__(self, requirement_data: Dict, parent=None):
        super().__init__(parent)
        self.requirement_data = requirement_data.copy()
        self.setup_ui()
        self.populate_fields()
        
    def setup_ui(self):
        """Initialize the dialog UI."""
        self.setWindowTitle("Edit Requirement")
        self.setModal(True)
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Form layout for requirement fields
        form_layout = QFormLayout()
        
        self.id_edit = QLineEdit()
        self.id_edit.setReadOnly(True)  # ID should not be editable
        form_layout.addRow("ID:", self.id_edit)
        
        self.description_edit = QPlainTextEdit()
        self.description_edit.setMaximumHeight(100)
        form_layout.addRow("Description:", self.description_edit)
        
        self.acceptance_criteria_edit = QPlainTextEdit()
        self.acceptance_criteria_edit.setPlaceholderText("Enter each criterion on a new line")
        form_layout.addRow("Acceptance Criteria:", self.acceptance_criteria_edit)
        
        # For software requirements, add derived from field
        self.derived_from_edit = QLineEdit()
        self.derived_from_edit.setPlaceholderText("Comma-separated requirement IDs")
        form_layout.addRow("Derived From:", self.derived_from_edit)
        
        layout.addLayout(form_layout)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def populate_fields(self):
        """Populate fields with requirement data."""
        self.id_edit.setText(self.requirement_data.get('id', ''))
        self.description_edit.setPlainText(self.requirement_data.get('description', ''))
        
        criteria = self.requirement_data.get('acceptance_criteria', [])
        if isinstance(criteria, list):
            self.acceptance_criteria_edit.setPlainText('\n'.join(criteria))
        else:
            self.acceptance_criteria_edit.setPlainText(str(criteria))
            
        derived_from = self.requirement_data.get('derived_from', [])
        if isinstance(derived_from, list):
            self.derived_from_edit.setText(', '.join(derived_from))
        else:
            self.derived_from_edit.setText(str(derived_from))
            
    def get_requirement_data(self) -> Dict:
        """Get the edited requirement data."""
        criteria_text = self.acceptance_criteria_edit.toPlainText().strip()
        criteria = [line.strip() for line in criteria_text.split('\n') if line.strip()]
        
        derived_text = self.derived_from_edit.text().strip()
        derived_from = [item.strip() for item in derived_text.split(',') if item.strip()]
        
        return {
            'id': self.id_edit.text(),
            'description': self.description_edit.toPlainText(),
            'acceptance_criteria': criteria,
            'derived_from': derived_from,
            'code_references': self.requirement_data.get('code_references', [])
        }


class RequirementsTab(QWidget):
    """Tab for displaying and editing requirements."""
    
    requirements_updated = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.user_requirements = []
        self.software_requirements = []
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Initialize the requirements tab UI."""
        layout = QVBoxLayout(self)
        
        # Create splitter for user and software requirements
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # User Requirements section
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
        ur_layout.addLayout(ur_toolbar)
        
        self.ur_table = QTableWidget()
        self.ur_table.setColumnCount(3)
        self.ur_table.setHorizontalHeaderLabels(["ID", "Description", "Acceptance Criteria"])
        self.ur_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ur_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        ur_layout.addWidget(self.ur_table)
        
        # Software Requirements section
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
        sr_layout.addLayout(sr_toolbar)
        
        self.sr_table = QTableWidget()
        self.sr_table.setColumnCount(4)
        self.sr_table.setHorizontalHeaderLabels(["ID", "Description", "Derived From", "Code References"])
        self.sr_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.sr_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        sr_layout.addWidget(self.sr_table)
        
        splitter.addWidget(ur_group)
        splitter.addWidget(sr_group)
        splitter.setSizes([400, 400])
        
        layout.addWidget(splitter)
        
        # Action buttons
        button_layout = QHBoxLayout()
        self.export_button = QPushButton("Export Requirements")
        self.save_button = QPushButton("Save Changes")
        self.refresh_button = QPushButton("Refresh")
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.export_button)
        layout.addLayout(button_layout)
        
    def setup_connections(self):
        """Set up signal connections."""
        # UR buttons
        self.add_ur_button.clicked.connect(self.add_user_requirement)
        self.edit_ur_button.clicked.connect(self.edit_user_requirement)
        self.delete_ur_button.clicked.connect(self.delete_user_requirement)
        
        # SR buttons
        self.add_sr_button.clicked.connect(self.add_software_requirement)
        self.edit_sr_button.clicked.connect(self.edit_software_requirement)
        self.delete_sr_button.clicked.connect(self.delete_software_requirement)
        
        # Table double-click editing
        self.ur_table.doubleClicked.connect(self.edit_user_requirement)
        self.sr_table.doubleClicked.connect(self.edit_software_requirement)
        
        # Save button
        self.save_button.clicked.connect(self.save_changes)
        
    def add_user_requirement(self):
        """Add a new user requirement."""
        new_id = f"UR-{len(self.user_requirements) + 1:03d}"
        new_req = {
            'id': new_id,
            'description': 'New user requirement',
            'acceptance_criteria': ['Acceptance criterion 1']
        }
        
        dialog = RequirementEditDialog(new_req, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            edited_req = dialog.get_requirement_data()
            self.user_requirements.append(edited_req)
            self.refresh_ur_table()
            self.requirements_updated.emit({'user_requirements': self.user_requirements})
            
    def edit_user_requirement(self):
        """Edit selected user requirement."""
        current_row = self.ur_table.currentRow()
        if current_row >= 0 and current_row < len(self.user_requirements):
            req_data = self.user_requirements[current_row]
            dialog = RequirementEditDialog(req_data, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                edited_req = dialog.get_requirement_data()
                self.user_requirements[current_row] = edited_req
                self.refresh_ur_table()
                self.requirements_updated.emit({'user_requirements': self.user_requirements})
                
    def delete_user_requirement(self):
        """Delete selected user requirement."""
        current_row = self.ur_table.currentRow()
        if current_row >= 0 and current_row < len(self.user_requirements):
            reply = QMessageBox.question(
                self, "Delete Requirement",
                f"Are you sure you want to delete requirement {self.user_requirements[current_row]['id']}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                del self.user_requirements[current_row]
                self.refresh_ur_table()
                self.requirements_updated.emit({'user_requirements': self.user_requirements})
                
    def add_software_requirement(self):
        """Add a new software requirement."""
        new_id = f"SR-{len(self.software_requirements) + 1:03d}"
        new_req = {
            'id': new_id,
            'description': 'New software requirement',
            'derived_from': [],
            'code_references': []
        }
        
        dialog = RequirementEditDialog(new_req, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            edited_req = dialog.get_requirement_data()
            self.software_requirements.append(edited_req)
            self.refresh_sr_table()
            self.requirements_updated.emit({'software_requirements': self.software_requirements})
            
    def edit_software_requirement(self):
        """Edit selected software requirement."""
        current_row = self.sr_table.currentRow()
        if current_row >= 0 and current_row < len(self.software_requirements):
            req_data = self.software_requirements[current_row]
            dialog = RequirementEditDialog(req_data, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                edited_req = dialog.get_requirement_data()
                self.software_requirements[current_row] = edited_req
                self.refresh_sr_table()
                self.requirements_updated.emit({'software_requirements': self.software_requirements})
                
    def delete_software_requirement(self):
        """Delete selected software requirement."""
        current_row = self.sr_table.currentRow()
        if current_row >= 0 and current_row < len(self.software_requirements):
            reply = QMessageBox.question(
                self, "Delete Requirement",
                f"Are you sure you want to delete requirement {self.software_requirements[current_row]['id']}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                del self.software_requirements[current_row]
                self.refresh_sr_table()
                self.requirements_updated.emit({'software_requirements': self.software_requirements})
                
    def save_changes(self):
        """Save all changes to requirements."""
        self.requirements_updated.emit({
            'user_requirements': self.user_requirements,
            'software_requirements': self.software_requirements
        })
        QMessageBox.information(self, "Saved", "Requirements changes have been saved.")
        
    def refresh_ur_table(self):
        """Refresh the user requirements table."""
        self.ur_table.setRowCount(len(self.user_requirements))
        for i, req in enumerate(self.user_requirements):
            self.ur_table.setItem(i, 0, QTableWidgetItem(req.get('id', '')))
            self.ur_table.setItem(i, 1, QTableWidgetItem(req.get('description', '')))
            criteria = req.get('acceptance_criteria', [])
            criteria_text = '\n'.join(criteria) if isinstance(criteria, list) else str(criteria)
            self.ur_table.setItem(i, 2, QTableWidgetItem(criteria_text))
            
    def refresh_sr_table(self):
        """Refresh the software requirements table."""
        self.sr_table.setRowCount(len(self.software_requirements))
        for i, req in enumerate(self.software_requirements):
            self.sr_table.setItem(i, 0, QTableWidgetItem(req.get('id', '')))
            self.sr_table.setItem(i, 1, QTableWidgetItem(req.get('description', '')))
            derived_from = req.get('derived_from', [])
            derived_text = ', '.join(derived_from) if isinstance(derived_from, list) else str(derived_from)
            self.sr_table.setItem(i, 2, QTableWidgetItem(derived_text))
            code_refs = req.get('code_references', [])
            self.sr_table.setItem(i, 3, QTableWidgetItem(str(len(code_refs))))
        
    def update_requirements(self, user_requirements: List[Dict], software_requirements: List[Dict]):
        """Update the requirements display."""
        self.user_requirements = user_requirements.copy()
        self.software_requirements = software_requirements.copy()
        self.refresh_ur_table()
        self.refresh_sr_table()


class RiskEditDialog(QDialog):
    """Dialog for editing individual risk items."""
    
    def __init__(self, risk_data: Dict, parent=None):
        super().__init__(parent)
        self.risk_data = risk_data.copy()
        self.setup_ui()
        self.populate_fields()
        
    def setup_ui(self):
        """Initialize the dialog UI."""
        self.setWindowTitle("Edit Risk Item")
        self.setModal(True)
        self.resize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # Form layout for risk fields
        form_layout = QFormLayout()
        
        self.id_edit = QLineEdit()
        self.id_edit.setReadOnly(True)  # ID should not be editable
        form_layout.addRow("ID:", self.id_edit)
        
        self.hazard_edit = QPlainTextEdit()
        self.hazard_edit.setMaximumHeight(80)
        form_layout.addRow("Hazard:", self.hazard_edit)
        
        self.cause_edit = QPlainTextEdit()
        self.cause_edit.setMaximumHeight(80)
        form_layout.addRow("Cause:", self.cause_edit)
        
        self.effect_edit = QPlainTextEdit()
        self.effect_edit.setMaximumHeight(80)
        form_layout.addRow("Effect:", self.effect_edit)
        
        self.severity_combo = QComboBox()
        self.severity_combo.addItems(["Minor", "Serious", "Catastrophic"])
        form_layout.addRow("Severity:", self.severity_combo)
        
        self.probability_combo = QComboBox()
        self.probability_combo.addItems(["Low", "Medium", "High"])
        form_layout.addRow("Probability:", self.probability_combo)
        
        self.risk_level_edit = QLineEdit()
        self.risk_level_edit.setReadOnly(True)  # Calculated automatically
        form_layout.addRow("Risk Level:", self.risk_level_edit)
        
        self.mitigation_edit = QPlainTextEdit()
        self.mitigation_edit.setMaximumHeight(100)
        form_layout.addRow("Mitigation:", self.mitigation_edit)
        
        self.verification_edit = QPlainTextEdit()
        self.verification_edit.setMaximumHeight(80)
        form_layout.addRow("Verification:", self.verification_edit)
        
        layout.addLayout(form_layout)
        
        # Connect severity/probability changes to risk level calculation
        self.severity_combo.currentTextChanged.connect(self.calculate_risk_level)
        self.probability_combo.currentTextChanged.connect(self.calculate_risk_level)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def populate_fields(self):
        """Populate fields with risk data."""
        self.id_edit.setText(self.risk_data.get('id', ''))
        self.hazard_edit.setPlainText(self.risk_data.get('hazard', ''))
        self.cause_edit.setPlainText(self.risk_data.get('cause', ''))
        self.effect_edit.setPlainText(self.risk_data.get('effect', ''))
        
        severity = self.risk_data.get('severity', 'Minor')
        if severity in ["Minor", "Serious", "Catastrophic"]:
            self.severity_combo.setCurrentText(severity)
            
        probability = self.risk_data.get('probability', 'Low')
        if probability in ["Low", "Medium", "High"]:
            self.probability_combo.setCurrentText(probability)
            
        self.mitigation_edit.setPlainText(self.risk_data.get('mitigation', ''))
        self.verification_edit.setPlainText(self.risk_data.get('verification', ''))
        
        self.calculate_risk_level()
        
    def calculate_risk_level(self):
        """Calculate risk level based on severity and probability."""
        severity = self.severity_combo.currentText()
        probability = self.probability_combo.currentText()
        
        # Risk matrix calculation
        risk_matrix = {
            ('Minor', 'Low'): 'Low',
            ('Minor', 'Medium'): 'Low',
            ('Minor', 'High'): 'Medium',
            ('Serious', 'Low'): 'Low',
            ('Serious', 'Medium'): 'Medium',
            ('Serious', 'High'): 'High',
            ('Catastrophic', 'Low'): 'Medium',
            ('Catastrophic', 'Medium'): 'High',
            ('Catastrophic', 'High'): 'High'
        }
        
        risk_level = risk_matrix.get((severity, probability), 'Unknown')
        self.risk_level_edit.setText(risk_level)
        
    def get_risk_data(self) -> Dict:
        """Get the edited risk data."""
        return {
            'id': self.id_edit.text(),
            'hazard': self.hazard_edit.toPlainText(),
            'cause': self.cause_edit.toPlainText(),
            'effect': self.effect_edit.toPlainText(),
            'severity': self.severity_combo.currentText(),
            'probability': self.probability_combo.currentText(),
            'risk_level': self.risk_level_edit.text(),
            'mitigation': self.mitigation_edit.toPlainText(),
            'verification': self.verification_edit.toPlainText(),
            'related_requirements': self.risk_data.get('related_requirements', [])
        }


class RiskRegisterTab(QWidget):
    """Tab for displaying and managing risk register."""
    
    risks_updated = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.risks = []
        self.filtered_risks = []
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Initialize the risk register tab UI."""
        layout = QVBoxLayout(self)
        
        # Filter controls
        filter_group = QGroupBox("Filters")
        filter_layout = QHBoxLayout(filter_group)
        
        filter_layout.addWidget(QLabel("Severity:"))
        self.severity_filter = QComboBox()
        self.severity_filter.addItems(["All", "Catastrophic", "Serious", "Minor"])
        filter_layout.addWidget(self.severity_filter)
        
        filter_layout.addWidget(QLabel("Risk Level:"))
        self.risk_level_filter = QComboBox()
        self.risk_level_filter.addItems(["All", "High", "Medium", "Low"])
        filter_layout.addWidget(self.risk_level_filter)
        
        filter_layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search hazards, causes, effects...")
        filter_layout.addWidget(self.search_edit)
        
        self.clear_filters_button = QPushButton("Clear Filters")
        filter_layout.addWidget(self.clear_filters_button)
        
        filter_layout.addStretch()
        layout.addWidget(filter_group)
        
        # Risk management toolbar
        toolbar_layout = QHBoxLayout()
        self.add_risk_button = QPushButton("Add Risk")
        self.edit_risk_button = QPushButton("Edit Risk")
        self.delete_risk_button = QPushButton("Delete Risk")
        toolbar_layout.addWidget(self.add_risk_button)
        toolbar_layout.addWidget(self.edit_risk_button)
        toolbar_layout.addWidget(self.delete_risk_button)
        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)
        
        # Risk table
        self.risk_table = QTableWidget()
        self.risk_table.setColumnCount(9)
        self.risk_table.setHorizontalHeaderLabels([
            "ID", "Hazard", "Cause", "Effect", "Severity", 
            "Probability", "Risk Level", "Mitigation", "Verification"
        ])
        self.risk_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.risk_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.risk_table.setSortingEnabled(True)
        layout.addWidget(self.risk_table)
        
        # Statistics
        stats_layout = QHBoxLayout()
        self.total_risks_label = QLabel("Total Risks: 0")
        self.high_risks_label = QLabel("High: 0")
        self.medium_risks_label = QLabel("Medium: 0")
        self.low_risks_label = QLabel("Low: 0")
        stats_layout.addWidget(self.total_risks_label)
        stats_layout.addWidget(self.high_risks_label)
        stats_layout.addWidget(self.medium_risks_label)
        stats_layout.addWidget(self.low_risks_label)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        # Action buttons
        button_layout = QHBoxLayout()
        self.export_button = QPushButton("Export Risk Register")
        self.save_button = QPushButton("Save Changes")
        self.refresh_button = QPushButton("Refresh")
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.export_button)
        layout.addLayout(button_layout)
        
    def setup_connections(self):
        """Set up signal connections."""
        # Filter connections
        self.severity_filter.currentTextChanged.connect(self.apply_filters)
        self.risk_level_filter.currentTextChanged.connect(self.apply_filters)
        self.search_edit.textChanged.connect(self.apply_filters)
        self.clear_filters_button.clicked.connect(self.clear_filters)
        
        # Risk management connections
        self.add_risk_button.clicked.connect(self.add_risk)
        self.edit_risk_button.clicked.connect(self.edit_risk)
        self.delete_risk_button.clicked.connect(self.delete_risk)
        
        # Table double-click editing
        self.risk_table.doubleClicked.connect(self.edit_risk)
        
        # Save button
        self.save_button.clicked.connect(self.save_changes)
        
    def add_risk(self):
        """Add a new risk item."""
        new_id = f"R-{len(self.risks) + 1:03d}"
        new_risk = {
            'id': new_id,
            'hazard': 'New hazard',
            'cause': 'Cause description',
            'effect': 'Effect description',
            'severity': 'Minor',
            'probability': 'Low',
            'risk_level': 'Low',
            'mitigation': 'Mitigation strategy',
            'verification': 'Verification method',
            'related_requirements': []
        }
        
        dialog = RiskEditDialog(new_risk, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            edited_risk = dialog.get_risk_data()
            self.risks.append(edited_risk)
            self.apply_filters()
            self.update_statistics()
            self.risks_updated.emit({'risks': self.risks})
            
    def edit_risk(self):
        """Edit selected risk item."""
        current_row = self.risk_table.currentRow()
        if current_row >= 0:
            # Find the actual risk in the original list
            risk_id = self.risk_table.item(current_row, 0).text()
            risk_data = next((r for r in self.risks if r['id'] == risk_id), None)
            
            if risk_data:
                dialog = RiskEditDialog(risk_data, self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    edited_risk = dialog.get_risk_data()
                    # Update the risk in the original list
                    for i, risk in enumerate(self.risks):
                        if risk['id'] == risk_id:
                            self.risks[i] = edited_risk
                            break
                    self.apply_filters()
                    self.update_statistics()
                    self.risks_updated.emit({'risks': self.risks})
                    
    def delete_risk(self):
        """Delete selected risk item."""
        current_row = self.risk_table.currentRow()
        if current_row >= 0:
            risk_id = self.risk_table.item(current_row, 0).text()
            reply = QMessageBox.question(
                self, "Delete Risk",
                f"Are you sure you want to delete risk {risk_id}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.risks = [r for r in self.risks if r['id'] != risk_id]
                self.apply_filters()
                self.update_statistics()
                self.risks_updated.emit({'risks': self.risks})
                
    def save_changes(self):
        """Save all changes to risks."""
        self.risks_updated.emit({'risks': self.risks})
        QMessageBox.information(self, "Saved", "Risk register changes have been saved.")
        
    def clear_filters(self):
        """Clear all filters."""
        self.severity_filter.setCurrentText("All")
        self.risk_level_filter.setCurrentText("All")
        self.search_edit.clear()
        
    def apply_filters(self):
        """Apply all active filters to the risk table."""
        filtered_risks = self.risks.copy()
        
        # Apply severity filter
        severity_filter = self.severity_filter.currentText()
        if severity_filter != "All":
            filtered_risks = [r for r in filtered_risks if r.get('severity') == severity_filter]
            
        # Apply risk level filter
        risk_level_filter = self.risk_level_filter.currentText()
        if risk_level_filter != "All":
            filtered_risks = [r for r in filtered_risks if r.get('risk_level') == risk_level_filter]
            
        # Apply search filter
        search_text = self.search_edit.text().lower()
        if search_text:
            filtered_risks = [
                r for r in filtered_risks 
                if (search_text in r.get('hazard', '').lower() or
                    search_text in r.get('cause', '').lower() or
                    search_text in r.get('effect', '').lower() or
                    search_text in r.get('mitigation', '').lower())
            ]
            
        self.filtered_risks = filtered_risks
        self.populate_table(filtered_risks)
        
    def populate_table(self, risks: List[Dict]):
        """Populate the risk table with risk data."""
        self.risk_table.setRowCount(len(risks))
        for i, risk in enumerate(risks):
            self.risk_table.setItem(i, 0, QTableWidgetItem(risk.get('id', '')))
            self.risk_table.setItem(i, 1, QTableWidgetItem(risk.get('hazard', '')))
            self.risk_table.setItem(i, 2, QTableWidgetItem(risk.get('cause', '')))
            self.risk_table.setItem(i, 3, QTableWidgetItem(risk.get('effect', '')))
            
            # Color-code severity
            severity_item = QTableWidgetItem(risk.get('severity', ''))
            if risk.get('severity') == 'Catastrophic':
                severity_item.setBackground(QColor(255, 200, 200))
            elif risk.get('severity') == 'Serious':
                severity_item.setBackground(QColor(255, 255, 200))
            elif risk.get('severity') == 'Minor':
                severity_item.setBackground(QColor(200, 255, 200))
            self.risk_table.setItem(i, 4, severity_item)
            
            # Color-code risk level
            risk_level_item = QTableWidgetItem(risk.get('risk_level', ''))
            if risk.get('risk_level') == 'High':
                risk_level_item.setBackground(QColor(255, 180, 180))
            elif risk.get('risk_level') == 'Medium':
                risk_level_item.setBackground(QColor(255, 255, 180))
            elif risk.get('risk_level') == 'Low':
                risk_level_item.setBackground(QColor(180, 255, 180))
            self.risk_table.setItem(i, 6, risk_level_item)
            
            self.risk_table.setItem(i, 5, QTableWidgetItem(risk.get('probability', '')))
            self.risk_table.setItem(i, 7, QTableWidgetItem(risk.get('mitigation', '')))
            self.risk_table.setItem(i, 8, QTableWidgetItem(risk.get('verification', '')))
            
    def update_statistics(self):
        """Update risk statistics display."""
        total = len(self.risks)
        high = len([r for r in self.risks if r.get('risk_level') == 'High'])
        medium = len([r for r in self.risks if r.get('risk_level') == 'Medium'])
        low = len([r for r in self.risks if r.get('risk_level') == 'Low'])
        
        self.total_risks_label.setText(f"Total Risks: {total}")
        self.high_risks_label.setText(f"High: {high}")
        self.medium_risks_label.setText(f"Medium: {medium}")
        self.low_risks_label.setText(f"Low: {low}")
        
    def update_risks(self, risks: List[Dict]):
        """Update the risk register display."""
        self.risks = risks.copy()
        self.apply_filters()
        self.update_statistics()


class TraceabilityTab(QWidget):
    """Tab for displaying traceability matrix with export capabilities."""
    
    export_requested = pyqtSignal(str)  # export_format
    
    def __init__(self):
        super().__init__()
        self.traceability_data = {}
        self.matrix_rows = []
        self.gaps = []
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Initialize the traceability tab UI."""
        layout = QVBoxLayout(self)
        
        # Filter and view controls
        controls_group = QGroupBox("Matrix Controls")
        controls_layout = QHBoxLayout(controls_group)
        
        controls_layout.addWidget(QLabel("View:"))
        self.view_combo = QComboBox()
        self.view_combo.addItems(["Full Matrix", "Code to Requirements", "Requirements to Risks", "Gap Analysis"])
        controls_layout.addWidget(self.view_combo)
        
        controls_layout.addWidget(QLabel("Filter:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter by file, requirement, or risk...")
        controls_layout.addWidget(self.filter_edit)
        
        self.show_gaps_checkbox = QCheckBox("Show Gaps Only")
        controls_layout.addWidget(self.show_gaps_checkbox)
        
        controls_layout.addStretch()
        layout.addWidget(controls_group)
        
        # Statistics panel
        stats_group = QGroupBox("Traceability Statistics")
        stats_layout = QHBoxLayout(stats_group)
        
        self.total_links_label = QLabel("Total Links: 0")
        self.code_links_label = QLabel("Code Links: 0")
        self.requirement_links_label = QLabel("Requirement Links: 0")
        self.risk_links_label = QLabel("Risk Links: 0")
        self.gaps_label = QLabel("Gaps: 0")
        
        stats_layout.addWidget(self.total_links_label)
        stats_layout.addWidget(self.code_links_label)
        stats_layout.addWidget(self.requirement_links_label)
        stats_layout.addWidget(self.risk_links_label)
        stats_layout.addWidget(self.gaps_label)
        stats_layout.addStretch()
        
        layout.addWidget(stats_group)
        
        # Traceability matrix table
        self.matrix_table = QTableWidget()
        self.matrix_table.setColumnCount(10)
        self.matrix_table.setHorizontalHeaderLabels([
            "Code Reference", "File Path", "Function", "Feature ID", 
            "Feature Description", "User Req ID", "User Requirement",
            "Software Req ID", "Software Requirement", "Risk ID"
        ])
        self.matrix_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.matrix_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.matrix_table.setSortingEnabled(True)
        self.matrix_table.setAlternatingRowColors(True)
        layout.addWidget(self.matrix_table)
        
        # Gap analysis panel (initially hidden)
        self.gaps_group = QGroupBox("Gap Analysis")
        gaps_layout = QVBoxLayout(self.gaps_group)
        
        self.gaps_text = QTextBrowser()
        self.gaps_text.setMaximumHeight(200)
        gaps_layout.addWidget(self.gaps_text)
        
        layout.addWidget(self.gaps_group)
        self.gaps_group.setVisible(False)
        
        # Action buttons
        button_layout = QHBoxLayout()
        self.export_csv_button = QPushButton("Export CSV")
        self.export_excel_button = QPushButton("Export Excel")
        self.export_gaps_button = QPushButton("Export Gap Report")
        self.refresh_button = QPushButton("Refresh")
        
        button_layout.addStretch()
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.export_gaps_button)
        button_layout.addWidget(self.export_csv_button)
        button_layout.addWidget(self.export_excel_button)
        layout.addLayout(button_layout)
        
    def setup_connections(self):
        """Set up signal connections."""
        self.view_combo.currentTextChanged.connect(self.update_view)
        self.filter_edit.textChanged.connect(self.apply_filter)
        self.show_gaps_checkbox.toggled.connect(self.toggle_gaps_view)
        
        self.export_csv_button.clicked.connect(lambda: self.export_requested.emit("csv"))
        self.export_excel_button.clicked.connect(lambda: self.export_requested.emit("excel"))
        self.export_gaps_button.clicked.connect(lambda: self.export_requested.emit("gaps"))
        
    def update_traceability(self, traceability_data: Dict):
        """Update the traceability matrix display."""
        self.traceability_data = traceability_data
        
        # Extract matrix rows and gaps from traceability data
        self.matrix_rows = traceability_data.get('matrix_rows', [])
        self.gaps = traceability_data.get('gaps', [])
        
        # Update statistics
        self.update_statistics()
        
        # Update the current view
        self.update_view()
        
    def update_statistics(self):
        """Update traceability statistics display."""
        matrix = self.traceability_data.get('matrix', {})
        metadata = matrix.get('metadata', {}) if matrix else {}
        
        total_links = metadata.get('total_links', 0)
        code_links = metadata.get('code_feature_links', 0) + metadata.get('code_sr_links', 0)
        req_links = metadata.get('feature_ur_links', 0) + metadata.get('ur_sr_links', 0)
        risk_links = metadata.get('sr_risk_links', 0)
        gaps_count = len(self.gaps)
        
        self.total_links_label.setText(f"Total Links: {total_links}")
        self.code_links_label.setText(f"Code Links: {code_links}")
        self.requirement_links_label.setText(f"Requirement Links: {req_links}")
        self.risk_links_label.setText(f"Risk Links: {risk_links}")
        self.gaps_label.setText(f"Gaps: {gaps_count}")
        
        # Color-code gaps label based on severity
        if gaps_count == 0:
            self.gaps_label.setStyleSheet("color: green;")
        elif gaps_count < 5:
            self.gaps_label.setStyleSheet("color: orange;")
        else:
            self.gaps_label.setStyleSheet("color: red;")
            
    def update_view(self):
        """Update the matrix view based on selected view type."""
        view_type = self.view_combo.currentText()
        
        if view_type == "Gap Analysis":
            self.show_gap_analysis()
        else:
            self.show_matrix_view(view_type)
            
    def show_matrix_view(self, view_type: str):
        """Show the traceability matrix view."""
        self.gaps_group.setVisible(False)
        self.matrix_table.setVisible(True)
        
        # Filter rows based on view type
        filtered_rows = self.filter_rows_by_view(view_type)
        
        # Apply text filter
        if self.filter_edit.text():
            filtered_rows = self.apply_text_filter(filtered_rows)
            
        # Populate table
        self.populate_matrix_table(filtered_rows)
        
    def show_gap_analysis(self):
        """Show the gap analysis view."""
        self.matrix_table.setVisible(False)
        self.gaps_group.setVisible(True)
        
        # Generate gap report
        gap_report = self.generate_gap_report()
        self.gaps_text.setHtml(gap_report)
        
    def filter_rows_by_view(self, view_type: str) -> List[Dict]:
        """Filter matrix rows based on view type."""
        if view_type == "Full Matrix":
            return self.matrix_rows
        elif view_type == "Code to Requirements":
            return [row for row in self.matrix_rows 
                   if row.get('code_reference') and row.get('software_requirement_id')]
        elif view_type == "Requirements to Risks":
            return [row for row in self.matrix_rows 
                   if row.get('software_requirement_id') and row.get('risk_id')]
        else:
            return self.matrix_rows
            
    def apply_text_filter(self, rows: List[Dict]) -> List[Dict]:
        """Apply text filter to rows."""
        filter_text = self.filter_edit.text().lower()
        if not filter_text:
            return rows
            
        filtered = []
        for row in rows:
            # Check if filter text appears in any relevant field
            searchable_fields = [
                'file_path', 'function_name', 'feature_description',
                'user_requirement_text', 'software_requirement_text', 'risk_hazard'
            ]
            
            for field in searchable_fields:
                if filter_text in str(row.get(field, '')).lower():
                    filtered.append(row)
                    break
                    
        return filtered
        
    def apply_filter(self):
        """Apply current filters to the view."""
        self.update_view()
        
    def toggle_gaps_view(self, show_gaps: bool):
        """Toggle between showing all rows or gaps only."""
        if show_gaps:
            self.view_combo.setCurrentText("Gap Analysis")
        else:
            self.update_view()
            
    def populate_matrix_table(self, rows: List[Dict]):
        """Populate the matrix table with filtered rows."""
        self.matrix_table.setRowCount(len(rows))
        
        for i, row in enumerate(rows):
            # Convert row dict to table items
            self.matrix_table.setItem(i, 0, QTableWidgetItem(str(row.get('code_reference', ''))))
            self.matrix_table.setItem(i, 1, QTableWidgetItem(str(row.get('file_path', ''))))
            self.matrix_table.setItem(i, 2, QTableWidgetItem(str(row.get('function_name', ''))))
            self.matrix_table.setItem(i, 3, QTableWidgetItem(str(row.get('feature_id', ''))))
            self.matrix_table.setItem(i, 4, QTableWidgetItem(str(row.get('feature_description', ''))))
            self.matrix_table.setItem(i, 5, QTableWidgetItem(str(row.get('user_requirement_id', ''))))
            self.matrix_table.setItem(i, 6, QTableWidgetItem(str(row.get('user_requirement_text', ''))))
            self.matrix_table.setItem(i, 7, QTableWidgetItem(str(row.get('software_requirement_id', ''))))
            self.matrix_table.setItem(i, 8, QTableWidgetItem(str(row.get('software_requirement_text', ''))))
            self.matrix_table.setItem(i, 9, QTableWidgetItem(str(row.get('risk_id', ''))))
            
            # Color-code rows based on completeness
            confidence = row.get('confidence', 1.0)
            if confidence < 0.5:
                # Low confidence - light red
                for col in range(10):
                    item = self.matrix_table.item(i, col)
                    if item:
                        item.setBackground(QColor(255, 230, 230))
            elif not row.get('risk_id'):
                # Missing risk - light yellow
                for col in range(10):
                    item = self.matrix_table.item(i, col)
                    if item:
                        item.setBackground(QColor(255, 255, 230))
                        
    def generate_gap_report(self) -> str:
        """Generate HTML gap analysis report."""
        if not self.gaps:
            return "<h3>No Traceability Gaps Detected</h3><p>The traceability matrix is complete.</p>"
            
        # Group gaps by severity and type
        high_gaps = [g for g in self.gaps if g.get('severity') == 'high']
        medium_gaps = [g for g in self.gaps if g.get('severity') == 'medium']
        low_gaps = [g for g in self.gaps if g.get('severity') == 'low']
        
        html = []
        html.append("<h3>Traceability Gap Analysis</h3>")
        html.append(f"<p><strong>Total Gaps:</strong> {len(self.gaps)}</p>")
        html.append(f"<p><span style='color: red;'>High: {len(high_gaps)}</span> | ")
        html.append(f"<span style='color: orange;'>Medium: {len(medium_gaps)}</span> | ")
        html.append(f"<span style='color: blue;'>Low: {len(low_gaps)}</span></p>")
        
        for severity, gaps, color in [("High", high_gaps, "red"), ("Medium", medium_gaps, "orange"), ("Low", low_gaps, "blue")]:
            if gaps:
                html.append(f"<h4 style='color: {color};'>{severity} Severity Gaps</h4>")
                html.append("<ul>")
                for gap in gaps:
                    html.append(f"<li><strong>{gap.get('gap_type', '').replace('_', ' ').title()}:</strong> ")
                    html.append(f"{gap.get('description', '')}")
                    if gap.get('recommendation'):
                        html.append(f"<br><em>Recommendation: {gap.get('recommendation')}</em>")
                    html.append("</li>")
                html.append("</ul>")
                
        return "".join(html)
        
    def export_matrix_csv(self) -> str:
        """Export matrix to CSV format."""
        if not self.matrix_rows:
            return ""
            
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "Code Reference", "File Path", "Function", "Feature ID", 
            "Feature Description", "User Req ID", "User Requirement",
            "Software Req ID", "Software Requirement", "Risk ID", "Confidence"
        ])
        
        # Write data rows
        for row in self.matrix_rows:
            writer.writerow([
                row.get('code_reference', ''),
                row.get('file_path', ''),
                row.get('function_name', ''),
                row.get('feature_id', ''),
                row.get('feature_description', ''),
                row.get('user_requirement_id', ''),
                row.get('user_requirement_text', ''),
                row.get('software_requirement_id', ''),
                row.get('software_requirement_text', ''),
                row.get('risk_id', ''),
                row.get('confidence', '')
            ])
            
        return output.getvalue()
        
    def export_gaps_report(self) -> str:
        """Export gap analysis as text report."""
        if not self.gaps:
            return "No traceability gaps detected. Traceability matrix is complete."
            
        lines = []
        lines.append("TRACEABILITY GAP ANALYSIS REPORT")
        lines.append("=" * 40)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Total gaps: {len(self.gaps)}")
        lines.append("")
        
        # Group by severity
        for severity in ['high', 'medium', 'low']:
            severity_gaps = [g for g in self.gaps if g.get('severity') == severity]
            if severity_gaps:
                lines.append(f"{severity.upper()} SEVERITY GAPS ({len(severity_gaps)}):")
                lines.append("-" * 30)
                
                for i, gap in enumerate(severity_gaps, 1):
                    lines.append(f"{i}. {gap.get('description', '')}")
                    lines.append(f"   Type: {gap.get('gap_type', '')}")
                    lines.append(f"   Source: {gap.get('source_type', '')} '{gap.get('source_id', '')}'")
                    if gap.get('target_type') and gap.get('target_id'):
                        lines.append(f"   Target: {gap.get('target_type', '')} '{gap.get('target_id', '')}'")
                    if gap.get('recommendation'):
                        lines.append(f"   Recommendation: {gap.get('recommendation', '')}")
                    lines.append("")
                    
        return "\n".join(lines)


class TestExecutionDialog(QDialog):
    """Dialog for configuring and monitoring test execution."""
    
    def __init__(self, test_suites: List[Dict], parent=None):
        super().__init__(parent)
        self.test_suites = test_suites
        self.execution_thread = None
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize the test execution dialog UI."""
        self.setWindowTitle("Test Execution")
        self.setModal(True)
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Test suite selection
        selection_group = QGroupBox("Test Suite Selection")
        selection_layout = QVBoxLayout(selection_group)
        
        self.suite_checkboxes = {}
        for suite in self.test_suites:
            checkbox = QCheckBox(f"{suite.get('name', 'Unknown')} ({suite.get('test_count', 0)} tests)")
            checkbox.setChecked(True)
            self.suite_checkboxes[suite.get('id', '')] = checkbox
            selection_layout.addWidget(checkbox)
            
        layout.addWidget(selection_group)
        
        # Execution options
        options_group = QGroupBox("Execution Options")
        options_layout = QFormLayout(options_group)
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(30, 3600)
        self.timeout_spin.setValue(300)
        self.timeout_spin.setSuffix(" seconds")
        options_layout.addRow("Timeout:", self.timeout_spin)
        
        self.parallel_checkbox = QCheckBox("Run tests in parallel")
        self.parallel_checkbox.setChecked(True)
        options_layout.addRow("", self.parallel_checkbox)
        
        self.coverage_checkbox = QCheckBox("Generate coverage report")
        self.coverage_checkbox.setChecked(True)
        options_layout.addRow("", self.coverage_checkbox)
        
        self.verbose_checkbox = QCheckBox("Verbose output")
        options_layout.addRow("", self.verbose_checkbox)
        
        layout.addWidget(options_group)
        
        # Progress and output
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.output_text = QTextEdit()
        self.output_text.setMaximumHeight(150)
        self.output_text.setVisible(False)
        layout.addWidget(self.output_text)
        
        # Dialog buttons
        button_box = QDialogButtonBox()
        self.run_button = QPushButton("Run Tests")
        self.cancel_button = QPushButton("Cancel")
        self.close_button = QPushButton("Close")
        
        button_box.addButton(self.run_button, QDialogButtonBox.ButtonRole.ActionRole)
        button_box.addButton(self.cancel_button, QDialogButtonBox.ButtonRole.RejectRole)
        button_box.addButton(self.close_button, QDialogButtonBox.ButtonRole.AcceptRole)
        
        self.run_button.clicked.connect(self.start_execution)
        self.cancel_button.clicked.connect(self.cancel_execution)
        self.close_button.clicked.connect(self.accept)
        
        layout.addWidget(button_box)
        
        # Initially hide cancel button
        self.cancel_button.setVisible(False)
        
    def start_execution(self):
        """Start test execution."""
        # Get selected test suites
        selected_suites = []
        for suite_id, checkbox in self.suite_checkboxes.items():
            if checkbox.isChecked():
                suite = next((s for s in self.test_suites if s.get('id') == suite_id), None)
                if suite:
                    selected_suites.append(suite)
                    
        if not selected_suites:
            QMessageBox.warning(self, "No Tests Selected", "Please select at least one test suite to run.")
            return
            
        # Show progress UI
        self.progress_bar.setVisible(True)
        self.output_text.setVisible(True)
        self.run_button.setVisible(False)
        self.cancel_button.setVisible(True)
        
        # Start execution (mock implementation)
        self.mock_test_execution(selected_suites)
        
    def mock_test_execution(self, selected_suites: List[Dict]):
        """Mock test execution for demonstration."""
        self.progress_bar.setRange(0, 100)
        self.output_text.append("Starting test execution...")
        
        total_tests = sum(suite.get('test_count', 0) for suite in selected_suites)
        self.output_text.append(f"Running {total_tests} tests from {len(selected_suites)} suites...")
        
        # Simulate progress
        import time
        for i in range(0, 101, 10):
            self.progress_bar.setValue(i)
            if i < 100:
                self.output_text.append(f"Progress: {i}% - Running tests...")
            else:
                self.output_text.append("Test execution completed!")
            QApplication.processEvents()
            time.sleep(0.1)
            
        # Show completion
        self.run_button.setVisible(True)
        self.cancel_button.setVisible(False)
        self.run_button.setText("Run Again")
        
    def cancel_execution(self):
        """Cancel test execution."""
        self.output_text.append("Test execution cancelled by user.")
        self.run_button.setVisible(True)
        self.cancel_button.setVisible(False)
        self.progress_bar.setVisible(False)


class TestingResultsTab(QWidget):
    """Tab for displaying test results with execution controls."""
    
    test_execution_requested = pyqtSignal(dict)  # execution_config
    export_requested = pyqtSignal(str)  # export_format
    
    def __init__(self):
        super().__init__()
        self.test_results = {}
        self.test_suites = []
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Initialize the test results tab UI."""
        layout = QVBoxLayout(self)
        
        # Test execution controls
        execution_group = QGroupBox("Test Execution")
        execution_layout = QHBoxLayout(execution_group)
        
        self.run_all_button = QPushButton("Run All Tests")
        self.run_selected_button = QPushButton("Run Selected")
        self.configure_button = QPushButton("Configure & Run")
        self.stop_button = QPushButton("Stop Execution")
        self.stop_button.setEnabled(False)
        
        execution_layout.addWidget(self.run_all_button)
        execution_layout.addWidget(self.run_selected_button)
        execution_layout.addWidget(self.configure_button)
        execution_layout.addWidget(self.stop_button)
        execution_layout.addStretch()
        
        layout.addWidget(execution_group)
        
        # Test summary with enhanced metrics
        summary_group = QGroupBox("Test Summary")
        summary_layout = QVBoxLayout(summary_group)
        
        # Main metrics row
        metrics_layout = QHBoxLayout()
        self.total_tests_label = QLabel("Total Tests: 0")
        self.passed_tests_label = QLabel("Passed: 0")
        self.failed_tests_label = QLabel("Failed: 0")
        self.skipped_tests_label = QLabel("Skipped: 0")
        self.coverage_label = QLabel("Coverage: 0%")
        
        metrics_layout.addWidget(self.total_tests_label)
        metrics_layout.addWidget(self.passed_tests_label)
        metrics_layout.addWidget(self.failed_tests_label)
        metrics_layout.addWidget(self.skipped_tests_label)
        metrics_layout.addWidget(self.coverage_label)
        metrics_layout.addStretch()
        
        summary_layout.addLayout(metrics_layout)
        
        # Execution status row
        status_layout = QHBoxLayout()
        self.execution_status_label = QLabel("Status: Ready")
        self.execution_time_label = QLabel("Execution Time: --")
        self.last_run_label = QLabel("Last Run: Never")
        
        status_layout.addWidget(self.execution_status_label)
        status_layout.addWidget(self.execution_time_label)
        status_layout.addWidget(self.last_run_label)
        status_layout.addStretch()
        
        summary_layout.addLayout(status_layout)
        layout.addWidget(summary_group)
        
        # Test suites and results
        results_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Test suites list
        suites_group = QGroupBox("Test Suites")
        suites_layout = QVBoxLayout(suites_group)
        
        self.suites_table = QTableWidget()
        self.suites_table.setColumnCount(5)
        self.suites_table.setHorizontalHeaderLabels(["Suite", "Tests", "Passed", "Failed", "Status"])
        self.suites_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.suites_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        suites_layout.addWidget(self.suites_table)
        
        results_splitter.addWidget(suites_group)
        
        # Test details and output
        details_group = QGroupBox("Test Details")
        details_layout = QVBoxLayout(details_group)
        
        # Tab widget for different views
        self.details_tabs = QTabWidget()
        
        # Test output tab
        self.test_output = QTextEdit()
        self.test_output.setReadOnly(True)
        self.test_output.setFont(QFont("Consolas", 9))
        self.details_tabs.addTab(self.test_output, "Output")
        
        # Failed tests tab
        self.failed_tests_table = QTableWidget()
        self.failed_tests_table.setColumnCount(4)
        self.failed_tests_table.setHorizontalHeaderLabels(["Test", "Suite", "Error", "File"])
        self.failed_tests_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.details_tabs.addTab(self.failed_tests_table, "Failed Tests")
        
        # Coverage report tab
        self.coverage_text = QTextBrowser()
        self.details_tabs.addTab(self.coverage_text, "Coverage")
        
        details_layout.addWidget(self.details_tabs)
        results_splitter.addWidget(details_group)
        
        results_splitter.setSizes([300, 500])
        layout.addWidget(results_splitter)
        
        # Action buttons
        button_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh")
        self.export_results_button = QPushButton("Export Results")
        self.export_coverage_button = QPushButton("Export Coverage")
        self.view_logs_button = QPushButton("View Logs")
        
        button_layout.addStretch()
        button_layout.addWidget(self.view_logs_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.export_coverage_button)
        button_layout.addWidget(self.export_results_button)
        layout.addLayout(button_layout)
        
    def setup_connections(self):
        """Set up signal connections."""
        self.run_all_button.clicked.connect(self.run_all_tests)
        self.run_selected_button.clicked.connect(self.run_selected_tests)
        self.configure_button.clicked.connect(self.configure_and_run)
        self.stop_button.clicked.connect(self.stop_execution)
        
        self.suites_table.itemSelectionChanged.connect(self.on_suite_selection_changed)
        self.failed_tests_table.itemDoubleClicked.connect(self.on_failed_test_double_clicked)
        
        self.export_results_button.clicked.connect(lambda: self.export_requested.emit("results"))
        self.export_coverage_button.clicked.connect(lambda: self.export_requested.emit("coverage"))
        
    def run_all_tests(self):
        """Run all available test suites."""
        config = {
            'suites': [suite.get('id') for suite in self.test_suites],
            'timeout': 300,
            'parallel': True,
            'coverage': True,
            'verbose': False
        }
        self.test_execution_requested.emit(config)
        self.set_execution_status("Running", True)
        
    def run_selected_tests(self):
        """Run selected test suites."""
        selected_rows = set(item.row() for item in self.suites_table.selectedItems())
        if not selected_rows:
            QMessageBox.information(self, "No Selection", "Please select test suites to run.")
            return
            
        selected_suites = [self.test_suites[row].get('id') for row in selected_rows 
                          if row < len(self.test_suites)]
        
        config = {
            'suites': selected_suites,
            'timeout': 300,
            'parallel': True,
            'coverage': True,
            'verbose': False
        }
        self.test_execution_requested.emit(config)
        self.set_execution_status("Running", True)
        
    def configure_and_run(self):
        """Open configuration dialog and run tests."""
        dialog = TestExecutionDialog(self.test_suites, self)
        dialog.exec()
        
    def stop_execution(self):
        """Stop test execution."""
        # Signal to stop execution
        self.test_execution_requested.emit({'action': 'stop'})
        self.set_execution_status("Stopped", False)
        
    def set_execution_status(self, status: str, running: bool):
        """Update execution status and button states."""
        self.execution_status_label.setText(f"Status: {status}")
        
        # Update button states
        self.run_all_button.setEnabled(not running)
        self.run_selected_button.setEnabled(not running)
        self.configure_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        
        if running:
            self.execution_status_label.setStyleSheet("color: blue;")
        elif status == "Completed":
            self.execution_status_label.setStyleSheet("color: green;")
        elif status == "Failed" or status == "Stopped":
            self.execution_status_label.setStyleSheet("color: red;")
        else:
            self.execution_status_label.setStyleSheet("")
            
    def on_suite_selection_changed(self):
        """Handle test suite selection change."""
        selected_rows = set(item.row() for item in self.suites_table.selectedItems())
        if selected_rows and len(selected_rows) == 1:
            row = list(selected_rows)[0]
            if row < len(self.test_suites):
                suite = self.test_suites[row]
                self.show_suite_details(suite)
                
    def show_suite_details(self, suite: Dict):
        """Show details for selected test suite."""
        output = suite.get('output', 'No output available for this test suite.')
        self.test_output.setPlainText(output)
        
        # Update failed tests table
        failed_tests = suite.get('failed_test_details', [])
        self.failed_tests_table.setRowCount(len(failed_tests))
        
        for i, test in enumerate(failed_tests):
            self.failed_tests_table.setItem(i, 0, QTableWidgetItem(test.get('name', '')))
            self.failed_tests_table.setItem(i, 1, QTableWidgetItem(suite.get('name', '')))
            self.failed_tests_table.setItem(i, 2, QTableWidgetItem(test.get('error', '')))
            self.failed_tests_table.setItem(i, 3, QTableWidgetItem(test.get('file', '')))
            
    def on_failed_test_double_clicked(self, item):
        """Handle double-click on failed test."""
        row = item.row()
        if row < self.failed_tests_table.rowCount():
            test_name = self.failed_tests_table.item(row, 0).text()
            file_path = self.failed_tests_table.item(row, 3).text()
            error = self.failed_tests_table.item(row, 2).text()
            
            # Show detailed error dialog
            QMessageBox.information(
                self, f"Test Failure: {test_name}",
                f"File: {file_path}\n\nError:\n{error}"
            )
            
    def update_test_results(self, test_results: Dict):
        """Update the test results display."""
        self.test_results = test_results
        
        # Update summary metrics
        total = test_results.get('total_tests', 0)
        passed = test_results.get('passed_tests', 0)
        failed = test_results.get('failed_tests', 0)
        skipped = test_results.get('skipped_tests', 0)
        coverage = test_results.get('coverage', 0)
        
        self.total_tests_label.setText(f"Total Tests: {total}")
        self.passed_tests_label.setText(f"Passed: {passed}")
        self.failed_tests_label.setText(f"Failed: {failed}")
        self.skipped_tests_label.setText(f"Skipped: {skipped}")
        self.coverage_label.setText(f"Coverage: {coverage}%")
        
        # Color-code metrics
        if failed > 0:
            self.failed_tests_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.failed_tests_label.setStyleSheet("color: green;")
            
        if coverage < 70:
            self.coverage_label.setStyleSheet("color: red;")
        elif coverage < 85:
            self.coverage_label.setStyleSheet("color: orange;")
        else:
            self.coverage_label.setStyleSheet("color: green;")
            
        # Update execution info
        execution_time = test_results.get('execution_time', 0)
        last_run = test_results.get('last_run', 'Never')
        
        self.execution_time_label.setText(f"Execution Time: {execution_time:.1f}s")
        self.last_run_label.setText(f"Last Run: {last_run}")
        
        # Update test suites
        self.test_suites = test_results.get('test_suites', [])
        self.update_suites_table()
        
        # Update details
        self.test_output.setPlainText(test_results.get('output', 'No test output available'))
        
        # Update coverage report
        coverage_report = test_results.get('coverage_report', 'No coverage report available')
        self.coverage_text.setPlainText(coverage_report)
        
        # Update execution status
        status = test_results.get('status', 'Completed')
        self.set_execution_status(status, False)
        
    def update_suites_table(self):
        """Update the test suites table."""
        self.suites_table.setRowCount(len(self.test_suites))
        
        for i, suite in enumerate(self.test_suites):
            self.suites_table.setItem(i, 0, QTableWidgetItem(suite.get('name', '')))
            self.suites_table.setItem(i, 1, QTableWidgetItem(str(suite.get('total_tests', 0))))
            self.suites_table.setItem(i, 2, QTableWidgetItem(str(suite.get('passed_tests', 0))))
            self.suites_table.setItem(i, 3, QTableWidgetItem(str(suite.get('failed_tests', 0))))
            
            # Status with color coding
            status = suite.get('status', 'Unknown')
            status_item = QTableWidgetItem(status)
            
            if status == 'Passed':
                status_item.setBackground(QColor(200, 255, 200))
            elif status == 'Failed':
                status_item.setBackground(QColor(255, 200, 200))
            elif status == 'Running':
                status_item.setBackground(QColor(200, 200, 255))
                
            self.suites_table.setItem(i, 4, status_item)


class SummaryTab(QWidget):
    """Tab for displaying analysis summary."""
    
    def __init__(self):
        super().__init__()
        self.summary_data = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize the summary tab UI."""
        layout = QVBoxLayout(self)
        
        # Project info
        project_group = QGroupBox("Project Information")
        project_layout = QVBoxLayout(project_group)
        
        self.project_path_label = QLabel("Project Path: Not set")
        self.files_analyzed_label = QLabel("Files Analyzed: 0")
        self.analysis_date_label = QLabel("Analysis Date: Not set")
        
        project_layout.addWidget(self.project_path_label)
        project_layout.addWidget(self.files_analyzed_label)
        project_layout.addWidget(self.analysis_date_label)
        
        layout.addWidget(project_group)
        
        # Analysis metrics
        metrics_group = QGroupBox("Analysis Metrics")
        metrics_layout = QVBoxLayout(metrics_group)
        
        self.features_found_label = QLabel("Features Found: 0")
        self.requirements_generated_label = QLabel("Requirements Generated: 0")
        self.risks_identified_label = QLabel("Risks Identified: 0")
        self.confidence_label = QLabel("Overall Confidence: 0%")
        
        metrics_layout.addWidget(self.features_found_label)
        metrics_layout.addWidget(self.requirements_generated_label)
        metrics_layout.addWidget(self.risks_identified_label)
        metrics_layout.addWidget(self.confidence_label)
        
        layout.addWidget(metrics_group)
        
        # Errors and warnings
        self.errors_group = QGroupBox("Errors and Warnings")
        errors_layout = QVBoxLayout(self.errors_group)
        
        self.errors_text = QTextEdit()
        self.errors_text.setReadOnly(True)
        self.errors_text.setMaximumHeight(150)
        errors_layout.addWidget(self.errors_text)
        
        layout.addWidget(self.errors_group)
        layout.addStretch()
        
        # Initially hide errors section
        self.errors_group.setVisible(False)
        
    def update_summary(self, summary_data: Dict):
        """Update the summary display."""
        self.summary_data = summary_data
        
        # Update project info
        self.project_path_label.setText(f"Project Path: {summary_data.get('project_path', 'Not set')}")
        self.files_analyzed_label.setText(f"Files Analyzed: {summary_data.get('files_analyzed', 0)}")
        self.analysis_date_label.setText(f"Analysis Date: {summary_data.get('analysis_date', 'Not set')}")
        
        # Update metrics
        self.features_found_label.setText(f"Features Found: {summary_data.get('features_found', 0)}")
        self.requirements_generated_label.setText(f"Requirements Generated: {summary_data.get('requirements_generated', 0)}")
        self.risks_identified_label.setText(f"Risks Identified: {summary_data.get('risks_identified', 0)}")
        self.confidence_label.setText(f"Overall Confidence: {summary_data.get('confidence', 0)}%")
        
        # Update errors and warnings
        errors = summary_data.get('errors', [])
        warnings = summary_data.get('warnings', [])
        
        if errors or warnings:
            error_text = ""
            if errors:
                error_text += "ERRORS:\n" + "\n".join(f"• {error}" for error in errors) + "\n\n"
            if warnings:
                error_text += "WARNINGS:\n" + "\n".join(f"• {warning}" for warning in warnings)
            self.errors_text.setPlainText(error_text)
            self.errors_group.setVisible(True)
        else:
            self.errors_group.setVisible(False)


class ResultsTabWidget(QTabWidget):
    """Main results tab widget containing all analysis result tabs."""
    
    # Signals
    export_requested = pyqtSignal(str, str)  # tab_name, export_type
    refresh_requested = pyqtSignal(str)  # tab_name
    
    def __init__(self, soup_service: Optional[SOUPService] = None):
        super().__init__()
        self.analysis_results = {}
        self.soup_service = soup_service
        self.setup_tabs()
        self.setup_connections()
        
    def setup_tabs(self):
        """Initialize all result tabs."""
        # Summary tab
        self.summary_tab = SummaryTab()
        self.addTab(self.summary_tab, "Summary")
        
        # Requirements tab
        self.requirements_tab = RequirementsTab()
        self.addTab(self.requirements_tab, "Requirements")
        
        # Risk register tab
        self.risk_tab = RiskRegisterTab()
        self.addTab(self.risk_tab, "Risk Register")
        
        # Traceability tab
        self.traceability_tab = TraceabilityTab()
        self.addTab(self.traceability_tab, "Traceability")
        
        # Test results tab
        self.test_tab = TestingResultsTab()
        self.addTab(self.test_tab, "Tests")
        
        # SOUP inventory tab
        if self.soup_service:
            self.soup_tab = SOUPWidget(self.soup_service)
            self.addTab(self.soup_tab, "SOUP")
        else:
            self.soup_tab = None
        
        # Initially disable all tabs
        self.setEnabled(False)
        
    def setup_connections(self):
        """Set up signal-slot connections."""
        # Connect export buttons from requirements tab
        self.requirements_tab.export_button.clicked.connect(
            lambda: self.export_requested.emit("requirements", "csv")
        )
        
        # Connect export buttons from risk tab
        self.risk_tab.export_button.clicked.connect(
            lambda: self.export_requested.emit("risks", "csv")
        )
        
        # Connect export signals from traceability tab
        self.traceability_tab.export_requested.connect(
            lambda format: self.export_requested.emit("traceability", format)
        )
        
        # Connect export signals from test tab
        self.test_tab.export_requested.connect(
            lambda format: self.export_requested.emit("tests", format)
        )
        
        # Connect test execution signal
        self.test_tab.test_execution_requested.connect(
            lambda config: self.export_requested.emit("test_execution", str(config))
        )
        
        # Connect refresh buttons
        self.requirements_tab.refresh_button.clicked.connect(
            lambda: self.refresh_requested.emit("requirements")
        )
        self.risk_tab.refresh_button.clicked.connect(
            lambda: self.refresh_requested.emit("risks")
        )
        self.traceability_tab.refresh_button.clicked.connect(
            lambda: self.refresh_requested.emit("traceability")
        )
        self.test_tab.refresh_button.clicked.connect(
            lambda: self.refresh_requested.emit("tests")
        )
        
        # Connect data update signals from editable tabs
        self.requirements_tab.requirements_updated.connect(self.on_requirements_updated)
        self.risk_tab.risks_updated.connect(self.on_risks_updated)
        
        # Connect SOUP tab signals if available
        if self.soup_tab:
            self.soup_tab.component_added.connect(self.on_soup_component_added)
            self.soup_tab.component_updated.connect(self.on_soup_component_updated)
            self.soup_tab.component_deleted.connect(self.on_soup_component_deleted)
        
    def update_results(self, results: Dict[str, Any]):
        """Update all tabs with analysis results."""
        self.analysis_results = results
        
        # Enable the widget
        self.setEnabled(True)
        
        # Update each tab
        if 'summary' in results:
            self.summary_tab.update_summary(results['summary'])
            
        if 'requirements' in results:
            req_data = results['requirements']
            self.requirements_tab.update_requirements(
                req_data.get('user_requirements', []),
                req_data.get('software_requirements', [])
            )
            
        if 'risks' in results:
            self.risk_tab.update_risks(results['risks'])
            
        if 'traceability' in results:
            self.traceability_tab.update_traceability(results['traceability'])
            
        if 'tests' in results:
            self.test_tab.update_test_results(results['tests'])
            
        # SOUP tab doesn't need updates from analysis results
        # as it's managed independently by the user
            
    def clear_results(self):
        """Clear all results and disable the widget."""
        self.analysis_results = {}
        self.setEnabled(False)
        
        # Clear individual tabs
        self.summary_tab.update_summary({})
        self.requirements_tab.update_requirements([], [])
        self.risk_tab.update_risks([])
        self.traceability_tab.update_traceability({})
        self.test_tab.update_test_results({})
        
    def show_partial_results(self, results: Dict[str, Any], errors: List[str]):
        """Show partial results with error information."""
        # Add error information to summary
        if 'summary' not in results:
            results['summary'] = {}
        results['summary']['errors'] = errors
        
        # Update with partial results
        self.update_results(results)
        
        # Show warning message
        QMessageBox.warning(
            self, "Partial Results",
            f"Analysis completed with {len(errors)} error(s). "
            "Some results may be incomplete. Check the Summary tab for details."
        )
        
    def get_current_tab_name(self) -> str:
        """Get the name of the currently active tab."""
        return self.tabText(self.currentIndex())
        
    def on_requirements_updated(self, data: Dict):
        """Handle requirements update from requirements tab."""
        # Update internal data and emit signal for persistence
        if 'user_requirements' in data:
            self.analysis_results.setdefault('requirements', {})['user_requirements'] = data['user_requirements']
        if 'software_requirements' in data:
            self.analysis_results.setdefault('requirements', {})['software_requirements'] = data['software_requirements']
            
    def on_risks_updated(self, data: Dict):
        """Handle risks update from risk tab."""
        # Update internal data and emit signal for persistence
        if 'risks' in data:
            self.analysis_results['risks'] = data['risks']
            
    def export_data(self, tab_name: str, export_format: str) -> Optional[str]:
        """Export data from specified tab in requested format."""
        try:
            if tab_name == "requirements" and export_format == "csv":
                return self._export_requirements_csv()
            elif tab_name == "risks" and export_format == "csv":
                return self._export_risks_csv()
            elif tab_name == "traceability":
                if export_format == "csv":
                    return self.traceability_tab.export_matrix_csv()
                elif export_format == "excel":
                    return self._export_traceability_excel()
                elif export_format == "gaps":
                    return self.traceability_tab.export_gaps_report()
            elif tab_name == "tests":
                if export_format == "results":
                    return self._export_test_results()
                elif export_format == "coverage":
                    return self._export_test_coverage()
            return None
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export {tab_name} data: {str(e)}")
            return None
            
    def _export_requirements_csv(self) -> str:
        """Export requirements to CSV format."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Export User Requirements
        writer.writerow(["USER REQUIREMENTS"])
        writer.writerow(["ID", "Description", "Acceptance Criteria"])
        
        for req in self.requirements_tab.user_requirements:
            criteria = "; ".join(req.get('acceptance_criteria', []))
            writer.writerow([req.get('id', ''), req.get('description', ''), criteria])
            
        writer.writerow([])  # Empty row
        
        # Export Software Requirements
        writer.writerow(["SOFTWARE REQUIREMENTS"])
        writer.writerow(["ID", "Description", "Derived From", "Code References"])
        
        for req in self.requirements_tab.software_requirements:
            derived_from = "; ".join(req.get('derived_from', []))
            code_refs = str(len(req.get('code_references', [])))
            writer.writerow([req.get('id', ''), req.get('description', ''), derived_from, code_refs])
            
        return output.getvalue()
        
    def _export_risks_csv(self) -> str:
        """Export risks to CSV format."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "ID", "Hazard", "Cause", "Effect", "Severity", 
            "Probability", "Risk Level", "Mitigation", "Verification"
        ])
        
        # Write risk data
        for risk in self.risk_tab.risks:
            writer.writerow([
                risk.get('id', ''),
                risk.get('hazard', ''),
                risk.get('cause', ''),
                risk.get('effect', ''),
                risk.get('severity', ''),
                risk.get('probability', ''),
                risk.get('risk_level', ''),
                risk.get('mitigation', ''),
                risk.get('verification', '')
            ])
            
        return output.getvalue()
        
    def _export_traceability_excel(self) -> str:
        """Export traceability matrix to Excel format (returns CSV for now)."""
        # For now, return CSV format. In a full implementation, 
        # this would use openpyxl or similar to create Excel files
        return self.traceability_tab.export_matrix_csv()
        
    def _export_test_results(self) -> str:
        """Export test results to text format."""
        lines = []
        lines.append("TEST EXECUTION RESULTS")
        lines.append("=" * 30)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Summary
        results = self.test_tab.test_results
        lines.append("SUMMARY:")
        lines.append(f"Total Tests: {results.get('total_tests', 0)}")
        lines.append(f"Passed: {results.get('passed_tests', 0)}")
        lines.append(f"Failed: {results.get('failed_tests', 0)}")
        lines.append(f"Skipped: {results.get('skipped_tests', 0)}")
        lines.append(f"Coverage: {results.get('coverage', 0)}%")
        lines.append(f"Execution Time: {results.get('execution_time', 0):.1f}s")
        lines.append("")
        
        # Test suites
        lines.append("TEST SUITES:")
        lines.append("-" * 15)
        for suite in self.test_tab.test_suites:
            lines.append(f"Suite: {suite.get('name', 'Unknown')}")
            lines.append(f"  Tests: {suite.get('total_tests', 0)}")
            lines.append(f"  Passed: {suite.get('passed_tests', 0)}")
            lines.append(f"  Failed: {suite.get('failed_tests', 0)}")
            lines.append(f"  Status: {suite.get('status', 'Unknown')}")
            lines.append("")
            
        # Failed tests details
        failed_tests = []
        for suite in self.test_tab.test_suites:
            suite_failed_tests = suite.get('failed_test_details', [])
            if isinstance(suite_failed_tests, list):
                failed_tests.extend(suite_failed_tests)
            
        if failed_tests:
            lines.append("FAILED TESTS:")
            lines.append("-" * 15)
            for test in failed_tests:
                lines.append(f"Test: {test.get('name', 'Unknown')}")
                lines.append(f"Error: {test.get('error', 'No error details')}")
                lines.append(f"File: {test.get('file', 'Unknown')}")
                lines.append("")
                
        return "\n".join(lines)
        
    def _export_test_coverage(self) -> str:
        """Export test coverage report."""
        coverage_report = self.test_tab.test_results.get('coverage_report', 'No coverage report available')
        
        lines = []
        lines.append("TEST COVERAGE REPORT")
        lines.append("=" * 25)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append(coverage_report)
        
        return "\n".join(lines)
        
    def save_export_file(self, content: str, filename: str, file_filter: str = "All Files (*.*)"):
        """Save exported content to file with file dialog."""
        if not content:
            QMessageBox.warning(self, "Export Warning", "No data to export.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Export", filename, file_filter
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                QMessageBox.information(self, "Export Successful", f"Data exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to save file:\n{str(e)}")
    
    def on_soup_component_added(self, component):
        """Handle SOUP component addition."""
        # Update analysis results to include SOUP data
        if 'soup' not in self.analysis_results:
            self.analysis_results['soup'] = []
        self.analysis_results['soup'].append(component)
    
    def on_soup_component_updated(self, component):
        """Handle SOUP component update."""
        # Update the component in analysis results
        if 'soup' in self.analysis_results:
            for i, existing_component in enumerate(self.analysis_results['soup']):
                if existing_component.id == component.id:
                    self.analysis_results['soup'][i] = component
                    break
    
    def on_soup_component_deleted(self, component_id):
        """Handle SOUP component deletion."""
        # Remove the component from analysis results
        if 'soup' in self.analysis_results:
            self.analysis_results['soup'] = [
                comp for comp in self.analysis_results['soup'] 
                if comp.id != component_id
            ]