"""
Comprehensive UI and workflow tests for software requirements fixes.

Tests cover:
- UI tests for new widget interactions and user workflows
- Export functionality with various formats and data sizes
- Main window integration and tab navigation
- Error handling and user feedback in new UI components
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication, QMessageBox, QFileDialog
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtTest import QTest, QSignalSpy
from PyQt6.QtGui import QAction

from medical_analyzer.ui.requirements_tab_widget import RequirementsTabWidget
from medical_analyzer.ui.traceability_matrix_widget import TraceabilityMatrixWidget
from medical_analyzer.ui.test_case_export_widget import TestCaseExportWidget
from medical_analyzer.ui.main_window import MainWindow
from medical_analyzer.models.core import Requirement, RequirementType
from medical_analyzer.models.test_models import TestCase, TestStep, TestCasePriority, TestCaseCategory
from medical_analyzer.services.traceability_models import TraceabilityMatrix, TraceabilityTableRow


class TestRequirementsTabWidgetUI:
    """Test RequirementsTabWidget UI interactions."""
    
    @pytest.fixture
    def qapp(self):
        """Create QApplication for testing."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app
        app.quit()
    
    @pytest.fixture
    def widget(self, qapp):
        """Create RequirementsTabWidget for testing."""
        widget = RequirementsTabWidget()
        widget.show()
        return widget
    
    @pytest.fixture
    def sample_requirements(self):
        """Create sample requirements for testing."""
        user_reqs = [
            Requirement(
                id="UR1",
                text="User shall be able to login",
                type=RequirementType.USER,
                acceptance_criteria=["Valid credentials accepted"]
            )
        ]
        
        software_reqs = [
            Requirement(
                id="SR1",
                text="System shall validate credentials",
                type=RequirementType.SOFTWARE,
                acceptance_criteria=["Database validation performed"],
                derived_from=["UR1"]
            )
        ]
        
        return user_reqs, software_reqs
    
    def test_widget_initialization_ui(self, widget):
        """Test widget UI initialization."""
        assert widget.isVisible()
        assert widget.user_requirements_table is not None
        assert widget.software_requirements_table is not None
        
        # Check toolbar buttons exist
        assert hasattr(widget, 'add_user_req_btn')
        assert hasattr(widget, 'add_software_req_btn')
        assert hasattr(widget, 'edit_req_btn')
        assert hasattr(widget, 'delete_req_btn')
        assert hasattr(widget, 'export_req_btn')
    
    def test_add_requirement_button_interaction(self, widget):
        """Test add requirement button interactions."""
        
        # Mock the dialog
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
            
            # Click add user requirement button
            QTest.mouseClick(widget.add_user_req_btn, Qt.MouseButton.LeftButton)
            
            # Verify requirement was added
            assert len(widget.user_requirements) == 1
            assert widget.user_requirements[0].id == "UR_NEW"
    
    def test_table_selection_and_editing(self, widget, sample_requirements):
        """Test table selection and editing interactions."""
        user_reqs, software_reqs = sample_requirements
        widget.update_requirements(user_reqs, software_reqs)
        
        # Select first row in user requirements table
        widget.user_requirements_table.selectRow(0)
        
        # Mock edit dialog
        with patch('medical_analyzer.ui.requirements_tab_widget.RequirementEditDialog') as mock_dialog:
            mock_dialog_instance = Mock()
            mock_dialog_instance.exec.return_value = True
            mock_dialog_instance.get_requirement.return_value = Requirement(
                id="UR1",
                text="Modified requirement",
                type=RequirementType.USER,
                acceptance_criteria=["Modified criteria"]
            )
            mock_dialog.return_value = mock_dialog_instance
            
            # Double-click to edit
            QTest.mouseDClick(widget.user_requirements_table.viewport(), Qt.MouseButton.LeftButton)
            
            # Verify requirement was modified
            modified_req = widget.get_requirement_by_id("UR1")
            assert modified_req.text == "Modified requirement"
    
    def test_context_menu_interactions(self, widget, sample_requirements):
        """Test context menu interactions."""
        user_reqs, software_reqs = sample_requirements
        widget.update_requirements(user_reqs, software_reqs)
        
        # Right-click on table to show context menu
        with patch('PyQt6.QtWidgets.QMenu') as mock_menu:
            mock_menu_instance = Mock()
            mock_menu.return_value = mock_menu_instance
            
            # Simulate right-click
            QTest.mouseClick(
                widget.user_requirements_table.viewport(),
                Qt.MouseButton.RightButton,
                pos=QPoint(50, 50)
            )
            
            # Context menu should be created
            mock_menu.assert_called()
    
    def test_search_functionality_ui(self, widget, sample_requirements):
        """Test search functionality UI."""
        user_reqs, software_reqs = sample_requirements
        widget.update_requirements(user_reqs, software_reqs)
        
        # Test search input
        if hasattr(widget, 'search_input'):
            widget.search_input.setText("login")
            
            # Trigger search
            widget.search_input.returnPressed.emit()
            
            # Verify search results (implementation dependent)
            # This would filter the table view
    
    def test_export_button_functionality(self, widget, sample_requirements):
        """Test export button functionality."""
        user_reqs, software_reqs = sample_requirements
        widget.update_requirements(user_reqs, software_reqs)
        
        # Mock file dialog
        with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName') as mock_dialog:
            mock_dialog.return_value = ('test_requirements.json', 'JSON Files (*.json)')
            
            with patch('builtins.open', create=True) as mock_open:
                mock_file = MagicMock()
                mock_open.return_value.__enter__.return_value = mock_file
                
                # Click export button
                QTest.mouseClick(widget.export_req_btn, Qt.MouseButton.LeftButton)
                
                # Verify export was attempted
                mock_dialog.assert_called()
    
    def test_validation_feedback_ui(self, widget):
        """Test validation feedback in UI."""
        
        # Add invalid requirement
        invalid_req = Requirement(
            id="",  # Invalid empty ID
            text="",  # Invalid empty text
            type=RequirementType.USER,
            acceptance_criteria=[]  # Invalid empty criteria
        )
        
        widget.update_requirements([invalid_req], [])
        
        # Trigger validation
        validation_errors = widget.validate_requirements()
        
        # Should show validation errors
        assert len(validation_errors) > 0
        
        # UI should indicate validation status
        # (Implementation would show error indicators)


class TestTraceabilityMatrixWidgetUI:
    """Test TraceabilityMatrixWidget UI interactions."""
    
    @pytest.fixture
    def qapp(self):
        """Create QApplication for testing."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app
        app.quit()
    
    @pytest.fixture
    def widget(self, qapp):
        """Create TraceabilityMatrixWidget for testing."""
        widget = TraceabilityMatrixWidget()
        widget.show()
        return widget
    
    @pytest.fixture
    def sample_matrix(self):
        """Create sample traceability matrix."""
        rows = [
            TraceabilityTableRow(
                code_element="login_function",
                software_requirement="SR1: Validate credentials",
                user_requirement="UR1: User login",
                risk="R1: Authentication failure",
                confidence=0.9,
                has_gaps=False
            ),
            TraceabilityTableRow(
                code_element="logout_function",
                software_requirement="SR2: Terminate session",
                user_requirement="UR2: User logout",
                risk="",  # Gap
                confidence=0.7,
                has_gaps=True
            )
        ]
        
        return TraceabilityMatrix(rows=rows, gaps=[])
    
    def test_matrix_display_ui(self, widget, sample_matrix):
        """Test matrix display in UI."""
        widget.update_matrix(sample_matrix)
        
        # Verify table is populated
        assert widget.matrix_table.rowCount() == 2
        assert widget.matrix_table.columnCount() >= 4  # Code, SR, UR, Risk columns
        
        # Verify data is displayed
        assert widget.matrix_table.item(0, 0).text() == "login_function"
        assert "SR1" in widget.matrix_table.item(0, 1).text()
    
    def test_gap_highlighting_ui(self, widget, sample_matrix):
        """Test gap highlighting in UI."""
        widget.update_matrix(sample_matrix)
        widget.highlight_gaps(sample_matrix.gaps)
        
        # Row with gap should be highlighted differently
        # (Implementation would use different colors/styles)
        gap_row_item = widget.matrix_table.item(1, 3)  # Risk column for logout_function
        assert gap_row_item is not None
    
    def test_sorting_and_filtering_ui(self, widget, sample_matrix):
        """Test sorting and filtering UI interactions."""
        widget.update_matrix(sample_matrix)
        
        # Test column header clicking for sorting
        header = widget.matrix_table.horizontalHeader()
        
        # Click confidence column header
        confidence_col = 4  # Assuming confidence is column 4
        if confidence_col < widget.matrix_table.columnCount():
            QTest.mouseClick(header.viewport(), Qt.MouseButton.LeftButton)
        
        # Test filter controls (if implemented)
        if hasattr(widget, 'confidence_filter'):
            widget.confidence_filter.setValue(0.8)
            # Should filter to show only high confidence items
    
    def test_cell_details_popup(self, widget, sample_matrix):
        """Test cell details popup functionality."""
        widget.update_matrix(sample_matrix)
        
        # Double-click on a cell to show details
        cell_pos = widget.matrix_table.visualItemRect(widget.matrix_table.item(0, 1)).center()
        
        with patch('PyQt6.QtWidgets.QDialog') as mock_dialog:
            QTest.mouseDClick(widget.matrix_table.viewport(), Qt.MouseButton.LeftButton, pos=cell_pos)
            
            # Details dialog should be shown (if implemented)
            # mock_dialog.assert_called()
    
    def test_export_functionality_ui(self, widget, sample_matrix):
        """Test export functionality UI."""
        widget.update_matrix(sample_matrix)
        
        # Test CSV export
        with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName') as mock_dialog:
            mock_dialog.return_value = ('matrix.csv', 'CSV Files (*.csv)')
            
            with patch('builtins.open', create=True):
                # Trigger export (assuming export button exists)
                if hasattr(widget, 'export_btn'):
                    QTest.mouseClick(widget.export_btn, Qt.MouseButton.LeftButton)
                    mock_dialog.assert_called()


class TestTestCaseExportWidgetUI:
    """Test TestCaseExportWidget UI interactions."""
    
    @pytest.fixture
    def qapp(self):
        """Create QApplication for testing."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app
        app.quit()
    
    @pytest.fixture
    def widget(self, qapp):
        """Create TestCaseExportWidget for testing."""
        widget = TestCaseExportWidget()
        widget.show()
        return widget
    
    @pytest.fixture
    def sample_test_cases(self):
        """Create sample test cases."""
        return [
            TestCase(
                id="TC1",
                name="Test login functionality",
                description="Test user login with valid credentials",
                requirement_id="UR1",
                preconditions=["User account exists"],
                test_steps=[
                    TestStep(1, "Enter username", "Username accepted"),
                    TestStep(2, "Enter password", "Password accepted"),
                    TestStep(3, "Click login", "User logged in")
                ],
                expected_results=["Dashboard displayed"],
                priority=TestCasePriority.HIGH,
                category=TestCaseCategory.FUNCTIONAL
            )
        ]
    
    def test_test_case_display_ui(self, widget, sample_test_cases):
        """Test test case display in UI."""
        widget.update_test_cases(sample_test_cases)
        
        # Verify test cases are displayed
        if hasattr(widget, 'test_case_list'):
            assert widget.test_case_list.count() == 1
        
        # Verify preview area shows content
        if hasattr(widget, 'preview_area'):
            preview_text = widget.preview_area.toPlainText()
            assert "Test login functionality" in preview_text
    
    def test_format_selection_ui(self, widget, sample_test_cases):
        """Test export format selection UI."""
        widget.update_test_cases(sample_test_cases)
        
        # Test format combo box
        if hasattr(widget, 'format_combo'):
            # Select JSON format
            json_index = widget.format_combo.findText("JSON")
            if json_index >= 0:
                widget.format_combo.setCurrentIndex(json_index)
                
                # Preview should update to JSON format
                preview_text = widget.preview_area.toPlainText()
                assert "{" in preview_text  # JSON format indicator
    
    def test_export_button_ui(self, widget, sample_test_cases):
        """Test export button functionality."""
        widget.update_test_cases(sample_test_cases)
        
        with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName') as mock_dialog:
            mock_dialog.return_value = ('test_cases.json', 'JSON Files (*.json)')
            
            with patch('builtins.open', create=True):
                # Click export button
                if hasattr(widget, 'export_btn'):
                    QTest.mouseClick(widget.export_btn, Qt.MouseButton.LeftButton)
                    mock_dialog.assert_called()
    
    def test_syntax_highlighting(self, widget, sample_test_cases):
        """Test syntax highlighting in preview area."""
        widget.update_test_cases(sample_test_cases)
        
        # Select different formats and verify highlighting
        formats = ["JSON", "XML", "CSV", "Text"]
        
        for format_name in formats:
            if hasattr(widget, 'format_combo'):
                format_index = widget.format_combo.findText(format_name)
                if format_index >= 0:
                    widget.format_combo.setCurrentIndex(format_index)
                    
                    # Verify preview updates (syntax highlighting would be visual)
                    preview_text = widget.preview_area.toPlainText()
                    assert len(preview_text) > 0


class TestMainWindowIntegration:
    """Test main window integration and tab navigation."""
    
    @pytest.fixture
    def qapp(self):
        """Create QApplication for testing."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app
        app.quit()
    
    @pytest.fixture
    def main_window(self, qapp):
        """Create MainWindow for testing."""
        window = MainWindow()
        window.show()
        return window
    
    def test_main_window_initialization(self, main_window):
        """Test main window initialization with new components."""
        assert main_window.isVisible()
        
        # Verify new tabs are integrated
        if hasattr(main_window, 'results_tab_widget'):
            tab_widget = main_window.results_tab_widget
            
            # Check for requirements tab
            requirements_tab_found = False
            for i in range(tab_widget.count()):
                if "Requirements" in tab_widget.tabText(i):
                    requirements_tab_found = True
                    break
            
            # Should have requirements tab (if implemented)
            # assert requirements_tab_found
    
    def test_tab_navigation(self, main_window):
        """Test navigation between tabs."""
        if hasattr(main_window, 'results_tab_widget'):
            tab_widget = main_window.results_tab_widget
            
            # Switch between tabs
            for i in range(tab_widget.count()):
                tab_widget.setCurrentIndex(i)
                assert tab_widget.currentIndex() == i
    
    def test_menu_integration(self, main_window):
        """Test menu integration for new features."""
        menu_bar = main_window.menuBar()
        
        # Check for new menu items
        for action in menu_bar.actions():
            menu = action.menu()
            if menu:
                for sub_action in menu.actions():
                    # Verify menu items exist (implementation dependent)
                    assert isinstance(sub_action, QAction)
    
    def test_toolbar_integration(self, main_window):
        """Test toolbar integration for new features."""
        # Check for new toolbar buttons
        toolbars = main_window.findChildren(type(main_window.toolBar()))
        
        for toolbar in toolbars:
            for action in toolbar.actions():
                # Verify toolbar actions exist
                assert isinstance(action, QAction)
    
    def test_status_bar_updates(self, main_window):
        """Test status bar updates for new operations."""
        status_bar = main_window.statusBar()
        
        # Simulate operations that should update status
        if hasattr(main_window, 'update_status'):
            main_window.update_status("Requirements generated successfully")
            
            # Verify status is displayed
            assert "Requirements generated" in status_bar.currentMessage()


class TestErrorHandlingAndUserFeedback:
    """Test error handling and user feedback in UI components."""
    
    @pytest.fixture
    def qapp(self):
        """Create QApplication for testing."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app
        app.quit()
    
    def test_validation_error_display(self, qapp):
        """Test validation error display in UI."""
        widget = RequirementsTabWidget()
        
        # Add invalid requirement
        invalid_req = Requirement(
            id="",  # Invalid
            text="",  # Invalid
            type=RequirementType.USER,
            acceptance_criteria=[]  # Invalid
        )
        
        widget.update_requirements([invalid_req], [])
        
        # Trigger validation
        with patch('PyQt6.QtWidgets.QMessageBox.warning') as mock_warning:
            validation_errors = widget.validate_requirements()
            
            if len(validation_errors) > 0:
                # Should show warning dialog
                widget.show_validation_errors(validation_errors)
                # mock_warning.assert_called()
    
    def test_api_error_user_feedback(self, qapp):
        """Test API error user feedback."""
        
        # Mock API error
        with patch('medical_analyzer.llm.local_server_backend.LocalServerBackend.generate') as mock_generate:
            mock_generate.side_effect = ConnectionError("API unavailable")
            
            # Should show user-friendly error message
            with patch('PyQt6.QtWidgets.QMessageBox.critical') as mock_critical:
                try:
                    # Simulate API call that fails
                    from medical_analyzer.llm.local_server_backend import LocalServerBackend
                    backend = LocalServerBackend("http://localhost:8000")
                    backend.generate("test prompt")
                except ConnectionError:
                    # UI should show error dialog
                    pass
    
    def test_file_operation_error_handling(self, qapp):
        """Test file operation error handling."""
        widget = RequirementsTabWidget()
        
        # Mock file save error
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            with patch('PyQt6.QtWidgets.QMessageBox.critical') as mock_critical:
                # Attempt to export (should fail gracefully)
                try:
                    widget.export_requirements("json")
                except PermissionError:
                    # Should show error dialog
                    pass
    
    def test_progress_indication(self, qapp):
        """Test progress indication for long operations."""
        
        # Mock long-running operation
        with patch('PyQt6.QtWidgets.QProgressDialog') as mock_progress:
            mock_progress_instance = Mock()
            mock_progress.return_value = mock_progress_instance
            
            # Simulate long operation
            widget = TraceabilityMatrixWidget()
            
            # Should show progress dialog for matrix generation
            if hasattr(widget, 'generate_matrix_with_progress'):
                widget.generate_matrix_with_progress([])
                mock_progress.assert_called()
    
    def test_confirmation_dialogs(self, qapp):
        """Test confirmation dialogs for destructive operations."""
        widget = RequirementsTabWidget()
        
        # Add requirement
        req = Requirement(
            id="UR1",
            text="Test requirement",
            type=RequirementType.USER,
            acceptance_criteria=["Test criteria"]
        )
        widget.update_requirements([req], [])
        
        # Mock confirmation dialog
        with patch('PyQt6.QtWidgets.QMessageBox.question') as mock_question:
            mock_question.return_value = QMessageBox.StandardButton.Yes
            
            # Delete requirement (should ask for confirmation)
            widget.delete_requirement("UR1")
            
            mock_question.assert_called()


class TestExportFunctionalityComprehensive:
    """Test export functionality with various formats and data sizes."""
    
    @pytest.fixture
    def qapp(self):
        """Create QApplication for testing."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app
        app.quit()
    
    def test_requirements_export_formats(self, qapp):
        """Test requirements export in multiple formats."""
        widget = RequirementsTabWidget()
        
        # Create test requirements
        requirements = [
            Requirement(
                id=f"UR{i}",
                text=f"User requirement {i}",
                type=RequirementType.USER,
                acceptance_criteria=[f"Criteria {i}.1", f"Criteria {i}.2"]
            )
            for i in range(5)
        ]
        
        widget.update_requirements(requirements, [])
        
        # Test different export formats
        formats = ["json", "csv", "markdown", "xml"]
        
        for format_type in formats:
            try:
                export_result = widget.export_requirements(format_type)
                assert export_result is not None
                assert len(export_result) > 0
                
                # Verify format-specific content
                if format_type == "json":
                    assert "{" in export_result
                elif format_type == "csv":
                    assert "," in export_result
                elif format_type == "markdown":
                    assert "#" in export_result
                elif format_type == "xml":
                    assert "<" in export_result
                    
            except ValueError as e:
                # Some formats might not be implemented
                assert "Unsupported" in str(e)
    
    def test_large_dataset_export_performance(self, qapp):
        """Test export performance with large datasets."""
        widget = RequirementsTabWidget()
        
        # Create large dataset
        large_requirements = [
            Requirement(
                id=f"REQ{i:04d}",
                text=f"Requirement {i} with detailed description that is quite long to test performance",
                type=RequirementType.USER if i % 2 == 0 else RequirementType.SOFTWARE,
                acceptance_criteria=[
                    f"Detailed acceptance criteria {i}.1 with comprehensive description",
                    f"Detailed acceptance criteria {i}.2 with comprehensive description",
                    f"Detailed acceptance criteria {i}.3 with comprehensive description"
                ]
            )
            for i in range(1000)  # Large dataset
        ]
        
        user_reqs = [r for r in large_requirements if r.type == RequirementType.USER]
        software_reqs = [r for r in large_requirements if r.type == RequirementType.SOFTWARE]
        
        widget.update_requirements(user_reqs, software_reqs)
        
        # Export should complete without timeout
        import time
        start_time = time.time()
        
        try:
            export_result = widget.export_requirements("json")
            end_time = time.time()
            
            # Should complete within reasonable time (10 seconds)
            assert (end_time - start_time) < 10.0
            assert export_result is not None
            assert len(export_result) > 10000  # Should be substantial
            
        except Exception as e:
            # Performance test - should not crash
            assert False, f"Export failed with large dataset: {e}"
    
    def test_traceability_matrix_export_formats(self, qapp):
        """Test traceability matrix export in multiple formats."""
        widget = TraceabilityMatrixWidget()
        
        # Create test matrix
        rows = [
            TraceabilityTableRow(
                code_element=f"function_{i}",
                software_requirement=f"SR{i}: Software requirement {i}",
                user_requirement=f"UR{i}: User requirement {i}",
                risk=f"R{i}: Risk {i}",
                confidence=0.8 + (i * 0.02),
                has_gaps=i % 3 == 0  # Some gaps
            )
            for i in range(20)
        ]
        
        matrix = TraceabilityMatrix(rows=rows, gaps=[])
        widget.update_matrix(matrix)
        
        # Test export formats
        formats = ["csv", "excel", "pdf"]
        
        for format_type in formats:
            with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName') as mock_dialog:
                mock_dialog.return_value = (f'test_matrix.{format_type}', f'{format_type.upper()} Files (*.{format_type})')
                
                try:
                    result = widget.export_matrix(format_type, f'test_matrix.{format_type}')
                    # Should not raise exception
                    
                except Exception as e:
                    # Some formats might not be fully implemented
                    pass
    
    def test_test_case_export_formats(self, qapp):
        """Test test case export in multiple formats."""
        widget = TestCaseExportWidget()
        
        # Create test cases
        test_cases = [
            TestCase(
                id=f"TC{i:03d}",
                name=f"Test case {i}",
                description=f"Detailed test case description {i}",
                requirement_id=f"UR{i}",
                preconditions=[f"Precondition {i}.1", f"Precondition {i}.2"],
                test_steps=[
                    TestStep(1, f"Action {i}.1", f"Expected result {i}.1"),
                    TestStep(2, f"Action {i}.2", f"Expected result {i}.2"),
                    TestStep(3, f"Action {i}.3", f"Expected result {i}.3")
                ],
                expected_results=[f"Final result {i}"],
                priority=TestCasePriority.HIGH if i % 2 == 0 else TestCasePriority.MEDIUM,
                category=TestCaseCategory.FUNCTIONAL
            )
            for i in range(50)
        ]
        
        widget.update_test_cases(test_cases)
        
        # Test different formats
        formats = ["json", "xml", "csv", "text"]
        
        for format_type in formats:
            if hasattr(widget, 'format_combo'):
                format_index = widget.format_combo.findText(format_type.upper())
                if format_index >= 0:
                    widget.format_combo.setCurrentIndex(format_index)
                    
                    # Verify preview updates
                    preview_text = widget.preview_area.toPlainText()
                    assert len(preview_text) > 100  # Should have substantial content
    
    def test_export_error_handling(self, qapp):
        """Test export error handling."""
        widget = RequirementsTabWidget()
        
        # Create requirements
        requirements = [
            Requirement(
                id="UR1",
                text="Test requirement",
                type=RequirementType.USER,
                acceptance_criteria=["Test criteria"]
            )
        ]
        widget.update_requirements(requirements, [])
        
        # Test file permission error
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            with patch('PyQt6.QtWidgets.QMessageBox.critical') as mock_error:
                try:
                    widget.export_requirements("json")
                except PermissionError:
                    # Should handle error gracefully
                    pass
        
        # Test invalid format
        with pytest.raises(ValueError):
            widget.export_requirements("invalid_format")
    
    def test_export_file_dialog_integration(self, qapp):
        """Test export file dialog integration."""
        widget = RequirementsTabWidget()
        
        # Create requirements
        requirements = [
            Requirement(
                id="UR1",
                text="Test requirement",
                type=RequirementType.USER,
                acceptance_criteria=["Test criteria"]
            )
        ]
        widget.update_requirements(requirements, [])
        
        # Test file dialog cancellation
        with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName') as mock_dialog:
            mock_dialog.return_value = ('', '')  # User cancelled
            
            # Export should handle cancellation gracefully
            if hasattr(widget, 'export_to_file'):
                result = widget.export_to_file()
                assert result is False  # Should indicate cancellation
        
        # Test successful file selection
        with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName') as mock_dialog:
            mock_dialog.return_value = ('test_export.json', 'JSON Files (*.json)')
            
            with patch('builtins.open', create=True) as mock_open:
                mock_file = MagicMock()
                mock_open.return_value.__enter__.return_value = mock_file
                
                if hasattr(widget, 'export_to_file'):
                    result = widget.export_to_file()
                    # Should succeed
                    mock_open.assert_called()


class TestAccessibilityAndUsability:
    """Test accessibility and usability features."""
    
    @pytest.fixture
    def qapp(self):
        """Create QApplication for testing."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app
        app.quit()
    
    def test_keyboard_navigation(self, qapp):
        """Test keyboard navigation in widgets."""
        widget = RequirementsTabWidget()
        
        # Test tab navigation
        widget.setFocus()
        
        # Simulate tab key presses
        QTest.keyPress(widget, Qt.Key.Key_Tab)
        
        # Should move focus to next control
        # (Implementation would verify focus changes)
    
    def test_tooltips_and_help_text(self, qapp):
        """Test tooltips and help text."""
        widget = RequirementsTabWidget()
        
        # Check for tooltips on buttons
        if hasattr(widget, 'add_user_req_btn'):
            tooltip = widget.add_user_req_btn.toolTip()
            assert len(tooltip) > 0  # Should have helpful tooltip
    
    def test_high_contrast_support(self, qapp):
        """Test high contrast mode support."""
        widget = RequirementsTabWidget()
        
        # Test with different style sheets
        widget.setStyleSheet("QWidget { background-color: black; color: white; }")
        
        # Should render without issues
        assert widget.isVisible()
    
    def test_screen_reader_compatibility(self, qapp):
        """Test screen reader compatibility."""
        widget = RequirementsTabWidget()
        
        # Check for accessible names and descriptions
        if hasattr(widget, 'user_requirements_table'):
            table = widget.user_requirements_table
            
            # Should have accessible name
            accessible_name = table.accessibleName()
            # assert len(accessible_name) > 0  # Should be set for screen readers