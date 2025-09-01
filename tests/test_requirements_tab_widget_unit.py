"""
Unit tests for RequirementsTabWidget class.

Tests cover:
- CRUD operations for requirements
- Validation logic
- Signal emissions
- Export functionality
- Error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication, QTableWidget
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QSignalSpy
from medical_analyzer.ui.requirements_tab_widget import RequirementsTabWidget
from medical_analyzer.models.core import Requirement, RequirementType


class TestRequirementsTabWidget:
    """Test suite for RequirementsTabWidget functionality."""
    
    @pytest.fixture
    def widget(self, qapp):
        """Create RequirementsTabWidget for testing."""
        widget = RequirementsTabWidget()
        return widget
    
    @pytest.fixture
    def sample_requirements(self):
        """Create sample requirements for testing."""
        user_reqs = [
            Requirement(
                id="UR1",
                text="User shall be able to login",
                type=RequirementType.USER,
                acceptance_criteria=["Valid credentials accepted", "Invalid credentials rejected"],
                priority="high"
            ),
            Requirement(
                id="UR2", 
                text="User shall be able to logout",
                type=RequirementType.USER,
                acceptance_criteria=["Session terminated on logout"],
                priority="medium"
            )
        ]
        
        software_reqs = [
            Requirement(
                id="SR1",
                text="System shall validate user credentials",
                type=RequirementType.SOFTWARE,
                acceptance_criteria=["Credentials checked against database"],
                derived_from=["UR1"],
                priority="high"
            ),
            Requirement(
                id="SR2",
                text="System shall terminate user session",
                type=RequirementType.SOFTWARE,
                acceptance_criteria=["Session data cleared"],
                derived_from=["UR2"],
                priority="medium"
            )
        ]
        
        return user_reqs, software_reqs
    
    def test_widget_initialization(self, widget):
        """Test widget initialization and basic structure."""
        assert widget is not None
        assert hasattr(widget, 'user_requirements_table')
        assert hasattr(widget, 'software_requirements_table')
        assert hasattr(widget, 'user_requirements')
        assert hasattr(widget, 'software_requirements')
        assert len(widget.user_requirements) == 0
        assert len(widget.software_requirements) == 0
    
    def test_update_requirements(self, widget, sample_requirements):
        """Test updating requirements data."""
        user_reqs, software_reqs = sample_requirements
        
        # Set up signal spy
        spy = QSignalSpy(widget.requirements_updated)
        
        widget.update_requirements(user_reqs, software_reqs)
        
        assert len(widget.user_requirements) == 2
        assert len(widget.software_requirements) == 2
        assert widget.user_requirements[0].id == "UR1"
        assert widget.software_requirements[0].id == "SR1"
        
        # Check that signal was emitted
        assert len(spy) == 1
    
    def test_add_user_requirement(self, widget):
        """Test adding new user requirement."""
        initial_count = len(widget.user_requirements)
        
        # Mock the edit dialog
        with patch('medical_analyzer.ui.requirements_tab_widget.RequirementEditDialog') as mock_dialog:
            mock_dialog_instance = Mock()
            mock_dialog_instance.exec.return_value = True
            mock_dialog_instance.get_requirement.return_value = Requirement(
                id="UR_NEW",
                text="New user requirement",
                type=RequirementType.USER,
                acceptance_criteria=["New criteria"]
            )
            mock_dialog.return_value = mock_dialog_instance
            
            widget.add_user_requirement()
            
            assert len(widget.user_requirements) == initial_count + 1
            assert widget.user_requirements[-1].id == "UR_NEW"
    
    def test_add_software_requirement(self, widget):
        """Test adding new software requirement."""
        initial_count = len(widget.software_requirements)
        
        # Mock the edit dialog
        with patch('medical_analyzer.ui.requirements_tab_widget.RequirementEditDialog') as mock_dialog:
            mock_dialog_instance = Mock()
            mock_dialog_instance.exec.return_value = True
            mock_dialog_instance.get_requirement.return_value = Requirement(
                id="SR_NEW",
                text="New software requirement",
                type=RequirementType.SOFTWARE,
                acceptance_criteria=["New criteria"],
                derived_from=["UR1"]
            )
            mock_dialog.return_value = mock_dialog_instance
            
            widget.add_software_requirement()
            
            assert len(widget.software_requirements) == initial_count + 1
            assert widget.software_requirements[-1].id == "SR_NEW"
    
    def test_edit_requirement(self, widget, sample_requirements):
        """Test editing existing requirement."""
        user_reqs, software_reqs = sample_requirements
        widget.update_requirements(user_reqs, software_reqs)
        
        # Mock the edit dialog
        with patch('medical_analyzer.ui.requirements_tab_widget.RequirementEditDialog') as mock_dialog:
            mock_dialog_instance = Mock()
            mock_dialog_instance.exec.return_value = True
            
            # Return modified requirement
            modified_req = Requirement(
                id="UR1",
                text="Modified user requirement",
                type=RequirementType.USER,
                acceptance_criteria=["Modified criteria"],
                priority="low"
            )
            mock_dialog_instance.get_requirement.return_value = modified_req
            mock_dialog.return_value = mock_dialog_instance
            
            widget.edit_requirement("UR1")
            
            # Find the modified requirement
            modified = next(req for req in widget.user_requirements if req.id == "UR1")
            assert modified.text == "Modified user requirement"
            assert modified.priority == "low"
    
    def test_delete_requirement(self, widget, sample_requirements):
        """Test deleting requirement."""
        user_reqs, software_reqs = sample_requirements
        widget.update_requirements(user_reqs, software_reqs)
        
        initial_count = len(widget.user_requirements)
        
        # Mock confirmation dialog
        with patch('PyQt6.QtWidgets.QMessageBox.question') as mock_question:
            mock_question.return_value = mock_question.Yes
            
            widget.delete_requirement("UR1")
            
            assert len(widget.user_requirements) == initial_count - 1
            assert not any(req.id == "UR1" for req in widget.user_requirements)
    
    def test_delete_requirement_cancelled(self, widget, sample_requirements):
        """Test cancelling requirement deletion."""
        user_reqs, software_reqs = sample_requirements
        widget.update_requirements(user_reqs, software_reqs)
        
        initial_count = len(widget.user_requirements)
        
        # Mock confirmation dialog - user cancels
        with patch('PyQt6.QtWidgets.QMessageBox.question') as mock_question:
            mock_question.return_value = mock_question.No
            
            widget.delete_requirement("UR1")
            
            # Should not delete
            assert len(widget.user_requirements) == initial_count
            assert any(req.id == "UR1" for req in widget.user_requirements)
    
    def test_validate_requirements_success(self, widget, sample_requirements):
        """Test successful requirements validation."""
        user_reqs, software_reqs = sample_requirements
        widget.update_requirements(user_reqs, software_reqs)
        
        validation_errors = widget.validate_requirements()
        
        assert len(validation_errors) == 0
    
    def test_validate_requirements_with_errors(self, widget):
        """Test requirements validation with errors."""
        # Create invalid requirements
        invalid_reqs = [
            Requirement(
                id="",  # Empty ID
                text="",  # Empty text
                type=RequirementType.USER,
                acceptance_criteria=[]  # Empty criteria
            ),
            Requirement(
                id="SR1",
                text="Software requirement without derivation",
                type=RequirementType.SOFTWARE,
                acceptance_criteria=["Some criteria"],
                derived_from=[]  # Software req should derive from user req
            )
        ]
        
        widget.update_requirements(invalid_reqs, [invalid_reqs[1]])
        
        validation_errors = widget.validate_requirements()
        
        assert len(validation_errors) > 0
        assert any("empty ID" in error.lower() for error in validation_errors)
        assert any("empty text" in error.lower() for error in validation_errors)
        assert any("empty acceptance criteria" in error.lower() for error in validation_errors)
    
    def test_export_requirements_json(self, widget, sample_requirements):
        """Test exporting requirements to JSON format."""
        user_reqs, software_reqs = sample_requirements
        widget.update_requirements(user_reqs, software_reqs)
        
        json_export = widget.export_requirements("json")
        
        assert json_export is not None
        assert "UR1" in json_export
        assert "SR1" in json_export
        assert "User shall be able to login" in json_export
    
    def test_export_requirements_csv(self, widget, sample_requirements):
        """Test exporting requirements to CSV format."""
        user_reqs, software_reqs = sample_requirements
        widget.update_requirements(user_reqs, software_reqs)
        
        csv_export = widget.export_requirements("csv")
        
        assert csv_export is not None
        assert "ID,Text,Type,Priority" in csv_export
        assert "UR1" in csv_export
        assert "SR1" in csv_export
    
    def test_export_requirements_markdown(self, widget, sample_requirements):
        """Test exporting requirements to Markdown format."""
        user_reqs, software_reqs = sample_requirements
        widget.update_requirements(user_reqs, software_reqs)
        
        md_export = widget.export_requirements("markdown")
        
        assert md_export is not None
        assert "# Requirements" in md_export
        assert "## User Requirements" in md_export
        assert "## Software Requirements" in md_export
        assert "UR1" in md_export
    
    def test_export_requirements_invalid_format(self, widget, sample_requirements):
        """Test exporting with invalid format."""
        user_reqs, software_reqs = sample_requirements
        widget.update_requirements(user_reqs, software_reqs)
        
        with pytest.raises(ValueError):
            widget.export_requirements("invalid_format")
    
    def test_search_requirements(self, widget, sample_requirements):
        """Test searching requirements functionality."""
        user_reqs, software_reqs = sample_requirements
        widget.update_requirements(user_reqs, software_reqs)
        
        # Search for "login"
        results = widget.search_requirements("login")
        
        assert len(results) >= 1
        assert any("login" in req.text.lower() for req in results)
    
    def test_filter_requirements_by_priority(self, widget, sample_requirements):
        """Test filtering requirements by priority."""
        user_reqs, software_reqs = sample_requirements
        widget.update_requirements(user_reqs, software_reqs)
        
        high_priority = widget.filter_requirements_by_priority("high")
        
        assert len(high_priority) >= 1
        assert all(req.priority == "high" for req in high_priority)
    
    def test_get_requirement_by_id(self, widget, sample_requirements):
        """Test getting requirement by ID."""
        user_reqs, software_reqs = sample_requirements
        widget.update_requirements(user_reqs, software_reqs)
        
        req = widget.get_requirement_by_id("UR1")
        
        assert req is not None
        assert req.id == "UR1"
        assert req.text == "User shall be able to login"
        
        # Test non-existent ID
        non_existent = widget.get_requirement_by_id("NON_EXISTENT")
        assert non_existent is None
    
    def test_update_traceability_links(self, widget, sample_requirements):
        """Test updating traceability links between requirements."""
        user_reqs, software_reqs = sample_requirements
        widget.update_requirements(user_reqs, software_reqs)
        
        # Update traceability for SR1
        widget.update_traceability_links("SR1", ["UR1", "UR2"])
        
        sr1 = widget.get_requirement_by_id("SR1")
        assert "UR1" in sr1.derived_from
        assert "UR2" in sr1.derived_from
    
    def test_requirements_updated_signal(self, widget, sample_requirements):
        """Test that requirements_updated signal is emitted correctly."""
        user_reqs, software_reqs = sample_requirements
        
        # Set up signal spy
        spy = QSignalSpy(widget.requirements_updated)
        
        # Update requirements
        widget.update_requirements(user_reqs, software_reqs)
        
        # Signal should be emitted once
        assert len(spy) == 1
        
        # Add a requirement
        with patch('medical_analyzer.ui.requirements_tab_widget.RequirementEditDialog') as mock_dialog:
            mock_dialog_instance = Mock()
            mock_dialog_instance.exec.return_value = True
            mock_dialog_instance.get_requirement.return_value = Requirement(
                id="UR_NEW",
                text="New requirement",
                type=RequirementType.USER,
                acceptance_criteria=["Criteria"]
            )
            mock_dialog.return_value = mock_dialog_instance
            
            widget.add_user_requirement()
            
            # Signal should be emitted again
            assert len(spy) == 2
    
    def test_table_population(self, widget, sample_requirements):
        """Test that tables are properly populated with requirements."""
        user_reqs, software_reqs = sample_requirements
        widget.update_requirements(user_reqs, software_reqs)
        
        # Check user requirements table
        user_table = widget.user_requirements_table
        assert user_table.rowCount() == len(user_reqs)
        
        # Check software requirements table
        software_table = widget.software_requirements_table
        assert software_table.rowCount() == len(software_reqs)
    
    def test_requirement_selection(self, widget, sample_requirements):
        """Test requirement selection in tables."""
        user_reqs, software_reqs = sample_requirements
        widget.update_requirements(user_reqs, software_reqs)
        
        # Select first row in user requirements table
        user_table = widget.user_requirements_table
        user_table.selectRow(0)
        
        selected_req = widget.get_selected_requirement("user")
        assert selected_req is not None
        assert selected_req.id == "UR1"
    
    def test_clear_requirements(self, widget, sample_requirements):
        """Test clearing all requirements."""
        user_reqs, software_reqs = sample_requirements
        widget.update_requirements(user_reqs, software_reqs)
        
        # Verify requirements are loaded
        assert len(widget.user_requirements) > 0
        assert len(widget.software_requirements) > 0
        
        # Clear requirements
        widget.clear_requirements()
        
        # Verify requirements are cleared
        assert len(widget.user_requirements) == 0
        assert len(widget.software_requirements) == 0
        assert widget.user_requirements_table.rowCount() == 0
        assert widget.software_requirements_table.rowCount() == 0
    
    def test_requirement_statistics(self, widget, sample_requirements):
        """Test getting requirement statistics."""
        user_reqs, software_reqs = sample_requirements
        widget.update_requirements(user_reqs, software_reqs)
        
        stats = widget.get_requirement_statistics()
        
        assert stats['total_user_requirements'] == 2
        assert stats['total_software_requirements'] == 2
        assert stats['high_priority_count'] == 2  # Both UR1 and SR1 are high priority
        assert stats['medium_priority_count'] == 2  # Both UR2 and SR2 are medium priority
        assert stats['traceability_coverage'] > 0  # Should have some traceability


class TestRequirementEditDialog:
    """Test RequirementEditDialog functionality."""
    
    @pytest.fixture
    def dialog(self, qapp):
        """Create RequirementEditDialog for testing."""
        from medical_analyzer.ui.requirements_tab_widget import RequirementEditDialog
        dialog = RequirementEditDialog()
        return dialog
    
    def test_dialog_initialization(self, dialog):
        """Test dialog initialization."""
        assert dialog is not None
        assert hasattr(dialog, 'id_edit')
        assert hasattr(dialog, 'text_edit')
        assert hasattr(dialog, 'type_combo')
        assert hasattr(dialog, 'priority_combo')
    
    def test_set_requirement(self, dialog):
        """Test setting requirement data in dialog."""
        req = Requirement(
            id="TEST1",
            text="Test requirement",
            type=RequirementType.USER,
            acceptance_criteria=["Test criteria"],
            priority="high"
        )
        
        dialog.set_requirement(req)
        
        assert dialog.id_edit.text() == "TEST1"
        assert dialog.text_edit.toPlainText() == "Test requirement"
        assert dialog.priority_combo.currentText() == "high"
    
    def test_get_requirement(self, dialog):
        """Test getting requirement data from dialog."""
        # Set up dialog fields
        dialog.id_edit.setText("TEST2")
        dialog.text_edit.setPlainText("Another test requirement")
        dialog.priority_combo.setCurrentText("medium")
        
        req = dialog.get_requirement()
        
        assert req.id == "TEST2"
        assert req.text == "Another test requirement"
        assert req.priority == "medium"
    
    def test_validate_dialog_input(self, dialog):
        """Test dialog input validation."""
        # Test with empty fields
        dialog.id_edit.setText("")
        dialog.text_edit.setPlainText("")
        
        is_valid, errors = dialog.validate_input()
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("ID" in error for error in errors)
        assert any("text" in error for error in errors)
        
        # Test with valid fields
        dialog.id_edit.setText("VALID_ID")
        dialog.text_edit.setPlainText("Valid requirement text")
        
        is_valid, errors = dialog.validate_input()
        
        assert is_valid is True
        assert len(errors) == 0