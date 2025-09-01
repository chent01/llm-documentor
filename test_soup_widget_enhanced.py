#!/usr/bin/env python3
"""
Test script for enhanced SOUP widget functionality.
"""

import pytest
import sys
import tempfile
import json
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt

# Add the medical_analyzer package to the path
sys.path.insert(0, str(Path(__file__).parent))

from medical_analyzer.ui.soup_widget import SOUPWidget
from medical_analyzer.services.soup_service import SOUPService
from medical_analyzer.database.schema import DatabaseManager
from medical_analyzer.models.core import SOUPComponent
from medical_analyzer.models.soup_models import DetectedSOUPComponent, DetectionMethod, IEC62304SafetyClass


def create_test_project():
    """Create a test project with dependency files for detection."""
    test_dir = Path(tempfile.mkdtemp())
    
    # Create package.json
    package_json = {
        "name": "test-medical-app",
        "version": "1.0.0",
        "dependencies": {
            "express": "^4.18.0",
            "sqlite3": "^5.1.0",
            "bcrypt": "^5.1.0"
        },
        "devDependencies": {
            "jest": "^29.0.0",
            "eslint": "^8.0.0"
        }
    }
    
    with open(test_dir / "package.json", "w") as f:
        json.dump(package_json, f, indent=2)
    
    # Create requirements.txt
    requirements_txt = """
flask==2.3.0
sqlalchemy>=1.4.0
cryptography==41.0.0
pytest==7.4.0
black==23.0.0
"""
    
    with open(test_dir / "requirements.txt", "w") as f:
        f.write(requirements_txt.strip())
    
    return str(test_dir)


def test_soup_widget(qapp):
    """Test the enhanced SOUP widget."""
    
    # Create temporary database
    db_path = tempfile.mktemp(suffix=".db")
    db_manager = DatabaseManager(db_path)
    
    # Initialize services
    soup_service = SOUPService(db_manager)
    
    # Create main window
    main_window = QMainWindow()
    main_window.setWindowTitle("Enhanced SOUP Widget Test")
    main_window.resize(1200, 800)
    
    # Create central widget
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    
    # Create SOUP widget
    soup_widget = SOUPWidget(soup_service)
    layout.addWidget(soup_widget)
    
    main_window.setCentralWidget(central_widget)
    
    # Add some test components
    import uuid
    test_components = [
        SOUPComponent(
            id=str(uuid.uuid4()),
            name="SQLite",
            version="3.42.0",
            usage_reason="Database storage for medical device data",
            safety_justification="Well-established database with extensive testing and validation",
            supplier="SQLite Development Team",
            license="Public Domain",
            criticality_level="High"
        ),
        SOUPComponent(
            id=str(uuid.uuid4()),
            name="OpenSSL",
            version="3.1.0",
            usage_reason="Cryptographic operations for secure communication",
            safety_justification="Industry standard cryptographic library with security audits",
            supplier="OpenSSL Software Foundation",
            license="Apache License 2.0",
            criticality_level="High"
        ),
        SOUPComponent(
            id=str(uuid.uuid4()),
            name="jQuery",
            version="3.7.0",
            usage_reason="User interface enhancements",
            safety_justification="Non-critical UI library with no safety impact",
            supplier="jQuery Foundation",
            license="MIT License",
            criticality_level="Low"
        )
    ]
    
    # Add test components
    for component in test_components:
        try:
            soup_service.add_component(component)
        except Exception as e:
            print(f"Failed to add component {component.name}: {e}")
    
    # Refresh the widget
    soup_widget.refresh_table()
    
    # Show the window
    main_window.show()
    
    print("Enhanced SOUP Widget Test")
    print("=" * 50)
    print("Features to test:")
    print("1. Auto-detect components (click 'Auto-Detect Components' and select a project folder)")
    print("2. Bulk import detected components")
    print("3. Classify components (click 'Classify' button in Actions column)")
    print("4. View component details (click 'Details' button in Actions column)")
    print("5. Export inventory (JSON, CSV formats)")
    print("6. Import inventory from file")
    print("7. Validate compliance for all components")
    print("8. Filter components by various criteria")
    print("9. Compliance status indicators (color-coded)")
    print("10. Safety class display with color coding")
    print()
    print("Test project created at:", create_test_project())
    print("Use this path for auto-detection testing.")
    
    # Test completed successfully


if __name__ == "__main__":
    # For standalone execution, use pytest
    sys.exit(pytest.main([__file__, "-v"]))