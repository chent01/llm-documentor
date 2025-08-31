#!/usr/bin/env python3
"""
Comprehensive verification test for Task 2.4:
Integrate Requirements Display with Results System

This test verifies all task requirements:
1. Modify ResultsTabWidget to include new requirements tab
2. Connect requirements updates to traceability matrix refresh  
3. Add requirements export functionality with multiple formats
4. Implement requirements validation with visual status indicators
"""

import sys
import os
import tempfile
import json
import time
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import QTimer, pyqtSignal
from medical_analyzer.ui.results_tab_widget import ResultsTabWidget
from medical_analyzer.ui.requirements_tab_widget import RequirementsTabWidget
from medical_analyzer.services.soup_service import SOUPService
from medical_analyzer.database.schema import DatabaseManager


class TestResultsIntegration:
    """Test class for verifying Task 2.4 requirements."""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.db_manager = DatabaseManager()
        self.soup_service = SOUPService(self.db_manager)
        self.results_widget = ResultsTabWidget(self.soup_service)
        
        # Track signals for testing
        self.export_signals = []
        self.refresh_signals = []
        
        # Connect signals
        self.results_widget.export_requested.connect(self.track_export_signal)
        self.results_widget.refresh_requested.connect(self.track_refresh_signal)
        
    def track_export_signal(self, tab_name: str, export_type: str):
        """Track export signals for verification."""
        self.export_signals.append((tab_name, export_type))
        
    def track_refresh_signal(self, tab_name: str):
        """Track refresh signals for verification."""
        self.refresh_signals.append(tab_name)
        
    def test_requirement_1_requirements_tab_integration(self):
        """Test: Modify ResultsTabWidget to include new requirements tab."""
        print("Testing Requirement 1: Requirements Tab Integration")
        print("-" * 50)
        
        # Check if requirements tab exists
        req_tab = None
        for i in range(self.results_widget.count()):
            if self.results_widget.tabText(i).startswith("Requirements"):
                req_tab = self.results_widget.widget(i)
                break
                
        assert req_tab is not None, "Requirements tab not found in ResultsTabWidget"
        assert isinstance(req_tab, RequirementsTabWidget), "Requirements tab is not RequirementsTabWidget instance"
        
        print("✓ Requirements tab exists in ResultsTabWidget")
        print("✓ Requirements tab is correct type (RequirementsTabWidget)")
        
        # Check tab properties
        tab_index = self.results_widget.indexOf(req_tab)
        tab_text = self.results_widget.tabText(tab_index)
        
        print(f"✓ Requirements tab text: '{tab_text}'")
        print("✓ Requirement 1: PASSED\n")
        
    def test_requirement_2_traceability_refresh_connection(self):
        """Test: Connect requirements updates to traceability matrix refresh."""
        print("Testing Requirement 2: Traceability Matrix Refresh Connection")
        print("-" * 60)
        
        # Clear previous signals
        self.refresh_signals.clear()
        
        # Load test data
        test_requirements = {
            'user_requirements': [
                {
                    'id': 'UR-TEST-001',
                    'description': 'Test user requirement',
                    'priority': 'Medium',
                    'status': 'Draft',
                    'acceptance_criteria': ['Test criterion 1']
                }
            ],
            'software_requirements': [
                {
                    'id': 'SR-TEST-001',
                    'description': 'Test software requirement',
                    'priority': 'High',
                    'status': 'Approved',
                    'derived_from': ['UR-TEST-001'],
                    'acceptance_criteria': ['Test criterion 1']
                }
            ]
        }
        
        # Update requirements (should trigger traceability refresh)
        self.results_widget.requirements_tab.update_requirements(
            test_requirements['user_requirements'],
            test_requirements['software_requirements']
        )
        
        # Process events and wait for delayed signal (50ms delay in update_requirements)
        self.app.processEvents()
        
        # Wait for the QTimer.singleShot(50, ...) to execute
        import time
        time.sleep(0.1)  # Wait 100ms to ensure 50ms timer fires
        self.app.processEvents()
        
        # Check if traceability refresh was requested
        traceability_refreshes = [sig for sig in self.refresh_signals if sig == "traceability"]
        
        assert len(traceability_refreshes) > 0, f"Traceability refresh signal not emitted. Signals received: {self.refresh_signals}"
        
        print("✓ Requirements update triggers traceability refresh")
        print(f"✓ Traceability refresh signals: {len(traceability_refreshes)}")
        print("✓ Requirement 2: PASSED\n")
        
    def test_requirement_3_export_functionality(self):
        """Test: Add requirements export functionality with multiple formats."""
        print("Testing Requirement 3: Export Functionality with Multiple Formats")
        print("-" * 65)
        
        # Ensure we have test data
        test_requirements = {
            'user_requirements': [
                {
                    'id': 'UR-EXPORT-001',
                    'description': 'Export test user requirement',
                    'priority': 'High',
                    'status': 'Approved',
                    'acceptance_criteria': ['Export criterion 1', 'Export criterion 2']
                }
            ],
            'software_requirements': [
                {
                    'id': 'SR-EXPORT-001',
                    'description': 'Export test software requirement',
                    'priority': 'Medium',
                    'status': 'Under Review',
                    'derived_from': ['UR-EXPORT-001'],
                    'code_references': [{'file': 'test.py', 'line': 42}],
                    'acceptance_criteria': ['Export criterion 1']
                }
            ]
        }
        
        self.results_widget.requirements_tab.update_requirements(
            test_requirements['user_requirements'],
            test_requirements['software_requirements']
        )
        
        # Test CSV export
        try:
            csv_content = self.results_widget._export_requirements_csv()
            assert len(csv_content) > 0, "CSV export returned empty content"
            assert "UR-EXPORT-001" in csv_content, "CSV export missing user requirement"
            assert "SR-EXPORT-001" in csv_content, "CSV export missing software requirement"
            print("✓ CSV export working correctly")
        except Exception as e:
            raise AssertionError(f"CSV export failed: {e}")
            
        # Test JSON export
        try:
            json_content = self.results_widget._export_requirements_json()
            json_data = json.loads(json_content)
            assert 'user_requirements' in json_data, "JSON export missing user_requirements"
            assert 'software_requirements' in json_data, "JSON export missing software_requirements"
            assert len(json_data['user_requirements']) == 1, "JSON export incorrect UR count"
            assert len(json_data['software_requirements']) == 1, "JSON export incorrect SR count"
            print("✓ JSON export working correctly")
        except Exception as e:
            raise AssertionError(f"JSON export failed: {e}")
            
        # Test Excel export
        try:
            excel_content = self.results_widget._export_requirements_excel()
            assert len(excel_content) > 0, "Excel export returned empty content"
            assert "Requirements Export Report" in excel_content, "Excel export missing header"
            print("✓ Excel export working correctly")
        except Exception as e:
            raise AssertionError(f"Excel export failed: {e}")
            
        # Test PDF export
        try:
            pdf_content = self.results_widget._export_requirements_pdf()
            assert len(pdf_content) > 0, "PDF export returned empty content"
            assert "REQUIREMENTS SPECIFICATION DOCUMENT" in pdf_content, "PDF export missing header"
            print("✓ PDF export working correctly")
        except Exception as e:
            raise AssertionError(f"PDF export failed: {e}")
            
        # Test export method exists and works
        try:
            export_data = self.results_widget.export_data("requirements", "csv")
            assert export_data is not None, "export_data method returned None"
            print("✓ export_data method working correctly")
        except Exception as e:
            raise AssertionError(f"export_data method failed: {e}")
            
        print("✓ All export formats (CSV, JSON, Excel, PDF) working")
        print("✓ Requirement 3: PASSED\n")
        
    def test_requirement_4_validation_indicators(self):
        """Test: Implement requirements validation with visual status indicators."""
        print("Testing Requirement 4: Requirements Validation with Visual Indicators")
        print("-" * 70)
        
        # Test with valid requirements
        valid_requirements = {
            'user_requirements': [
                {
                    'id': 'UR-VALID-001',
                    'description': 'Valid user requirement',
                    'priority': 'High',
                    'status': 'Approved',
                    'acceptance_criteria': ['Valid criterion']
                }
            ],
            'software_requirements': [
                {
                    'id': 'SR-VALID-001',
                    'description': 'Valid software requirement',
                    'priority': 'Medium',
                    'status': 'Implemented',
                    'derived_from': ['UR-VALID-001'],
                    'acceptance_criteria': ['Valid criterion']
                }
            ]
        }
        
        self.results_widget.requirements_tab.update_requirements(
            valid_requirements['user_requirements'],
            valid_requirements['software_requirements']
        )
        
        # Test validation status
        validation_status = self.results_widget.get_requirements_validation_status()
        assert validation_status['validation_passed'] == True, "Valid requirements failed validation"
        assert validation_status['total_errors'] == 0, "Valid requirements have errors"
        
        print("✓ Valid requirements pass validation")
        
        # Test with invalid requirements
        invalid_requirements = {
            'user_requirements': [
                {
                    'id': '',  # Invalid: empty ID
                    'description': 'Invalid user requirement',
                    'priority': 'InvalidPriority',  # Invalid priority
                    'status': 'Approved',
                    'acceptance_criteria': []  # Invalid: empty criteria
                }
            ],
            'software_requirements': [
                {
                    'id': 'INVALID-001',  # Invalid: doesn't start with SR-
                    'description': '',  # Invalid: empty description
                    'priority': 'Medium',
                    'status': 'InvalidStatus',  # Invalid status
                    'acceptance_criteria': ['Valid criterion']
                }
            ]
        }
        
        self.results_widget.requirements_tab.update_requirements(
            invalid_requirements['user_requirements'],
            invalid_requirements['software_requirements']
        )
        
        # Wait for validation update and process events
        time.sleep(0.1)
        self.app.processEvents()
        
        # Test validation status with invalid requirements
        validation_status = self.results_widget.get_requirements_validation_status()
        assert validation_status['validation_passed'] == False, "Invalid requirements passed validation"
        assert validation_status['total_errors'] > 0, "Invalid requirements have no errors"
        
        print("✓ Invalid requirements fail validation")
        print(f"✓ Validation errors detected: {validation_status['total_errors']}")
        
        # Test visual indicators
        req_tab_index = self.results_widget.indexOf(self.results_widget.requirements_tab)
        tab_text = self.results_widget.tabText(req_tab_index)
        tab_tooltip = self.results_widget.tabToolTip(req_tab_index)
        
        # Should show warning indicator for invalid requirements
        assert "⚠" in tab_text, f"Tab text should show warning indicator, got: '{tab_text}'"
        
        print(f"✓ Visual indicator in tab text: '{tab_text}'")
        print(f"✓ Tooltip information: '{tab_tooltip}'")
        
        # Test validation method exists
        assert hasattr(self.results_widget.requirements_tab, 'validate_all_requirements'), "validate_all_requirements method missing"
        assert hasattr(self.results_widget.requirements_tab, '_validate_requirement'), "_validate_requirement method missing"
        
        print("✓ Validation methods exist")
        print("✓ Visual status indicators working")
        print("✓ Requirement 4: PASSED\n")
        
    def run_all_tests(self):
        """Run all verification tests."""
        print("=" * 80)
        print("TASK 2.4 VERIFICATION TEST")
        print("Integrate Requirements Display with Results System")
        print("=" * 80)
        print()
        
        try:
            self.test_requirement_1_requirements_tab_integration()
            self.test_requirement_2_traceability_refresh_connection()
            self.test_requirement_3_export_functionality()
            self.test_requirement_4_validation_indicators()
            
            print("=" * 80)
            print("✅ ALL TESTS PASSED - TASK 2.4 IMPLEMENTATION VERIFIED")
            print("=" * 80)
            print()
            print("Task Requirements Verified:")
            print("✓ 1. Requirements tab integrated into ResultsTabWidget")
            print("✓ 2. Requirements updates trigger traceability matrix refresh")
            print("✓ 3. Multiple export formats (CSV, JSON, Excel, PDF) implemented")
            print("✓ 4. Requirements validation with visual status indicators")
            print()
            return True
            
        except AssertionError as e:
            print("=" * 80)
            print(f"❌ TEST FAILED: {e}")
            print("=" * 80)
            return False
        except Exception as e:
            print("=" * 80)
            print(f"❌ UNEXPECTED ERROR: {e}")
            print("=" * 80)
            return False


def main():
    """Run the verification test."""
    tester = TestResultsIntegration()
    success = tester.run_all_tests()
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)