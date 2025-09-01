"""
Unit tests for TestCaseGenerator class.

Tests cover:
- Test case generation from requirements
- Template-based test creation
- Export functionality
- Coverage analysis
- Integration with LLM backend
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from medical_analyzer.services.test_case_generator import TestCaseGenerator
from medical_analyzer.models.test_models import TestCase, TestStep, TestOutline, CoverageReport, TestCasePriority, TestCaseCategory
from medical_analyzer.models.core import Requirement, RequirementType
from medical_analyzer.llm.backend import LLMBackend


class TestTestCaseGenerator:
    """Test suite for TestCaseGenerator functionality."""
    
    @pytest.fixture
    def mock_llm_backend(self):
        """Create mock LLM backend."""
        backend = Mock(spec=LLMBackend)
        backend.generate.return_value = {
            'test_cases': [
                {
                    'name': 'Test user login with valid credentials',
                    'description': 'Verify that user can login with valid username and password',
                    'preconditions': ['User account exists', 'Application is running'],
                    'test_steps': [
                        {'step_number': 1, 'action': 'Enter valid username', 'expected_result': 'Username field accepts input'},
                        {'step_number': 2, 'action': 'Enter valid password', 'expected_result': 'Password field accepts input'},
                        {'step_number': 3, 'action': 'Click login button', 'expected_result': 'User is logged in successfully'}
                    ],
                    'expected_results': ['User dashboard is displayed', 'Session is established'],
                    'priority': 'high',
                    'category': 'security'
                }
            ]
        }
        return backend
    
    @pytest.fixture
    def generator(self, mock_llm_backend):
        """Create TestCaseGenerator with mock backend."""
        return TestCaseGenerator(mock_llm_backend)
    
    @pytest.fixture
    def sample_requirements(self):
        """Create sample requirements for testing."""
        return [
            Requirement(
                id="UR1",
                text="User shall be able to login with valid credentials",
                type=RequirementType.USER,
                acceptance_criteria=[
                    "Valid username and password are accepted",
                    "User is redirected to dashboard after login",
                    "Session is established and maintained"
                ]
            ),
            Requirement(
                id="SR1",
                text="System shall validate user credentials against database",
                type=RequirementType.SOFTWARE,
                acceptance_criteria=[
                    "Credentials are checked against user database",
                    "Invalid credentials are rejected with error message",
                    "Account lockout after 3 failed attempts"
                ],
                derived_from=["UR1"]
            )
        ]
    
    def test_generator_initialization(self, mock_llm_backend):
        """Test TestCaseGenerator initialization."""
        generator = TestCaseGenerator(mock_llm_backend)
        
        assert generator.llm_backend == mock_llm_backend
        assert hasattr(generator, 'templates')
        assert len(generator.templates) > 0
    
    def test_generate_test_cases_success(self, generator, sample_requirements):
        """Test successful test case generation."""
        test_cases = generator.generate_test_cases(sample_requirements)
        
        assert len(test_cases) > 0
        assert isinstance(test_cases[0], TestCase)
        assert test_cases[0].name == 'Test user login with valid credentials'
        assert test_cases[0].requirement_id == 'UR1'
        assert len(test_cases[0].test_steps) == 3
        assert test_cases[0].priority == 'high'
    
    def test_generate_test_cases_llm_failure(self, generator, sample_requirements):
        """Test test case generation when LLM fails."""
        generator.llm_backend.generate.side_effect = Exception("LLM connection failed")
        
        with pytest.raises(Exception, match="LLM connection failed"):
            generator.generate_test_cases(sample_requirements)
    
    def test_generate_test_cases_empty_requirements(self, generator):
        """Test test case generation with empty requirements list."""
        test_cases = generator.generate_test_cases([])
        
        assert len(test_cases) == 0
    
    def test_create_test_outline_single_requirement(self, generator, sample_requirements):
        """Test creating test outline for single requirement."""
        requirement = sample_requirements[0]
        
        outline = generator.create_test_outline(requirement)
        
        assert isinstance(outline, TestOutline)
        assert len(outline.test_cases) > 0
        assert outline.test_cases[0].requirement_id == requirement.id
        assert 'coverage_summary' in outline.generation_metadata
    
    def test_export_test_cases_json(self, generator, sample_requirements):
        """Test exporting test cases to JSON format."""
        test_cases = generator.generate_test_cases(sample_requirements)
        
        json_export = generator.export_test_cases(test_cases, 'json')
        
        assert json_export is not None
        assert 'test_cases' in json_export
        assert 'Test user login' in json_export
    
    def test_export_test_cases_xml(self, generator, sample_requirements):
        """Test exporting test cases to XML format."""
        test_cases = generator.generate_test_cases(sample_requirements)
        
        xml_export = generator.export_test_cases(test_cases, 'xml')
        
        assert xml_export is not None
        assert '<testcase' in xml_export
        assert 'Test user login' in xml_export
    
    def test_export_test_cases_csv(self, generator, sample_requirements):
        """Test exporting test cases to CSV format."""
        test_cases = generator.generate_test_cases(sample_requirements)
        
        csv_export = generator.export_test_cases(test_cases, 'csv')
        
        assert csv_export is not None
        assert 'Test Name,Description,Priority' in csv_export
        assert 'Test user login' in csv_export
    
    def test_export_test_cases_plain_text(self, generator, sample_requirements):
        """Test exporting test cases to plain text format."""
        test_cases = generator.generate_test_cases(sample_requirements)
        
        text_export = generator.export_test_cases(test_cases, 'text')
        
        assert text_export is not None
        assert 'Test Case:' in text_export
        assert 'Test user login' in text_export
        assert 'Steps:' in text_export
    
    def test_export_test_cases_invalid_format(self, generator, sample_requirements):
        """Test exporting with invalid format."""
        test_cases = generator.generate_test_cases(sample_requirements)
        
        with pytest.raises(ValueError, match="Unsupported export format"):
            generator.export_test_cases(test_cases, 'invalid_format')
    
    def test_generate_coverage_report(self, generator, sample_requirements):
        """Test generating coverage report."""
        test_cases = generator.generate_test_cases(sample_requirements)
        
        coverage_report = generator.generate_coverage_report(test_cases)
        
        assert isinstance(coverage_report, CoverageReport)
        assert coverage_report.total_requirements > 0
        assert coverage_report.covered_requirements > 0
        assert coverage_report.coverage_percentage >= 0
        assert len(coverage_report.requirement_coverage) > 0
    
    def test_generate_coverage_report_empty_tests(self, generator):
        """Test coverage report with no test cases."""
        coverage_report = generator.generate_coverage_report([])
        
        assert coverage_report.total_requirements == 0
        assert coverage_report.covered_requirements == 0
        assert coverage_report.coverage_percentage == 0
        assert len(coverage_report.requirement_coverage) == 0
    
    def test_validate_test_case_valid(self, generator):
        """Test validation of valid test case."""
        test_case = TestCase(
            id="TC1",
            name="Valid test case",
            description="Test description",
            requirement_id="UR1",
            preconditions=["Precondition 1"],
            test_steps=[
                TestStep(1, "Action 1", "Expected 1")
            ],
            expected_results=["Result 1"],
            priority=TestCasePriority.MEDIUM,
            category=TestCaseCategory.FUNCTIONAL
        )
        
        validation_errors = generator.validate_test_case(test_case)
        
        assert len(validation_errors) == 0
    
    def test_validate_test_case_invalid(self, generator):
        """Test validation of invalid test case."""
        test_case = TestCase(
            id="",  # Empty ID
            name="",  # Empty name
            description="Test description",
            requirement_id="",  # Empty requirement ID
            preconditions=[],
            test_steps=[],  # Empty steps
            expected_results=[],
            priority="invalid_priority",  # Invalid priority
            category=TestCaseCategory.FUNCTIONAL
        )
        
        validation_errors = generator.validate_test_case(test_case)
        
        assert len(validation_errors) > 0
        assert any("empty ID" in error.lower() for error in validation_errors)
        assert any("empty name" in error.lower() for error in validation_errors)
        assert any("empty requirement" in error.lower() for error in validation_errors)
        assert any("no test steps" in error.lower() for error in validation_errors)
        assert any("invalid priority" in error.lower() for error in validation_errors)
    
    def test_get_template_by_type(self, generator):
        """Test getting template by requirement type."""
        user_template = generator.get_template_by_type(RequirementType.USER)
        software_template = generator.get_template_by_type(RequirementType.SOFTWARE)
        
        assert user_template is not None
        assert software_template is not None
        assert user_template != software_template
    
    def test_generate_test_steps_from_criteria(self, generator):
        """Test generating test steps from acceptance criteria."""
        acceptance_criteria = [
            "Valid username and password are accepted",
            "User is redirected to dashboard after login",
            "Session is established and maintained"
        ]
        
        test_steps = generator.generate_test_steps_from_criteria(acceptance_criteria)
        
        assert len(test_steps) >= len(acceptance_criteria)
        assert all(isinstance(step, TestStep) for step in test_steps)
        assert all(step.step_number > 0 for step in test_steps)
        assert all(step.action and step.expected_result for step in test_steps)
    
    def test_organize_tests_by_requirement(self, generator, sample_requirements):
        """Test organizing test cases by requirement."""
        test_cases = generator.generate_test_cases(sample_requirements)
        
        organized = generator.organize_tests_by_requirement(test_cases)
        
        assert isinstance(organized, dict)
        assert len(organized) > 0
        
        for req_id, tests in organized.items():
            assert isinstance(tests, list)
            assert all(test.requirement_id == req_id for test in tests)
    
    def test_generate_test_summary(self, generator, sample_requirements):
        """Test generating test summary statistics."""
        test_cases = generator.generate_test_cases(sample_requirements)
        
        summary = generator.generate_test_summary(test_cases)
        
        assert 'total_test_cases' in summary
        assert 'high_priority_tests' in summary
        assert 'medium_priority_tests' in summary
        assert 'low_priority_tests' in summary
        assert 'categories' in summary
        assert 'requirements_covered' in summary
        
        assert summary['total_test_cases'] == len(test_cases)
        assert summary['requirements_covered'] > 0
    
    def test_filter_tests_by_priority(self, generator, sample_requirements):
        """Test filtering test cases by priority."""
        test_cases = generator.generate_test_cases(sample_requirements)
        
        high_priority = generator.filter_tests_by_priority(test_cases, 'high')
        
        assert len(high_priority) > 0
        assert all(test.priority == 'high' for test in high_priority)
    
    def test_filter_tests_by_category(self, generator, sample_requirements):
        """Test filtering test cases by category."""
        test_cases = generator.generate_test_cases(sample_requirements)
        
        security_tests = generator.filter_tests_by_category(test_cases, 'security')
        
        assert len(security_tests) > 0
        assert all(test.category == 'security' for test in security_tests)
    
    def test_update_test_case_metadata(self, generator):
        """Test updating test case metadata."""
        test_case = TestCase(
            id="TC1",
            name="Test case",
            description="Description",
            requirement_id="UR1",
            preconditions=[],
            test_steps=[],
            expected_results=[],
            priority=TestCasePriority.MEDIUM,
            category=TestCaseCategory.FUNCTIONAL
        )
        
        metadata = {
            'author': 'Test Author',
            'created_date': '2024-01-01',
            'estimated_duration': '5 minutes'
        }
        
        generator.update_test_case_metadata(test_case, metadata)
        
        assert test_case.metadata == metadata
    
    def test_batch_generate_from_requirements(self, generator, sample_requirements):
        """Test batch generation from multiple requirements."""
        # Mock LLM to return different responses for different requirements
        def mock_generate(prompt, **kwargs):
            if "UR1" in prompt:
                return {
                    'test_cases': [
                        {
                            'name': 'Test login functionality',
                            'description': 'Test user login',
                            'preconditions': ['User exists'],
                            'test_steps': [
                                {'step_number': 1, 'action': 'Login', 'expected_result': 'Success'}
                            ],
                            'expected_results': ['Logged in'],
                            'priority': 'high',
                            'category': 'security'
                        }
                    ]
                }
            else:
                return {
                    'test_cases': [
                        {
                            'name': 'Test credential validation',
                            'description': 'Test system validation',
                            'preconditions': ['Database available'],
                            'test_steps': [
                                {'step_number': 1, 'action': 'Validate', 'expected_result': 'Validated'}
                            ],
                            'expected_results': ['Validation complete'],
                            'priority': 'high',
                            'category': 'security'
                        }
                    ]
                }
        
        generator.llm_backend.generate.side_effect = mock_generate
        
        all_test_cases = generator.batch_generate_from_requirements(sample_requirements)
        
        assert len(all_test_cases) == 2
        assert all_test_cases[0].name == 'Test login functionality'
        assert all_test_cases[1].name == 'Test credential validation'


class TestTestCaseTemplates:
    """Test test case template functionality."""
    
    @pytest.fixture
    def generator(self):
        """Create TestCaseGenerator with mock backend."""
        mock_backend = Mock(spec=LLMBackend)
        return TestCaseGenerator(mock_backend)
    
    def test_load_templates(self, generator):
        """Test loading test case templates."""
        templates = generator.load_templates()
        
        assert isinstance(templates, dict)
        assert len(templates) > 0
        assert RequirementType.USER in templates
        assert RequirementType.SOFTWARE in templates
    
    def test_apply_template_user_requirement(self, generator):
        """Test applying template for user requirement."""
        requirement = Requirement(
            id="UR1",
            text="User shall be able to login",
            type=RequirementType.USER,
            acceptance_criteria=["Valid credentials accepted"]
        )
        
        template_content = generator.apply_template(requirement)
        
        assert 'user' in template_content.lower()
        assert 'login' in template_content.lower()
        assert requirement.id in template_content
    
    def test_apply_template_software_requirement(self, generator):
        """Test applying template for software requirement."""
        requirement = Requirement(
            id="SR1",
            text="System shall validate credentials",
            type=RequirementType.SOFTWARE,
            acceptance_criteria=["Database validation performed"]
        )
        
        template_content = generator.apply_template(requirement)
        
        assert 'system' in template_content.lower()
        assert 'validate' in template_content.lower()
        assert requirement.id in template_content
    
    def test_customize_template(self, generator):
        """Test customizing template with specific parameters."""
        template_params = {
            'test_type': 'integration',
            'complexity': 'high',
            'automation_level': 'full'
        }
        
        customized = generator.customize_template(RequirementType.USER, template_params)
        
        assert 'integration' in customized.lower()
        assert 'high' in customized.lower()
        assert 'full' in customized.lower()


class TestTestCaseExport:
    """Test test case export functionality."""
    
    @pytest.fixture
    def generator(self):
        """Create TestCaseGenerator with mock backend."""
        mock_backend = Mock(spec=LLMBackend)
        return TestCaseGenerator(mock_backend)
    
    @pytest.fixture
    def sample_test_cases(self):
        """Create sample test cases for export testing."""
        return [
            TestCase(
                id="TC1",
                name="Test login",
                description="Test user login functionality",
                requirement_id="UR1",
                preconditions=["User account exists"],
                test_steps=[
                    TestStep(1, "Enter username", "Username accepted"),
                    TestStep(2, "Enter password", "Password accepted"),
                    TestStep(3, "Click login", "User logged in")
                ],
                expected_results=["Dashboard displayed"],
                priority=TestCasePriority.HIGH,
                category=TestCaseCategory.SECURITY
            ),
            TestCase(
                id="TC2",
                name="Test logout",
                description="Test user logout functionality",
                requirement_id="UR2",
                preconditions=["User is logged in"],
                test_steps=[
                    TestStep(1, "Click logout", "User logged out")
                ],
                expected_results=["Login page displayed"],
                priority=TestCasePriority.MEDIUM,
                category=TestCaseCategory.SECURITY
            )
        ]
    
    def test_export_json_format(self, generator, sample_test_cases):
        """Test JSON export format validation."""
        json_export = generator.export_test_cases(sample_test_cases, 'json')
        
        import json
        parsed = json.loads(json_export)
        
        assert 'test_cases' in parsed
        assert len(parsed['test_cases']) == 2
        assert parsed['test_cases'][0]['name'] == 'Test login'
        assert len(parsed['test_cases'][0]['test_steps']) == 3
    
    def test_export_xml_format_validation(self, generator, sample_test_cases):
        """Test XML export format validation."""
        xml_export = generator.export_test_cases(sample_test_cases, 'xml')
        
        # Basic XML validation
        assert xml_export.startswith('<?xml')
        assert '<testsuites>' in xml_export
        assert '<testsuite' in xml_export
        assert '<testcase' in xml_export
        assert 'Test login' in xml_export
        assert xml_export.endswith('</testsuites>')
    
    def test_export_csv_format_validation(self, generator, sample_test_cases):
        """Test CSV export format validation."""
        csv_export = generator.export_test_cases(sample_test_cases, 'csv')
        
        lines = csv_export.strip().split('\n')
        
        # Check header
        header = lines[0]
        assert 'Test Name' in header
        assert 'Description' in header
        assert 'Priority' in header
        assert 'Category' in header
        
        # Check data rows
        assert len(lines) == 3  # Header + 2 test cases
        assert 'Test login' in lines[1]
        assert 'Test logout' in lines[2]
    
    def test_export_text_format_readability(self, generator, sample_test_cases):
        """Test plain text export readability."""
        text_export = generator.export_test_cases(sample_test_cases, 'text')
        
        # Check structure
        assert 'Test Case: TC1' in text_export
        assert 'Name: Test login' in text_export
        assert 'Description: Test user login functionality' in text_export
        assert 'Steps:' in text_export
        assert '1. Enter username' in text_export
        assert 'Expected Results:' in text_export
        assert 'Dashboard displayed' in text_export
    
    def test_export_with_metadata(self, generator, sample_test_cases):
        """Test export including metadata."""
        # Add metadata to test cases
        sample_test_cases[0].metadata = {
            'author': 'Test Author',
            'created_date': '2024-01-01'
        }
        
        json_export = generator.export_test_cases(sample_test_cases, 'json')
        
        assert 'author' in json_export
        assert 'Test Author' in json_export
        assert 'created_date' in json_export
    
    def test_export_large_dataset(self, generator):
        """Test export performance with large dataset."""
        # Create large number of test cases
        large_test_cases = []
        for i in range(100):
            test_case = TestCase(
                id=f"TC{i}",
                name=f"Test case {i}",
                description=f"Description {i}",
                requirement_id=f"UR{i}",
                preconditions=[f"Precondition {i}"],
                test_steps=[
                    TestStep(1, f"Action {i}", f"Expected {i}")
                ],
                expected_results=[f"Result {i}"],
                priority=TestCasePriority.MEDIUM,
                category=TestCaseCategory.FUNCTIONAL
            )
            large_test_cases.append(test_case)
        
        # Should complete without errors
        json_export = generator.export_test_cases(large_test_cases, 'json')
        csv_export = generator.export_test_cases(large_test_cases, 'csv')
        
        assert len(json_export) > 1000  # Should be substantial
        assert len(csv_export.split('\n')) == 101  # Header + 100 rows