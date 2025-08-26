#!/usr/bin/env python3
"""
Demo script for enhanced results tab widget functionality.
Shows the editable requirements display, risk register with filtering,
traceability matrix viewer with export, and test results with execution controls.
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PyQt6.QtCore import QTimer

from medical_analyzer.ui.results_tab_widget import ResultsTabWidget


class EnhancedResultsDemo(QMainWindow):
    """Demo window for enhanced results tab functionality."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enhanced Results Tab Widget Demo")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create control buttons
        button_layout = QHBoxLayout()
        
        self.load_sample_data_btn = QPushButton("Load Sample Data")
        self.load_sample_data_btn.clicked.connect(self.load_sample_data)
        button_layout.addWidget(self.load_sample_data_btn)
        
        self.clear_data_btn = QPushButton("Clear Data")
        self.clear_data_btn.clicked.connect(self.clear_data)
        button_layout.addWidget(self.clear_data_btn)
        
        self.export_demo_btn = QPushButton("Demo Export")
        self.export_demo_btn.clicked.connect(self.demo_export)
        button_layout.addWidget(self.export_demo_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Create results tab widget
        self.results_widget = ResultsTabWidget()
        layout.addWidget(self.results_widget)
        
        # Connect signals
        self.results_widget.export_requested.connect(self.handle_export_request)
        self.results_widget.refresh_requested.connect(self.handle_refresh_request)
        
        # Load sample data after a short delay
        QTimer.singleShot(500, self.load_sample_data)
        
    def load_sample_data(self):
        """Load comprehensive sample data to demonstrate all features."""
        
        # Sample summary data
        summary_data = {
            'project_path': '/path/to/medical/device/project',
            'files_analyzed': 42,
            'analysis_date': '2024-01-15 14:30:00',
            'features_found': 18,
            'requirements_generated': 35,
            'risks_identified': 12,
            'confidence': 87,
            'errors': ['Warning: Low confidence in feature extraction for legacy_module.c'],
            'warnings': ['Info: Some functions lack documentation comments']
        }
        
        # Sample requirements data
        requirements_data = {
            'user_requirements': [
                {
                    'id': 'UR-001',
                    'description': 'The system shall provide secure user authentication',
                    'acceptance_criteria': [
                        'System shall validate user credentials against secure database',
                        'System shall lock account after 3 failed attempts',
                        'System shall require password complexity requirements'
                    ]
                },
                {
                    'id': 'UR-002',
                    'description': 'The system shall monitor patient vital signs continuously',
                    'acceptance_criteria': [
                        'System shall sample vital signs every 100ms',
                        'System shall alert on abnormal readings within 2 seconds',
                        'System shall maintain 99.9% uptime'
                    ]
                },
                {
                    'id': 'UR-003',
                    'description': 'The system shall store patient data securely',
                    'acceptance_criteria': [
                        'System shall encrypt all patient data at rest',
                        'System shall provide audit trail for data access',
                        'System shall comply with HIPAA requirements'
                    ]
                }
            ],
            'software_requirements': [
                {
                    'id': 'SR-001',
                    'description': 'Implement authentication service with secure password hashing',
                    'derived_from': ['UR-001'],
                    'code_references': [
                        {'file': 'auth/authentication.c', 'line': 45},
                        {'file': 'auth/password_hash.c', 'line': 23},
                        {'file': 'ui/login_dialog.js', 'line': 156}
                    ]
                },
                {
                    'id': 'SR-002',
                    'description': 'Implement real-time vital signs monitoring with alarm system',
                    'derived_from': ['UR-002'],
                    'code_references': [
                        {'file': 'monitoring/vital_signs.c', 'line': 78},
                        {'file': 'alarms/alarm_manager.c', 'line': 134},
                        {'file': 'hardware/sensor_interface.c', 'line': 92}
                    ]
                },
                {
                    'id': 'SR-003',
                    'description': 'Implement encrypted database storage with access logging',
                    'derived_from': ['UR-003'],
                    'code_references': [
                        {'file': 'database/encryption.c', 'line': 67},
                        {'file': 'database/audit_log.c', 'line': 189},
                        {'file': 'database/patient_data.c', 'line': 234}
                    ]
                }
            ]
        }
        
        # Sample risk data
        risks_data = [
            {
                'id': 'R-001',
                'hazard': 'Unauthorized access to patient data',
                'cause': 'Weak authentication or compromised credentials',
                'effect': 'Patient privacy breach, regulatory violations',
                'severity': 'Catastrophic',
                'probability': 'Medium',
                'risk_level': 'High',
                'mitigation': 'Implement multi-factor authentication, regular security audits',
                'verification': 'Penetration testing, security code review',
                'related_requirements': ['SR-001']
            },
            {
                'id': 'R-002',
                'hazard': 'False alarm or missed critical vital sign changes',
                'cause': 'Sensor malfunction or software algorithm error',
                'effect': 'Delayed medical response, patient harm',
                'severity': 'Catastrophic',
                'probability': 'Low',
                'risk_level': 'Medium',
                'mitigation': 'Redundant sensors, algorithm validation, regular calibration',
                'verification': 'Clinical testing, sensor validation protocols',
                'related_requirements': ['SR-002']
            },
            {
                'id': 'R-003',
                'hazard': 'Data corruption or loss',
                'cause': 'Database failure, encryption key loss, or hardware failure',
                'effect': 'Loss of patient history, treatment delays',
                'severity': 'Serious',
                'probability': 'Low',
                'risk_level': 'Low',
                'mitigation': 'Regular backups, redundant storage, key escrow',
                'verification': 'Backup/restore testing, disaster recovery drills',
                'related_requirements': ['SR-003']
            },
            {
                'id': 'R-004',
                'hazard': 'System performance degradation',
                'cause': 'High CPU usage, memory leaks, or network congestion',
                'effect': 'Delayed response times, system instability',
                'severity': 'Serious',
                'probability': 'Medium',
                'risk_level': 'Medium',
                'mitigation': 'Performance monitoring, resource optimization, load testing',
                'verification': 'Performance testing, stress testing, monitoring alerts',
                'related_requirements': ['SR-001', 'SR-002', 'SR-003']
            }
        ]
        
        # Sample traceability data
        traceability_data = {
            'matrix_rows': [
                {
                    'code_reference': 'auth/authentication.c:45-78',
                    'file_path': 'auth/authentication.c',
                    'function_name': 'authenticate_user',
                    'feature_id': 'F-001',
                    'feature_description': 'User authentication with password validation',
                    'user_requirement_id': 'UR-001',
                    'user_requirement_text': 'The system shall provide secure user authentication',
                    'software_requirement_id': 'SR-001',
                    'software_requirement_text': 'Implement authentication service with secure password hashing',
                    'risk_id': 'R-001',
                    'confidence': 0.95
                },
                {
                    'code_reference': 'monitoring/vital_signs.c:78-156',
                    'file_path': 'monitoring/vital_signs.c',
                    'function_name': 'monitor_vital_signs',
                    'feature_id': 'F-002',
                    'feature_description': 'Continuous vital signs monitoring',
                    'user_requirement_id': 'UR-002',
                    'user_requirement_text': 'The system shall monitor patient vital signs continuously',
                    'software_requirement_id': 'SR-002',
                    'software_requirement_text': 'Implement real-time vital signs monitoring with alarm system',
                    'risk_id': 'R-002',
                    'confidence': 0.88
                },
                {
                    'code_reference': 'database/encryption.c:67-123',
                    'file_path': 'database/encryption.c',
                    'function_name': 'encrypt_patient_data',
                    'feature_id': 'F-003',
                    'feature_description': 'Patient data encryption and secure storage',
                    'user_requirement_id': 'UR-003',
                    'user_requirement_text': 'The system shall store patient data securely',
                    'software_requirement_id': 'SR-003',
                    'software_requirement_text': 'Implement encrypted database storage with access logging',
                    'risk_id': 'R-003',
                    'confidence': 0.92
                }
            ],
            'gaps': [
                {
                    'gap_type': 'orphaned_code',
                    'description': 'Function legacy_data_handler() has no feature mapping',
                    'severity': 'medium',
                    'source_type': 'code',
                    'source_id': 'legacy/data_handler.c:234-267',
                    'recommendation': 'Map to existing feature or create new feature requirement'
                },
                {
                    'gap_type': 'missing_risk',
                    'description': 'Software requirement SR-004 has no associated risk assessment',
                    'severity': 'high',
                    'source_type': 'requirement',
                    'source_id': 'SR-004',
                    'recommendation': 'Conduct risk assessment for network communication requirements'
                }
            ],
            'matrix': {
                'metadata': {
                    'total_links': 15,
                    'code_feature_links': 8,
                    'code_sr_links': 8,
                    'feature_ur_links': 6,
                    'ur_sr_links': 6,
                    'sr_risk_links': 4
                }
            }
        }
        
        # Sample test data
        test_data = {
            'total_tests': 127,
            'passed_tests': 119,
            'failed_tests': 6,
            'skipped_tests': 2,
            'coverage': 84,
            'execution_time': 45.7,
            'last_run': '2024-01-15 14:25:33',
            'status': 'Completed',
            'test_suites': [
                {
                    'id': 'unit_tests',
                    'name': 'Unit Tests',
                    'total_tests': 89,
                    'passed_tests': 85,
                    'failed_tests': 3,
                    'status': 'Failed',
                    'output': 'Unit test execution completed with 3 failures in authentication module',
                    'failed_test_details': [
                        {
                            'name': 'test_password_complexity',
                            'error': 'AssertionError: Password validation failed for edge case',
                            'file': 'tests/test_authentication.c'
                        },
                        {
                            'name': 'test_account_lockout',
                            'error': 'Timeout: Account lockout not triggered within expected time',
                            'file': 'tests/test_authentication.c'
                        },
                        {
                            'name': 'test_session_timeout',
                            'error': 'Session remained active beyond configured timeout',
                            'file': 'tests/test_session.c'
                        }
                    ]
                },
                {
                    'id': 'integration_tests',
                    'name': 'Integration Tests',
                    'total_tests': 28,
                    'passed_tests': 25,
                    'failed_tests': 2,
                    'status': 'Failed',
                    'output': 'Integration test execution completed with 2 failures in monitoring module',
                    'failed_test_details': [
                        {
                            'name': 'test_alarm_response_time',
                            'error': 'Response time exceeded 2 second requirement: 2.3s',
                            'file': 'tests/test_monitoring_integration.c'
                        },
                        {
                            'name': 'test_sensor_redundancy',
                            'error': 'Failover to backup sensor not triggered',
                            'file': 'tests/test_sensor_integration.c'
                        }
                    ]
                },
                {
                    'id': 'system_tests',
                    'name': 'System Tests',
                    'total_tests': 10,
                    'passed_tests': 9,
                    'failed_tests': 1,
                    'skipped_tests': 2,
                    'status': 'Failed',
                    'output': 'System test execution completed with 1 failure, 2 tests skipped due to hardware unavailability',
                    'failed_test_details': [
                        {
                            'name': 'test_end_to_end_workflow',
                            'error': 'Database connection timeout during patient data retrieval',
                            'file': 'tests/test_system_workflow.c'
                        }
                    ]
                }
            ],
            'output': 'Test execution completed with 6 failures across 3 test suites. See individual suite details for specific failure information.',
            'coverage_report': '''
COVERAGE REPORT
===============
File                          Lines    Covered    Percentage
auth/authentication.c           234       198         84.6%
auth/password_hash.c            89        76         85.4%
monitoring/vital_signs.c       345       289         83.8%
alarms/alarm_manager.c         156       134         85.9%
database/encryption.c          123       108         87.8%
database/audit_log.c           167       142         85.0%
database/patient_data.c        289       234         81.0%
hardware/sensor_interface.c    198       156         78.8%
ui/login_dialog.js             234       201         85.9%
legacy/data_handler.c          145        89         61.4%
===============================================
TOTAL                         1980      1627         82.2%

Low coverage files (< 80%):
- legacy/data_handler.c (61.4%) - Consider refactoring or adding tests
- hardware/sensor_interface.c (78.8%) - Hardware simulation tests needed
'''
        }
        
        # Combine all data
        complete_results = {
            'summary': summary_data,
            'requirements': requirements_data,
            'risks': risks_data,
            'traceability': traceability_data,
            'tests': test_data
        }
        
        # Update the results widget
        self.results_widget.update_results(complete_results)
        
        print("Sample data loaded successfully!")
        print("Try the following features:")
        print("1. Edit requirements by double-clicking on them in the Requirements tab")
        print("2. Add/edit/delete risks in the Risk Register tab")
        print("3. Filter risks by severity or search for specific hazards")
        print("4. View traceability matrix and export options in the Traceability tab")
        print("5. Check test execution results and failed test details in the Tests tab")
        print("6. Use the 'Demo Export' button to see export functionality")
        
    def clear_data(self):
        """Clear all data from the results widget."""
        self.results_widget.clear_results()
        print("Data cleared.")
        
    def demo_export(self):
        """Demonstrate export functionality."""
        print("\n=== Export Demo ===")
        
        # Export requirements
        req_csv = self.results_widget.export_data("requirements", "csv")
        if req_csv:
            print(f"Requirements CSV export: {len(req_csv)} characters")
            print("First 200 characters:", req_csv[:200] + "...")
        
        # Export risks
        risk_csv = self.results_widget.export_data("risks", "csv")
        if risk_csv:
            print(f"Risk register CSV export: {len(risk_csv)} characters")
            print("First 200 characters:", risk_csv[:200] + "...")
        
        # Export traceability
        trace_csv = self.results_widget.export_data("traceability", "csv")
        if trace_csv:
            print(f"Traceability matrix CSV export: {len(trace_csv)} characters")
            print("First 200 characters:", trace_csv[:200] + "...")
        
        # Export test results
        test_results = self.results_widget.export_data("tests", "results")
        if test_results:
            print(f"Test results export: {len(test_results)} characters")
            print("First 200 characters:", test_results[:200] + "...")
        
        # Export gaps report
        gaps_report = self.results_widget.export_data("traceability", "gaps")
        if gaps_report:
            print(f"Gaps report export: {len(gaps_report)} characters")
            print("First 200 characters:", gaps_report[:200] + "...")
        
        print("Export demo completed!")
        
    def handle_export_request(self, tab_name: str, export_type: str):
        """Handle export requests from the results widget."""
        print(f"Export requested: {tab_name} -> {export_type}")
        
        # Get the exported data
        exported_data = self.results_widget.export_data(tab_name, export_type)
        
        if exported_data:
            print(f"Export successful: {len(exported_data)} characters")
            # In a real application, you would save this to a file
            # For demo purposes, just show the first few lines
            lines = exported_data.split('\n')[:5]
            print("Preview:")
            for line in lines:
                print(f"  {line}")
        else:
            print("Export failed or returned no data")
            
    def handle_refresh_request(self, tab_name: str):
        """Handle refresh requests from the results widget."""
        print(f"Refresh requested for tab: {tab_name}")
        # In a real application, you would reload data from the analysis engine
        print("Refresh completed (demo - no actual refresh performed)")


def main():
    """Run the enhanced results tab demo."""
    app = QApplication(sys.argv)
    
    # Create and show the demo window
    demo = EnhancedResultsDemo()
    demo.show()
    
    print("Enhanced Results Tab Widget Demo")
    print("================================")
    print("This demo showcases the enhanced results tab functionality:")
    print("- Editable requirements display with text fields")
    print("- Risk register table with filtering capabilities")
    print("- Traceability matrix viewer with export options")
    print("- Test results display with execution controls")
    print("- Comprehensive UI tests for result editing and interaction")
    print("\nInteract with the tabs to explore the functionality!")
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()