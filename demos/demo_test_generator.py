#!/usr/bin/env python3
"""
Demo script for the test generator service.

This script demonstrates how to use the TestGenerator to create unit test
skeletons and integration test stubs for C and JavaScript functions.
"""

import os
import tempfile
from datetime import datetime

from medical_analyzer.tests.test_generator import TestGenerator
from medical_analyzer.models.core import ProjectStructure, FileMetadata
from medical_analyzer.parsers.c_parser import FunctionSignature as CFunctionSignature, CCodeStructure
from medical_analyzer.parsers.js_parser import FunctionSignature as JSFunctionSignature, JSCodeStructure


def create_sample_c_parsed_file():
    """Create a sample parsed C file for demonstration."""
    # Create sample C functions
    functions = [
        CFunctionSignature(
            name="calculate_insulin_dose",
            return_type="float",
            parameters=[
                {"type": "float", "name": "blood_glucose"},
                {"type": "float", "name": "patient_weight"},
                {"type": "int", "name": "carb_ratio"}
            ],
            start_line=15,
            end_line=35,
            is_static=False,
            is_inline=False
        ),
        CFunctionSignature(
            name="gpio_read_sensor",
            return_type="int",
            parameters=[
                {"type": "int", "name": "pin_number"}
            ],
            start_line=40,
            end_line=50,
            is_static=True,
            is_inline=False
        ),
        CFunctionSignature(
            name="validate_range",
            return_type="bool",
            parameters=[
                {"type": "float", "name": "value"},
                {"type": "float", "name": "min_val"},
                {"type": "float", "name": "max_val"}
            ],
            start_line=55,
            end_line=65,
            is_static=False,
            is_inline=True
        )
    ]
    
    # Create mock parsed file
    class MockParsedFile:
        def __init__(self):
            self.file_path = "src/insulin_calculator.c"
            self.file_metadata = FileMetadata(
                file_path="src/insulin_calculator.c",
                file_size=2048,
                last_modified=datetime.now(),
                file_type="c",
                line_count=100,
                function_count=3
            )
            self.code_structure = CCodeStructure(
                file_path="src/insulin_calculator.c",
                functions=functions,
                includes=["#include <stdio.h>", "#include <stdbool.h>"],
                defines=[{"name": "MAX_DOSE", "value": "50.0"}],
                global_variables=[{"type": "float", "name": "safety_factor"}],
                structs=[],
                enums=[]
            )
    
    return MockParsedFile()


def create_sample_js_parsed_file():
    """Create a sample parsed JavaScript file for demonstration."""
    # Create sample JavaScript functions
    functions = [
        JSFunctionSignature(
            name="validatePatientData",
            parameters=["patientData", "schema"],
            start_line=10,
            end_line=25,
            is_async=True,
            is_arrow=False,
            is_method=False
        ),
        JSFunctionSignature(
            name="sendToDevice",
            parameters=["deviceId", "command", "...args"],
            start_line=30,
            end_line=45,
            is_async=True,
            is_arrow=False,
            is_method=False
        ),
        JSFunctionSignature(
            name="formatDisplayValue",
            parameters=["value", "unit"],
            start_line=50,
            end_line=60,
            is_async=False,
            is_arrow=True,
            is_method=False
        )
    ]
    
    # Create mock parsed file
    class MockParsedFile:
        def __init__(self):
            self.file_path = "src/device_interface.js"
            self.file_metadata = FileMetadata(
                file_path="src/device_interface.js",
                file_size=3072,
                last_modified=datetime.now(),
                file_type="javascript",
                line_count=120,
                function_count=3
            )
            self.code_structure = JSCodeStructure(
                file_path="src/device_interface.js",
                functions=functions,
                classes=[],
                imports=[{"type": "import", "statement": "import { ipcRenderer } from 'electron';"}],
                exports=[{"type": "export", "statement": "export { validatePatientData };"}],
                variables=[{"type": "const", "name": "API_ENDPOINT"}],
                requires=["serialport"]
            )
    
    return MockParsedFile()


def demo_test_generation():
    """Demonstrate test generation functionality."""
    print("=== Medical Software Test Generator Demo ===\n")
    
    # Initialize test generator
    generator = TestGenerator()
    
    # Create sample project structure
    project_structure = ProjectStructure(
        root_path="/medical_device_project",
        selected_files=["src/insulin_calculator.c", "src/device_interface.js"],
        description="Medical device software for insulin dose calculation and device communication"
    )
    
    # Create sample parsed files
    c_parsed_file = create_sample_c_parsed_file()
    js_parsed_file = create_sample_js_parsed_file()
    parsed_files = [c_parsed_file, js_parsed_file]
    
    print("1. Generating comprehensive test suite...")
    test_suite = generator.generate_test_suite(
        project_structure,
        parsed_files,
        c_framework='unity',
        js_framework='jest'
    )
    
    print(f"   ✓ Generated {len(test_suite.test_skeletons)} unit test skeletons")
    print(f"   ✓ Generated {len(test_suite.integration_tests)} integration test stubs")
    print(f"   ✓ Created framework configurations for {len(test_suite.framework_configs)} languages")
    
    print("\n2. Unit Test Examples:")
    print("   " + "="*50)
    
    # Show C unit test example
    c_tests = [t for t in test_suite.test_skeletons if t.language == 'c']
    if c_tests:
        print(f"\n   C Unit Test (Unity Framework) - {c_tests[0].target_function}:")
        print("   " + "-"*50)
        print("   " + c_tests[0].test_content[:300].replace('\n', '\n   ') + "...")
    
    # Show JavaScript unit test example
    js_tests = [t for t in test_suite.test_skeletons if t.language == 'javascript']
    if js_tests:
        print(f"\n   JavaScript Unit Test (Jest Framework) - {js_tests[0].target_function}:")
        print("   " + "-"*50)
        print("   " + js_tests[0].test_content[:300].replace('\n', '\n   ') + "...")
    
    print("\n3. Integration Test Examples:")
    print("   " + "="*50)
    
    # Show integration test examples
    c_integration = [t for t in test_suite.integration_tests if t.language == 'c']
    if c_integration:
        print(f"\n   C Integration Test - {c_integration[0].target_function}:")
        print("   " + "-"*50)
        print("   " + c_integration[0].test_content[:300].replace('\n', '\n   ') + "...")
    
    js_integration = [t for t in test_suite.integration_tests if t.language == 'javascript']
    if js_integration:
        print(f"\n   JavaScript Integration Test - {js_integration[0].target_function}:")
        print("   " + "-"*50)
        print("   " + js_integration[0].test_content[:300].replace('\n', '\n   ') + "...")
    
    print("\n4. Framework Configurations:")
    print("   " + "="*50)
    
    for language, config in test_suite.framework_configs.items():
        print(f"\n   {language.upper()} Framework: {config['framework']}")
        print(f"   Config file: {config['config_file']}")
        if 'dependencies' in config:
            print(f"   Dependencies: {', '.join(config['dependencies'])}")
        if 'package_dependencies' in config:
            print(f"   Package dependencies: {', '.join(config['package_dependencies'])}")
    
    print("\n5. Exporting test suite to files...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        exported_files = generator.export_test_suite(test_suite, temp_dir)
        
        print(f"   ✓ Exported {len(exported_files)} files to {temp_dir}")
        
        # List exported files
        for file_path in sorted(exported_files.keys()):
            rel_path = os.path.relpath(file_path, temp_dir)
            print(f"     - {rel_path}")
        
        # Show directory structure
        print(f"\n   Directory structure:")
        for root, dirs, files in os.walk(temp_dir):
            level = root.replace(temp_dir, '').count(os.sep)
            indent = ' ' * 4 * (level + 1)
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 4 * (level + 2)
            for file in files:
                print(f"{subindent}{file}")
    
    print("\n6. Test Validation:")
    print("   " + "="*50)
    
    # Validate some test skeletons
    validation_results = []
    for test in test_suite.test_skeletons[:3]:  # Validate first 3 tests
        errors = generator.validate_test_skeleton(test)
        validation_results.append((test.test_name, len(errors), errors))
    
    for test_name, error_count, errors in validation_results:
        if error_count == 0:
            print(f"   ✓ {test_name}: Valid")
        else:
            print(f"   ✗ {test_name}: {error_count} errors")
            for error in errors:
                print(f"     - {error}")
    
    print("\n7. Test Statistics:")
    print("   " + "="*50)
    
    # Calculate statistics
    total_tests = len(test_suite.test_skeletons) + len(test_suite.integration_tests)
    c_tests_count = len([t for t in test_suite.test_skeletons if t.language == 'c'])
    js_tests_count = len([t for t in test_suite.test_skeletons if t.language == 'javascript'])
    unity_tests = len([t for t in test_suite.test_skeletons if t.framework == 'unity'])
    jest_tests = len([t for t in test_suite.test_skeletons if t.framework == 'jest'])
    
    print(f"   Total tests generated: {total_tests}")
    print(f"   Unit tests: {len(test_suite.test_skeletons)}")
    print(f"   Integration tests: {len(test_suite.integration_tests)}")
    print(f"   C tests: {c_tests_count} (Unity framework)")
    print(f"   JavaScript tests: {js_tests_count} (Jest framework)")
    
    print("\n=== Demo Complete ===")
    print("\nThe test generator successfully created:")
    print("• Unit test skeletons for all functions")
    print("• Integration test stubs for hardware/system interactions")
    print("• Framework configuration files")
    print("• Proper test file organization")
    print("• Medical device specific test patterns")
    
    return test_suite


if __name__ == "__main__":
    try:
        demo_test_generation()
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()