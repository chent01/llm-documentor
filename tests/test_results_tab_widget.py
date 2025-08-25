"""
Tests for the ResultsTabWidget and its components.
"""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtGui import QColor
import sys

from medical_analyzer.ui.results_tab_widget import (
    ResultsTabWidget, RequirementsTab, RiskRegisterTab, 
    TraceabilityTab, TestingResultsTab, SummaryTab, TestExecutionDialog,
    RequirementEditDialog, RiskEditDialog
)


@pytest.fixture
def app():
    """Create QApplication instance for testing."""
    if not QApplication.instance():
        return QApplication(sys.argv)
    return QApplication.instance()


@pytest.fixture
def results_widget(app):
    """Create ResultsTabWidget instance for testing."""
    widget = ResultsTabWidget()
    return widget


@pytest.fixture
def requirements_tab(app):
    """Create RequirementsTab instance for testing."""
    tab = RequirementsTab()
    return tab


@pytest.fixture
def risk_tab(app):
    """Create RiskRegisterTab instance for testing."""
    tab = RiskRegisterTab()
    return tab


@pytest.fixture
def summary_tab(app):
    """Create SummaryTab instance for testing."""
    tab = SummaryTab()
    return tab


@pytest.fixture
def sample_requirements():
    """Sample requirements data for testing."""
    return {
        'user_requirements': [
            {
                'id': 'UR-001',
                'description': 'User shall be able to login',
                'acceptance_criteria': [
                    'System shall validate credentials',
                    'System shall provide feedback on invalid login'
                ]
            },
            {
                'id': 'UR-002', 
                'description': 'User shall be able to view data',
                'acceptance_criteria': ['System shall display data in table format']
            }
        ],
        'software_requirements': [
            {
                'id': 'SR-001',
                'description': 'Implement authentication service',
                'derived_from': ['UR-001'],
                'code_references': [
                    {'file': 'auth.c', 'line': 45},
                    {'file': 'login.js', 'line': 123}
                ]
            }
        ]
    }


@pytest.fixture
def sample_risks():
    """Sample risk data for testing."""
    return [
        {
            'id': 'R-001',
            'hazard': 'Unauthorized access',
            'cause': 'Weak authentication',
            'effect': 'Data breach',
            'severity': 'Catastrophic',
            'probability': 'Medium',
            'risk_level': 'High',
            'mitigation': 'Implement strong authentication'
        },
        {
            'id': 'R-002',
            'hazard': 'System crash',
            'cause': 'Memory leak',
            'effect': 'Service unavailable',
            'severity': 'Serious',
            'probability': 'Low',
            'risk_level': 'Medium',
            'mitigation': 'Regular memory monitoring'
        }
    ]


@pytest.fixture
def sample_summary():
    """Sample summary data for testing."""
    return {
        'project_path': '/path/to/project',
        'files_analyzed': 25,
        'analysis_date': '2023-01-01 12:00:00',
        'features_found': 15,
        'requirements_generated': 30,
        'risks_identified': 8,
        'confidence': 85,
        'errors': ['Error in parsing file X'],
        'warnings': ['Warning: Low confidence in feature Y']
    }


class TestRequirementsTab:
    """Test cases for RequirementsTab."""
    
    def test_initialization(self, requirements_tab):
        """Test requirements tab initialization."""
        assert requirements_tab.user_requirements == []
        assert requirements_tab.software_requirements == []
        assert requirements_tab.ur_table.columnCount() == 3
        assert requirements_tab.sr_table.columnCount() == 4
        
    def test_update_requirements(self, requirements_tab, sample_requirements):
        """Test updating requirements display."""
        requirements_tab.update_requirements(
            sample_requirements['user_requirements'],
            sample_requirements['software_requirements']
        )
        
        # Check user requirements table
        assert requirements_tab.ur_table.rowCount() == 2
        assert requirements_tab.ur_table.item(0, 0).text() == 'UR-001'
        assert 'login' in requirements_tab.ur_table.item(0, 1).text()
        
        # Check software requirements table
        assert requirements_tab.sr_table.rowCount() == 1
        assert requirements_tab.sr_table.item(0, 0).text() == 'SR-001'
        assert 'authentication' in requirements_tab.sr_table.item(0, 1).text()
        assert 'UR-001' in requirements_tab.sr_table.item(0, 2).text()
        assert requirements_tab.sr_table.item(0, 3).text() == '2'  # 2 code references
        
    def test_signal_emissions(self, requirements_tab):
        """Test signal emissions from requirements tab."""
        signal_received = False
        
        def on_requirements_updated(data):
            nonlocal signal_received
            signal_received = True
            
        requirements_tab.requirements_updated.connect(on_requirements_updated)
        
        # This would typically be triggered by user editing
        # For now, just verify the signal exists
        assert hasattr(requirements_tab, 'requirements_updated')


class TestRiskRegisterTab:
    """Test cases for RiskRegisterTab."""
    
    def test_initialization(self, risk_tab):
        """Test risk register tab initialization."""
        assert risk_tab.risks == []
        assert risk_tab.risk_table.columnCount() == 9
        assert risk_tab.severity_filter.count() == 4  # All, Catastrophic, Serious, Minor
        
    def test_update_risks(self, risk_tab, sample_risks):
        """Test updating risk register display."""
        risk_tab.update_risks(sample_risks)
        
        assert risk_tab.risk_table.rowCount() == 2
        assert risk_tab.risk_table.item(0, 0).text() == 'R-001'
        assert 'Unauthorized access' in risk_tab.risk_table.item(0, 1).text()
        assert risk_tab.risk_table.item(0, 4).text() == 'Catastrophic'
        
        # Check color coding for severity
        severity_item = risk_tab.risk_table.item(0, 4)
        assert severity_item.background().color().red() == 255  # Red background for catastrophic
        
    def test_severity_filtering(self, risk_tab, sample_risks):
        """Test severity filtering functionality."""
        risk_tab.update_risks(sample_risks)
        
        # Filter by Catastrophic
        risk_tab.severity_filter.setCurrentText("Catastrophic")
        risk_tab.apply_filters()
        
        # Should show only 1 row (the catastrophic risk)
        assert risk_tab.risk_table.rowCount() == 1
        assert risk_tab.risk_table.item(0, 4).text() == 'Catastrophic'
        
        # Filter by All
        risk_tab.severity_filter.setCurrentText("All")
        risk_tab.apply_filters()
        
        # Should show all risks again
        assert risk_tab.risk_table.rowCount() == 2


class TestSummaryTab:
    """Test cases for SummaryTab."""
    
    def test_initialization(self, summary_tab):
        """Test summary tab initialization."""
        assert summary_tab.summary_data == {}
        assert not summary_tab.errors_group.isVisible()  # Initially hidden
        
    def test_update_summary(self, summary_tab, sample_summary):
        """Test updating summary display."""
        summary_tab.update_summary(sample_summary)
        
        assert '/path/to/project' in summary_tab.project_path_label.text()
        assert '25' in summary_tab.files_analyzed_label.text()
        assert '2023-01-01' in summary_tab.analysis_date_label.text()
        assert '15' in summary_tab.features_found_label.text()
        assert '30' in summary_tab.requirements_generated_label.text()
        assert '8' in summary_tab.risks_identified_label.text()
        assert '85%' in summary_tab.confidence_label.text()
        
        # Check that errors section is visible when errors exist
        # Debug: check if errors are in the data
        errors = sample_summary.get('errors', [])
        warnings = sample_summary.get('warnings', [])
        print(f"Debug - Errors: {errors}, Warnings: {warnings}")
        print(f"Debug - Errors group visible: {summary_tab.errors_group.isVisible()}")
        
        assert summary_tab.errors_group.isVisible()
        error_text = summary_tab.errors_text.toPlainText()
        assert 'Error in parsing file X' in error_text
        assert 'Warning: Low confidence in feature Y' in error_text
        
    def test_no_errors_handling(self, summary_tab):
        """Test summary display when no errors exist."""
        summary_data = {
            'project_path': '/path/to/project',
            'files_analyzed': 10,
            'errors': [],
            'warnings': []
        }
        
        summary_tab.update_summary(summary_data)
        
        # Errors section should be hidden
        assert not summary_tab.errors_group.isVisible()


class TestResultsTabWidget:
    """Test cases for ResultsTabWidget."""
    
    def test_initialization(self, results_widget):
        """Test results tab widget initialization."""
        assert results_widget.count() == 5  # Summary, Requirements, Risk, Traceability, Tests
        assert not results_widget.isEnabled()  # Initially disabled
        
        # Check tab names
        tab_names = [results_widget.tabText(i) for i in range(results_widget.count())]
        expected_names = ["Summary", "Requirements", "Risk Register", "Traceability", "Tests"]
        assert tab_names == expected_names
        
    def test_update_results(self, results_widget, sample_requirements, sample_risks, sample_summary):
        """Test updating all results."""
        results_data = {
            'summary': sample_summary,
            'requirements': sample_requirements,
            'risks': sample_risks,
            'traceability': {'matrix_rows': [], 'gaps': [], 'matrix': {'metadata': {}}},
            'tests': {'total_tests': 10, 'passed_tests': 8, 'failed_tests': 2}
        }
        
        results_widget.update_results(results_data)
        
        # Widget should be enabled after update
        assert results_widget.isEnabled()
        
        # Check that data was passed to individual tabs
        assert results_widget.summary_tab.summary_data == sample_summary
        assert results_widget.requirements_tab.user_requirements == sample_requirements['user_requirements']
        assert results_widget.risk_tab.risks == sample_risks
        
    def test_clear_results(self, results_widget, sample_requirements):
        """Test clearing results."""
        # First update with some data
        results_widget.update_results({'requirements': sample_requirements})
        assert results_widget.isEnabled()
        
        # Then clear
        results_widget.clear_results()
        
        assert not results_widget.isEnabled()
        assert results_widget.analysis_results == {}
        
    def test_show_partial_results(self, results_widget, sample_requirements):
        """Test showing partial results with errors."""
        errors = ['Stage 1 failed', 'Stage 3 failed']
        
        with patch.object(QMessageBox, 'warning') as mock_warning:
            results_widget.show_partial_results(
                {'requirements': sample_requirements}, 
                errors
            )
            
            # Should show warning dialog
            mock_warning.assert_called_once()
            
            # Should update results with error information
            assert results_widget.isEnabled()
            assert 'errors' in results_widget.analysis_results['summary']
            assert results_widget.analysis_results['summary']['errors'] == errors
            
    def test_signal_connections(self, results_widget):
        """Test signal connections between tabs and main widget."""
        # Test that export signal exists and can be connected
        export_signal_received = False
        export_params = None
        
        def on_export(tab_name, export_type):
            nonlocal export_signal_received, export_params
            export_signal_received = True
            export_params = (tab_name, export_type)
            
        results_widget.export_requested.connect(on_export)
        
        # Manually emit the signal to test connection
        results_widget.export_requested.emit("requirements", "csv")
        
        assert export_signal_received
        assert export_params == ("requirements", "csv")
        
        # Test refresh signal
        refresh_signal_received = False
        refresh_tab = None
        
        def on_refresh(tab_name):
            nonlocal refresh_signal_received, refresh_tab
            refresh_signal_received = True
            refresh_tab = tab_name
            
        results_widget.refresh_requested.connect(on_refresh)
        
        # Manually emit the signal to test connection
        results_widget.refresh_requested.emit("requirements")
        
        assert refresh_signal_received
        assert refresh_tab == "requirements"
        
    def test_get_current_tab_name(self, results_widget):
        """Test getting current tab name."""
        # Default should be first tab (Summary)
        assert results_widget.get_current_tab_name() == "Summary"
        
        # Change to requirements tab
        results_widget.setCurrentIndex(1)
        assert results_widget.get_current_tab_name() == "Requirements"
        
    def test_tab_switching(self, results_widget):
        """Test tab switching functionality."""
        # Initially on Summary tab
        assert results_widget.currentIndex() == 0
        
        # Switch to each tab
        for i in range(results_widget.count()):
            results_widget.setCurrentIndex(i)
            assert results_widget.currentIndex() == i
            
    def test_export_functionality(self, results_widget, sample_requirements, sample_risks):
        """Test export functionality for different tabs."""
        # Set up test data
        results_widget.requirements_tab.user_requirements = sample_requirements['user_requirements']
        results_widget.requirements_tab.software_requirements = sample_requirements['software_requirements']
        results_widget.risk_tab.risks = sample_risks
        
        # Test requirements CSV export
        csv_content = results_widget._export_requirements_csv()
        assert 'USER REQUIREMENTS' in csv_content
        assert 'SOFTWARE REQUIREMENTS' in csv_content
        assert 'UR-001' in csv_content
        assert 'SR-001' in csv_content
        assert 'User shall be able to login' in csv_content
        
        # Test risks CSV export
        risks_csv = results_widget._export_risks_csv()
        assert 'ID,Hazard,Cause,Effect' in risks_csv
        assert 'R-001' in risks_csv
        assert 'Unauthorized access' in risks_csv
        assert 'Catastrophic' in risks_csv
        
    def test_data_update_signals(self, results_widget):
        """Test data update signal handling."""
        # Test requirements update
        requirements_data = {
            'user_requirements': [{'id': 'UR-NEW', 'description': 'New requirement'}],
            'software_requirements': [{'id': 'SR-NEW', 'description': 'New software requirement'}]
        }
        
        results_widget.on_requirements_updated(requirements_data)
        
        # Check that internal data was updated
        assert 'requirements' in results_widget.analysis_results
        assert results_widget.analysis_results['requirements']['user_requirements'] == requirements_data['user_requirements']
        assert results_widget.analysis_results['requirements']['software_requirements'] == requirements_data['software_requirements']
        
        # Test risks update
        risks_data = {'risks': [{'id': 'R-NEW', 'hazard': 'New hazard'}]}
        results_widget.on_risks_updated(risks_data)
        
        # Check that internal data was updated
        assert results_widget.analysis_results['risks'] == risks_data['risks']
        
    def test_export_data_method(self, results_widget):
        """Test the generic export_data method."""
        # Set up some test data
        results_widget.requirements_tab.user_requirements = [
            {'id': 'UR-001', 'description': 'Test requirement', 'acceptance_criteria': ['Test criteria']}
        ]
        
        # Test requirements export
        csv_content = results_widget.export_data("requirements", "csv")
        assert csv_content is not None
        assert 'UR-001' in csv_content
        
        # Test invalid export
        invalid_content = results_widget.export_data("invalid_tab", "csv")
        assert invalid_content is None


class TestTestingResultsTab:
    """Test cases for TestingResultsTab."""
    
    def test_initialization(self, app):
        """Test test results tab initialization."""
        tab = TestingResultsTab()
        
        assert tab.test_results == {}
        assert tab.test_suites == []
        assert tab.total_tests_label.text() == "Total Tests: 0"
        assert tab.passed_tests_label.text() == "Passed: 0"
        assert tab.failed_tests_label.text() == "Failed: 0"
        assert tab.skipped_tests_label.text() == "Skipped: 0"
        assert tab.coverage_label.text() == "Coverage: 0%"
        assert tab.execution_status_label.text() == "Status: Ready"
        
    def test_update_test_results(self, app):
        """Test updating test results display."""
        tab = TestingResultsTab()
        
        test_suites = [
            {
                'id': 'suite1',
                'name': 'Unit Tests',
                'total_tests': 15,
                'passed_tests': 12,
                'failed_tests': 3,
                'status': 'Failed',
                'output': 'Test suite output...',
                'failed_test_details': [
                    {'name': 'test_auth', 'error': 'Assertion failed', 'file': 'test_auth.c'}
                ]
            },
            {
                'id': 'suite2',
                'name': 'Integration Tests',
                'total_tests': 10,
                'passed_tests': 10,
                'failed_tests': 0,
                'status': 'Passed'
            }
        ]
        
        test_data = {
            'total_tests': 25,
            'passed_tests': 22,
            'failed_tests': 3,
            'skipped_tests': 0,
            'coverage': 85,
            'execution_time': 45.2,
            'last_run': '2023-01-01 12:00:00',
            'status': 'Completed',
            'test_suites': test_suites,
            'output': 'Test execution completed with 3 failures',
            'coverage_report': 'Coverage: 85% (120/140 lines covered)'
        }
        
        tab.update_test_results(test_data)
        
        # Check summary metrics
        assert tab.total_tests_label.text() == "Total Tests: 25"
        assert tab.passed_tests_label.text() == "Passed: 22"
        assert tab.failed_tests_label.text() == "Failed: 3"
        assert tab.skipped_tests_label.text() == "Skipped: 0"
        assert tab.coverage_label.text() == "Coverage: 85%"
        assert tab.execution_time_label.text() == "Execution Time: 45.2s"
        assert tab.last_run_label.text() == "Last Run: 2023-01-01 12:00:00"
        
        # Check test suites table
        assert tab.suites_table.rowCount() == 2
        assert tab.suites_table.item(0, 0).text() == "Unit Tests"
        assert tab.suites_table.item(0, 1).text() == "15"
        assert tab.suites_table.item(0, 2).text() == "12"
        assert tab.suites_table.item(0, 3).text() == "3"
        assert tab.suites_table.item(0, 4).text() == "Failed"
        
        # Check that failed tests have red background
        failed_status_item = tab.suites_table.item(0, 4)
        assert failed_status_item.background().color() == QColor(255, 200, 200)
        
        # Check that passed tests have green background
        passed_status_item = tab.suites_table.item(1, 4)
        assert passed_status_item.background().color() == QColor(200, 255, 200)
        
    def test_execution_status_management(self, app):
        """Test execution status and button state management."""
        tab = TestingResultsTab()
        
        # Test running state
        tab.set_execution_status("Running", True)
        assert tab.execution_status_label.text() == "Status: Running"
        assert not tab.run_all_button.isEnabled()
        assert not tab.run_selected_button.isEnabled()
        assert not tab.configure_button.isEnabled()
        assert tab.stop_button.isEnabled()
        
        # Test completed state
        tab.set_execution_status("Completed", False)
        assert tab.execution_status_label.text() == "Status: Completed"
        assert tab.run_all_button.isEnabled()
        assert tab.run_selected_button.isEnabled()
        assert tab.configure_button.isEnabled()
        assert not tab.stop_button.isEnabled()
        
    def test_suite_selection(self, app):
        """Test test suite selection and detail display."""
        tab = TestingResultsTab()
        
        # Set up test data
        test_suites = [
            {
                'id': 'suite1',
                'name': 'Unit Tests',
                'output': 'Unit test output...',
                'failed_test_details': [
                    {'name': 'test_login', 'error': 'Login failed', 'file': 'auth_test.c'}
                ]
            }
        ]
        tab.test_suites = test_suites
        tab.update_suites_table()
        
        # Simulate suite selection
        tab.show_suite_details(test_suites[0])
        
        # Check that details are displayed
        assert 'Unit test output...' in tab.test_output.toPlainText()
        assert tab.failed_tests_table.rowCount() == 1
        assert tab.failed_tests_table.item(0, 0).text() == "test_login"
        assert tab.failed_tests_table.item(0, 2).text() == "Login failed"
        
    def test_signal_emissions(self, app):
        """Test signal emissions for test execution."""
        tab = TestingResultsTab()
        
        # Set up test suites
        tab.test_suites = [
            {'id': 'suite1', 'name': 'Test Suite 1'},
            {'id': 'suite2', 'name': 'Test Suite 2'}
        ]
        
        # Test run all signal
        execution_signal_received = False
        execution_config = None
        
        def on_execution_requested(config):
            nonlocal execution_signal_received, execution_config
            execution_signal_received = True
            execution_config = config
            
        tab.test_execution_requested.connect(on_execution_requested)
        
        # Trigger run all tests
        tab.run_all_tests()
        
        assert execution_signal_received
        assert execution_config['suites'] == ['suite1', 'suite2']
        assert execution_config['timeout'] == 300
        assert execution_config['parallel'] == True
        assert execution_config['coverage'] == True


class TestTraceabilityTab:
    """Test cases for TraceabilityTab."""
    
    def test_initialization(self, app):
        """Test traceability tab initialization."""
        tab = TraceabilityTab()
        
        assert tab.traceability_data == {}
        assert tab.matrix_rows == []
        assert tab.gaps == []
        assert tab.matrix_table.columnCount() == 10
        
    def test_update_traceability(self, app):
        """Test updating traceability display."""
        tab = TraceabilityTab()
        
        sample_matrix_rows = [
            {
                'code_reference': 'auth.c:45-60',
                'file_path': 'src/auth.c',
                'function_name': 'authenticate_user',
                'feature_id': 'F-001',
                'feature_description': 'User authentication',
                'user_requirement_id': 'UR-001',
                'user_requirement_text': 'User shall be able to login',
                'software_requirement_id': 'SR-001',
                'software_requirement_text': 'Implement authentication service',
                'risk_id': 'R-001',
                'confidence': 0.85
            }
        ]
        
        sample_gaps = [
            {
                'gap_type': 'orphaned_code',
                'source_type': 'code',
                'source_id': 'test.c:10-20',
                'description': 'Code without feature link',
                'severity': 'medium',
                'recommendation': 'Link to feature or remove'
            }
        ]
        
        traceability_data = {
            'matrix_rows': sample_matrix_rows,
            'gaps': sample_gaps,
            'matrix': {
                'metadata': {
                    'total_links': 5,
                    'code_feature_links': 2,
                    'ur_sr_links': 1,
                    'sr_risk_links': 1
                }
            }
        }
        
        tab.update_traceability(traceability_data)
        
        assert tab.traceability_data == traceability_data
        assert tab.matrix_rows == sample_matrix_rows
        assert tab.gaps == sample_gaps
        
    def test_view_filtering(self, app):
        """Test view filtering functionality."""
        tab = TraceabilityTab()
        
        # Set up test data
        matrix_rows = [
            {'code_reference': 'test1', 'software_requirement_id': 'SR-001', 'risk_id': ''},
            {'code_reference': 'test2', 'software_requirement_id': 'SR-002', 'risk_id': 'R-001'},
            {'code_reference': '', 'software_requirement_id': 'SR-003', 'risk_id': 'R-002'}
        ]
        tab.matrix_rows = matrix_rows
        
        # Test "Code to Requirements" filter
        filtered = tab.filter_rows_by_view("Code to Requirements")
        assert len(filtered) == 2  # Only rows with both code_reference and software_requirement_id
        
        # Test "Requirements to Risks" filter
        filtered = tab.filter_rows_by_view("Requirements to Risks")
        assert len(filtered) == 2  # Only rows with both software_requirement_id and risk_id
        
    def test_export_functionality(self, app):
        """Test export functionality."""
        tab = TraceabilityTab()
        
        # Set up test data
        tab.matrix_rows = [
            {
                'code_reference': 'test.c:1-10',
                'file_path': 'test.c',
                'function_name': 'test_func',
                'feature_id': 'F-001',
                'feature_description': 'Test feature',
                'user_requirement_id': 'UR-001',
                'user_requirement_text': 'Test requirement',
                'software_requirement_id': 'SR-001',
                'software_requirement_text': 'Test software requirement',
                'risk_id': 'R-001',
                'confidence': 0.9
            }
        ]
        
        # Test CSV export
        csv_content = tab.export_matrix_csv()
        assert 'Code Reference' in csv_content
        assert 'test.c:1-10' in csv_content
        assert 'Test feature' in csv_content
        
        # Test gaps export
        tab.gaps = [
            {
                'gap_type': 'orphaned_code',
                'description': 'Test gap',
                'severity': 'high',
                'source_type': 'code',
                'source_id': 'test.c:1-5',
                'recommendation': 'Fix this gap'
            }
        ]
        
        gaps_report = tab.export_gaps_report()
        assert 'TRACEABILITY GAP ANALYSIS REPORT' in gaps_report
        assert 'Test gap' in gaps_report
        assert 'HIGH SEVERITY GAPS' in gaps_report


class TestTestExecutionDialog:
    """Test cases for TestExecutionDialog."""
    
    def test_initialization(self, app):
        """Test test execution dialog initialization."""
        test_suites = [
            {'id': 'suite1', 'name': 'Unit Tests', 'test_count': 15},
            {'id': 'suite2', 'name': 'Integration Tests', 'test_count': 8}
        ]
        
        dialog = TestExecutionDialog(test_suites)
        
        assert len(dialog.suite_checkboxes) == 2
        assert dialog.timeout_spin.value() == 300
        assert dialog.parallel_checkbox.isChecked()
        assert dialog.coverage_checkbox.isChecked()
        assert not dialog.verbose_checkbox.isChecked()
        
        # Check that all suites are initially selected
        for checkbox in dialog.suite_checkboxes.values():
            assert checkbox.isChecked()
            
    def test_suite_selection(self, app):
        """Test suite selection functionality."""
        test_suites = [
            {'id': 'suite1', 'name': 'Unit Tests', 'test_count': 15},
            {'id': 'suite2', 'name': 'Integration Tests', 'test_count': 8}
        ]
        
        dialog = TestExecutionDialog(test_suites)
        
        # Uncheck first suite
        dialog.suite_checkboxes['suite1'].setChecked(False)
        
        # Check selection state
        assert not dialog.suite_checkboxes['suite1'].isChecked()
        assert dialog.suite_checkboxes['suite2'].isChecked()


class TestRequirementEditDialog:
    """Test cases for RequirementEditDialog."""
    
    def test_initialization(self, app):
        """Test requirement edit dialog initialization."""
        requirement_data = {
            'id': 'UR-001',
            'description': 'Test requirement',
            'acceptance_criteria': ['Criterion 1', 'Criterion 2'],
            'derived_from': ['F-001'],
            'code_references': [{'file': 'test.c', 'line': 10}]
        }
        
        dialog = RequirementEditDialog(requirement_data)
        
        assert dialog.id_edit.text() == 'UR-001'
        assert dialog.description_edit.toPlainText() == 'Test requirement'
        assert 'Criterion 1\nCriterion 2' in dialog.acceptance_criteria_edit.toPlainText()
        assert dialog.derived_from_edit.text() == 'F-001'
        assert dialog.id_edit.isReadOnly()
        
    def test_get_requirement_data(self, app):
        """Test getting edited requirement data."""
        requirement_data = {
            'id': 'UR-001',
            'description': 'Original description',
            'acceptance_criteria': ['Original criterion'],
            'derived_from': [],
            'code_references': []
        }
        
        dialog = RequirementEditDialog(requirement_data)
        
        # Modify the fields
        dialog.description_edit.setPlainText('Modified description')
        dialog.acceptance_criteria_edit.setPlainText('New criterion 1\nNew criterion 2')
        dialog.derived_from_edit.setText('F-001, F-002')
        
        edited_data = dialog.get_requirement_data()
        
        assert edited_data['id'] == 'UR-001'
        assert edited_data['description'] == 'Modified description'
        assert edited_data['acceptance_criteria'] == ['New criterion 1', 'New criterion 2']
        assert edited_data['derived_from'] == ['F-001', 'F-002']
        assert edited_data['code_references'] == []


class TestRiskEditDialog:
    """Test cases for RiskEditDialog."""
    
    def test_initialization(self, app):
        """Test risk edit dialog initialization."""
        risk_data = {
            'id': 'R-001',
            'hazard': 'Test hazard',
            'cause': 'Test cause',
            'effect': 'Test effect',
            'severity': 'Serious',
            'probability': 'Medium',
            'mitigation': 'Test mitigation',
            'verification': 'Test verification',
            'related_requirements': ['SR-001']
        }
        
        dialog = RiskEditDialog(risk_data)
        
        assert dialog.id_edit.text() == 'R-001'
        assert dialog.hazard_edit.toPlainText() == 'Test hazard'
        assert dialog.cause_edit.toPlainText() == 'Test cause'
        assert dialog.effect_edit.toPlainText() == 'Test effect'
        assert dialog.severity_combo.currentText() == 'Serious'
        assert dialog.probability_combo.currentText() == 'Medium'
        assert dialog.mitigation_edit.toPlainText() == 'Test mitigation'
        assert dialog.verification_edit.toPlainText() == 'Test verification'
        
    def test_risk_level_calculation(self, app):
        """Test automatic risk level calculation."""
        risk_data = {
            'id': 'R-001',
            'hazard': 'Test hazard',
            'cause': 'Test cause',
            'effect': 'Test effect',
            'severity': 'Minor',
            'probability': 'Low',
            'mitigation': 'Test mitigation',
            'verification': 'Test verification'
        }
        
        dialog = RiskEditDialog(risk_data)
        
        # Test different combinations
        test_cases = [
            ('Minor', 'Low', 'Low'),
            ('Minor', 'Medium', 'Low'),
            ('Minor', 'High', 'Medium'),
            ('Serious', 'Low', 'Low'),
            ('Serious', 'Medium', 'Medium'),
            ('Serious', 'High', 'High'),
            ('Catastrophic', 'Low', 'Medium'),
            ('Catastrophic', 'Medium', 'High'),
            ('Catastrophic', 'High', 'High')
        ]
        
        for severity, probability, expected_risk_level in test_cases:
            dialog.severity_combo.setCurrentText(severity)
            dialog.probability_combo.setCurrentText(probability)
            dialog.calculate_risk_level()
            assert dialog.risk_level_edit.text() == expected_risk_level
            
    def test_get_risk_data(self, app):
        """Test getting edited risk data."""
        risk_data = {
            'id': 'R-001',
            'hazard': 'Original hazard',
            'cause': 'Original cause',
            'effect': 'Original effect',
            'severity': 'Minor',
            'probability': 'Low',
            'mitigation': 'Original mitigation',
            'verification': 'Original verification',
            'related_requirements': []
        }
        
        dialog = RiskEditDialog(risk_data)
        
        # Modify the fields
        dialog.hazard_edit.setPlainText('Modified hazard')
        dialog.cause_edit.setPlainText('Modified cause')
        dialog.effect_edit.setPlainText('Modified effect')
        dialog.severity_combo.setCurrentText('Catastrophic')
        dialog.probability_combo.setCurrentText('High')
        dialog.mitigation_edit.setPlainText('Modified mitigation')
        dialog.verification_edit.setPlainText('Modified verification')
        
        edited_data = dialog.get_risk_data()
        
        assert edited_data['id'] == 'R-001'
        assert edited_data['hazard'] == 'Modified hazard'
        assert edited_data['cause'] == 'Modified cause'
        assert edited_data['effect'] == 'Modified effect'
        assert edited_data['severity'] == 'Catastrophic'
        assert edited_data['probability'] == 'High'
        assert edited_data['risk_level'] == 'High'  # Calculated automatically
        assert edited_data['mitigation'] == 'Modified mitigation'
        assert edited_data['verification'] == 'Modified verification'


class TestRequirementsTabEditing:
    """Test cases for requirements tab editing functionality."""
    
    def test_add_user_requirement(self, requirements_tab):
        """Test adding a new user requirement."""
        initial_count = len(requirements_tab.user_requirements)
        
        # Mock the dialog to simulate user input
        with patch('medical_analyzer.ui.results_tab_widget.RequirementEditDialog') as mock_dialog:
            mock_instance = Mock()
            mock_instance.exec.return_value = QDialog.DialogCode.Accepted
            mock_instance.get_requirement_data.return_value = {
                'id': 'UR-NEW',
                'description': 'New user requirement',
                'acceptance_criteria': ['New criterion'],
                'derived_from': [],
                'code_references': []
            }
            mock_dialog.return_value = mock_instance
            
            requirements_tab.add_user_requirement()
            
            assert len(requirements_tab.user_requirements) == initial_count + 1
            assert requirements_tab.user_requirements[-1]['id'] == 'UR-NEW'
            assert requirements_tab.user_requirements[-1]['description'] == 'New user requirement'
            
    def test_edit_user_requirement(self, requirements_tab):
        """Test editing an existing user requirement."""
        # Set up initial requirement
        requirements_tab.user_requirements = [
            {
                'id': 'UR-001',
                'description': 'Original description',
                'acceptance_criteria': ['Original criterion']
            }
        ]
        requirements_tab.refresh_ur_table()
        
        # Select the first row
        requirements_tab.ur_table.setCurrentCell(0, 0)
        
        # Mock the dialog to simulate user editing
        with patch('medical_analyzer.ui.results_tab_widget.RequirementEditDialog') as mock_dialog:
            mock_instance = Mock()
            mock_instance.exec.return_value = QDialog.DialogCode.Accepted
            mock_instance.get_requirement_data.return_value = {
                'id': 'UR-001',
                'description': 'Modified description',
                'acceptance_criteria': ['Modified criterion'],
                'derived_from': [],
                'code_references': []
            }
            mock_dialog.return_value = mock_instance
            
            requirements_tab.edit_user_requirement()
            
            assert requirements_tab.user_requirements[0]['description'] == 'Modified description'
            assert requirements_tab.user_requirements[0]['acceptance_criteria'] == ['Modified criterion']
            
    def test_delete_user_requirement(self, requirements_tab):
        """Test deleting a user requirement."""
        # Set up initial requirements
        requirements_tab.user_requirements = [
            {'id': 'UR-001', 'description': 'First requirement'},
            {'id': 'UR-002', 'description': 'Second requirement'}
        ]
        requirements_tab.refresh_ur_table()
        
        # Select the first row
        requirements_tab.ur_table.setCurrentCell(0, 0)
        
        # Mock the confirmation dialog
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            requirements_tab.delete_user_requirement()
            
            assert len(requirements_tab.user_requirements) == 1
            assert requirements_tab.user_requirements[0]['id'] == 'UR-002'
            
    def test_add_software_requirement(self, requirements_tab):
        """Test adding a new software requirement."""
        initial_count = len(requirements_tab.software_requirements)
        
        # Mock the dialog to simulate user input
        with patch('medical_analyzer.ui.results_tab_widget.RequirementEditDialog') as mock_dialog:
            mock_instance = Mock()
            mock_instance.exec.return_value = QDialog.DialogCode.Accepted
            mock_instance.get_requirement_data.return_value = {
                'id': 'SR-NEW',
                'description': 'New software requirement',
                'derived_from': ['UR-001'],
                'code_references': []
            }
            mock_dialog.return_value = mock_instance
            
            requirements_tab.add_software_requirement()
            
            assert len(requirements_tab.software_requirements) == initial_count + 1
            assert requirements_tab.software_requirements[-1]['id'] == 'SR-NEW'
            assert requirements_tab.software_requirements[-1]['description'] == 'New software requirement'
            assert requirements_tab.software_requirements[-1]['derived_from'] == ['UR-001']


class TestRiskRegisterTabEditing:
    """Test cases for risk register tab editing functionality."""
    
    def test_add_risk(self, risk_tab):
        """Test adding a new risk item."""
        initial_count = len(risk_tab.risks)
        
        # Mock the dialog to simulate user input
        with patch('medical_analyzer.ui.results_tab_widget.RiskEditDialog') as mock_dialog:
            mock_instance = Mock()
            mock_instance.exec.return_value = QDialog.DialogCode.Accepted
            mock_instance.get_risk_data.return_value = {
                'id': 'R-NEW',
                'hazard': 'New hazard',
                'cause': 'New cause',
                'effect': 'New effect',
                'severity': 'Serious',
                'probability': 'Medium',
                'risk_level': 'Medium',
                'mitigation': 'New mitigation',
                'verification': 'New verification',
                'related_requirements': []
            }
            mock_dialog.return_value = mock_instance
            
            risk_tab.add_risk()
            
            assert len(risk_tab.risks) == initial_count + 1
            assert risk_tab.risks[-1]['id'] == 'R-NEW'
            assert risk_tab.risks[-1]['hazard'] == 'New hazard'
            
    def test_edit_risk(self, risk_tab):
        """Test editing an existing risk item."""
        # Set up initial risk
        risk_tab.risks = [
            {
                'id': 'R-001',
                'hazard': 'Original hazard',
                'cause': 'Original cause',
                'effect': 'Original effect',
                'severity': 'Minor',
                'probability': 'Low',
                'risk_level': 'Low',
                'mitigation': 'Original mitigation',
                'verification': 'Original verification'
            }
        ]
        risk_tab.apply_filters()
        
        # Select the first row
        risk_tab.risk_table.setCurrentCell(0, 0)
        
        # Mock the dialog to simulate user editing
        with patch('medical_analyzer.ui.results_tab_widget.RiskEditDialog') as mock_dialog:
            mock_instance = Mock()
            mock_instance.exec.return_value = QDialog.DialogCode.Accepted
            mock_instance.get_risk_data.return_value = {
                'id': 'R-001',
                'hazard': 'Modified hazard',
                'cause': 'Modified cause',
                'effect': 'Modified effect',
                'severity': 'Catastrophic',
                'probability': 'High',
                'risk_level': 'High',
                'mitigation': 'Modified mitigation',
                'verification': 'Modified verification',
                'related_requirements': []
            }
            mock_dialog.return_value = mock_instance
            
            risk_tab.edit_risk()
            
            assert risk_tab.risks[0]['hazard'] == 'Modified hazard'
            assert risk_tab.risks[0]['severity'] == 'Catastrophic'
            assert risk_tab.risks[0]['risk_level'] == 'High'
            
    def test_delete_risk(self, risk_tab):
        """Test deleting a risk item."""
        # Set up initial risks
        risk_tab.risks = [
            {'id': 'R-001', 'hazard': 'First hazard'},
            {'id': 'R-002', 'hazard': 'Second hazard'}
        ]
        risk_tab.apply_filters()
        
        # Select the first row
        risk_tab.risk_table.setCurrentCell(0, 0)
        
        # Mock the confirmation dialog
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            risk_tab.delete_risk()
            
            assert len(risk_tab.risks) == 1
            assert risk_tab.risks[0]['id'] == 'R-002'
            
    def test_search_filtering(self, risk_tab, sample_risks):
        """Test search filtering functionality."""
        risk_tab.update_risks(sample_risks)
        
        # Test search for "access"
        risk_tab.search_edit.setText("access")
        risk_tab.apply_filters()
        
        # Should show only the risk with "Unauthorized access"
        assert risk_tab.risk_table.rowCount() == 1
        assert 'Unauthorized access' in risk_tab.risk_table.item(0, 1).text()
        
        # Test search for "memory"
        risk_tab.search_edit.setText("memory")
        risk_tab.apply_filters()
        
        # Should show only the risk with "Memory leak"
        assert risk_tab.risk_table.rowCount() == 1
        assert 'Memory leak' in risk_tab.risk_table.item(0, 2).text()
        
        # Clear search
        risk_tab.search_edit.setText("")
        risk_tab.apply_filters()
        
        # Should show all risks again
        assert risk_tab.risk_table.rowCount() == 2


class TestTraceabilityTabExport:
    """Test cases for traceability tab export functionality."""
    
    def test_export_csv_with_data(self, app):
        """Test CSV export with actual data."""
        tab = TraceabilityTab()
        
        # Set up comprehensive test data
        tab.matrix_rows = [
            {
                'code_reference': 'auth.c:45-60',
                'file_path': 'src/auth.c',
                'function_name': 'authenticate_user',
                'feature_id': 'F-001',
                'feature_description': 'User authentication feature',
                'user_requirement_id': 'UR-001',
                'user_requirement_text': 'User shall be able to login securely',
                'software_requirement_id': 'SR-001',
                'software_requirement_text': 'Implement secure authentication service',
                'risk_id': 'R-001',
                'confidence': 0.95
            },
            {
                'code_reference': 'data.c:120-150',
                'file_path': 'src/data.c',
                'function_name': 'validate_data',
                'feature_id': 'F-002',
                'feature_description': 'Data validation feature',
                'user_requirement_id': 'UR-002',
                'user_requirement_text': 'System shall validate all input data',
                'software_requirement_id': 'SR-002',
                'software_requirement_text': 'Implement input validation routines',
                'risk_id': 'R-002',
                'confidence': 0.88
            }
        ]
        
        csv_content = tab.export_matrix_csv()
        
        # Check header
        assert 'Code Reference,File Path,Function,Feature ID' in csv_content
        
        # Check data rows
        assert 'auth.c:45-60' in csv_content
        assert 'src/auth.c' in csv_content
        assert 'authenticate_user' in csv_content
        assert 'F-001' in csv_content
        assert 'User authentication feature' in csv_content
        assert 'UR-001' in csv_content
        assert 'SR-001' in csv_content
        assert 'R-001' in csv_content
        assert '0.95' in csv_content
        
        # Check second row
        assert 'data.c:120-150' in csv_content
        assert 'validate_data' in csv_content
        assert 'F-002' in csv_content
        
    def test_export_gaps_with_multiple_severities(self, app):
        """Test gap export with multiple severity levels."""
        tab = TraceabilityTab()
        
        tab.gaps = [
            {
                'gap_type': 'orphaned_code',
                'description': 'Code function without feature mapping',
                'severity': 'high',
                'source_type': 'code',
                'source_id': 'orphan.c:10-25',
                'recommendation': 'Map to existing feature or create new feature'
            },
            {
                'gap_type': 'missing_risk',
                'description': 'Software requirement without risk assessment',
                'severity': 'medium',
                'source_type': 'requirement',
                'source_id': 'SR-005',
                'target_type': 'risk',
                'target_id': '',
                'recommendation': 'Conduct risk assessment for this requirement'
            },
            {
                'gap_type': 'weak_traceability',
                'description': 'Low confidence traceability link',
                'severity': 'low',
                'source_type': 'feature',
                'source_id': 'F-010',
                'recommendation': 'Review and strengthen traceability evidence'
            }
        ]
        
        gaps_report = tab.export_gaps_report()
        
        # Check report structure
        assert 'TRACEABILITY GAP ANALYSIS REPORT' in gaps_report
        assert 'Total gaps: 3' in gaps_report
        
        # Check severity sections
        assert 'HIGH SEVERITY GAPS (1):' in gaps_report
        assert 'MEDIUM SEVERITY GAPS (1):' in gaps_report
        assert 'LOW SEVERITY GAPS (1):' in gaps_report
        
        # Check gap details
        assert 'Code function without feature mapping' in gaps_report
        assert 'orphan.c:10-25' in gaps_report
        assert 'Map to existing feature or create new feature' in gaps_report
        
        assert 'Software requirement without risk assessment' in gaps_report
        assert 'SR-005' in gaps_report
        assert 'Conduct risk assessment for this requirement' in gaps_report
        
        assert 'Low confidence traceability link' in gaps_report
        assert 'F-010' in gaps_report


class TestTestingResultsTabExecution:
    """Test cases for test execution functionality."""
    
    def test_run_selected_tests_with_selection(self, app):
        """Test running selected test suites."""
        tab = TestingResultsTab()
        
        # Set up test suites
        tab.test_suites = [
            {'id': 'suite1', 'name': 'Unit Tests'},
            {'id': 'suite2', 'name': 'Integration Tests'},
            {'id': 'suite3', 'name': 'System Tests'}
        ]
        tab.update_suites_table()
        
        # Select first and third suites (rows 0 and 2)
        # We need to select items, not just rows
        for col in range(tab.suites_table.columnCount()):
            tab.suites_table.item(0, col).setSelected(True)
            tab.suites_table.item(2, col).setSelected(True)
        
        # Capture the execution request signal
        execution_signal_received = False
        execution_config = None
        
        def on_execution_requested(config):
            nonlocal execution_signal_received, execution_config
            execution_signal_received = True
            execution_config = config
            
        tab.test_execution_requested.connect(on_execution_requested)
        
        # Trigger run selected tests
        tab.run_selected_tests()
        
        assert execution_signal_received
        assert set(execution_config['suites']) == {'suite1', 'suite3'}
        
    def test_run_selected_tests_no_selection(self, app):
        """Test running selected tests with no selection."""
        tab = TestingResultsTab()
        
        # Set up test suites but don't select any
        tab.test_suites = [
            {'id': 'suite1', 'name': 'Unit Tests'}
        ]
        tab.update_suites_table()
        
        # Mock the message box
        with patch.object(QMessageBox, 'information') as mock_info:
            tab.run_selected_tests()
            
            # Should show information dialog
            mock_info.assert_called_once()
            args = mock_info.call_args[0]
            assert "No Selection" in args[1]
            
    def test_failed_test_double_click(self, app):
        """Test double-clicking on failed test."""
        tab = TestingResultsTab()
        
        # Set up failed tests table
        tab.failed_tests_table.setRowCount(1)
        tab.failed_tests_table.setItem(0, 0, QTableWidgetItem("test_login"))
        tab.failed_tests_table.setItem(0, 1, QTableWidgetItem("Auth Suite"))
        tab.failed_tests_table.setItem(0, 2, QTableWidgetItem("Login validation failed"))
        tab.failed_tests_table.setItem(0, 3, QTableWidgetItem("auth_test.c"))
        
        # Mock the message box
        with patch.object(QMessageBox, 'information') as mock_info:
            # Simulate double-click on first row
            item = tab.failed_tests_table.item(0, 0)
            tab.on_failed_test_double_clicked(item)
            
            # Should show detailed error dialog
            mock_info.assert_called_once()
            args = mock_info.call_args[0]
            assert "Test Failure: test_login" in args[1]
            assert "auth_test.c" in args[2]
            assert "Login validation failed" in args[2]
            
    def test_color_coding_in_metrics(self, app):
        """Test color coding of test metrics."""
        tab = TestingResultsTab()
        
        # Test with failures - should color failed tests red
        test_data_with_failures = {
            'total_tests': 20,
            'passed_tests': 15,
            'failed_tests': 5,
            'skipped_tests': 0,
            'coverage': 60,  # Low coverage
            'test_suites': []
        }
        
        tab.update_test_results(test_data_with_failures)
        
        # Check that failed tests label is red
        assert "color: red" in tab.failed_tests_label.styleSheet()
        
        # Check that low coverage is red
        assert "color: red" in tab.coverage_label.styleSheet()
        
        # Test with no failures - should color failed tests green
        test_data_no_failures = {
            'total_tests': 20,
            'passed_tests': 20,
            'failed_tests': 0,
            'skipped_tests': 0,
            'coverage': 90,  # High coverage
            'test_suites': []
        }
        
        tab.update_test_results(test_data_no_failures)
        
        # Check that failed tests label is green (no failures)
        assert "color: green" in tab.failed_tests_label.styleSheet()
        
        # Check that high coverage is green
        assert "color: green" in tab.coverage_label.styleSheet()


class TestResultsTabWidgetIntegration:
    """Integration tests for the complete results tab widget."""
    
    def test_complete_workflow(self, results_widget, sample_requirements, sample_risks, sample_summary):
        """Test complete workflow from data update to export."""
        # Prepare comprehensive test data
        traceability_data = {
            'matrix_rows': [
                {
                    'code_reference': 'test.c:1-10',
                    'file_path': 'test.c',
                    'function_name': 'test_func',
                    'feature_id': 'F-001',
                    'feature_description': 'Test feature',
                    'user_requirement_id': 'UR-001',
                    'user_requirement_text': 'Test requirement',
                    'software_requirement_id': 'SR-001',
                    'software_requirement_text': 'Test software requirement',
                    'risk_id': 'R-001',
                    'confidence': 0.9
                }
            ],
            'gaps': [],
            'matrix': {'metadata': {'total_links': 1}}
        }
        
        test_data = {
            'total_tests': 15,
            'passed_tests': 12,
            'failed_tests': 3,
            'skipped_tests': 0,
            'coverage': 85,
            'test_suites': [
                {
                    'id': 'suite1',
                    'name': 'Unit Tests',
                    'total_tests': 15,
                    'passed_tests': 12,
                    'failed_tests': 3,
                    'status': 'Failed'
                }
            ]
        }
        
        complete_results = {
            'summary': sample_summary,
            'requirements': sample_requirements,
            'risks': sample_risks,
            'traceability': traceability_data,
            'tests': test_data
        }
        
        # Update all results
        results_widget.update_results(complete_results)
        
        # Verify all tabs are updated
        assert results_widget.isEnabled()
        assert results_widget.summary_tab.summary_data == sample_summary
        assert len(results_widget.requirements_tab.user_requirements) == 2
        assert len(results_widget.risk_tab.risks) == 2
        assert len(results_widget.traceability_tab.matrix_rows) == 1
        assert results_widget.test_tab.test_results['total_tests'] == 15
        
        # Test exports from each tab
        req_csv = results_widget.export_data("requirements", "csv")
        assert req_csv is not None
        assert 'UR-001' in req_csv
        
        risk_csv = results_widget.export_data("risks", "csv")
        assert risk_csv is not None
        assert 'R-001' in risk_csv
        
        trace_csv = results_widget.export_data("traceability", "csv")
        assert trace_csv is not None
        assert 'test.c:1-10' in trace_csv
        
        test_results = results_widget.export_data("tests", "results")
        assert test_results is not None
        assert 'TEST EXECUTION RESULTS' in test_results
        
    def test_tab_interaction_signals(self, results_widget):
        """Test interaction between tabs through signals."""
        # Set up signal tracking
        export_signals = []
        refresh_signals = []
        
        def track_export(tab_name, export_type):
            export_signals.append((tab_name, export_type))
            
        def track_refresh(tab_name):
            refresh_signals.append(tab_name)
            
        results_widget.export_requested.connect(track_export)
        results_widget.refresh_requested.connect(track_refresh)
        
        # Simulate button clicks from different tabs
        results_widget.requirements_tab.export_button.click()
        results_widget.risk_tab.export_button.click()
        results_widget.requirements_tab.refresh_button.click()
        results_widget.risk_tab.refresh_button.click()
        
        # Verify signals were emitted
        assert len(export_signals) == 2
        assert ('requirements', 'csv') in export_signals
        assert ('risks', 'csv') in export_signals
        
        assert len(refresh_signals) == 2
        assert 'requirements' in refresh_signals
        assert 'risks' in refresh_signals
        
    def test_error_handling_in_export(self, results_widget):
        """Test error handling during export operations."""
        # Set up invalid data that might cause export errors
        results_widget.requirements_tab.user_requirements = [
            {'id': 'UR-001', 'description': None}  # Invalid data
        ]
        
        # Mock an exception during CSV writing
        with patch('medical_analyzer.ui.results_tab_widget.csv.writer') as mock_writer:
            mock_writer.side_effect = Exception("CSV write error")
            
            with patch.object(QMessageBox, 'critical') as mock_critical:
                result = results_widget.export_data("requirements", "csv")
                
                # Should handle error gracefully
                assert result is None
                mock_critical.assert_called_once()
                args = mock_critical.call_args[0]
                assert "Export Error" in args[1]
                assert "CSV write error" in args[2]


if __name__ == '__main__':
    pytest.main([__file__])