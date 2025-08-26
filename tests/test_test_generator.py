"""
Unit tests for the test generator service.
"""

import pytest
import os
import tempfile
from datetime import datetime
from unittest.mock import Mock, patch

from medical_analyzer.tests.test_generator import (
    TestGenerator, TestSkeleton, TestSuite
)
from medical_analyzer.models.core import ProjectStructure, FileMetadata
from medical_analyzer.parsers.c_parser import FunctionSignature as CFunctionSignature, CCodeStructure
from medical_analyzer.parsers.js_parser import FunctionSignature as JSFunctionSignature, JSCodeStructure


class TestTestGenerator:
    """Test cases for TestGenerator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TestGenerator()
        
        # Create mock project structure
        self.project_structure = ProjectStructure(
            root_path="/test/project",
            selected_files=["src/main.c", "src/utils.js"],
            description="Test medical device project"
        )
        
        # Create mock C function
        self.c_function = CFunctionSignature(
            name="calculate_dosage",
            return_type="int",
            parameters=[
                {"type": "float", "name": "weight"},
                {"type": "int", "name": "age"}
            ],
            start_line=10,
            end_line=25,
            is_static=False,
            is_inline=False
        )
        
        # Create mock JavaScript function
        self.js_function = JSFunctionSignature(
            name="validateInput",
            parameters=["data", "schema"],
            start_line=5,
            end_line=15,
            is_async=True,
            is_arrow=False,
            is_method=False
        )
        
        # Create mock parsed files
        self.c_parsed_file = Mock()
        self.c_parsed_file.file_path = "src/main.c"
        self.c_parsed_file.file_metadata = FileMetadata(
            file_path="src/main.c",
            file_size=1024,
            last_modified=datetime.now(),
            file_type="c",
            line_count=50,
            function_count=3
        )
        self.c_parsed_file.code_structure = CCodeStructure(
            file_path="src/main.c",
            functions=[self.c_function],
            includes=["#include <stdio.h>"],
            defines=[{"name": "MAX_DOSE", "value": "100"}],
            global_variables=[],
            structs=[],
            enums=[]
        )
        
        self.js_parsed_file = Mock()
        self.js_parsed_file.file_path = "src/utils.js"
        self.js_parsed_file.file_metadata = FileMetadata(
            file_path="src/utils.js",
            file_size=2048,
            last_modified=datetime.now(),
            file_type="javascript",
            line_count=80,
            function_count=5
        )
        self.js_parsed_file.code_structure = JSCodeStructure(
            file_path="src/utils.js",
            functions=[self.js_function],
            classes=[],
            imports=[],
            exports=[],
            variables=[],
            requires=[]
        )
    
    def test_init(self):
        """Test TestGenerator initialization."""
        generator = TestGenerator()
        
        assert generator.c_frameworks == ['unity', 'minunit']
        assert generator.js_frameworks == ['jest', 'mocha']
    
    def test_generate_test_suite_success(self):
        """Test successful test suite generation."""
        parsed_files = [self.c_parsed_file, self.js_parsed_file]
        
        test_suite = self.generator.generate_test_suite(
            self.project_structure,
            parsed_files,
            c_framework='unity',
            js_framework='jest'
        )
        
        assert isinstance(test_suite, TestSuite)
        assert test_suite.project_name == "project"
        assert len(test_suite.test_skeletons) >= 2  # At least one for each file
        assert len(test_suite.framework_configs) == 2  # C and JavaScript configs
        assert 'c' in test_suite.framework_configs
        assert 'javascript' in test_suite.framework_configs
    
    def test_generate_test_suite_invalid_framework(self):
        """Test test suite generation with invalid framework."""
        parsed_files = [self.c_parsed_file]
        
        with pytest.raises(ValueError, match="Unsupported C framework"):
            self.generator.generate_test_suite(
                self.project_structure,
                parsed_files,
                c_framework='invalid_framework'
            )
        
        with pytest.raises(ValueError, match="Unsupported JS framework"):
            self.generator.generate_test_suite(
                self.project_structure,
                parsed_files,
                js_framework='invalid_framework'
            )
    
    def test_generate_c_unit_tests_unity(self):
        """Test C unit test generation with Unity framework."""
        tests = self.generator._generate_c_unit_tests(self.c_parsed_file, 'unity')
        
        assert len(tests) == 1
        test = tests[0]
        
        assert test.test_name == "test_calculate_dosage"
        assert test.framework == "unity"
        assert test.language == "c"
        assert test.target_function == "calculate_dosage"
        assert "#include \"unity.h\"" in test.test_content
        assert "void test_calculate_dosage(void)" in test.test_content
        assert "TEST_ASSERT" in test.test_content
        assert test.file_path == "tests/unit/test_main.c"
    
    def test_generate_c_unit_tests_minunit(self):
        """Test C unit test generation with MinUnit framework."""
        tests = self.generator._generate_c_unit_tests(self.c_parsed_file, 'minunit')
        
        assert len(tests) == 1
        test = tests[0]
        
        assert test.test_name == "test_calculate_dosage"
        assert test.framework == "minunit"
        assert test.language == "c"
        assert "#include \"minunit.h\"" in test.test_content
        assert "static char* test_calculate_dosage()" in test.test_content
        assert "mu_assert" in test.test_content
    
    def test_generate_js_unit_tests_jest(self):
        """Test JavaScript unit test generation with Jest framework."""
        tests = self.generator._generate_js_unit_tests(self.js_parsed_file, 'jest')
        
        assert len(tests) == 1
        test = tests[0]
        
        assert test.test_name == "test_validateInput"
        assert test.framework == "jest"
        assert test.language == "javascript"
        assert test.target_function == "validateInput"
        assert "describe('validateInput'" in test.test_content
        assert "test('test validateInput'" in test.test_content
        assert "expect(" in test.test_content
        assert "await" in test.test_content  # Because function is async
        assert test.file_path == "tests/unit/utils.test.js"
    
    def test_generate_js_unit_tests_mocha(self):
        """Test JavaScript unit test generation with Mocha framework."""
        tests = self.generator._generate_js_unit_tests(self.js_parsed_file, 'mocha')
        
        assert len(tests) == 1
        test = tests[0]
        
        assert test.test_name == "test_validateInput"
        assert test.framework == "mocha"
        assert test.language == "javascript"
        assert "describe('validateInput'" in test.test_content
        assert "it('should work correctly'" in test.test_content
        assert "expect(" in test.test_content
        assert "async function()" in test.test_content  # Because function is async
        assert test.file_path == "tests/unit/utils.spec.js"
    
    def test_identify_hardware_functions(self):
        """Test identification of hardware-related C functions."""
        # Create functions with hardware-related names
        gpio_function = CFunctionSignature(
            name="gpio_set_pin",
            return_type="void",
            parameters=[{"type": "int", "name": "pin"}],
            start_line=1,
            end_line=5
        )
        
        normal_function = CFunctionSignature(
            name="calculate_sum",
            return_type="int",
            parameters=[{"type": "int", "name": "a"}, {"type": "int", "name": "b"}],
            start_line=10,
            end_line=15
        )
        
        sensor_function = CFunctionSignature(
            name="read_temperature",
            return_type="float",
            parameters=[{"type": "sensor_t*", "name": "sensor"}],
            start_line=20,
            end_line=30
        )
        
        functions = [gpio_function, normal_function, sensor_function]
        hardware_functions = self.generator._identify_hardware_functions(functions)
        
        assert len(hardware_functions) == 2
        assert gpio_function in hardware_functions
        assert sensor_function in hardware_functions
        assert normal_function not in hardware_functions
    
    def test_identify_integration_functions(self):
        """Test identification of integration-related JavaScript functions."""
        # Create functions that need integration testing
        api_function = JSFunctionSignature(
            name="fetchApiData",
            parameters=["endpoint"],
            start_line=1,
            end_line=10,
            is_async=True
        )
        
        normal_function = JSFunctionSignature(
            name="formatString",
            parameters=["text"],
            start_line=15,
            end_line=20,
            is_async=False
        )
        
        db_function = JSFunctionSignature(
            name="queryDatabase",
            parameters=["query", "params"],
            start_line=25,
            end_line=35,
            is_async=True
        )
        
        functions = [api_function, normal_function, db_function]
        integration_functions = self.generator._identify_integration_functions(functions)
        
        # All async functions and functions with integration keywords should be identified
        assert len(integration_functions) == 2
        assert api_function in integration_functions
        assert db_function in integration_functions
        assert normal_function not in integration_functions
    
    def test_generate_c_parameter_setup(self):
        """Test C parameter setup generation."""
        parameters = [
            {"type": "int", "name": "count"},
            {"type": "float", "name": "value"},
            {"type": "char*", "name": "message"},
            {"type": "void*", "name": "data"}
        ]
        
        setup = self.generator._generate_c_parameter_setup(parameters)
        
        assert "int count = 42" in setup
        assert "float value = 3.14" in setup
        assert "char* message = \"test_string\"" in setup
        assert "void* data = NULL" in setup
    
    def test_generate_c_parameter_setup_empty(self):
        """Test C parameter setup with no parameters."""
        setup = self.generator._generate_c_parameter_setup([])
        assert "No parameters" in setup
    
    def test_generate_js_parameter_setup(self):
        """Test JavaScript parameter setup generation."""
        parameters = ["name", "age", "...options"]
        
        setup = self.generator._generate_js_parameter_setup(parameters)
        
        assert "const name = 'test_value'" in setup
        assert "const age = 'test_value'" in setup
        assert "const options = [1, 2, 3]" in setup
    
    def test_generate_js_parameter_setup_empty(self):
        """Test JavaScript parameter setup with no parameters."""
        setup = self.generator._generate_js_parameter_setup([])
        assert "No parameters" in setup
    
    def test_generate_c_assertions_void_return(self):
        """Test C assertion generation for void return type."""
        assertions = self.generator._generate_c_assertions("void", "test_function")
        
        assert "test_function(" in assertions
        assert "side effects" in assertions
    
    def test_generate_c_assertions_int_return_unity(self):
        """Test C assertion generation for int return type with Unity."""
        assertions = self.generator._generate_c_assertions("int", "test_function", "unity")
        
        assert "int result = test_function(" in assertions
        assert "TEST_ASSERT_EQUAL" in assertions
    
    def test_generate_c_assertions_int_return_minunit(self):
        """Test C assertion generation for int return type with MinUnit."""
        assertions = self.generator._generate_c_assertions("int", "test_function", "minunit")
        
        assert "int result = test_function(" in assertions
        assert "mu_assert" in assertions
    
    def test_generate_c_assertions_pointer_return(self):
        """Test C assertion generation for pointer return type."""
        assertions = self.generator._generate_c_assertions("char*", "test_function")
        
        assert "char* result = test_function(" in assertions
        assert "TEST_ASSERT_NOT_NULL" in assertions
    
    def test_get_test_file_path_c_unity(self):
        """Test test file path generation for C with Unity."""
        path = self.generator._get_test_file_path("src/main.c", "c", "unity")
        assert path == "tests/unit/test_main.c"
    
    def test_get_test_file_path_js_jest(self):
        """Test test file path generation for JavaScript with Jest."""
        path = self.generator._get_test_file_path("src/utils.js", "javascript", "jest")
        assert path == "tests/unit/utils.test.js"
    
    def test_get_test_file_path_js_mocha(self):
        """Test test file path generation for JavaScript with Mocha."""
        path = self.generator._get_test_file_path("src/utils.js", "javascript", "mocha")
        assert path == "tests/unit/utils.spec.js"
    
    def test_get_integration_test_file_path_c(self):
        """Test integration test file path generation for C."""
        path = self.generator._get_integration_test_file_path("src/main.c", "c", "unity")
        assert path == "tests/integration/integration_test_main.c"
    
    def test_get_integration_test_file_path_js_jest(self):
        """Test integration test file path generation for JavaScript with Jest."""
        path = self.generator._get_integration_test_file_path("src/utils.js", "javascript", "jest")
        assert path == "tests/integration/utils.integration.test.js"
    
    def test_generate_c_framework_config_unity(self):
        """Test Unity framework configuration generation."""
        config = self.generator._generate_c_framework_config('unity')
        
        assert config['framework'] == 'unity'
        assert config['config_file'] == 'unity_config.h'
        assert 'unity.c' in config['dependencies']
        assert 'unity.h' in config['dependencies']
        assert '-DUNITY_INCLUDE_CONFIG_H' in config['compiler_flags']
    
    def test_generate_c_framework_config_minunit(self):
        """Test MinUnit framework configuration generation."""
        config = self.generator._generate_c_framework_config('minunit')
        
        assert config['framework'] == 'minunit'
        assert config['config_file'] == 'minunit.h'
        assert 'minunit.h' in config['dependencies']
    
    def test_generate_js_framework_config_jest(self):
        """Test Jest framework configuration generation."""
        config = self.generator._generate_js_framework_config('jest')
        
        assert config['framework'] == 'jest'
        assert config['config_file'] == 'jest.config.js'
        assert 'jest' in config['package_dependencies']
        assert '@types/jest' in config['package_dependencies']
        assert config['coverage_threshold']['global']['branches'] == 80
    
    def test_generate_js_framework_config_mocha(self):
        """Test Mocha framework configuration generation."""
        config = self.generator._generate_js_framework_config('mocha')
        
        assert config['framework'] == 'mocha'
        assert config['config_file'] == '.mocharc.json'
        assert 'mocha' in config['package_dependencies']
        assert 'chai' in config['package_dependencies']
        assert 'sinon' in config['package_dependencies']
    
    def test_export_test_suite(self):
        """Test test suite export functionality."""
        # Create a test suite
        test_skeleton = TestSkeleton(
            test_name="test_example",
            test_content="// Test content",
            framework="unity",
            language="c",
            target_function="example",
            file_path="tests/unit/test_example.c",
            metadata={}
        )
        
        test_suite = TestSuite(
            project_name="test_project",
            test_skeletons=[test_skeleton],
            framework_configs={'c': self.generator._generate_c_framework_config('unity')},
            integration_tests=[],
            created_at=datetime.now()
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            exported_files = self.generator.export_test_suite(test_suite, temp_dir)
            
            # Check that files were created
            assert len(exported_files) >= 2  # At least test file and config file
            
            # Check test file was created
            test_file_path = os.path.join(temp_dir, "tests/unit/test_example.c")
            assert test_file_path in exported_files
            assert os.path.exists(test_file_path)
            
            # Check config file was created
            config_files = [f for f in exported_files.keys() if 'unity_config.h' in f]
            assert len(config_files) == 1
    
    def test_validate_test_skeleton_valid(self):
        """Test validation of a valid test skeleton."""
        test_skeleton = TestSkeleton(
            test_name="test_valid",
            test_content="void test_valid(void) { TEST_ASSERT_TRUE(1); }",
            framework="unity",
            language="c",
            target_function="valid_function",
            file_path="tests/unit/test_valid.c",
            metadata={}
        )
        
        errors = self.generator.validate_test_skeleton(test_skeleton)
        assert len(errors) == 0
    
    def test_validate_test_skeleton_invalid_empty_name(self):
        """Test validation of test skeleton with empty name."""
        test_skeleton = TestSkeleton(
            test_name="",
            test_content="void test_valid(void) { TEST_ASSERT_TRUE(1); }",
            framework="unity",
            language="c",
            target_function="valid_function",
            file_path="tests/unit/test_valid.c",
            metadata={}
        )
        
        errors = self.generator.validate_test_skeleton(test_skeleton)
        assert "Test name cannot be empty" in errors
    
    def test_validate_test_skeleton_invalid_framework(self):
        """Test validation of test skeleton with invalid framework."""
        test_skeleton = TestSkeleton(
            test_name="test_valid",
            test_content="void test_valid(void) { TEST_ASSERT_TRUE(1); }",
            framework="invalid_framework",
            language="c",
            target_function="valid_function",
            file_path="tests/unit/test_valid.c",
            metadata={}
        )
        
        errors = self.generator.validate_test_skeleton(test_skeleton)
        assert "Unsupported framework: invalid_framework" in errors
    
    def test_validate_test_skeleton_c_missing_assertions(self):
        """Test validation of C test skeleton missing assertions."""
        test_skeleton = TestSkeleton(
            test_name="test_invalid",
            test_content="void test_invalid(void) { /* no assertions */ }",
            framework="unity",
            language="c",
            target_function="invalid_function",
            file_path="tests/unit/test_invalid.c",
            metadata={}
        )
        
        errors = self.generator.validate_test_skeleton(test_skeleton)
        assert "C test should contain assertions" in errors
    
    def test_validate_test_skeleton_js_missing_assertions(self):
        """Test validation of JavaScript test skeleton missing assertions."""
        test_skeleton = TestSkeleton(
            test_name="test_invalid",
            test_content="test('invalid', () => { /* no assertions */ });",
            framework="jest",
            language="javascript",
            target_function="invalid_function",
            file_path="tests/unit/invalid.test.js",
            metadata={}
        )
        
        errors = self.generator.validate_test_skeleton(test_skeleton)
        assert "JavaScript test should contain expect assertions" in errors


class TestTestSkeleton:
    """Test cases for TestSkeleton dataclass."""
    
    def test_test_skeleton_creation(self):
        """Test TestSkeleton creation."""
        skeleton = TestSkeleton(
            test_name="test_example",
            test_content="// Test content",
            framework="unity",
            language="c",
            target_function="example",
            file_path="tests/unit/test_example.c",
            metadata={"key": "value"}
        )
        
        assert skeleton.test_name == "test_example"
        assert skeleton.test_content == "// Test content"
        assert skeleton.framework == "unity"
        assert skeleton.language == "c"
        assert skeleton.target_function == "example"
        assert skeleton.file_path == "tests/unit/test_example.c"
        assert skeleton.metadata == {"key": "value"}


class TestTestSuite:
    """Test cases for TestSuite dataclass."""
    
    def test_test_suite_creation(self):
        """Test TestSuite creation."""
        test_skeleton = TestSkeleton(
            test_name="test_example",
            test_content="// Test content",
            framework="unity",
            language="c",
            target_function="example",
            file_path="tests/unit/test_example.c",
            metadata={}
        )
        
        created_at = datetime.now()
        suite = TestSuite(
            project_name="test_project",
            test_skeletons=[test_skeleton],
            framework_configs={"c": {"framework": "unity"}},
            integration_tests=[],
            created_at=created_at
        )
        
        assert suite.project_name == "test_project"
        assert len(suite.test_skeletons) == 1
        assert suite.test_skeletons[0] == test_skeleton
        assert suite.framework_configs == {"c": {"framework": "unity"}}
        assert suite.integration_tests == []
        assert suite.created_at == created_at


if __name__ == '__main__':
    pytest.main([__file__])