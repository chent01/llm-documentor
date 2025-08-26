"""
Test skeleton generation service for C and JavaScript functions.
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from ..models.core import CodeChunk, ProjectStructure
from ..models.enums import ChunkType
from ..parsers.c_parser import FunctionSignature as CFunctionSignature
from ..parsers.js_parser import FunctionSignature as JSFunctionSignature


@dataclass
class TestSkeleton:
    """Represents a generated test skeleton."""
    test_name: str
    test_content: str
    framework: str  # 'unity', 'minunit', 'jest', 'mocha'
    language: str   # 'c', 'javascript'
    target_function: str
    file_path: str
    metadata: Dict[str, Any]


@dataclass
class TestSuite:
    """Collection of test skeletons for a project."""
    project_name: str
    test_skeletons: List[TestSkeleton]
    framework_configs: Dict[str, Dict[str, Any]]
    integration_tests: List[TestSkeleton]
    created_at: datetime


class TestGenerator:
    """Service for generating unit test skeletons and integration test stubs."""
    
    def __init__(self):
        """Initialize the test generator."""
        self.c_frameworks = ['unity', 'minunit']
        self.js_frameworks = ['jest', 'mocha']
        
    def generate_test_suite(self, project_structure: ProjectStructure, 
                          parsed_files: List[Any],
                          c_framework: str = 'unity',
                          js_framework: str = 'jest') -> TestSuite:
        """Generate complete test suite for a project.
        
        Args:
            project_structure: Project structure with selected files
            parsed_files: List of ParsedFile objects from ParserService
            c_framework: Framework to use for C tests ('unity' or 'minunit')
            js_framework: Framework to use for JS tests ('jest' or 'mocha')
            
        Returns:
            TestSuite containing all generated test skeletons
        """
        if c_framework not in self.c_frameworks:
            raise ValueError(f"Unsupported C framework: {c_framework}")
        if js_framework not in self.js_frameworks:
            raise ValueError(f"Unsupported JS framework: {js_framework}")
        
        test_skeletons = []
        integration_tests = []
        
        # Generate unit tests for each parsed file
        for parsed_file in parsed_files:
            file_metadata = parsed_file.file_metadata
            
            if file_metadata.file_type == 'c':
                # Generate C unit tests
                c_tests = self._generate_c_unit_tests(
                    parsed_file, c_framework
                )
                test_skeletons.extend(c_tests)
                
                # Generate C integration tests
                c_integration = self._generate_c_integration_tests(
                    parsed_file, c_framework
                )
                integration_tests.extend(c_integration)
                
            elif file_metadata.file_type == 'javascript':
                # Generate JavaScript unit tests
                js_tests = self._generate_js_unit_tests(
                    parsed_file, js_framework
                )
                test_skeletons.extend(js_tests)
                
                # Generate JavaScript integration tests
                js_integration = self._generate_js_integration_tests(
                    parsed_file, js_framework
                )
                integration_tests.extend(js_integration)
        
        # Generate framework configurations
        framework_configs = {
            'c': self._generate_c_framework_config(c_framework),
            'javascript': self._generate_js_framework_config(js_framework)
        }
        
        return TestSuite(
            project_name=os.path.basename(project_structure.root_path),
            test_skeletons=test_skeletons,
            framework_configs=framework_configs,
            integration_tests=integration_tests,
            created_at=datetime.now()
        )
    
    def _generate_c_unit_tests(self, parsed_file: Any, framework: str) -> List[TestSkeleton]:
        """Generate unit tests for C functions."""
        test_skeletons = []
        
        if not hasattr(parsed_file, 'code_structure'):
            return test_skeletons
        
        code_structure = parsed_file.code_structure
        
        for function in code_structure.functions:
            if framework == 'unity':
                test_content = self._generate_unity_test(function, parsed_file.file_path)
            else:  # minunit
                test_content = self._generate_minunit_test(function, parsed_file.file_path)
            
            test_skeleton = TestSkeleton(
                test_name=f"test_{function.name}",
                test_content=test_content,
                framework=framework,
                language='c',
                target_function=function.name,
                file_path=self._get_test_file_path(parsed_file.file_path, 'c', framework),
                metadata={
                    'return_type': function.return_type,
                    'parameters': function.parameters,
                    'is_static': function.is_static,
                    'source_file': parsed_file.file_path,
                    'start_line': function.start_line,
                    'end_line': function.end_line
                }
            )
            test_skeletons.append(test_skeleton)
        
        return test_skeletons
    
    def _generate_js_unit_tests(self, parsed_file: Any, framework: str) -> List[TestSkeleton]:
        """Generate unit tests for JavaScript functions."""
        test_skeletons = []
        
        if not hasattr(parsed_file, 'code_structure'):
            return test_skeletons
        
        code_structure = parsed_file.code_structure
        
        for function in code_structure.functions:
            if framework == 'jest':
                test_content = self._generate_jest_test(function, parsed_file.file_path)
            else:  # mocha
                test_content = self._generate_mocha_test(function, parsed_file.file_path)
            
            test_skeleton = TestSkeleton(
                test_name=f"test_{function.name}",
                test_content=test_content,
                framework=framework,
                language='javascript',
                target_function=function.name,
                file_path=self._get_test_file_path(parsed_file.file_path, 'javascript', framework),
                metadata={
                    'parameters': function.parameters,
                    'is_async': function.is_async,
                    'is_arrow': function.is_arrow,
                    'is_method': function.is_method,
                    'class_name': function.class_name,
                    'source_file': parsed_file.file_path,
                    'start_line': function.start_line,
                    'end_line': function.end_line
                }
            )
            test_skeletons.append(test_skeleton)
        
        return test_skeletons
    
    def _generate_unity_test(self, function: CFunctionSignature, source_file: str) -> str:
        """Generate Unity framework test for a C function."""
        test_name = f"test_{function.name}"
        
        # Generate parameter setup based on function signature
        param_setup = self._generate_c_parameter_setup(function.parameters)
        
        # Generate basic assertions based on return type
        assertions = self._generate_c_assertions(function.return_type, function.name)
        
        test_content = f'''#include "unity.h"
#include "{os.path.basename(source_file)}"

void setUp(void) {{
    // Set up test fixtures, if any
}}

void tearDown(void) {{
    // Clean up after test, if any
}}

void {test_name}(void) {{
    // Test for function: {function.name}
    // Return type: {function.return_type}
    // Parameters: {len(function.parameters)}
    
{param_setup}
    
    // Call the function under test
{assertions}
    
    // TODO: Add specific test assertions based on expected behavior
    // Example assertions:
    // TEST_ASSERT_EQUAL(expected_value, actual_value);
    // TEST_ASSERT_NOT_NULL(pointer_value);
    // TEST_ASSERT_TRUE(boolean_condition);
}}
'''
        return test_content
    
    def _generate_minunit_test(self, function: CFunctionSignature, source_file: str) -> str:
        """Generate MinUnit framework test for a C function."""
        test_name = f"test_{function.name}"
        
        param_setup = self._generate_c_parameter_setup(function.parameters)
        assertions = self._generate_c_assertions(function.return_type, function.name, framework='minunit')
        
        test_content = f'''#include "minunit.h"
#include "{os.path.basename(source_file)}"

static char* {test_name}() {{
    // Test for function: {function.name}
    // Return type: {function.return_type}
    // Parameters: {len(function.parameters)}
    
{param_setup}
    
    // Call the function under test
{assertions}
    
    // TODO: Add specific test assertions based on expected behavior
    // Example assertions:
    // mu_assert("error message", condition);
    
    return 0;
}}
'''
        return test_content
    
    def _generate_jest_test(self, function: JSFunctionSignature, source_file: str) -> str:
        """Generate Jest framework test for a JavaScript function."""
        test_name = f"test {function.name}"
        
        # Determine import statement based on file type
        import_statement = self._generate_js_import_statement(source_file, function)
        
        param_setup = self._generate_js_parameter_setup(function.parameters)
        
        test_content = f'''{import_statement}

describe('{function.name}', () => {{
    test('{test_name}', () => {{
        // Test for function: {function.name}
        // Parameters: {function.parameters}
        // Async: {function.is_async}
        // Method: {function.is_method}
        
{param_setup}
        
        // Call the function under test
        {'const result = await ' if function.is_async else 'const result = '}{function.name}({', '.join(function.parameters)});
        
        // TODO: Add specific test assertions based on expected behavior
        // Example assertions:
        // expect(result).toBe(expectedValue);
        // expect(result).toEqual(expectedObject);
        // expect(result).toBeTruthy();
        // expect(result).toBeNull();
        
        // Placeholder assertion
        expect(result).toBeDefined();
    }});
    
    test('{function.name} handles edge cases', () => {{
        // TODO: Add edge case tests
        // Test with null/undefined inputs
        // Test with boundary values
        // Test error conditions
    }});
}});
'''
        return test_content
    
    def _generate_mocha_test(self, function: JSFunctionSignature, source_file: str) -> str:
        """Generate Mocha framework test for a JavaScript function."""
        test_name = f"test {function.name}"
        
        import_statement = self._generate_js_import_statement(source_file, function)
        param_setup = self._generate_js_parameter_setup(function.parameters)
        
        test_content = f'''const {{ expect }} = require('chai');
{import_statement}

describe('{function.name}', function() {{
    it('should work correctly', {'async ' if function.is_async else ''}function() {{
        // Test for function: {function.name}
        // Parameters: {function.parameters}
        // Async: {function.is_async}
        // Method: {function.is_method}
        
{param_setup}
        
        // Call the function under test
        {'const result = await ' if function.is_async else 'const result = '}{function.name}({', '.join(function.parameters)});
        
        // TODO: Add specific test assertions based on expected behavior
        // Example assertions:
        // expect(result).to.equal(expectedValue);
        // expect(result).to.be.an('object');
        // expect(result).to.be.true;
        // expect(result).to.be.null;
        
        // Placeholder assertion
        expect(result).to.exist;
    }});
    
    it('should handle edge cases', function() {{
        // TODO: Add edge case tests
        // Test with null/undefined inputs
        // Test with boundary values
        // Test error conditions
    }});
}});
'''
        return test_content   
 
    def _generate_c_integration_tests(self, parsed_file: Any, framework: str) -> List[TestSkeleton]:
        """Generate integration test stubs for C functions with hardware mocks."""
        integration_tests = []
        
        if not hasattr(parsed_file, 'code_structure'):
            return integration_tests
        
        code_structure = parsed_file.code_structure
        
        # Look for functions that might interact with hardware
        hardware_functions = self._identify_hardware_functions(code_structure.functions)
        
        for function in hardware_functions:
            if framework == 'unity':
                test_content = self._generate_unity_integration_test(function, parsed_file.file_path)
            else:  # minunit
                test_content = self._generate_minunit_integration_test(function, parsed_file.file_path)
            
            test_skeleton = TestSkeleton(
                test_name=f"integration_test_{function.name}",
                test_content=test_content,
                framework=framework,
                language='c',
                target_function=function.name,
                file_path=self._get_integration_test_file_path(parsed_file.file_path, 'c', framework),
                metadata={
                    'test_type': 'integration',
                    'hardware_mock': True,
                    'return_type': function.return_type,
                    'parameters': function.parameters,
                    'source_file': parsed_file.file_path
                }
            )
            integration_tests.append(test_skeleton)
        
        return integration_tests
    
    def _generate_js_integration_tests(self, parsed_file: Any, framework: str) -> List[TestSkeleton]:
        """Generate integration test stubs for JavaScript functions with hardware mocks."""
        integration_tests = []
        
        if not hasattr(parsed_file, 'code_structure'):
            return integration_tests
        
        code_structure = parsed_file.code_structure
        
        # Look for functions that might interact with hardware or external systems
        integration_functions = self._identify_integration_functions(code_structure.functions)
        
        for function in integration_functions:
            if framework == 'jest':
                test_content = self._generate_jest_integration_test(function, parsed_file.file_path)
            else:  # mocha
                test_content = self._generate_mocha_integration_test(function, parsed_file.file_path)
            
            test_skeleton = TestSkeleton(
                test_name=f"integration_test_{function.name}",
                test_content=test_content,
                framework=framework,
                language='javascript',
                target_function=function.name,
                file_path=self._get_integration_test_file_path(parsed_file.file_path, 'javascript', framework),
                metadata={
                    'test_type': 'integration',
                    'hardware_mock': True,
                    'parameters': function.parameters,
                    'is_async': function.is_async,
                    'source_file': parsed_file.file_path
                }
            )
            integration_tests.append(test_skeleton)
        
        return integration_tests
    
    def _identify_hardware_functions(self, functions: List[CFunctionSignature]) -> List[CFunctionSignature]:
        """Identify C functions that likely interact with hardware."""
        hardware_keywords = [
            'gpio', 'pin', 'port', 'register', 'interrupt', 'timer', 'adc', 'dac',
            'spi', 'i2c', 'uart', 'usart', 'can', 'pwm', 'dma', 'clock',
            'sensor', 'actuator', 'device', 'peripheral', 'hardware', 'hal'
        ]
        
        hardware_functions = []
        
        for function in functions:
            func_name_lower = function.name.lower()
            
            # Check if function name contains hardware-related keywords
            if any(keyword in func_name_lower for keyword in hardware_keywords):
                hardware_functions.append(function)
                continue
            
            # Check parameters for hardware-related types
            for param in function.parameters:
                param_type_lower = param.get('type', '').lower()
                if any(keyword in param_type_lower for keyword in hardware_keywords):
                    hardware_functions.append(function)
                    break
        
        return hardware_functions
    
    def _identify_integration_functions(self, functions: List[JSFunctionSignature]) -> List[JSFunctionSignature]:
        """Identify JavaScript functions that likely need integration testing."""
        integration_keywords = [
            'api', 'request', 'response', 'fetch', 'axios', 'http', 'websocket',
            'database', 'db', 'query', 'connection', 'serial', 'device',
            'hardware', 'sensor', 'actuator', 'electron', 'ipc', 'main', 'renderer'
        ]
        
        integration_functions = []
        
        for function in functions:
            func_name_lower = function.name.lower()
            
            # Check if function name contains integration-related keywords
            if any(keyword in func_name_lower for keyword in integration_keywords):
                integration_functions.append(function)
                continue
            
            # Async functions are often good candidates for integration testing
            if function.is_async:
                integration_functions.append(function)
        
        return integration_functions
    
    def _generate_c_parameter_setup(self, parameters: List[Dict[str, str]]) -> str:
        """Generate parameter setup code for C tests."""
        if not parameters:
            return "    // No parameters"
        
        setup_lines = []
        setup_lines.append("    // Set up test parameters")
        
        for i, param in enumerate(parameters):
            param_type = param.get('type', 'int')
            param_name = param.get('name', f'param{i}')
            
            if 'int' in param_type.lower():
                setup_lines.append(f"    {param_type} {param_name} = 42; // TODO: Set appropriate test value")
            elif 'float' in param_type.lower() or 'double' in param_type.lower():
                setup_lines.append(f"    {param_type} {param_name} = 3.14; // TODO: Set appropriate test value")
            elif 'char' in param_type.lower() and '*' in param_type:
                setup_lines.append(f"    {param_type} {param_name} = \"test_string\"; // TODO: Set appropriate test value")
            elif '*' in param_type:
                setup_lines.append(f"    {param_type} {param_name} = NULL; // TODO: Set appropriate test value")
            else:
                setup_lines.append(f"    {param_type} {param_name}; // TODO: Initialize test value")
        
        return '\n'.join(setup_lines)
    
    def _generate_c_assertions(self, return_type: str, function_name: str, framework: str = 'unity') -> str:
        """Generate assertion code for C tests based on return type."""
        param_call = "/* parameters */"  # Simplified for skeleton
        
        if return_type.lower() == 'void':
            assertion = f"    {function_name}({param_call});\n    // TODO: Add assertions for side effects"
        elif 'int' in return_type.lower():
            if framework == 'unity':
                assertion = f"    int result = {function_name}({param_call});\n    TEST_ASSERT_EQUAL(expected_value, result);"
            else:  # minunit
                assertion = f"    int result = {function_name}({param_call});\n    mu_assert(\"Result should match expected value\", result == expected_value);"
        elif 'float' in return_type.lower() or 'double' in return_type.lower():
            if framework == 'unity':
                assertion = f"    {return_type} result = {function_name}({param_call});\n    TEST_ASSERT_FLOAT_WITHIN(0.001, expected_value, result);"
            else:  # minunit
                assertion = f"    {return_type} result = {function_name}({param_call});\n    mu_assert(\"Result should be within tolerance\", fabs(result - expected_value) < 0.001);"
        elif '*' in return_type:
            if framework == 'unity':
                assertion = f"    {return_type} result = {function_name}({param_call});\n    TEST_ASSERT_NOT_NULL(result);"
            else:  # minunit
                assertion = f"    {return_type} result = {function_name}({param_call});\n    mu_assert(\"Result should not be NULL\", result != NULL);"
        else:
            assertion = f"    {return_type} result = {function_name}({param_call});\n    // TODO: Add appropriate assertion for {return_type}"
        
        return assertion
    
    def _generate_js_parameter_setup(self, parameters: List[str]) -> str:
        """Generate parameter setup code for JavaScript tests."""
        if not parameters:
            return "        // No parameters"
        
        setup_lines = []
        setup_lines.append("        // Set up test parameters")
        
        for param in parameters:
            if param.startswith('...'):
                # Rest parameter
                param_name = param[3:]
                setup_lines.append(f"        const {param_name} = [1, 2, 3]; // TODO: Set appropriate test values")
            else:
                setup_lines.append(f"        const {param} = 'test_value'; // TODO: Set appropriate test value")
        
        return '\n'.join(setup_lines)
    
    def _generate_js_import_statement(self, source_file: str, function: JSFunctionSignature) -> str:
        """Generate appropriate import statement for JavaScript tests."""
        file_name = os.path.splitext(os.path.basename(source_file))[0]
        
        if function.is_method and function.class_name:
            return f"const {{ {function.class_name} }} = require('../{file_name}');"
        else:
            return f"const {{ {function.name} }} = require('../{file_name}');"
    
    def _generate_unity_integration_test(self, function: CFunctionSignature, source_file: str) -> str:
        """Generate Unity integration test with hardware mocks."""
        test_name = f"integration_test_{function.name}"
        
        test_content = f'''#include "unity.h"
#include "mock_hardware.h"  // Hardware abstraction layer mock
#include "{os.path.basename(source_file)}"

// Mock hardware state
static mock_hardware_state_t mock_state;

void setUp(void) {{
    // Initialize hardware mocks
    mock_hardware_init(&mock_state);
}}

void tearDown(void) {{
    // Clean up hardware mocks
    mock_hardware_cleanup(&mock_state);
}}

void {test_name}(void) {{
    // Integration test for function: {function.name}
    // This test verifies the function works with mocked hardware
    
    // Set up mock hardware expectations
    mock_hardware_expect_call(&mock_state, "expected_hardware_function");
    
    // Set up test parameters
{self._generate_c_parameter_setup(function.parameters)}
    
    // Call the function under test
{self._generate_c_assertions(function.return_type, function.name)}
    
    // Verify hardware interactions
    TEST_ASSERT_TRUE(mock_hardware_verify_expectations(&mock_state));
    
    // TODO: Add specific integration test assertions
    // Verify that hardware was called correctly
    // Check side effects on hardware state
    // Validate timing requirements if applicable
}}
'''
        return test_content
    
    def _generate_minunit_integration_test(self, function: CFunctionSignature, source_file: str) -> str:
        """Generate MinUnit integration test with hardware mocks."""
        test_name = f"integration_test_{function.name}"
        
        test_content = f'''#include "minunit.h"
#include "mock_hardware.h"  // Hardware abstraction layer mock
#include "{os.path.basename(source_file)}"

// Mock hardware state
static mock_hardware_state_t mock_state;

static char* {test_name}() {{
    // Integration test for function: {function.name}
    // This test verifies the function works with mocked hardware
    
    // Initialize hardware mocks
    mock_hardware_init(&mock_state);
    
    // Set up mock hardware expectations
    mock_hardware_expect_call(&mock_state, "expected_hardware_function");
    
    // Set up test parameters
{self._generate_c_parameter_setup(function.parameters)}
    
    // Call the function under test
{self._generate_c_assertions(function.return_type, function.name, 'minunit')}
    
    // Verify hardware interactions
    mu_assert("Hardware expectations should be met", 
              mock_hardware_verify_expectations(&mock_state));
    
    // Clean up
    mock_hardware_cleanup(&mock_state);
    
    // TODO: Add specific integration test assertions
    
    return 0;
}}
'''
        return test_content
    
    def _generate_jest_integration_test(self, function: JSFunctionSignature, source_file: str) -> str:
        """Generate Jest integration test with hardware/system mocks."""
        test_name = f"integration test {function.name}"
        
        import_statement = self._generate_js_import_statement(source_file, function)
        
        test_content = f'''const {{ ipcRenderer }} = require('electron');
{import_statement}

// Mock hardware/system dependencies
jest.mock('serialport');
jest.mock('electron', () => ({{
    ipcRenderer: {{
        invoke: jest.fn(),
        send: jest.fn(),
        on: jest.fn()
    }}
}}));

describe('{function.name} Integration Tests', () => {{
    beforeEach(() => {{
        // Reset mocks before each test
        jest.clearAllMocks();
    }});
    
    test('{test_name}', {'async ' if function.is_async else ''}() => {{
        // Integration test for function: {function.name}
        // This test verifies the function works with mocked external systems
        
        // Set up mock expectations
        ipcRenderer.invoke.mockResolvedValue({{ success: true, data: 'mock_data' }});
        
        // Set up test parameters
{self._generate_js_parameter_setup(function.parameters)}
        
        // Call the function under test
        {'const result = await ' if function.is_async else 'const result = '}{function.name}({', '.join(function.parameters)});
        
        // Verify external system interactions
        expect(ipcRenderer.invoke).toHaveBeenCalled();
        
        // Verify result
        expect(result).toBeDefined();
        
        // TODO: Add specific integration test assertions
        // Verify IPC calls were made correctly
        // Check hardware communication
        // Validate data flow between components
    }});
    
    test('{function.name} handles hardware errors', {'async ' if function.is_async else ''}() => {{
        // Test error handling in integration scenarios
        ipcRenderer.invoke.mockRejectedValue(new Error('Hardware communication failed'));
        
        // TODO: Test error scenarios
        // Verify graceful error handling
        // Check fallback mechanisms
    }});
}});
'''
        return test_content
    
    def _generate_mocha_integration_test(self, function: JSFunctionSignature, source_file: str) -> str:
        """Generate Mocha integration test with hardware/system mocks."""
        test_name = f"integration test {function.name}"
        
        import_statement = self._generate_js_import_statement(source_file, function)
        
        test_content = f'''const {{ expect }} = require('chai');
const sinon = require('sinon');
const {{ ipcRenderer }} = require('electron');
{import_statement}

describe('{function.name} Integration Tests', function() {{
    let ipcStub;
    
    beforeEach(function() {{
        // Set up stubs for external dependencies
        ipcStub = sinon.stub(ipcRenderer, 'invoke');
    }});
    
    afterEach(function() {{
        // Clean up stubs
        sinon.restore();
    }});
    
    it('should work with mocked hardware', {'async ' if function.is_async else ''}function() {{
        // Integration test for function: {function.name}
        // This test verifies the function works with mocked external systems
        
        // Set up mock expectations
        ipcStub.resolves({{ success: true, data: 'mock_data' }});
        
        // Set up test parameters
{self._generate_js_parameter_setup(function.parameters)}
        
        // Call the function under test
        {'const result = await ' if function.is_async else 'const result = '}{function.name}({', '.join(function.parameters)});
        
        // Verify external system interactions
        expect(ipcStub).to.have.been.called;
        
        // Verify result
        expect(result).to.exist;
        
        // TODO: Add specific integration test assertions
    }});
    
    it('should handle hardware errors gracefully', {'async ' if function.is_async else ''}function() {{
        // Test error handling in integration scenarios
        ipcStub.rejects(new Error('Hardware communication failed'));
        
        // TODO: Test error scenarios
    }});
}});
'''
        return test_content
    
    def _get_test_file_path(self, source_file: str, language: str, framework: str) -> str:
        """Generate test file path based on source file and framework."""
        base_name = os.path.splitext(os.path.basename(source_file))[0]
        
        if language == 'c':
            if framework == 'unity':
                return f"tests/unit/test_{base_name}.c"
            else:  # minunit
                return f"tests/unit/test_{base_name}.c"
        else:  # javascript
            if framework == 'jest':
                return f"tests/unit/{base_name}.test.js"
            else:  # mocha
                return f"tests/unit/{base_name}.spec.js"
    
    def _get_integration_test_file_path(self, source_file: str, language: str, framework: str) -> str:
        """Generate integration test file path based on source file and framework."""
        base_name = os.path.splitext(os.path.basename(source_file))[0]
        
        if language == 'c':
            return f"tests/integration/integration_test_{base_name}.c"
        else:  # javascript
            if framework == 'jest':
                return f"tests/integration/{base_name}.integration.test.js"
            else:  # mocha
                return f"tests/integration/{base_name}.integration.spec.js"
    
    def _generate_c_framework_config(self, framework: str) -> Dict[str, Any]:
        """Generate configuration for C testing framework."""
        if framework == 'unity':
            return {
                'framework': 'unity',
                'config_file': 'unity_config.h',
                'runner_template': 'unity_runner.c.template',
                'build_script': 'build_unity_tests.sh',
                'dependencies': ['unity.c', 'unity.h'],
                'compiler_flags': ['-DUNITY_INCLUDE_CONFIG_H'],
                'linker_flags': []
            }
        else:  # minunit
            return {
                'framework': 'minunit',
                'config_file': 'minunit.h',
                'runner_template': 'minunit_runner.c.template',
                'build_script': 'build_minunit_tests.sh',
                'dependencies': ['minunit.h'],
                'compiler_flags': [],
                'linker_flags': []
            }
    
    def _generate_js_framework_config(self, framework: str) -> Dict[str, Any]:
        """Generate configuration for JavaScript testing framework."""
        if framework == 'jest':
            return {
                'framework': 'jest',
                'config_file': 'jest.config.js',
                'package_dependencies': ['jest', '@types/jest'],
                'test_patterns': ['**/*.test.js', '**/*.spec.js'],
                'coverage_threshold': {
                    'global': {
                        'branches': 80,
                        'functions': 80,
                        'lines': 80,
                        'statements': 80
                    }
                }
            }
        else:  # mocha
            return {
                'framework': 'mocha',
                'config_file': '.mocharc.json',
                'package_dependencies': ['mocha', 'chai', 'sinon'],
                'test_patterns': ['**/*.spec.js', '**/*.test.js'],
                'reporter': 'spec',
                'timeout': 5000
            }
    
    def export_test_suite(self, test_suite: TestSuite, output_dir: str) -> Dict[str, str]:
        """Export test suite to files in the specified directory.
        
        Args:
            test_suite: TestSuite to export
            output_dir: Directory to write test files
            
        Returns:
            Dictionary mapping file paths to their content
        """
        exported_files = {}
        
        # Create output directory structure
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'unit'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'integration'), exist_ok=True)
        
        # Export unit tests
        for test_skeleton in test_suite.test_skeletons:
            file_path = os.path.join(output_dir, test_skeleton.file_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(test_skeleton.test_content)
            
            exported_files[file_path] = test_skeleton.test_content
        
        # Export integration tests
        for integration_test in test_suite.integration_tests:
            file_path = os.path.join(output_dir, integration_test.file_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(integration_test.test_content)
            
            exported_files[file_path] = integration_test.test_content
        
        # Export framework configuration files
        for language, config in test_suite.framework_configs.items():
            config_content = self._generate_framework_config_file(config)
            if config_content:
                config_file = config.get('config_file', f'{language}_config')
                config_path = os.path.join(output_dir, config_file)
                
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.write(config_content)
                
                exported_files[config_path] = config_content
        
        return exported_files
    
    def _generate_framework_config_file(self, config: Dict[str, Any]) -> Optional[str]:
        """Generate framework-specific configuration file content."""
        framework = config.get('framework')
        
        if framework == 'unity':
            return '''#ifndef UNITY_CONFIG_H
#define UNITY_CONFIG_H

// Unity configuration for medical device testing
#define UNITY_INCLUDE_DOUBLE
#define UNITY_INCLUDE_FLOAT
#define UNITY_SUPPORT_64

// Custom assertion macros for medical device testing
#define TEST_ASSERT_WITHIN_TOLERANCE(expected, actual, tolerance) \\
    TEST_ASSERT_FLOAT_WITHIN(tolerance, expected, actual)

#define TEST_ASSERT_SAFETY_CRITICAL(condition) \\
    TEST_ASSERT_TRUE_MESSAGE(condition, "Safety critical assertion failed")

#endif // UNITY_CONFIG_H
'''
        elif framework == 'jest':
            return '''module.exports = {
  testEnvironment: 'node',
  collectCoverage: true,
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  testMatch: [
    '**/__tests__/**/*.js',
    '**/?(*.)+(spec|test).js'
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  },
  setupFilesAfterEnv: ['<rootDir>/tests/setup.js'],
  testTimeout: 10000
};
'''
        elif framework == 'mocha':
            return '''{
  "require": ["tests/setup.js"],
  "recursive": true,
  "reporter": "spec",
  "timeout": 5000,
  "exit": true
}
'''
        
        return None
    
    def validate_test_skeleton(self, test_skeleton: TestSkeleton) -> List[str]:
        """Validate a test skeleton for completeness and correctness.
        
        Args:
            test_skeleton: TestSkeleton to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Basic field validation
        if not test_skeleton.test_name:
            errors.append("Test name cannot be empty")
        
        if not test_skeleton.test_content:
            errors.append("Test content cannot be empty")
        
        if test_skeleton.framework not in self.c_frameworks + self.js_frameworks:
            errors.append(f"Unsupported framework: {test_skeleton.framework}")
        
        if test_skeleton.language not in ['c', 'javascript']:
            errors.append(f"Unsupported language: {test_skeleton.language}")
        
        # Framework-specific validation
        if test_skeleton.language == 'c':
            if test_skeleton.framework not in self.c_frameworks:
                errors.append(f"Framework {test_skeleton.framework} not supported for C")
            
            # Check for required C test elements
            if 'TEST_ASSERT' not in test_skeleton.test_content and 'mu_assert' not in test_skeleton.test_content:
                errors.append("C test should contain assertions")
        
        elif test_skeleton.language == 'javascript':
            if test_skeleton.framework not in self.js_frameworks:
                errors.append(f"Framework {test_skeleton.framework} not supported for JavaScript")
            
            # Check for required JS test elements
            if 'expect(' not in test_skeleton.test_content:
                errors.append("JavaScript test should contain expect assertions")
        
        return errors