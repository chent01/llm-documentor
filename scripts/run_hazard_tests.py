#!/usr/bin/env python3
"""
Test runner for hazard identification tests.
"""

import sys
import traceback
from unittest.mock import Mock

# Import the test class directly
sys.path.append('.')
from tests.test_hazard_identification import TestHazardIdentification
from medical_analyzer.models.core import Requirement, CodeReference
from medical_analyzer.models.enums import RequirementType, Severity, Probability, RiskLevel
from medical_analyzer.llm.backend import LLMError

def run_test_method(test_instance, method_name, *args, **kwargs):
    """Run a single test method and report results."""
    try:
        method = getattr(test_instance, method_name)
        if args or kwargs:
            method(*args, **kwargs)
        else:
            method()
        print(f"✓ {method_name} passed")
        return True
    except Exception as e:
        print(f"✗ {method_name} failed: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """Run all hazard identification tests."""
    print("Running Hazard Identification Tests...")
    print("=" * 50)
    
    # Create test instance
    test_instance = TestHazardIdentification()
    
    # Create fixtures
    mock_llm_backend = Mock()
    mock_llm_backend.__class__.__name__ = "MockLLMBackend"
    
    orchestrator = test_instance.orchestrator(mock_llm_backend)
    hazard_identifier = test_instance.hazard_identifier(mock_llm_backend)
    sample_requirements = test_instance.sample_software_requirements()
    
    # List of tests to run
    tests = [
        ("test_identify_hazards_success", orchestrator, mock_llm_backend, sample_requirements),
        ("test_identify_hazards_empty_requirements", orchestrator),
        ("test_parse_severity_levels", hazard_identifier),
        ("test_parse_probability_levels", hazard_identifier),
        ("test_calculate_risk_level_matrix", hazard_identifier),
        ("test_calculate_risk_score", hazard_identifier),
        ("test_fallback_hazard_identification", hazard_identifier, sample_requirements),
        ("test_get_risk_statistics_empty", hazard_identifier),
        ("test_get_risk_statistics_with_risks", hazard_identifier),
        ("test_filter_risks_by_level", hazard_identifier),
        ("test_group_risks_by_severity", hazard_identifier),
    ]
    
    passed = 0
    failed = 0
    
    for test_info in tests:
        method_name = test_info[0]
        args = test_info[1:]
        
        if run_test_method(test_instance, method_name, *args):
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All hazard identification tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())