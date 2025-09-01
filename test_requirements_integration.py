#!/usr/bin/env python3
"""
Test script to verify requirements display integration with results system.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from medical_analyzer.ui.results_tab_widget import ResultsTabWidget
from medical_analyzer.services.soup_service import SOUPService
from medical_analyzer.database.schema import DatabaseManager

def test_requirements_integration(qapp):
    """Test the requirements integration functionality."""
    
    # Create test data
    test_user_requirements = [
        {
            'id': 'UR-001',
            'description': 'The system shall provide user authentication',
            'priority': 'High',
            'status': 'Approved',
            'acceptance_criteria': [
                'User can log in with valid credentials',
                'Invalid credentials are rejected'
            ]
        },
        {
            'id': 'UR-002',
            'description': 'The system shall log user activities',
            'priority': 'Medium',
            'status': 'Draft',
            'acceptance_criteria': [
                'All user actions are logged with timestamp',
                'Logs are stored securely'
            ]
        }
    ]
    
    test_software_requirements = [
        {
            'id': 'SR-001',
            'description': 'Implement password hashing using bcrypt',
            'priority': 'High',
            'status': 'Implemented',
            'derived_from': ['UR-001'],
            'code_references': ['auth/password_manager.py'],
            'acceptance_criteria': [
                'Passwords are hashed using bcrypt with salt rounds >= 12',
                'Hash verification works correctly'
            ]
        }
    ]
    
    # Create results widget
    db_manager = DatabaseManager()
    soup_service = SOUPService(db_manager)
    results_widget = ResultsTabWidget(soup_service)
    
    # Test data update
    test_results = {
        'requirements': {
            'user_requirements': test_user_requirements,
            'software_requirements': test_software_requirements
        },
        'summary': {
            'total_files': 5,
            'analysis_time': 45.2,
            'status': 'completed'
        }
    }
    
    # Update results
    results_widget.update_results(test_results)
    
    # Test validation indicators
    print("Testing validation indicators...")
    validation_passed = results_widget.requirements_tab.validate_all_requirements()
    print(f"Validation passed: {validation_passed}")
    
    # Test export functionality
    print("Testing export functionality...")
    csv_export = results_widget.export_data("requirements", "csv")
    json_export = results_widget.export_data("requirements", "json")
    excel_export = results_widget.export_data("requirements", "excel")
    pdf_export = results_widget.export_data("requirements", "pdf")
    
    print(f"CSV export length: {len(csv_export) if csv_export else 0}")
    print(f"JSON export length: {len(json_export) if json_export else 0}")
    print(f"Excel export length: {len(excel_export) if excel_export else 0}")
    print(f"PDF export length: {len(pdf_export) if pdf_export else 0}")
    
    # Test requirements update signal
    print("Testing requirements update signal...")
    signal_received = False
    
    def on_requirements_updated(data):
        nonlocal signal_received
        signal_received = True
        print(f"Requirements updated signal received with {len(data.get('user_requirements', []))} URs and {len(data.get('software_requirements', []))} SRs")
    
    results_widget.requirements_tab.requirements_updated.connect(on_requirements_updated)
    
    # Trigger an update
    results_widget.requirements_tab.emit_requirements_updated()
    
    # Process events to handle signals
    qapp.processEvents()
    
    print(f"Signal received: {signal_received}")
    
    print("✓ Requirements integration test completed successfully!")
    
    # Use assertions instead of return values for pytest
    assert validation_passed, "Requirements validation should pass"
    assert signal_received, "Requirements update signal should be received"
    assert len(csv_export) > 0, "CSV export should not be empty"
    assert len(json_export) > 0, "JSON export should not be empty"

if __name__ == "__main__":
    # For standalone execution, use pytest
    pytest.main([__file__, "-v"])