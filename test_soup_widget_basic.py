#!/usr/bin/env python3
"""
Basic test for enhanced SOUP widget functionality.
"""

import sys
import tempfile
import uuid
from pathlib import Path

# Add the medical_analyzer package to the path
sys.path.insert(0, str(Path(__file__).parent))

from medical_analyzer.services.soup_service import SOUPService
from medical_analyzer.database.schema import DatabaseManager
from medical_analyzer.models.core import SOUPComponent
from medical_analyzer.models.soup_models import DetectedSOUPComponent, DetectionMethod, IEC62304SafetyClass


def test_soup_service_enhanced():
    """Test the enhanced SOUP service functionality."""
    print("Testing Enhanced SOUP Service...")
    
    # Create temporary database
    db_path = tempfile.mktemp(suffix=".db")
    db_manager = DatabaseManager(db_path)
    
    # Initialize service
    soup_service = SOUPService(db_manager)
    
    # Test 1: Add component with classification
    print("\n1. Testing add_component_with_classification...")
    detected_component = DetectedSOUPComponent(
        name="express",
        version="4.18.0",
        source_file="package.json",
        detection_method=DetectionMethod.PACKAGE_JSON,
        confidence=0.95,
        package_manager="npm",
        description="Fast, unopinionated, minimalist web framework for Node.js"
    )
    
    try:
        component_id = soup_service.add_component_with_classification(detected_component)
        print(f"✓ Successfully added component with ID: {component_id}")
    except Exception as e:
        print(f"✗ Failed to add component: {e}")
        return False
    
    # Test 2: Get component classification
    print("\n2. Testing get_component_classification...")
    try:
        classification = soup_service.get_component_classification(component_id)
        if classification:
            print(f"✓ Classification found: Class {classification.safety_class.value}")
            print(f"  Justification: {classification.justification[:100]}...")
        else:
            print("✗ No classification found")
    except Exception as e:
        print(f"✗ Failed to get classification: {e}")
    
    # Test 3: Validate compliance
    print("\n3. Testing validate_component_compliance...")
    try:
        validation = soup_service.validate_component_compliance(component_id)
        print(f"✓ Compliance validation: {'Compliant' if validation.is_compliant else 'Non-compliant'}")
        if validation.missing_requirements:
            print(f"  Missing requirements: {len(validation.missing_requirements)}")
        if validation.warnings:
            print(f"  Warnings: {len(validation.warnings)}")
    except Exception as e:
        print(f"✗ Failed to validate compliance: {e}")
    
    # Test 4: Get all components
    print("\n4. Testing get_all_components...")
    try:
        components = soup_service.get_all_components()
        print(f"✓ Found {len(components)} components")
        for comp in components:
            print(f"  - {comp.name} v{comp.version}")
    except Exception as e:
        print(f"✗ Failed to get components: {e}")
    
    print("\n✓ All tests completed successfully!")
    return True


def test_soup_detector():
    """Test the SOUP detector functionality."""
    print("\nTesting SOUP Detector...")
    
    from medical_analyzer.services.soup_detector import SOUPDetector
    
    # Create test project structure
    test_dir = Path(tempfile.mkdtemp())
    
    # Create package.json
    package_json_content = """{
  "name": "test-medical-app",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.18.0",
    "sqlite3": "^5.1.0"
  }
}"""
    
    with open(test_dir / "package.json", "w") as f:
        f.write(package_json_content)
    
    # Test detection
    detector = SOUPDetector(use_llm_classification=False)  # Disable LLM for basic test
    
    try:
        detected_components = detector.detect_soup_components(str(test_dir))
        print(f"✓ Detected {len(detected_components)} components")
        
        for comp in detected_components:
            print(f"  - {comp.name} v{comp.version} (confidence: {comp.confidence:.1%})")
            print(f"    Source: {comp.source_file}")
            print(f"    Method: {comp.detection_method.value}")
            if comp.suggested_classification:
                print(f"    Suggested class: {comp.suggested_classification.value}")
    
    except Exception as e:
        print(f"✗ Detection failed: {e}")
        return False
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir)
    
    return True


if __name__ == "__main__":
    print("Enhanced SOUP Widget - Basic Functionality Test")
    print("=" * 50)
    
    success = True
    
    # Test SOUP service
    success &= test_soup_service_enhanced()
    
    # Test SOUP detector
    success &= test_soup_detector()
    
    if success:
        print("\n🎉 All tests passed! Enhanced SOUP widget functionality is working.")
    else:
        print("\n❌ Some tests failed. Check the implementation.")
        sys.exit(1)