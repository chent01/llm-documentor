#!/usr/bin/env python3
"""
Demo script for the enhanced progress and results display functionality.
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtCore import QTimer, pyqtSignal

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from medical_analyzer.ui.progress_widget import AnalysisProgressWidget, AnalysisStage, StageStatus
from medical_analyzer.ui.results_tab_widget import ResultsTabWidget


class ProgressAndResultsDemo(QMainWindow):
    """Demo window for progress and results widgets."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Progress and Results Display Demo")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Control buttons
        button_layout = QVBoxLayout()
        
        self.start_demo_button = QPushButton("Start Analysis Demo")
        self.start_demo_button.clicked.connect(self.start_analysis_demo)
        button_layout.addWidget(self.start_demo_button)
        
        self.show_results_button = QPushButton("Show Sample Results")
        self.show_results_button.clicked.connect(self.show_sample_results)
        button_layout.addWidget(self.show_results_button)
        
        self.clear_button = QPushButton("Clear All")
        self.clear_button.clicked.connect(self.clear_all)
        button_layout.addWidget(self.clear_button)
        
        layout.addLayout(button_layout)
        
        # Progress widget
        self.progress_widget = AnalysisProgressWidget()
        layout.addWidget(self.progress_widget)
        
        # Results widget
        self.results_widget = ResultsTabWidget()
        layout.addWidget(self.results_widget)
        
        # Timer for demo progression
        self.demo_timer = QTimer()
        self.demo_timer.timeout.connect(self.advance_demo)
        self.demo_stage = 0
        
        # Demo stages
        self.demo_stages = [
            (AnalysisStage.INITIALIZATION, "Initializing analysis environment..."),
            (AnalysisStage.FILE_SCANNING, "Scanning project files..."),
            (AnalysisStage.CODE_PARSING, "Parsing C and JavaScript files..."),
            (AnalysisStage.FEATURE_EXTRACTION, "Extracting software features..."),
            (AnalysisStage.REQUIREMENTS_GENERATION, "Generating requirements..."),
            (AnalysisStage.RISK_ANALYSIS, "Analyzing potential risks..."),
            (AnalysisStage.TRACEABILITY_MAPPING, "Creating traceability matrix..."),
            (AnalysisStage.TEST_GENERATION, "Generating test skeletons..."),
            (AnalysisStage.FINALIZATION, "Finalizing analysis results...")
        ]
        
    def start_analysis_demo(self):
        """Start the analysis progress demo."""
        self.progress_widget.start_analysis()
        self.results_widget.clear_results()
        self.demo_stage = 0
        self.demo_timer.start(2000)  # Update every 2 seconds
        self.start_demo_button.setEnabled(False)
        
    def advance_demo(self):
        """Advance the demo to the next stage."""
        if self.demo_stage < len(self.demo_stages):
            stage, message = self.demo_stages[self.demo_stage]
            
            # Start the stage
            self.progress_widget.update_stage_progress(
                stage, 0, StageStatus.IN_PROGRESS, message
            )
            
            # Simulate progress within the stage
            for progress in [25, 50, 75, 100]:
                QTimer.singleShot(
                    500 * (progress // 25), 
                    lambda p=progress, s=stage, m=message: self.update_stage_progress(s, p, m)
                )
            
            self.demo_stage += 1
            
            # Add some failures for demonstration
            if self.demo_stage == 4:  # Fail feature extraction
                QTimer.singleShot(
                    1500,
                    lambda: self.progress_widget.update_stage_progress(
                        AnalysisStage.FEATURE_EXTRACTION, 75, StageStatus.FAILED,
                        error_message="Failed to extract features from complex.c"
                    )
                )
                
        else:
            # Demo complete
            self.demo_timer.stop()
            self.progress_widget.complete_analysis(success=True)
            self.start_demo_button.setEnabled(True)
            
            # Show results after completion
            QTimer.singleShot(1000, self.show_sample_results)
            
    def update_stage_progress(self, stage, progress, message):
        """Update stage progress during demo."""
        status = StageStatus.COMPLETED if progress == 100 else StageStatus.IN_PROGRESS
        self.progress_widget.update_stage_progress(stage, progress, status, message)
        
    def show_sample_results(self):
        """Show sample analysis results."""
        sample_results = {
            'summary': {
                'project_path': '/demo/medical-device-project',
                'files_analyzed': 42,
                'analysis_date': '2023-12-01 14:30:00',
                'features_found': 18,
                'requirements_generated': 35,
                'risks_identified': 12,
                'confidence': 87,
                'errors': ['Failed to parse complex.c line 245'],
                'warnings': [
                    'Low confidence in feature "Data Encryption"',
                    'Missing documentation for function authenticate()'
                ]
            },
            'requirements': {
                'user_requirements': [
                    {
                        'id': 'UR-001',
                        'description': 'The system shall authenticate users before granting access',
                        'acceptance_criteria': [
                            'System shall validate user credentials against secure database',
                            'System shall lock account after 3 failed attempts',
                            'System shall log all authentication attempts'
                        ]
                    },
                    {
                        'id': 'UR-002',
                        'description': 'The system shall encrypt all patient data at rest and in transit',
                        'acceptance_criteria': [
                            'System shall use AES-256 encryption for data at rest',
                            'System shall use TLS 1.3 for data in transit',
                            'System shall manage encryption keys securely'
                        ]
                    },
                    {
                        'id': 'UR-003',
                        'description': 'The system shall provide real-time monitoring of patient vitals',
                        'acceptance_criteria': [
                            'System shall update vital signs every 5 seconds',
                            'System shall alert on abnormal readings',
                            'System shall maintain 99.9% uptime'
                        ]
                    }
                ],
                'software_requirements': [
                    {
                        'id': 'SR-001',
                        'description': 'Implement secure authentication service',
                        'derived_from': ['UR-001'],
                        'code_references': [
                            {'file': 'auth.c', 'line': 45},
                            {'file': 'login.js', 'line': 123}
                        ]
                    },
                    {
                        'id': 'SR-002',
                        'description': 'Implement data encryption module',
                        'derived_from': ['UR-002'],
                        'code_references': [
                            {'file': 'crypto.c', 'line': 78},
                            {'file': 'encryption.js', 'line': 56}
                        ]
                    },
                    {
                        'id': 'SR-003',
                        'description': 'Implement real-time data acquisition',
                        'derived_from': ['UR-003'],
                        'code_references': [
                            {'file': 'sensors.c', 'line': 234},
                            {'file': 'monitor.js', 'line': 89}
                        ]
                    }
                ]
            },
            'risks': [
                {
                    'id': 'R-001',
                    'hazard': 'Unauthorized access to patient data',
                    'cause': 'Weak authentication mechanism',
                    'effect': 'Privacy breach, regulatory violation',
                    'severity': 'Catastrophic',
                    'probability': 'Medium',
                    'risk_level': 'High',
                    'mitigation': 'Implement multi-factor authentication and regular security audits'
                },
                {
                    'id': 'R-002',
                    'hazard': 'Data corruption during transmission',
                    'cause': 'Network interference or encryption failure',
                    'effect': 'Incorrect patient data, misdiagnosis',
                    'severity': 'Serious',
                    'probability': 'Low',
                    'risk_level': 'Medium',
                    'mitigation': 'Implement data integrity checks and redundant transmission paths'
                },
                {
                    'id': 'R-003',
                    'hazard': 'System failure during critical monitoring',
                    'cause': 'Hardware failure or software crash',
                    'effect': 'Loss of patient monitoring, delayed response',
                    'severity': 'Catastrophic',
                    'probability': 'Low',
                    'risk_level': 'High',
                    'mitigation': 'Implement redundant systems and automatic failover mechanisms'
                },
                {
                    'id': 'R-004',
                    'hazard': 'False alarms from monitoring system',
                    'cause': 'Sensor calibration drift or software bugs',
                    'effect': 'Alarm fatigue, ignored real emergencies',
                    'severity': 'Serious',
                    'probability': 'Medium',
                    'risk_level': 'Medium',
                    'mitigation': 'Regular sensor calibration and intelligent alarm filtering'
                }
            ],
            'traceability': {
                'matrix': 'Sample traceability matrix data',
                'links': [
                    {'source': 'UR-001', 'target': 'SR-001', 'type': 'derives'},
                    {'source': 'SR-001', 'target': 'auth.c:45', 'type': 'implements'},
                    {'source': 'UR-002', 'target': 'SR-002', 'type': 'derives'},
                    {'source': 'SR-002', 'target': 'crypto.c:78', 'type': 'implements'}
                ]
            },
            'tests': {
                'total_tests': 156,
                'passed_tests': 142,
                'failed_tests': 14,
                'coverage': 78,
                'details': '''Test Execution Summary:
                
Unit Tests:
✓ Authentication module: 45/48 tests passed
✗ Encryption module: 12/15 tests passed (3 failures)
✓ Monitoring module: 38/40 tests passed
✗ Data validation: 25/28 tests passed (3 failures)

Integration Tests:
✓ End-to-end authentication flow: PASSED
✗ Data encryption/decryption cycle: FAILED (timeout)
✓ Real-time monitoring pipeline: PASSED

Failed Tests:
1. test_encryption_large_files - Timeout after 30s
2. test_key_rotation - Invalid key format error
3. test_concurrent_access - Race condition detected
4. test_sensor_calibration - Calibration drift beyond tolerance
5. test_alarm_threshold - False positive rate too high

Coverage Report:
- Authentication: 95%
- Encryption: 65% (low due to error handling paths)
- Monitoring: 82%
- Data validation: 71%
- Overall: 78%'''
            }
        }
        
        self.results_widget.update_results(sample_results)
        
    def clear_all(self):
        """Clear all displays."""
        self.progress_widget.hide_progress()
        self.results_widget.clear_results()
        self.demo_timer.stop()
        self.start_demo_button.setEnabled(True)


def main():
    """Run the demo application."""
    app = QApplication(sys.argv)
    
    # Create and show the demo window
    demo = ProgressAndResultsDemo()
    demo.show()
    
    print("Progress and Results Display Demo")
    print("=================================")
    print("This demo shows the enhanced progress tracking and results display features.")
    print("Click 'Start Analysis Demo' to see the progress widget in action.")
    print("Click 'Show Sample Results' to see the results tabs with sample data.")
    print("Click 'Clear All' to reset the display.")
    print("\nFeatures demonstrated:")
    print("- Detailed progress tracking for each analysis stage")
    print("- Real-time progress updates with timing information")
    print("- Error handling and partial results display")
    print("- Organized results tabs (Summary, Requirements, Risks, Traceability, Tests)")
    print("- Interactive results with filtering and export options")
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()