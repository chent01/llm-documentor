"""
Unit tests for SOUP widget.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from medical_analyzer.models.core import SOUPComponent
from medical_analyzer.ui.soup_widget import SOUPWidget, SOUPComponentDialog
from medical_analyzer.services.soup_service import SOUPService


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_soup_service():
    """Create a mock SOUP service."""
    service = Mock(spec=SOUPService)
    service.get_all_components.return_value = []
    service.get_components_by_criticality.return_value = []
    return service


@pytest.fixture
def sample_component():
    """Create a sample SOUP component."""
    return SOUPComponent(
        id="test-id-123",
        name="SQLite",
        version="3.36.0",
        usage_reason="Database storage for analysis results",
        safety_justification="Well-tested, widely used database engine",
        supplier="SQLite Development Team",
        license="Public Domain",
        website="https://sqlite.org",
        description="Lightweight SQL database engine",
        criticality_level="Medium",
        verification_method="Unit testing",
        anomaly_list=["None known"]
    )


class TestSOUPComponentDialog:
    """Test cases for SOUPComponentDialog."""
    
    def test_dialog_initialization_new_component(self, qapp):
        """Test dialog initialization for new component."""
        dialog = SOUPComponentDialog()
        
        assert dialog.windowTitle() == "Add SOUP Component"
        assert not dialog.is_edit_mode
        assert dialog.component is None
        
        # Check that required fields are empty
        assert dialog.name_edit.text() == ""
        assert dialog.version_edit.text() == ""
        assert dialog.usage_reason_edit.toPlainText() == ""
        assert dialog.safety_justification_edit.toPlainText() == ""
    
    def test_dialog_initialization_edit_component(self, qapp, sample_component):
        """Test dialog initialization for editing existing component."""
        dialog = SOUPComponentDialog(component=sample_component)
        
        assert dialog.windowTitle() == "Edit SOUP Component"
        assert dialog.is_edit_mode
        assert dialog.component == sample_component
        
        # Check that fields are populated
        assert dialog.name_edit.text() == sample_component.name
        assert dialog.version_edit.text() == sample_component.version
        assert dialog.usage_reason_edit.toPlainText() == sample_component.usage_reason
        assert dialog.safety_justification_edit.toPlainText() == sample_component.safety_justification
    
    def test_validate_form_success(self, qapp):
        """Test successful form validation."""
        dialog = SOUPComponentDialog()
        
        # Fill required fields
        dialog.name_edit.setText("Test Component")
        dialog.version_edit.setText("1.0")
        dialog.usage_reason_edit.setPlainText("Testing purposes")
        dialog.safety_justification_edit.setPlainText("Safe for testing")
        
        errors = dialog.validate_form()
        assert errors == []
    
    def test_validate_form_missing_required_fields(self, qapp):
        """Test form validation with missing required fields."""
        dialog = SOUPComponentDialog()
        
        errors = dialog.validate_form()
        
        assert len(errors) == 4
        assert "Component name is required" in errors
        assert "Version is required" in errors
        assert "Usage reason is required" in errors
        assert "Safety justification is required" in errors
    
    def test_get_component_data_minimal(self, qapp):
        """Test getting component data with minimal required fields."""
        dialog = SOUPComponentDialog()
        
        dialog.name_edit.setText("Test Component")
        dialog.version_edit.setText("1.0")
        dialog.usage_reason_edit.setPlainText("Testing")
        dialog.safety_justification_edit.setPlainText("Safe")
        
        component = dialog.get_component_data()
        
        assert component.name == "Test Component"
        assert component.version == "1.0"
        assert component.usage_reason == "Testing"
        assert component.safety_justification == "Safe"
        assert component.id  # Should have generated ID
    
    def test_get_component_data_complete(self, qapp):
        """Test getting component data with all fields filled."""
        dialog = SOUPComponentDialog()
        
        dialog.name_edit.setText("Complete Component")
        dialog.version_edit.setText("2.0")
        dialog.usage_reason_edit.setPlainText("Complete testing")
        dialog.safety_justification_edit.setPlainText("Completely safe")
        dialog.supplier_edit.setText("Test Supplier")
        dialog.license_edit.setText("MIT")
        dialog.website_edit.setText("https://example.com")
        dialog.description_edit.setPlainText("Complete description")
        dialog.criticality_combo.setCurrentText("High")
        dialog.verification_method_edit.setText("Complete verification")
        dialog.anomaly_list_edit.setPlainText("Anomaly 1\nAnomaly 2")
        
        component = dialog.get_component_data()
        
        assert component.name == "Complete Component"
        assert component.supplier == "Test Supplier"
        assert component.license == "MIT"
        assert component.website == "https://example.com"
        assert component.description == "Complete description"
        assert component.criticality_level == "High"
        assert component.verification_method == "Complete verification"
        assert len(component.anomaly_list) == 2
        assert "Anomaly 1" in component.anomaly_list
        assert "Anomaly 2" in component.anomaly_list


class TestSOUPWidget:
    """Test cases for SOUPWidget."""
    
    def test_widget_initialization(self, qapp, mock_soup_service):
        """Test widget initialization."""
        widget = SOUPWidget(mock_soup_service)
        
        assert widget.soup_service == mock_soup_service
        assert widget.table.columnCount() == 8
        assert widget.table.rowCount() == 0
        
        # Check that service was called to load components
        mock_soup_service.get_all_components.assert_called_once()
    
    def test_refresh_table_success(self, qapp, mock_soup_service, sample_component):
        """Test successful table refresh."""
        mock_soup_service.get_all_components.return_value = [sample_component]
        
        widget = SOUPWidget(mock_soup_service)
        widget.refresh_table()
        
        assert widget.table.rowCount() == 1
        assert widget.table.item(0, 0).text() == sample_component.name
        assert widget.table.item(0, 1).text() == sample_component.version
        assert "1 SOUP components" in widget.status_label.text()
    
    @patch('medical_analyzer.ui.soup_widget.QMessageBox.critical')
    def test_refresh_table_error(self, mock_msgbox, qapp, mock_soup_service):
        """Test table refresh with service error."""
        mock_soup_service.get_all_components.side_effect = Exception("Database error")
        
        widget = SOUPWidget(mock_soup_service)
        widget.refresh_table()
        
        mock_msgbox.assert_called_once()
        assert "Error loading components" in widget.status_label.text()
    
    def test_populate_table_multiple_components(self, qapp, mock_soup_service):
        """Test populating table with multiple components."""
        components = [
            SOUPComponent(
                id="comp1", name="Component A", version="1.0",
                usage_reason="Test A", safety_justification="Safe A",
                supplier="Supplier A", criticality_level="High"
            ),
            SOUPComponent(
                id="comp2", name="Component B", version="2.0",
                usage_reason="Test B", safety_justification="Safe B",
                supplier="Supplier B", criticality_level="Low"
            )
        ]
        
        widget = SOUPWidget(mock_soup_service)
        widget.populate_table(components)
        
        assert widget.table.rowCount() == 2
        assert widget.table.item(0, 0).text() == "Component A"
        assert widget.table.item(1, 0).text() == "Component B"
        assert widget.table.item(0, 4).text() == "High"
        assert widget.table.item(1, 4).text() == "Low"
    
    def test_filter_components_all(self, qapp, mock_soup_service, sample_component):
        """Test filtering components - show all."""
        mock_soup_service.get_all_components.return_value = [sample_component]
        
        widget = SOUPWidget(mock_soup_service)
        widget.criticality_filter.setCurrentText("All Components")
        widget.filter_components()
        
        mock_soup_service.get_all_components.assert_called()
        assert widget.table.rowCount() == 1
    
    def test_filter_components_by_criticality(self, qapp, mock_soup_service, sample_component):
        """Test filtering components by criticality."""
        mock_soup_service.get_components_by_criticality.return_value = [sample_component]
        
        widget = SOUPWidget(mock_soup_service)
        widget.criticality_filter.setCurrentText("High Criticality")
        widget.filter_components()
        
        mock_soup_service.get_components_by_criticality.assert_called_with("High")
    
    def test_selection_changed_enables_buttons(self, qapp, mock_soup_service, sample_component):
        """Test that button states change with selection."""
        mock_soup_service.get_all_components.return_value = [sample_component]
        
        widget = SOUPWidget(mock_soup_service)
        widget.refresh_table()
        
        # Initially no selection, buttons should be disabled
        assert not widget.edit_button.isEnabled()
        assert not widget.delete_button.isEnabled()
        
        # Select first row
        widget.table.selectRow(0)
        widget.on_selection_changed()
        
        # Buttons should now be enabled
        assert widget.edit_button.isEnabled()
        assert widget.delete_button.isEnabled()
    
    @patch('medical_analyzer.ui.soup_widget.SOUPComponentDialog')
    def test_add_component_success(self, mock_dialog_class, qapp, mock_soup_service):
        """Test successful component addition."""
        # Setup mock dialog
        mock_dialog = Mock()
        mock_dialog.exec.return_value = 1  # QDialog.Accepted
        mock_component = Mock(spec=SOUPComponent)
        mock_component.name = "New Component"
        mock_dialog.get_component_data.return_value = mock_component
        mock_dialog_class.return_value = mock_dialog
        
        # Setup mock service
        mock_soup_service.add_component.return_value = "new-id"
        mock_soup_service.get_all_components.return_value = []
        
        widget = SOUPWidget(mock_soup_service)
        widget.add_component()
        
        # Verify dialog was created and service was called
        mock_dialog_class.assert_called_once_with(widget)
        mock_soup_service.add_component.assert_called_once_with(mock_component)
        
        # Verify signal was emitted
        # Note: In a real test, you'd connect to the signal and verify it was emitted
    
    @patch('medical_analyzer.ui.soup_widget.SOUPComponentDialog')
    def test_add_component_cancelled(self, mock_dialog_class, qapp, mock_soup_service):
        """Test cancelled component addition."""
        # Setup mock dialog to return rejected
        mock_dialog = Mock()
        mock_dialog.exec.return_value = 0  # QDialog.Rejected
        mock_dialog_class.return_value = mock_dialog
        
        widget = SOUPWidget(mock_soup_service)
        widget.add_component()
        
        # Service should not be called
        mock_soup_service.add_component.assert_not_called()
    
    @patch('medical_analyzer.ui.soup_widget.QMessageBox.critical')
    @patch('medical_analyzer.ui.soup_widget.SOUPComponentDialog')
    def test_add_component_service_error(self, mock_dialog_class, mock_msgbox, qapp, mock_soup_service):
        """Test component addition with service error."""
        # Setup mock dialog
        mock_dialog = Mock()
        mock_dialog.exec.return_value = 1  # QDialog.Accepted
        mock_component = Mock(spec=SOUPComponent)
        mock_dialog.get_component_data.return_value = mock_component
        mock_dialog_class.return_value = mock_dialog
        
        # Setup service to raise error
        mock_soup_service.add_component.side_effect = Exception("Service error")
        
        widget = SOUPWidget(mock_soup_service)
        widget.add_component()
        
        # Error message should be shown
        mock_msgbox.assert_called_once()
    
    def test_get_selected_component_id_with_selection(self, qapp, mock_soup_service, sample_component):
        """Test getting selected component ID when row is selected."""
        mock_soup_service.get_all_components.return_value = [sample_component]
        
        widget = SOUPWidget(mock_soup_service)
        widget.refresh_table()
        widget.table.selectRow(0)
        
        selected_id = widget.get_selected_component_id()
        assert selected_id == sample_component.id
    
    def test_get_selected_component_id_no_selection(self, qapp, mock_soup_service):
        """Test getting selected component ID when no row is selected."""
        widget = SOUPWidget(mock_soup_service)
        
        selected_id = widget.get_selected_component_id()
        assert selected_id is None
    
    def test_get_component_count(self, qapp, mock_soup_service, sample_component):
        """Test getting component count."""
        mock_soup_service.get_all_components.return_value = [sample_component]
        
        widget = SOUPWidget(mock_soup_service)
        widget.refresh_table()
        
        count = widget.get_component_count()
        assert count == 1
    
    @patch('medical_analyzer.ui.soup_widget.QMessageBox.question')
    def test_delete_component_confirmed(self, mock_msgbox, qapp, mock_soup_service, sample_component):
        """Test component deletion when confirmed."""
        mock_msgbox.return_value = QMessageBox.StandardButton.Yes
        mock_soup_service.get_all_components.return_value = [sample_component]
        mock_soup_service.delete_component.return_value = True
        
        widget = SOUPWidget(mock_soup_service)
        widget.refresh_table()
        widget.table.selectRow(0)
        widget.delete_component()
        
        mock_soup_service.delete_component.assert_called_once_with(sample_component.id)
    
    @patch('medical_analyzer.ui.soup_widget.QMessageBox.question')
    def test_delete_component_cancelled(self, mock_msgbox, qapp, mock_soup_service, sample_component):
        """Test component deletion when cancelled."""
        mock_msgbox.return_value = QMessageBox.StandardButton.No
        mock_soup_service.get_all_components.return_value = [sample_component]
        
        widget = SOUPWidget(mock_soup_service)
        widget.refresh_table()
        widget.table.selectRow(0)
        widget.delete_component()
        
        mock_soup_service.delete_component.assert_not_called()