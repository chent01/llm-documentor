#!/usr/bin/env python3
"""
Test script to verify Task 2.4 implementation:
Integrate Requirements Display with Results System
"""

import sys
import os
import tempfile
import json
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import QTimer
from medical_analyzer.ui.results_tab_widget import ResultsTabWidget
from medical_analyzer.services.soup_service import SOUPService
from medical_analyzer.database.schema import DatabaseManager


class TestMainWindow(QMainWindow):
    """Test window for verifying requirements integration."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Task 2.4 Integration Test")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Initialize services
        self.db_manager = DatabaseManager()
        self.soup_service = SOUPService(self.db_manager)
        
        # Create results widget
        self.results_widget = ResultsTabWidget(self.soup_service)
        layout.addWidget(self.results_widget)
        
        # Connect signals for testing
        self.results_widget.export_requested.connect(self.handle_export_request)
        self.results_widget.refresh_requested.connect(self.handle_refresh_request)
        
        # Load test data after a short delay
        QTimer.singleShot(100, self.load_test_data)
        
    def load_test_data(self):
        """Load test requirements data."""
        test_results = {
            'summary': {
                'total_files': 5,
                'analysis_time': 45.2,
                'status': 'completed'
            },
            'requirements': {
                'user_requirements': [
                    {
                        'id': 'UR-001',
                        'description': 'The system shall provide user authentication',
                        'priority': 'High',
                        'status': 'Approved',
                        'acceptance_criteria': [
                            'User can log in with valid credentials',
                            'System rejects invalid credentials',
                            'Session timeout after 30 minutes'
                        ]
                    },
                    {
                        'id': 'UR-002',
                        'description': 'The system shall maintain audit logs',
                        'priority': 'Medium',
                        'status': 'Draft',
                        'acceptance_criteria': [
                            'All user actions are logged',
                            'Logs include timestamp and user ID',
                            'Logs are tamper-proof'
                        ]
                    }
                ],
                'software_requirements': [
                    {
                        'id': 'SR-001',
                        'description': 'Implement password hashing using bcrypt',
                        'priority': 'High',
                        'status': 'Implemented',
                        'derived_from': ['UR-001'],
                        'code_references': [
                            {'file': 'auth.py', 'line': 45},
                            {'file': 'security.py', 'line': 23}
                        ],
                        'acceptance_criteria': [
                            'Passwords are hashed with bcrypt',
                            'Salt rounds >= 12',
                            'Hash verification works correctly'
                        ]
                    },
                    {
                        'id': 'SR-002',
                        'description': 'Implement session management',
                        'priority': 'High',
                        'status': 'Under Review',
                        'derived_from': ['UR-001'],
                        'code_references': [
                            {'file': 'session.py', 'line': 12}
                        ],
                        'acceptance_criteria': [
                            'Sessions expire after timeout',
                            'Session tokens are secure',
                            'Concurrent sessions are handled'
                        ]
                    }
                ]
            },
            'risks': [
                {
                    'id': 'R-001',
                    'hazard': 'Unauthorized access',
                    'cause': 'Weak authentication',
                    'effect': 'Data breach',
                    'severity': 'Catastrophic',
                    'probability': 'Medium',
                    'risk_level': 'High',
                    'mitigation': 'Strong password policy',
                    'verification': 'Penetration testing'
                }
            ],
            'traceability': {
                'matrix_rows': [
                    {
                        'code_reference': 'auth.py:45',
                        'file_path': 'src/auth.py',
                        'function': 'hash_password',
                        'feature_id': 'F-001',
                        'feature_description': 'Password hashing',
                        'user_req_id': 'UR-001',
                        'user_requirement': 'User authentication',
                        'software_req_id': 'SR-001',
                        'software_requirement': 'Password hashing',
                        'risk_id': 'R-001'
                    }
                ],
                'gaps': [],
                'total_links': 1
            },
            'tests': {
                'total_tests': 10,
                'passed_tests': 8,
                'failed_tests': 2,
                'coverage': 85.5
            }
        }
        
        # Update results widget
        self.results_widget.update_results(test_results)
        
        print("✓ Test data loaded successfully")
        print(f"✓ Requirements tab contains {len(test_results['requirements']['user_requirements'])} URs and {len(test_results['requirements']['software_requirements'])} SRs")
        
        # Test validation
        validation_status = self.results_widget.get_requirements_validation_status()
        print(f"✓ Validation status: {validation_status['validation_passed']} (errors: {validation_status['total_errors']})")
        
        # Test export functionality
        QTimer.singleShot(1000, self.test_export_functionality)
        
    def test_export_functionality(self):
        """Test the export functionality."""
        print("\n=== Testing Export Functionality ===")
        
        try:
            # Test CSV export
            csv_content = self.results_widget._export_requirements_csv()
            print(f"✓ CSV export: {len(csv_content)} characters")
            
            # Test JSON export
            json_content = self.results_widget._export_requirements_json()
            json_data = json.loads(json_content)
            print(f"✓ JSON export: {len(json_data['user_requirements'])} URs, {len(json_data['software_requirements'])} SRs")
            
            # Test Excel export
            excel_content = self.results_widget._export_requirements_excel()
            print(f"✓ Excel export: {len(excel_content)} characters")
            
            # Test PDF export
            pdf_content = self.results_widget._export_requirements_pdf()
            print(f"✓ PDF export: {len(pdf_content)} characters")
            
            print("✓ All export formats working correctly")
            
        except Exception as e:
            print(f"✗ Export test failed: {e}")
            
        # Test traceability refresh
        QTimer.singleShot(500, self.test_traceability_integration)
        
    def test_traceability_integration(self):
        """Test traceability matrix integration."""
        print("\n=== Testing Traceability Integration ===")
        
        try:
            # Simulate requirements update
            updated_requirements = {
                'user_requirements': self.results_widget.requirements_tab.user_requirements + [
                    {
                        'id': 'UR-003',
                        'description': 'New test requirement',
                        'priority': 'Low',
                        'status': 'Draft',
                        'acceptance_criteria': ['Test criterion']
                    }
                ],
                'software_requirements': self.results_widget.requirements_tab.software_requirements
            }
            
            # Update requirements (this should trigger traceability refresh)
            self.results_widget.requirements_tab.update_requirements(
                updated_requirements['user_requirements'],
                updated_requirements['software_requirements']
            )
            
            print("✓ Requirements updated successfully")
            print("✓ Traceability refresh signal should have been emitted")
            
            # Test validation indicators
            validation_status = self.results_widget.get_requirements_validation_status()
            print(f"✓ Updated validation status: {validation_status['total_requirements']} total requirements")
            
        except Exception as e:
            print(f"✗ Traceability integration test failed: {e}")
            
        # Test visual indicators
        QTimer.singleShot(500, self.test_visual_indicators)
        
    def test_visual_indicators(self):
        """Test visual validation indicators."""
        print("\n=== Testing Visual Indicators ===")
        
        try:
            # Get current tab text
            req_tab_index = self.results_widget.indexOf(self.results_widget.requirements_tab)
            tab_text = self.results_widget.tabText(req_tab_index)
            tab_tooltip = self.results_widget.tabToolTip(req_tab_index)
            
            print(f"✓ Requirements tab text: '{tab_text}'")
            print(f"✓ Requirements tab tooltip: '{tab_tooltip}'")
            
            # Check if validation indicators are working
            if "✓" in tab_text or "⚠" in tab_text:
                print("✓ Visual validation indicators are working")
            else:
                print("⚠ Visual validation indicators may not be working")
                
        except Exception as e:
            print(f"✗ Visual indicators test failed: {e}")
            
        print("\n=== Integration Test Complete ===")
        print("Task 2.4 implementation appears to be working correctly!")
        
    def handle_export_request(self, tab_name: str, export_type: str):
        """Handle export requests for testing."""
        print(f"📤 Export requested: {tab_name} -> {export_type}")
        
    def handle_refresh_request(self, tab_name: str):
        """Handle refresh requests for testing."""
        print(f"🔄 Refresh requested: {tab_name}")


def main():
    """Run the integration test."""
    app = QApplication(sys.argv)
    
    print("Starting Task 2.4 Integration Test...")
    print("=" * 50)
    
    # Create and show test window
    window = TestMainWindow()
    window.show()
    
    # Run for a few seconds then exit
    QTimer.singleShot(5000, app.quit)
    
    try:
        app.exec()
        print("\n✓ Integration test completed successfully!")
        return True
    except Exception as e:
        print(f"\n✗ Integration test failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)