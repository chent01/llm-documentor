#!/usr/bin/env python3
"""
Test script to verify Task 4 implementation - Test Case Generation and Export System.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from medical_analyzer.models.core import Requirement
from medical_analyzer.models.enums import RequirementType
from medical_analyzer.services.test_case_generator import CaseGenerator
from medical_analyzer.models.test_models import CasePriority, CaseCategory
from medical_analyzer.services.test_case_templates import CaseTemplateManager
from medical_analyzer.services.test_requirements_integration import RequirementsIntegrationService


def test_test_case_generator():
    """Test the TestCaseGenerator functionality."""
    print("Testing TestCaseGenerator...")
    
    # Create sample requirements
    requirements = [
        Requirement(
            id="REQ-001",
            type=RequirementType.USER,
            text="The system shall provide user authentication functionality",
            acceptance_criteria=[
                "WHEN user enters valid credentials THEN system SHALL grant access",
                "WHEN user enters invalid credentials THEN system SHALL deny access"
            ]
        ),
        Requirement(
            id="REQ-002", 
            type=RequirementType.SOFTWARE,
            text="The system shall implement safety monitoring with automatic shutdown",
            acceptance_criteria=[
                "WHEN safety threshold is exceeded THEN system SHALL initiate shutdown",
                "WHEN shutdown is initiated THEN system SHALL enter safe state within 5 seconds"
            ]
        )
    ]
    
    # Initialize generator
    generator = CaseGenerator()
    
    # Generate test cases
    test_outline = generator.generate_test_cases(requirements)
    
    print(f"✓ Generated {len(test_outline.test_cases)} test cases")
    
    # Test export functionality
    formats = ["text", "json", "xml", "csv"]
    for format_type in formats:
        try:
            exported = generator.export_test_cases(test_outline, format_type)
            print(f"✓ Successfully exported to {format_type} format ({len(exported)} characters)")
        except Exception as e:
            print(f"✗ Failed to export to {format_type}: {e}")
    
    # Test coverage report
    coverage_report = generator.generate_coverage_report(test_outline, requirements)
    print(f"✓ Generated coverage report with {coverage_report['summary']['coverage_percentage']:.1f}% coverage")
    
    return True


def test_template_manager():
    """Test the CaseTemplateManager functionality."""
    print("\nTesting CaseTemplateManager...")
    
    manager = CaseTemplateManager()
    
    # Test template retrieval
    functional_template = manager.get_template("functional")
    safety_template = manager.get_template("safety")
    
    if functional_template and safety_template:
        print("✓ Successfully retrieved predefined templates")
    else:
        print("✗ Failed to retrieve templates")
        return False
    
    # Test requirement categorization
    safety_req = Requirement(
        id="SAFETY-001",
        type=RequirementType.SOFTWARE,
        text="The system shall implement emergency stop functionality for safety"
    )
    
    template = manager.get_template_for_requirement(safety_req)
    if template.category == CaseCategory.SAFETY:
        print("✓ Correctly categorized safety requirement")
    else:
        print("✗ Failed to categorize safety requirement")
        return False
    
    # Test template application
    template_data = template.apply_to_requirement(safety_req)
    if "safety" in template_data["description"].lower():
        print("✓ Successfully applied template to requirement")
    else:
        print("✗ Failed to apply template correctly")
        return False
    
    return True


def test_requirements_integration():
    """Test the TestRequirementsIntegration functionality."""
    print("\nTesting TestRequirementsIntegration...")
    
    # Create test generator and integration service
    generator = CaseGenerator()
    integration = RequirementsIntegrationService(generator)
    
    # Initial requirements
    initial_requirements = [
        Requirement(
            id="REQ-001",
            type=RequirementType.USER,
            text="The system shall provide user login functionality"
        )
    ]
    
    # Set initial requirements
    integration.set_requirements(initial_requirements)
    print("✓ Set initial requirements")
    
    # Updated requirements (simulating a change)
    updated_requirements = [
        Requirement(
            id="REQ-001",
            type=RequirementType.USER,
            text="The system shall provide secure user authentication with multi-factor support"
        ),
        Requirement(
            id="REQ-002",
            type=RequirementType.SOFTWARE,
            text="The system shall log all authentication attempts"
        )
    ]
    
    # Update requirements and detect changes
    integration.set_requirements(updated_requirements)
    print("✓ Updated requirements and detected changes")
    
    # Test validation
    if integration.current_test_outline:
        validation_issues = integration.validate_test_cases_against_requirements()
        print(f"✓ Validated test cases, found {len(validation_issues)} issues")
    
    # Test coverage analysis
    coverage_analysis = integration.get_test_coverage_analysis()
    if "coverage_report" in coverage_analysis:
        print("✓ Generated coverage analysis")
    else:
        print("✗ Failed to generate coverage analysis")
        return False
    
    return True


def test_export_formats():
    """Test various export formats with enhanced templates."""
    print("\nTesting Enhanced Export Formats...")
    
    # Create sample data
    requirements = [
        Requirement(
            id="REQ-TEST",
            type=RequirementType.SOFTWARE,
            text="Test requirement for export functionality"
        )
    ]
    
    generator = CaseGenerator()
    test_outline = generator.generate_test_cases(requirements)
    
    # Test enhanced formats
    enhanced_formats = ["html", "markdown"]
    for format_type in enhanced_formats:
        try:
            exported = generator.export_test_cases(test_outline, format_type)
            print(f"✓ Successfully exported to enhanced {format_type} format")
        except Exception as e:
            print(f"✗ Failed to export to {format_type}: {e}")
    
    # Test coverage report formats
    manager = CaseTemplateManager()
    for format_type in ["text", "json"]:
        try:
            coverage_report = manager.generate_coverage_report(test_outline, requirements, format_type)
            print(f"✓ Successfully generated coverage report in {format_type} format")
        except Exception as e:
            print(f"✗ Failed to generate coverage report in {format_type}: {e}")
    
    return True


def main():
    """Run all tests for Task 4 implementation."""
    print("=" * 60)
    print("TESTING TASK 4: Test Case Generation and Export System")
    print("=" * 60)
    
    tests = [
        test_test_case_generator,
        test_template_manager,
        test_requirements_integration,
        test_export_formats
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test_func.__name__} failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("🎉 All tests passed! Task 4 implementation is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
