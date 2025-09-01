"""
Enhanced SOUP (Software of Unknown Provenance) inventory management widget.
Includes automatic detection, IEC 62304 compliance management, and bulk operations.
"""

import uuid
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QDialog, QFormLayout, QLineEdit, QTextEdit, QComboBox,
    QDateEdit, QMessageBox, QHeaderView, QLabel, QGroupBox, QSplitter,
    QFrame, QScrollArea, QTabWidget, QProgressBar, QCheckBox, QFileDialog,
    QTreeWidget, QTreeWidgetItem, QSpinBox, QPlainTextEdit, QApplication
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap, QPainter

from ..models.core import SOUPComponent
from ..models.soup_models import DetectedSOUPComponent, IEC62304SafetyClass, IEC62304Classification
from ..services.soup_service import SOUPService
from ..services.soup_detector import SOUPDetector


class DetectionWorker(QThread):
    """Worker thread for SOUP component detection."""
    
    detection_finished = pyqtSignal(list)  # List[DetectedSOUPComponent]
    detection_error = pyqtSignal(str)
    detection_progress = pyqtSignal(str)
    
    def __init__(self, project_path: str, soup_detector: SOUPDetector):
        super().__init__()
        self.project_path = project_path
        self.soup_detector = soup_detector
    
    def run(self):
        """Run detection in background thread."""
        try:
            self.detection_progress.emit("Scanning project for dependency files...")
            detected_components = self.soup_detector.detect_soup_components(self.project_path)
            
            self.detection_progress.emit(f"Found {len(detected_components)} components")
            self.detection_finished.emit(detected_components)
        except Exception as e:
            self.detection_error.emit(str(e))


class ClassificationDialog(QDialog):
    """Dialog for managing IEC 62304 classification of SOUP components."""
    
    def __init__(self, parent=None, component: Optional[SOUPComponent] = None, 
                 classification: Optional[IEC62304Classification] = None):
        super().__init__(parent)
        self.component = component
        self.classification = classification
        
        self.setWindowTitle("IEC 62304 Classification")
        self.setModal(True)
        self.resize(800, 600)
        
        self.setup_ui()
        
        if self.classification:
            self.populate_fields()
    
    def setup_ui(self):
        """Set up the classification dialog UI."""
        layout = QVBoxLayout(self)
        
        # Component info
        if self.component:
            info_group = QGroupBox(f"Component: {self.component.name} v{self.component.version}")
            info_layout = QFormLayout(info_group)
            
            info_layout.addRow("Usage Reason:", QLabel(self.component.usage_reason))
            if self.component.supplier:
                info_layout.addRow("Supplier:", QLabel(self.component.supplier))
            
            layout.addWidget(info_group)
        
        # Classification form
        form_group = QGroupBox("IEC 62304 Classification")
        form_layout = QFormLayout(form_group)
        
        # Safety class
        self.safety_class_combo = QComboBox()
        self.safety_class_combo.addItems([
            "Class A - No safety impact",
            "Class B - Non-life-supporting, injury possible", 
            "Class C - Life-supporting or life-sustaining"
        ])
        form_layout.addRow("Safety Class*:", self.safety_class_combo)
        
        # Justification
        self.justification_edit = QTextEdit()
        self.justification_edit.setMaximumHeight(100)
        self.justification_edit.setPlaceholderText("Provide justification for this safety classification...")
        form_layout.addRow("Justification*:", self.justification_edit)
        
        # Risk assessment
        self.risk_assessment_edit = QTextEdit()
        self.risk_assessment_edit.setMaximumHeight(100)
        self.risk_assessment_edit.setPlaceholderText("Describe potential risks and their impact...")
        form_layout.addRow("Risk Assessment*:", self.risk_assessment_edit)
        
        layout.addWidget(form_group)
        
        # Requirements
        req_group = QGroupBox("Requirements")
        req_layout = QVBoxLayout(req_group)
        
        # Verification requirements
        req_layout.addWidget(QLabel("Verification Requirements:"))
        self.verification_edit = QPlainTextEdit()
        self.verification_edit.setMaximumHeight(80)
        self.verification_edit.setPlaceholderText("List verification requirements, one per line...")
        req_layout.addWidget(self.verification_edit)
        
        # Documentation requirements
        req_layout.addWidget(QLabel("Documentation Requirements:"))
        self.documentation_edit = QPlainTextEdit()
        self.documentation_edit.setMaximumHeight(80)
        self.documentation_edit.setPlaceholderText("List documentation requirements, one per line...")
        req_layout.addWidget(self.documentation_edit)
        
        layout.addWidget(req_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.save_button = QPushButton("Save Classification")
        self.save_button.clicked.connect(self.accept)
        self.save_button.setDefault(True)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
    
    def populate_fields(self):
        """Populate form fields with classification data."""
        if not self.classification:
            return
        
        # Set safety class
        class_index = {
            IEC62304SafetyClass.CLASS_A: 0,
            IEC62304SafetyClass.CLASS_B: 1,
            IEC62304SafetyClass.CLASS_C: 2
        }.get(self.classification.safety_class, 1)
        self.safety_class_combo.setCurrentIndex(class_index)
        
        # Set text fields
        self.justification_edit.setPlainText(self.classification.justification)
        self.risk_assessment_edit.setPlainText(self.classification.risk_assessment)
        
        # Set requirements
        if self.classification.verification_requirements:
            self.verification_edit.setPlainText("\n".join(self.classification.verification_requirements))
        
        if self.classification.documentation_requirements:
            self.documentation_edit.setPlainText("\n".join(self.classification.documentation_requirements))
    
    def get_classification_data(self) -> IEC62304Classification:
        """Get classification data from form fields."""
        # Map combo box index to safety class
        safety_classes = [
            IEC62304SafetyClass.CLASS_A,
            IEC62304SafetyClass.CLASS_B,
            IEC62304SafetyClass.CLASS_C
        ]
        safety_class = safety_classes[self.safety_class_combo.currentIndex()]
        
        # Parse requirements
        verification_reqs = [
            line.strip() for line in self.verification_edit.toPlainText().split('\n')
            if line.strip()
        ]
        
        documentation_reqs = [
            line.strip() for line in self.documentation_edit.toPlainText().split('\n')
            if line.strip()
        ]
        
        return IEC62304Classification(
            safety_class=safety_class,
            justification=self.justification_edit.toPlainText().strip(),
            risk_assessment=self.risk_assessment_edit.toPlainText().strip(),
            verification_requirements=verification_reqs,
            documentation_requirements=documentation_reqs,
            change_control_requirements=[]  # Could be added in future
        )
    
    def validate_form(self) -> List[str]:
        """Validate form data."""
        errors = []
        
        if not self.justification_edit.toPlainText().strip():
            errors.append("Justification is required")
        
        if not self.risk_assessment_edit.toPlainText().strip():
            errors.append("Risk assessment is required")
        
        return errors
    
    def accept(self):
        """Override accept to validate form."""
        errors = self.validate_form()
        if errors:
            QMessageBox.warning(self, "Validation Error", 
                              "Please fix the following errors:\n\n" + "\n".join(f"• {error}" for error in errors))
            return
        
        super().accept()


class BulkImportDialog(QDialog):
    """Dialog for bulk import of detected SOUP components."""
    
    def __init__(self, parent=None, detected_components: List[DetectedSOUPComponent] = None):
        super().__init__(parent)
        self.detected_components = detected_components or []
        self.selected_components = []
        
        self.setWindowTitle("Bulk Import SOUP Components")
        self.setModal(True)
        self.resize(1000, 700)
        
        self.setup_ui()
        self.populate_components()
    
    def setup_ui(self):
        """Set up the bulk import dialog UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Select Components to Import")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Select all/none buttons
        self.select_all_button = QPushButton("Select All")
        self.select_all_button.clicked.connect(self.select_all)
        header_layout.addWidget(self.select_all_button)
        
        self.select_none_button = QPushButton("Select None")
        self.select_none_button.clicked.connect(self.select_none)
        header_layout.addWidget(self.select_none_button)
        
        layout.addLayout(header_layout)
        
        # Components tree
        self.components_tree = QTreeWidget()
        self.components_tree.setHeaderLabels([
            "Import", "Name", "Version", "Source File", "Detection Method", 
            "Confidence", "Suggested Class", "Package Manager"
        ])
        self.components_tree.setRootIsDecorated(False)
        self.components_tree.setAlternatingRowColors(True)
        
        # Configure column widths
        header = self.components_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Checkbox
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Name
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Version
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Source File
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Detection Method
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Confidence
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Suggested Class
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Package Manager
        
        layout.addWidget(self.components_tree)
        
        # Summary
        self.summary_label = QLabel()
        layout.addWidget(self.summary_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.import_button = QPushButton("Import Selected")
        self.import_button.clicked.connect(self.accept)
        self.import_button.setDefault(True)
        button_layout.addWidget(self.import_button)
        
        layout.addLayout(button_layout)
    
    def populate_components(self):
        """Populate the components tree."""
        self.components_tree.clear()
        
        for component in self.detected_components:
            item = QTreeWidgetItem()
            
            # Checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(True)  # Default to selected
            checkbox.stateChanged.connect(self.update_summary)
            self.components_tree.setItemWidget(item, 0, checkbox)
            
            # Component data
            item.setText(1, component.name)
            item.setText(2, component.version)
            item.setText(3, component.source_file)
            item.setText(4, component.detection_method.value)
            item.setText(5, f"{component.confidence:.1%}")
            
            suggested_class = component.suggested_classification
            if suggested_class:
                item.setText(6, f"Class {suggested_class.value}")
            else:
                item.setText(6, "Not classified")
            
            item.setText(7, component.package_manager or "Unknown")
            
            # Store component reference
            item.setData(0, Qt.ItemDataRole.UserRole, component)
            
            self.components_tree.addTopLevelItem(item)
        
        self.update_summary()
    
    def select_all(self):
        """Select all components."""
        for i in range(self.components_tree.topLevelItemCount()):
            item = self.components_tree.topLevelItem(i)
            checkbox = self.components_tree.itemWidget(item, 0)
            checkbox.setChecked(True)
    
    def select_none(self):
        """Deselect all components."""
        for i in range(self.components_tree.topLevelItemCount()):
            item = self.components_tree.topLevelItem(i)
            checkbox = self.components_tree.itemWidget(item, 0)
            checkbox.setChecked(False)
    
    def update_summary(self):
        """Update the summary label."""
        selected_count = 0
        total_count = self.components_tree.topLevelItemCount()
        
        for i in range(total_count):
            item = self.components_tree.topLevelItem(i)
            checkbox = self.components_tree.itemWidget(item, 0)
            if checkbox.isChecked():
                selected_count += 1
        
        self.summary_label.setText(f"Selected {selected_count} of {total_count} components for import")
        self.import_button.setEnabled(selected_count > 0)
    
    def get_selected_components(self) -> List[DetectedSOUPComponent]:
        """Get list of selected components."""
        selected = []
        
        for i in range(self.components_tree.topLevelItemCount()):
            item = self.components_tree.topLevelItem(i)
            checkbox = self.components_tree.itemWidget(item, 0)
            
            if checkbox.isChecked():
                component = item.data(0, Qt.ItemDataRole.UserRole)
                selected.append(component)
        
        return selected


class SOUPComponentDialog(QDialog):
    """Dialog for adding/editing SOUP components."""
    
    def __init__(self, parent=None, component: Optional[SOUPComponent] = None):
        super().__init__(parent)
        self.component = component
        self.is_edit_mode = component is not None
        
        self.setWindowTitle("Edit SOUP Component" if self.is_edit_mode else "Add SOUP Component")
        self.setModal(True)
        self.resize(600, 700)
        
        self.setup_ui()
        
        if self.is_edit_mode:
            self.populate_fields()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Create scroll area for form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(10)
        
        # Required fields group
        required_group = QGroupBox("Required Information")
        required_layout = QFormLayout(required_group)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., SQLite, OpenSSL, jQuery")
        required_layout.addRow("Component Name*:", self.name_edit)
        
        self.version_edit = QLineEdit()
        self.version_edit.setPlaceholderText("e.g., 3.36.0, 1.1.1k")
        required_layout.addRow("Version*:", self.version_edit)
        
        self.usage_reason_edit = QTextEdit()
        self.usage_reason_edit.setMaximumHeight(80)
        self.usage_reason_edit.setPlaceholderText("Explain why this component is used in the system")
        required_layout.addRow("Usage Reason*:", self.usage_reason_edit)
        
        self.safety_justification_edit = QTextEdit()
        self.safety_justification_edit.setMaximumHeight(80)
        self.safety_justification_edit.setPlaceholderText("Justify why this component is safe for medical device use")
        required_layout.addRow("Safety Justification*:", self.safety_justification_edit)
        
        form_layout.addRow(required_group)
        
        # Optional fields group
        optional_group = QGroupBox("Additional Information")
        optional_layout = QFormLayout(optional_group)
        
        self.supplier_edit = QLineEdit()
        self.supplier_edit.setPlaceholderText("Component supplier/vendor")
        optional_layout.addRow("Supplier:", self.supplier_edit)
        
        self.license_edit = QLineEdit()
        self.license_edit.setPlaceholderText("e.g., MIT, GPL-3.0, Apache-2.0")
        optional_layout.addRow("License:", self.license_edit)
        
        self.website_edit = QLineEdit()
        self.website_edit.setPlaceholderText("https://...")
        optional_layout.addRow("Website:", self.website_edit)
        
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        self.description_edit.setPlaceholderText("Brief description of the component")
        optional_layout.addRow("Description:", self.description_edit)
        
        self.criticality_combo = QComboBox()
        self.criticality_combo.addItems(["", "High", "Medium", "Low"])
        optional_layout.addRow("Criticality Level:", self.criticality_combo)
        
        self.verification_method_edit = QLineEdit()
        self.verification_method_edit.setPlaceholderText("How component safety/functionality is verified")
        optional_layout.addRow("Verification Method:", self.verification_method_edit)
        
        # Date fields
        self.installation_date_edit = QDateEdit()
        self.installation_date_edit.setCalendarPopup(True)
        self.installation_date_edit.setSpecialValueText("Not set")
        self.installation_date_edit.setDate(QDate.currentDate())
        optional_layout.addRow("Installation Date:", self.installation_date_edit)
        
        self.last_updated_edit = QDateEdit()
        self.last_updated_edit.setCalendarPopup(True)
        self.last_updated_edit.setSpecialValueText("Not set")
        self.last_updated_edit.setDate(QDate.currentDate())
        optional_layout.addRow("Last Updated:", self.last_updated_edit)
        
        # Anomaly list
        self.anomaly_list_edit = QTextEdit()
        self.anomaly_list_edit.setMaximumHeight(80)
        self.anomaly_list_edit.setPlaceholderText("List known anomalies, one per line")
        optional_layout.addRow("Known Anomalies:", self.anomaly_list_edit)
        
        form_layout.addRow(optional_group)
        
        scroll.setWidget(form_widget)
        layout.addWidget(scroll)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.save_button = QPushButton("Update" if self.is_edit_mode else "Add")
        self.save_button.clicked.connect(self.accept)
        self.save_button.setDefault(True)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
    
    def populate_fields(self):
        """Populate form fields with component data."""
        if not self.component:
            return
        
        self.name_edit.setText(self.component.name)
        self.version_edit.setText(self.component.version)
        self.usage_reason_edit.setPlainText(self.component.usage_reason)
        self.safety_justification_edit.setPlainText(self.component.safety_justification)
        
        if self.component.supplier:
            self.supplier_edit.setText(self.component.supplier)
        if self.component.license:
            self.license_edit.setText(self.component.license)
        if self.component.website:
            self.website_edit.setText(self.component.website)
        if self.component.description:
            self.description_edit.setPlainText(self.component.description)
        if self.component.criticality_level:
            self.criticality_combo.setCurrentText(self.component.criticality_level)
        if self.component.verification_method:
            self.verification_method_edit.setText(self.component.verification_method)
        
        if self.component.installation_date:
            self.installation_date_edit.setDate(QDate.fromString(
                self.component.installation_date.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
        
        if self.component.last_updated:
            self.last_updated_edit.setDate(QDate.fromString(
                self.component.last_updated.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
        
        if self.component.anomaly_list:
            self.anomaly_list_edit.setPlainText("\n".join(self.component.anomaly_list))
    
    def get_component_data(self) -> SOUPComponent:
        """Get component data from form fields."""
        # Parse anomaly list
        anomaly_text = self.anomaly_list_edit.toPlainText().strip()
        anomaly_list = [line.strip() for line in anomaly_text.split('\n') if line.strip()] if anomaly_text else []
        
        # Parse dates
        installation_date = None
        if self.installation_date_edit.date() != self.installation_date_edit.minimumDate():
            installation_date = datetime.strptime(
                self.installation_date_edit.date().toString("yyyy-MM-dd"), "%Y-%m-%d")
        
        last_updated = None
        if self.last_updated_edit.date() != self.last_updated_edit.minimumDate():
            last_updated = datetime.strptime(
                self.last_updated_edit.date().toString("yyyy-MM-dd"), "%Y-%m-%d")
        
        return SOUPComponent(
            id=self.component.id if self.component else str(uuid.uuid4()),
            name=self.name_edit.text().strip(),
            version=self.version_edit.text().strip(),
            usage_reason=self.usage_reason_edit.toPlainText().strip(),
            safety_justification=self.safety_justification_edit.toPlainText().strip(),
            supplier=self.supplier_edit.text().strip() or None,
            license=self.license_edit.text().strip() or None,
            website=self.website_edit.text().strip() or None,
            description=self.description_edit.toPlainText().strip() or None,
            installation_date=installation_date,
            last_updated=last_updated,
            criticality_level=self.criticality_combo.currentText() or None,
            verification_method=self.verification_method_edit.text().strip() or None,
            anomaly_list=anomaly_list
        )
    
    def validate_form(self) -> List[str]:
        """Validate form data."""
        errors = []
        
        if not self.name_edit.text().strip():
            errors.append("Component name is required")
        
        if not self.version_edit.text().strip():
            errors.append("Version is required")
        
        if not self.usage_reason_edit.toPlainText().strip():
            errors.append("Usage reason is required")
        
        if not self.safety_justification_edit.toPlainText().strip():
            errors.append("Safety justification is required")
        
        return errors
    
    def accept(self):
        """Override accept to validate form."""
        errors = self.validate_form()
        if errors:
            QMessageBox.warning(self, "Validation Error", 
                              "Please fix the following errors:\n\n" + "\n".join(f"• {error}" for error in errors))
            return
        
        super().accept()


class SOUPWidget(QWidget):
    """Enhanced widget for managing SOUP inventory with IEC 62304 compliance."""
    
    component_added = pyqtSignal(SOUPComponent)
    component_updated = pyqtSignal(SOUPComponent)
    component_deleted = pyqtSignal(str)
    components_imported = pyqtSignal(int)  # Number of components imported
    
    def __init__(self, soup_service: SOUPService, parent=None):
        super().__init__(parent)
        self.soup_service = soup_service
        self.soup_detector = SOUPDetector(use_llm_classification=True)
        self.detection_worker = None
        
        self.setup_ui()
        self.refresh_table()
    
    def setup_ui(self):
        """Set up the enhanced widget UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("SOUP Inventory Management")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Filter controls
        self.criticality_filter = QComboBox()
        self.criticality_filter.addItems([
            "All Components", "High Criticality", "Medium Criticality", "Low Criticality",
            "Class A Components", "Class B Components", "Class C Components",
            "Compliant Components", "Non-Compliant Components"
        ])
        self.criticality_filter.currentTextChanged.connect(self.filter_components)
        header_layout.addWidget(QLabel("Filter:"))
        header_layout.addWidget(self.criticality_filter)
        
        layout.addLayout(header_layout)
        
        # Enhanced toolbar with detection and bulk operations
        toolbar_layout = QHBoxLayout()
        
        # Detection group
        detection_group = QGroupBox("Detection")
        detection_layout = QHBoxLayout(detection_group)
        
        self.detect_button = QPushButton("Auto-Detect Components")
        self.detect_button.clicked.connect(self.detect_components)
        detection_layout.addWidget(self.detect_button)
        
        self.bulk_import_button = QPushButton("Bulk Import")
        self.bulk_import_button.clicked.connect(self.bulk_import_components)
        self.bulk_import_button.setEnabled(False)
        detection_layout.addWidget(self.bulk_import_button)
        
        toolbar_layout.addWidget(detection_group)
        
        # Component management group
        management_group = QGroupBox("Component Management")
        management_layout = QHBoxLayout(management_group)
        
        self.add_button = QPushButton("Add Component")
        self.add_button.clicked.connect(self.add_component)
        management_layout.addWidget(self.add_button)
        
        self.edit_button = QPushButton("Edit Selected")
        self.edit_button.clicked.connect(self.edit_component)
        self.edit_button.setEnabled(False)
        management_layout.addWidget(self.edit_button)
        
        self.classify_button = QPushButton("Classify Selected")
        self.classify_button.clicked.connect(self.classify_component)
        self.classify_button.setEnabled(False)
        management_layout.addWidget(self.classify_button)
        
        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self.delete_component)
        self.delete_button.setEnabled(False)
        management_layout.addWidget(self.delete_button)
        
        toolbar_layout.addWidget(management_group)
        
        # Export/Import group
        export_group = QGroupBox("Export/Import")
        export_layout = QHBoxLayout(export_group)
        
        self.export_button = QPushButton("Export Inventory")
        self.export_button.clicked.connect(self.export_inventory)
        export_layout.addWidget(self.export_button)
        
        self.import_button = QPushButton("Import Inventory")
        self.import_button.clicked.connect(self.import_inventory)
        export_layout.addWidget(self.import_button)
        
        self.validate_button = QPushButton("Validate Compliance")
        self.validate_button.clicked.connect(self.validate_compliance)
        export_layout.addWidget(self.validate_button)
        
        toolbar_layout.addWidget(export_group)
        
        toolbar_layout.addStretch()
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_table)
        toolbar_layout.addWidget(self.refresh_button)
        
        layout.addLayout(toolbar_layout)
        
        # Progress bar for detection
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Enhanced components table with compliance indicators
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "Name", "Version", "Supplier", "License", "Safety Class", 
            "Compliance", "Criticality", "Installation Date", "Last Updated", 
            "Usage Reason", "Actions"
        ])
        
        # Configure table
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Version
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Supplier
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # License
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Safety Class
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Compliance
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Criticality
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Installation Date
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)  # Last Updated
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)  # Usage Reason
        header.setSectionResizeMode(10, QHeaderView.ResizeMode.ResizeToContents)  # Actions
        
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        self.table.itemDoubleClicked.connect(self.edit_component)
        
        layout.addWidget(self.table)
        
        # Enhanced status bar with compliance summary
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.compliance_summary_label = QLabel()
        status_layout.addWidget(self.compliance_summary_label)
        
        layout.addLayout(status_layout)
        
        # Store detected components for bulk import
        self.detected_components = []
    
    def detect_components(self):
        """Detect SOUP components from project files."""
        project_path = QFileDialog.getExistingDirectory(
            self, "Select Project Directory", "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not project_path:
            return
        
        # Start detection in background thread
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.detect_button.setEnabled(False)
        
        self.detection_worker = DetectionWorker(project_path, self.soup_detector)
        self.detection_worker.detection_finished.connect(self.on_detection_finished)
        self.detection_worker.detection_error.connect(self.on_detection_error)
        self.detection_worker.detection_progress.connect(self.on_detection_progress)
        self.detection_worker.start()
    
    def on_detection_finished(self, detected_components: List[DetectedSOUPComponent]):
        """Handle detection completion."""
        self.progress_bar.setVisible(False)
        self.detect_button.setEnabled(True)
        
        self.detected_components = detected_components
        
        if detected_components:
            self.bulk_import_button.setEnabled(True)
            self.status_label.setText(f"Detected {len(detected_components)} SOUP components")
            
            # Show summary message
            QMessageBox.information(
                self, "Detection Complete",
                f"Found {len(detected_components)} SOUP components.\n"
                f"Click 'Bulk Import' to review and import them."
            )
        else:
            self.status_label.setText("No SOUP components detected")
            QMessageBox.information(
                self, "Detection Complete",
                "No SOUP components were detected in the selected project."
            )
    
    def on_detection_error(self, error_message: str):
        """Handle detection error."""
        self.progress_bar.setVisible(False)
        self.detect_button.setEnabled(True)
        
        QMessageBox.critical(self, "Detection Error", f"Failed to detect components:\n{error_message}")
        self.status_label.setText("Detection failed")
    
    def on_detection_progress(self, message: str):
        """Handle detection progress updates."""
        self.status_label.setText(message)
    
    def bulk_import_components(self):
        """Show bulk import dialog for detected components."""
        if not self.detected_components:
            QMessageBox.warning(self, "No Components", "No detected components available for import.")
            return
        
        dialog = BulkImportDialog(self, self.detected_components)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_components = dialog.get_selected_components()
            
            if not selected_components:
                return
            
            # Import selected components
            imported_count = 0
            errors = []
            
            for component in selected_components:
                try:
                    component_id = self.soup_service.add_component_with_classification(component)
                    imported_count += 1
                except Exception as e:
                    errors.append(f"{component.name}: {str(e)}")
            
            # Show results
            if imported_count > 0:
                self.refresh_table()
                self.components_imported.emit(imported_count)
                
                message = f"Successfully imported {imported_count} components."
                if errors:
                    message += f"\n\nErrors occurred for {len(errors)} components:\n" + "\n".join(errors[:5])
                    if len(errors) > 5:
                        message += f"\n... and {len(errors) - 5} more errors."
                
                QMessageBox.information(self, "Import Complete", message)
            else:
                QMessageBox.warning(self, "Import Failed", 
                                  f"Failed to import components:\n" + "\n".join(errors[:10]))
            
            # Clear detected components after import
            self.detected_components = []
            self.bulk_import_button.setEnabled(False)
    
    def classify_component(self):
        """Classify the selected component according to IEC 62304."""
        current_row = self.table.currentRow()
        if current_row < 0:
            return
        
        component_id = self.table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
        
        try:
            component = self.soup_service.get_component(component_id)
            if not component:
                QMessageBox.warning(self, "Error", "Component not found")
                return
            
            # Get existing classification if any
            classification = self.soup_service.get_component_classification(component_id)
            
            dialog = ClassificationDialog(self, component, classification)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_classification = dialog.get_classification_data()
                
                # Store classification
                self.soup_service._store_classification(component_id, new_classification)
                
                # Update component criticality based on safety class
                criticality_map = {
                    IEC62304SafetyClass.CLASS_A: "Low",
                    IEC62304SafetyClass.CLASS_B: "Medium", 
                    IEC62304SafetyClass.CLASS_C: "High"
                }
                component.criticality_level = criticality_map[new_classification.safety_class]
                component.safety_justification = new_classification.justification
                
                self.soup_service.update_component(component)
                self.refresh_table()
                
                self.status_label.setText(f"Classified component: {component.name}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to classify component:\n{str(e)}")
    
    def export_inventory(self):
        """Export SOUP inventory to various formats."""
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Export SOUP Inventory", "soup_inventory",
            "JSON Files (*.json);;CSV Files (*.csv);;Excel Files (*.xlsx)"
        )
        
        if not file_path:
            return
        
        try:
            components = self.soup_service.get_all_components()
            
            if selected_filter.startswith("JSON"):
                self._export_to_json(file_path, components)
            elif selected_filter.startswith("CSV"):
                self._export_to_csv(file_path, components)
            elif selected_filter.startswith("Excel"):
                self._export_to_excel(file_path, components)
            
            QMessageBox.information(self, "Export Complete", 
                                  f"Successfully exported {len(components)} components to {file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export inventory:\n{str(e)}")
    
    def _export_to_json(self, file_path: str, components: List[SOUPComponent]):
        """Export components to JSON format."""
        export_data = {
            "soup_inventory": {
                "export_timestamp": datetime.now().isoformat(),
                "component_count": len(components),
                "components": []
            }
        }
        
        for component in components:
            # Get classification info
            classification = self.soup_service.get_component_classification(component.id)
            
            component_data = {
                "id": component.id,
                "name": component.name,
                "version": component.version,
                "usage_reason": component.usage_reason,
                "safety_justification": component.safety_justification,
                "supplier": component.supplier,
                "license": component.license,
                "website": component.website,
                "description": component.description,
                "installation_date": component.installation_date.isoformat() if component.installation_date else None,
                "last_updated": component.last_updated.isoformat() if component.last_updated else None,
                "criticality_level": component.criticality_level,
                "verification_method": component.verification_method,
                "anomaly_list": component.anomaly_list,
                "metadata": component.metadata
            }
            
            if classification:
                component_data["iec62304_classification"] = {
                    "safety_class": classification.safety_class.value,
                    "justification": classification.justification,
                    "risk_assessment": classification.risk_assessment,
                    "verification_requirements": classification.verification_requirements,
                    "documentation_requirements": classification.documentation_requirements
                }
            
            export_data["soup_inventory"]["components"].append(component_data)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    def _export_to_csv(self, file_path: str, components: List[SOUPComponent]):
        """Export components to CSV format."""
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                "Name", "Version", "Supplier", "License", "Safety Class", 
                "Criticality", "Usage Reason", "Safety Justification",
                "Installation Date", "Last Updated", "Verification Method",
                "Known Anomalies"
            ])
            
            # Write component data
            for component in components:
                classification = self.soup_service.get_component_classification(component.id)
                safety_class = classification.safety_class.value if classification else "Not classified"
                
                writer.writerow([
                    component.name,
                    component.version,
                    component.supplier or "",
                    component.license or "",
                    safety_class,
                    component.criticality_level or "",
                    component.usage_reason,
                    component.safety_justification,
                    component.installation_date.strftime("%Y-%m-%d") if component.installation_date else "",
                    component.last_updated.strftime("%Y-%m-%d") if component.last_updated else "",
                    component.verification_method or "",
                    "; ".join(component.anomaly_list) if component.anomaly_list else ""
                ])
    
    def _export_to_excel(self, file_path: str, components: List[SOUPComponent]):
        """Export components to Excel format (basic implementation)."""
        # For now, export as CSV with .xlsx extension
        # In a full implementation, you would use openpyxl or xlsxwriter
        csv_path = file_path.replace('.xlsx', '.csv')
        self._export_to_csv(csv_path, components)
        
        # Rename to xlsx (this is a simplified approach)
        import shutil
        shutil.move(csv_path, file_path)
    
    def import_inventory(self):
        """Import SOUP inventory from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import SOUP Inventory", "",
            "JSON Files (*.json);;CSV Files (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            if file_path.endswith('.json'):
                self._import_from_json(file_path)
            elif file_path.endswith('.csv'):
                self._import_from_csv(file_path)
            
            self.refresh_table()
            
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import inventory:\n{str(e)}")
    
    def _import_from_json(self, file_path: str):
        """Import components from JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        components_data = data.get("soup_inventory", {}).get("components", [])
        imported_count = 0
        
        for comp_data in components_data:
            try:
                # Create SOUPComponent
                component = SOUPComponent(
                    id=comp_data.get("id", str(uuid.uuid4())),
                    name=comp_data["name"],
                    version=comp_data["version"],
                    usage_reason=comp_data["usage_reason"],
                    safety_justification=comp_data["safety_justification"],
                    supplier=comp_data.get("supplier"),
                    license=comp_data.get("license"),
                    website=comp_data.get("website"),
                    description=comp_data.get("description"),
                    installation_date=datetime.fromisoformat(comp_data["installation_date"]) if comp_data.get("installation_date") else None,
                    last_updated=datetime.fromisoformat(comp_data["last_updated"]) if comp_data.get("last_updated") else None,
                    criticality_level=comp_data.get("criticality_level"),
                    verification_method=comp_data.get("verification_method"),
                    anomaly_list=comp_data.get("anomaly_list", []),
                    metadata=comp_data.get("metadata", {})
                )
                
                self.soup_service.add_component(component)
                imported_count += 1
                
            except Exception as e:
                print(f"Failed to import component {comp_data.get('name', 'unknown')}: {e}")
        
        QMessageBox.information(self, "Import Complete", 
                              f"Successfully imported {imported_count} components")
    
    def _import_from_csv(self, file_path: str):
        """Import components from CSV file."""
        imported_count = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    component = SOUPComponent(
                        id=str(uuid.uuid4()),
                        name=row["Name"],
                        version=row["Version"],
                        usage_reason=row["Usage Reason"],
                        safety_justification=row["Safety Justification"],
                        supplier=row.get("Supplier") or None,
                        license=row.get("License") or None,
                        criticality_level=row.get("Criticality") or None,
                        verification_method=row.get("Verification Method") or None,
                        anomaly_list=row.get("Known Anomalies", "").split("; ") if row.get("Known Anomalies") else []
                    )
                    
                    self.soup_service.add_component(component)
                    imported_count += 1
                    
                except Exception as e:
                    print(f"Failed to import component {row.get('Name', 'unknown')}: {e}")
        
        QMessageBox.information(self, "Import Complete", 
                              f"Successfully imported {imported_count} components")
    
    def validate_compliance(self):
        """Validate IEC 62304 compliance for all components."""
        try:
            components = self.soup_service.get_all_components()
            
            if not components:
                QMessageBox.information(self, "No Components", "No components to validate.")
                return
            
            compliant_count = 0
            non_compliant_count = 0
            validation_results = []
            
            for component in components:
                validation = self.soup_service.validate_component_compliance(component.id)
                validation_results.append((component, validation))
                
                if validation.is_compliant:
                    compliant_count += 1
                else:
                    non_compliant_count += 1
            
            # Show validation summary
            summary_text = f"Compliance Validation Results:\n\n"
            summary_text += f"✓ Compliant: {compliant_count} components\n"
            summary_text += f"✗ Non-compliant: {non_compliant_count} components\n\n"
            
            if non_compliant_count > 0:
                summary_text += "Non-compliant components:\n"
                for component, validation in validation_results:
                    if not validation.is_compliant:
                        summary_text += f"• {component.name} v{component.version}\n"
                        for req in validation.missing_requirements[:3]:  # Show first 3 issues
                            summary_text += f"  - {req}\n"
                        if len(validation.missing_requirements) > 3:
                            summary_text += f"  - ... and {len(validation.missing_requirements) - 3} more issues\n"
            
            QMessageBox.information(self, "Compliance Validation", summary_text)
            
            # Update compliance summary in status bar
            self.update_compliance_summary()
            
        except Exception as e:
            QMessageBox.critical(self, "Validation Error", f"Failed to validate compliance:\n{str(e)}")
    
    def update_compliance_summary(self):
        """Update the compliance summary in the status bar."""
        try:
            components = self.soup_service.get_all_components()
            
            if not components:
                self.compliance_summary_label.setText("")
                return
            
            compliant_count = 0
            for component in components:
                validation = self.soup_service.validate_component_compliance(component.id)
                if validation.is_compliant:
                    compliant_count += 1
            
            total_count = len(components)
            compliance_percentage = (compliant_count / total_count) * 100 if total_count > 0 else 0
            
            self.compliance_summary_label.setText(
                f"Compliance: {compliant_count}/{total_count} ({compliance_percentage:.1f}%)"
            )
            
        except Exception:
            self.compliance_summary_label.setText("Compliance: Unknown")
    
    def refresh_table(self):
        """Refresh the components table."""
        try:
            components = self.soup_service.get_all_components()
            self.populate_table(components)
            self.status_label.setText(f"Loaded {len(components)} SOUP components")
            self.update_compliance_summary()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load SOUP components:\n{str(e)}")
            self.status_label.setText("Error loading components")
    
    def populate_table(self, components: List[SOUPComponent]):
        """Populate table with components including compliance indicators."""
        self.table.setRowCount(len(components))
        
        for row, component in enumerate(components):
            # Store component ID in first column for reference
            name_item = QTableWidgetItem(component.name)
            name_item.setData(Qt.ItemDataRole.UserRole, component.id)
            self.table.setItem(row, 0, name_item)
            
            self.table.setItem(row, 1, QTableWidgetItem(component.version))
            self.table.setItem(row, 2, QTableWidgetItem(component.supplier or ""))
            self.table.setItem(row, 3, QTableWidgetItem(component.license or ""))
            
            # Safety class column
            classification = self.soup_service.get_component_classification(component.id)
            if classification:
                safety_class_item = QTableWidgetItem(f"Class {classification.safety_class.value}")
                # Color code by safety class
                if classification.safety_class == IEC62304SafetyClass.CLASS_C:
                    safety_class_item.setBackground(QColor(255, 200, 200))  # Light red
                elif classification.safety_class == IEC62304SafetyClass.CLASS_B:
                    safety_class_item.setBackground(QColor(255, 255, 200))  # Light yellow
                else:  # CLASS_A
                    safety_class_item.setBackground(QColor(200, 255, 200))  # Light green
            else:
                safety_class_item = QTableWidgetItem("Not classified")
                safety_class_item.setBackground(QColor(240, 240, 240))  # Light gray
            
            self.table.setItem(row, 4, safety_class_item)
            
            # Compliance status column
            try:
                validation = self.soup_service.validate_component_compliance(component.id)
                if validation.is_compliant:
                    compliance_item = QTableWidgetItem("✓ Compliant")
                    compliance_item.setBackground(QColor(200, 255, 200))  # Light green
                else:
                    compliance_item = QTableWidgetItem(f"✗ {len(validation.missing_requirements)} issues")
                    compliance_item.setBackground(QColor(255, 200, 200))  # Light red
                    compliance_item.setToolTip("\n".join(validation.missing_requirements[:5]))
            except Exception:
                compliance_item = QTableWidgetItem("Unknown")
                compliance_item.setBackground(QColor(240, 240, 240))  # Light gray
            
            self.table.setItem(row, 5, compliance_item)
            
            # Criticality level
            self.table.setItem(row, 6, QTableWidgetItem(component.criticality_level or ""))
            
            # Dates
            install_date = component.installation_date.strftime("%Y-%m-%d") if component.installation_date else ""
            self.table.setItem(row, 7, QTableWidgetItem(install_date))
            
            update_date = component.last_updated.strftime("%Y-%m-%d") if component.last_updated else ""
            self.table.setItem(row, 8, QTableWidgetItem(update_date))
            
            # Truncate usage reason for table display
            usage_reason = component.usage_reason
            if len(usage_reason) > 100:
                usage_reason = usage_reason[:97] + "..."
            self.table.setItem(row, 9, QTableWidgetItem(usage_reason))
            
            # Actions column - add action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            
            # Classify button
            classify_btn = QPushButton("Classify")
            classify_btn.setMaximumSize(60, 25)
            classify_btn.clicked.connect(lambda checked, cid=component.id: self.classify_component_by_id(cid))
            actions_layout.addWidget(classify_btn)
            
            # View details button
            details_btn = QPushButton("Details")
            details_btn.setMaximumSize(60, 25)
            details_btn.clicked.connect(lambda checked, cid=component.id: self.view_component_details(cid))
            actions_layout.addWidget(details_btn)
            
            actions_layout.addStretch()
            self.table.setCellWidget(row, 10, actions_widget)
    
    def classify_component_by_id(self, component_id: str):
        """Classify a component by its ID."""
        try:
            component = self.soup_service.get_component(component_id)
            if not component:
                QMessageBox.warning(self, "Error", "Component not found")
                return
            
            # Get existing classification if any
            classification = self.soup_service.get_component_classification(component_id)
            
            dialog = ClassificationDialog(self, component, classification)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_classification = dialog.get_classification_data()
                
                # Store classification
                self.soup_service._store_classification(component_id, new_classification)
                
                # Update component criticality based on safety class
                criticality_map = {
                    IEC62304SafetyClass.CLASS_A: "Low",
                    IEC62304SafetyClass.CLASS_B: "Medium", 
                    IEC62304SafetyClass.CLASS_C: "High"
                }
                component.criticality_level = criticality_map[new_classification.safety_class]
                component.safety_justification = new_classification.justification
                
                self.soup_service.update_component(component)
                self.refresh_table()
                
                self.status_label.setText(f"Classified component: {component.name}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to classify component:\n{str(e)}")
    
    def view_component_details(self, component_id: str):
        """View detailed information about a component."""
        try:
            component = self.soup_service.get_component(component_id)
            if not component:
                QMessageBox.warning(self, "Error", "Component not found")
                return
            
            classification = self.soup_service.get_component_classification(component_id)
            validation = self.soup_service.validate_component_compliance(component_id)
            
            # Create details dialog
            details_dialog = QDialog(self)
            details_dialog.setWindowTitle(f"Component Details: {component.name}")
            details_dialog.setModal(True)
            details_dialog.resize(600, 500)
            
            layout = QVBoxLayout(details_dialog)
            
            # Component info
            info_text = f"""
<h3>{component.name} v{component.version}</h3>
<p><b>Usage Reason:</b> {component.usage_reason}</p>
<p><b>Safety Justification:</b> {component.safety_justification}</p>
<p><b>Supplier:</b> {component.supplier or 'Not specified'}</p>
<p><b>License:</b> {component.license or 'Not specified'}</p>
<p><b>Criticality:</b> {component.criticality_level or 'Not specified'}</p>
"""
            
            if classification:
                info_text += f"""
<h4>IEC 62304 Classification</h4>
<p><b>Safety Class:</b> Class {classification.safety_class.value}</p>
<p><b>Justification:</b> {classification.justification}</p>
<p><b>Risk Assessment:</b> {classification.risk_assessment}</p>
"""
                
                if classification.verification_requirements:
                    info_text += "<p><b>Verification Requirements:</b></p><ul>"
                    for req in classification.verification_requirements:
                        info_text += f"<li>{req}</li>"
                    info_text += "</ul>"
            
            if validation:
                info_text += f"""
<h4>Compliance Status</h4>
<p><b>Status:</b> {'✓ Compliant' if validation.is_compliant else '✗ Non-compliant'}</p>
"""
                
                if validation.missing_requirements:
                    info_text += "<p><b>Missing Requirements:</b></p><ul>"
                    for req in validation.missing_requirements:
                        info_text += f"<li>{req}</li>"
                    info_text += "</ul>"
                
                if validation.warnings:
                    info_text += "<p><b>Warnings:</b></p><ul>"
                    for warning in validation.warnings:
                        info_text += f"<li>{warning}</li>"
                    info_text += "</ul>"
            
            details_label = QLabel(info_text)
            details_label.setWordWrap(True)
            details_label.setTextFormat(Qt.TextFormat.RichText)
            
            scroll_area = QScrollArea()
            scroll_area.setWidget(details_label)
            scroll_area.setWidgetResizable(True)
            layout.addWidget(scroll_area)
            
            # Close button
            close_button = QPushButton("Close")
            close_button.clicked.connect(details_dialog.accept)
            layout.addWidget(close_button)
            
            details_dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load component details:\n{str(e)}")
    
    def filter_components(self):
        """Filter components by various criteria."""
        filter_text = self.criticality_filter.currentText()
        
        try:
            if filter_text == "All Components":
                components = self.soup_service.get_all_components()
            elif filter_text.endswith("Criticality"):
                criticality = filter_text.split()[0]  # Extract "High", "Medium", or "Low"
                components = self.soup_service.get_components_by_criticality(criticality)
            elif filter_text.startswith("Class"):
                # Filter by safety class
                class_letter = filter_text.split()[1]  # Extract "A", "B", or "C"
                components = self._filter_by_safety_class(class_letter)
            elif filter_text == "Compliant Components":
                components = self._filter_by_compliance(True)
            elif filter_text == "Non-Compliant Components":
                components = self._filter_by_compliance(False)
            else:
                components = self.soup_service.get_all_components()
            
            self.populate_table(components)
            self.status_label.setText(f"Showing {len(components)} components")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to filter components:\n{str(e)}")
    
    def _filter_by_safety_class(self, class_letter: str) -> List[SOUPComponent]:
        """Filter components by IEC 62304 safety class."""
        all_components = self.soup_service.get_all_components()
        filtered_components = []
        
        target_class = IEC62304SafetyClass(class_letter)
        
        for component in all_components:
            classification = self.soup_service.get_component_classification(component.id)
            if classification and classification.safety_class == target_class:
                filtered_components.append(component)
        
        return filtered_components
    
    def _filter_by_compliance(self, is_compliant: bool) -> List[SOUPComponent]:
        """Filter components by compliance status."""
        all_components = self.soup_service.get_all_components()
        filtered_components = []
        
        for component in all_components:
            try:
                validation = self.soup_service.validate_component_compliance(component.id)
                if validation.is_compliant == is_compliant:
                    filtered_components.append(component)
            except Exception:
                # If validation fails, consider as non-compliant
                if not is_compliant:
                    filtered_components.append(component)
        
        return filtered_components
    
    def on_selection_changed(self):
        """Handle table selection changes."""
        has_selection = len(self.table.selectedItems()) > 0
        self.edit_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)
    
    def add_component(self):
        """Add a new SOUP component."""
        dialog = SOUPComponentDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                component = dialog.get_component_data()
                component_id = self.soup_service.add_component(component)
                self.refresh_table()
                self.component_added.emit(component)
                self.status_label.setText(f"Added component: {component.name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add component:\n{str(e)}")
    
    def edit_component(self):
        """Edit the selected SOUP component."""
        current_row = self.table.currentRow()
        if current_row < 0:
            return
        
        component_id = self.table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
        
        try:
            component = self.soup_service.get_component(component_id)
            if not component:
                QMessageBox.warning(self, "Error", "Component not found")
                return
            
            dialog = SOUPComponentDialog(self, component)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                updated_component = dialog.get_component_data()
                success = self.soup_service.update_component(updated_component)
                if success:
                    self.refresh_table()
                    self.component_updated.emit(updated_component)
                    self.status_label.setText(f"Updated component: {updated_component.name}")
                else:
                    QMessageBox.warning(self, "Error", "Failed to update component")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to edit component:\n{str(e)}")
    
    def delete_component(self):
        """Delete the selected SOUP component."""
        current_row = self.table.currentRow()
        if current_row < 0:
            return
        
        component_id = self.table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
        component_name = self.table.item(current_row, 0).text()
        
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete the SOUP component '{component_name}'?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.soup_service.delete_component(component_id)
                if success:
                    self.refresh_table()
                    self.component_deleted.emit(component_id)
                    self.status_label.setText(f"Deleted component: {component_name}")
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete component")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete component:\n{str(e)}")
    
    def get_selected_component_id(self) -> Optional[str]:
        """Get the ID of the currently selected component."""
        current_row = self.table.currentRow()
        if current_row >= 0:
            return self.table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
        return None
    
    def get_component_count(self) -> int:
        """Get the total number of components."""
        return self.table.rowCount()