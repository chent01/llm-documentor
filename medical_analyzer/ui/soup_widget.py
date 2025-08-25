"""
SOUP (Software of Unknown Provenance) inventory management widget.
"""

import uuid
from datetime import datetime
from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QDialog, QFormLayout, QLineEdit, QTextEdit, QComboBox,
    QDateEdit, QMessageBox, QHeaderView, QLabel, QGroupBox, QSplitter,
    QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QFont

from ..models.core import SOUPComponent
from ..services.soup_service import SOUPService


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
    """Widget for managing SOUP inventory."""
    
    component_added = pyqtSignal(SOUPComponent)
    component_updated = pyqtSignal(SOUPComponent)
    component_deleted = pyqtSignal(str)
    
    def __init__(self, soup_service: SOUPService, parent=None):
        super().__init__(parent)
        self.soup_service = soup_service
        
        self.setup_ui()
        self.refresh_table()
    
    def setup_ui(self):
        """Set up the widget UI."""
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
        
        # Filter by criticality
        self.criticality_filter = QComboBox()
        self.criticality_filter.addItems(["All Components", "High Criticality", "Medium Criticality", "Low Criticality"])
        self.criticality_filter.currentTextChanged.connect(self.filter_components)
        header_layout.addWidget(QLabel("Filter:"))
        header_layout.addWidget(self.criticality_filter)
        
        layout.addLayout(header_layout)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        self.add_button = QPushButton("Add Component")
        self.add_button.clicked.connect(self.add_component)
        toolbar_layout.addWidget(self.add_button)
        
        self.edit_button = QPushButton("Edit Selected")
        self.edit_button.clicked.connect(self.edit_component)
        self.edit_button.setEnabled(False)
        toolbar_layout.addWidget(self.edit_button)
        
        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self.delete_component)
        self.delete_button.setEnabled(False)
        toolbar_layout.addWidget(self.delete_button)
        
        toolbar_layout.addStretch()
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_table)
        toolbar_layout.addWidget(self.refresh_button)
        
        layout.addLayout(toolbar_layout)
        
        # Components table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Name", "Version", "Supplier", "License", "Criticality", 
            "Installation Date", "Last Updated", "Usage Reason"
        ])
        
        # Configure table
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Version
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Supplier
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # License
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Criticality
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Installation Date
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Last Updated
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)  # Usage Reason
        
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        self.table.itemDoubleClicked.connect(self.edit_component)
        
        layout.addWidget(self.table)
        
        # Status bar
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
    
    def refresh_table(self):
        """Refresh the components table."""
        try:
            components = self.soup_service.get_all_components()
            self.populate_table(components)
            self.status_label.setText(f"Loaded {len(components)} SOUP components")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load SOUP components:\n{str(e)}")
            self.status_label.setText("Error loading components")
    
    def populate_table(self, components: List[SOUPComponent]):
        """Populate table with components."""
        self.table.setRowCount(len(components))
        
        for row, component in enumerate(components):
            # Store component ID in first column for reference
            name_item = QTableWidgetItem(component.name)
            name_item.setData(Qt.ItemDataRole.UserRole, component.id)
            self.table.setItem(row, 0, name_item)
            
            self.table.setItem(row, 1, QTableWidgetItem(component.version))
            self.table.setItem(row, 2, QTableWidgetItem(component.supplier or ""))
            self.table.setItem(row, 3, QTableWidgetItem(component.license or ""))
            self.table.setItem(row, 4, QTableWidgetItem(component.criticality_level or ""))
            
            install_date = component.installation_date.strftime("%Y-%m-%d") if component.installation_date else ""
            self.table.setItem(row, 5, QTableWidgetItem(install_date))
            
            update_date = component.last_updated.strftime("%Y-%m-%d") if component.last_updated else ""
            self.table.setItem(row, 6, QTableWidgetItem(update_date))
            
            # Truncate usage reason for table display
            usage_reason = component.usage_reason
            if len(usage_reason) > 100:
                usage_reason = usage_reason[:97] + "..."
            self.table.setItem(row, 7, QTableWidgetItem(usage_reason))
    
    def filter_components(self):
        """Filter components by criticality level."""
        filter_text = self.criticality_filter.currentText()
        
        try:
            if filter_text == "All Components":
                components = self.soup_service.get_all_components()
            else:
                criticality = filter_text.split()[0]  # Extract "High", "Medium", or "Low"
                components = self.soup_service.get_components_by_criticality(criticality)
            
            self.populate_table(components)
            self.status_label.setText(f"Showing {len(components)} components")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to filter components:\n{str(e)}")
    
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