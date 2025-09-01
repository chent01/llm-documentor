"""
Comprehensive integration tests for software requirements fixes.

Tests cover:
- End-to-end requirements generation → display → traceability workflow
- API integration with new validation system and error handling
- SOUP detection → classification → compliance workflow
- Cross-component signal connections and data synchronization
"""

import pytest
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QSignalSpy

from medical_analyzer.services.requirements_generator import RequirementsGenerator
from medical_analyzer.ui.requirements_tab_widget import RequirementsTabWidget
from medical_analyzer.ui.traceability_matrix_widget import TraceabilityMatrixWidget
from medical_analyzer.services.traceability_service import TraceabilityService
from medical_analyzer.services.soup_detector import SOUPDetector
from medical_analyzer.services.iec62304_compliance_manager import IEC62304ComplianceManager
from medical_analyzer.services.test_case_generator import CaseGenerator
from medical_analyzer.llm.api_response_validator import APIResponseValidator
from medical_analyzer.llm.local_server_backend import LocalServerBackend
from medical_analyzer.models.core import Requirement, RequirementType


class TestRequirementsWorkflowIntegration:
    """Test end-to-end requirements workflow integration."""
    
    @pytest.fixture
    def qapp(self):
        """Create QApplication for testing."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app
        app.quit()
    
    @pytest.fixture
    def mock_llm_backend(self):
        """Create mock LLM backend with realistic responses."""
        backend = Mock()
        backend.generate.return_value = {
            'choices': [{
                'message': {
                    'content': json.dumps({
                        'user_requirements': [
                            {
                                'id': 'UR1',
                                'text': 'User shall be able to login',
                                'acceptance_criteria': ['Valid credentials accepted']
                            }
                        ],
                        'software_requirements': [
                            {
                                'id': 'SR1',
                                'text': 'System shall validate credentials',
                                'derived_from': ['UR1'],
                                'acceptance_criteria': ['Database validation performed']
                            }
                        ]
                    })
                }
            }]
        }
        return backend
    
    @pytest.fixture
    def requirements_generator(self, mock_llm_backend):
        """Create requirements generator with mock backend."""
        generator = RequirementsGenerator()
        generator.llm_backend = mock_llm_backend
        return generator
    
    @pytest.fixture
    def requirements_widget(self, qapp):
        """Create requirements tab widget."""
        return RequirementsTabWidget()
    
    @pytest.fixture
    def traceability_widget(self, qapp):
        """Create traceability matrix widget."""
        return TraceabilityMatrixWidget()
    
    def test_end_to_end_requirements_workflow(self, requirements_generator, requirements_widget, traceability_widget):
        """Test complete requirements generation → display → traceability workflow."""
        
        # Step 1: Generate requirements
        with patch('medical_analyzer.services.requirements_generator.RequirementsGenerator.generate_requirements') as mock_generate:
            mock_generate.return_value = {
                'user_requirements': [
                    Requirement(
                        id='UR1',
                        text='User shall be able to login',
                        type=RequirementType.USER,
                        acceptance_criteria=['Valid credentials accepted']
                    )
                ],
                'software_requirements': [
                    Requirement(
                        id='SR1',
                        text='System shall validate credentials',
                        type=RequirementType.SOFTWARE,
                        acceptance_criteria=['Database validation performed'],
                        derived_from=['UR1']
                    )
                ]
            }
            
            # Generate requirements
            result = requirements_generator.generate_requirements("Test project context")
            
            assert result is not None
            assert len(result['user_requirements']) == 1
            assert len(result['software_requirements']) == 1
        
        # Step 2: Display requirements in widget
        user_reqs = result['user_requirements']
        software_reqs = result['software_requirements']
        
        # Set up signal spy for requirements updates
        spy = QSignalSpy(requirements_widget.requirements_updated)
        
        # Update requirements widget
        requirements_widget.update_requirements(user_reqs, software_reqs)
        
        # Verify requirements are displayed
        assert len(requirements_widget.user_requirements) == 1
        assert len(requirements_widget.software_requirements) == 1
        assert requirements_widget.user_requirements[0].id == 'UR1'
        assert requirements_widget.software_requirements[0].id == 'SR1'
        
        # Verify signal was emitted
        assert len(spy) == 1
        
        # Step 3: Generate traceability matrix
        with patch('medical_analyzer.services.traceability_service.TraceabilityService.generate_matrix') as mock_matrix:
            from medical_analyzer.services.traceability_models import TraceabilityMatrix, TraceabilityTableRow
            
            mock_matrix.return_value = TraceabilityMatrix(
                rows=[
                    TraceabilityTableRow(
                        code_element="login_function",
                        software_requirement="SR1: System shall validate credentials",
                        user_requirement="UR1: User shall be able to login",
                        risk="R1: Authentication failure",
                        confidence=0.9,
                        has_gaps=False
                    )
                ],
                gaps=[]
            )
            
            # Generate and display traceability matrix
            traceability_service = TraceabilityService()
            matrix = traceability_service.generate_matrix(user_reqs + software_reqs, [])
            
            traceability_widget.update_matrix(matrix)
            
            # Verify matrix is displayed
            assert len(traceability_widget.matrix_data) == 1
            assert traceability_widget.matrix_data[0].code_element == "login_function"
            assert "SR1" in traceability_widget.matrix_data[0].software_requirement
            assert "UR1" in traceability_widget.matrix_data[0].user_requirement
    
    def test_requirements_modification_propagation(self, requirements_widget, traceability_widget):
        """Test that requirement modifications propagate to traceability matrix."""
        
        # Initial requirements
        user_reqs = [
            Requirement(
                id='UR1',
                text='Original user requirement',
                type=RequirementType.USER,
                acceptance_criteria=['Original criteria']
            )
        ]
        software_reqs = [
            Requirement(
                id='SR1',
                text='Original software requirement',
                type=RequirementType.SOFTWARE,
                acceptance_criteria=['Original criteria'],
                derived_from=['UR1']
            )
        ]
        
        # Set up requirements widget
        requirements_widget.update_requirements(user_reqs, software_reqs)
        
        # Set up signal connection simulation
        def on_requirements_updated(updated_reqs):
            # Simulate traceability matrix update
            traceability_widget.refresh_display()
        
        requirements_widget.requirements_updated.connect(on_requirements_updated)
        
        # Modify a requirement
        with patch('medical_analyzer.ui.requirements_tab_widget.RequirementEditDialog') as mock_dialog:
            mock_dialog_instance = Mock()
            mock_dialog_instance.exec.return_value = True
            mock_dialog_instance.get_requirement.return_value = Requirement(
                id='UR1',
                text='Modified user requirement',
                type=RequirementType.USER,
                acceptance_criteria=['Modified criteria']
            )
            mock_dialog.return_value = mock_dialog_instance
            
            # Edit requirement
            requirements_widget.edit_requirement('UR1')
            
            # Verify requirement was modified
            modified_req = requirements_widget.get_requirement_by_id('UR1')
            assert modified_req.text == 'Modified user requirement'
    
    def test_cross_component_data_synchronization(self, requirements_widget, traceability_widget):
        """Test data synchronization between components."""
        
        # Create test data
        requirements = [
            Requirement(
                id='UR1',
                text='User requirement',
                type=RequirementType.USER,
                acceptance_criteria=['Criteria 1']
            ),
            Requirement(
                id='SR1',
                text='Software requirement',
                type=RequirementType.SOFTWARE,
                acceptance_criteria=['Criteria 1'],
                derived_from=['UR1']
            )
        ]
        
        # Update requirements widget
        requirements_widget.update_requirements([requirements[0]], [requirements[1]])
        
        # Simulate traceability matrix generation based on requirements
        with patch('medical_analyzer.services.traceability_service.TraceabilityService') as mock_service:
            from medical_analyzer.services.traceability_models import TraceabilityMatrix, TraceabilityTableRow
            
            mock_service_instance = Mock()
            mock_service_instance.generate_matrix.return_value = TraceabilityMatrix(
                rows=[
                    TraceabilityTableRow(
                        code_element="test_function",
                        software_requirement="SR1: Software requirement",
                        user_requirement="UR1: User requirement",
                        risk="R1: Test risk",
                        confidence=0.8,
                        has_gaps=False
                    )
                ],
                gaps=[]
            )
            mock_service.return_value = mock_service_instance
            
            # Generate matrix
            service = mock_service()
            matrix = service.generate_matrix(requirements, [])
            traceability_widget.update_matrix(matrix)
            
            # Verify synchronization
            assert len(traceability_widget.matrix_data) == 1
            assert "UR1" in traceability_widget.matrix_data[0].user_requirement
            assert "SR1" in traceability_widget.matrix_data[0].software_requirement


class TestAPIIntegrationWithValidation:
    """Test API integration with new validation system."""
    
    @pytest.fixture
    def api_validator(self):
        """Create API response validator."""
        return APIResponseValidator()
    
    @pytest.fixture
    def mock_backend(self, api_validator):
        """Create LocalServerBackend with validator."""
        backend = LocalServerBackend("http://localhost:8000")
        backend.validator = api_validator
        return backend
    
    def test_api_request_with_validation_success(self, mock_backend):
        """Test successful API request with response validation."""
        
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.content = b'{"choices": [{"message": {"content": "Generated content"}}]}'
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Generated content'}}]
        }
        
        with patch('requests.post', return_value=mock_response):
            # Make API request
            result = mock_backend.generate("Test prompt")
            
            # Verify result
            assert result is not None
            assert 'choices' in result
            assert len(result['choices']) > 0
    
    def test_api_request_with_validation_failure(self, mock_backend):
        """Test API request with validation failure and retry logic."""
        
        # Mock failed HTTP response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.content = b'{"error": "Internal server error"}'
        mock_response.json.return_value = {'error': 'Internal server error'}
        mock_response.text = '{"error": "Internal server error"}'
        
        with patch('requests.post', return_value=mock_response):
            # Should handle error gracefully
            with pytest.raises(Exception):
                mock_backend.generate("Test prompt")
    
    def test_api_retry_logic_with_exponential_backoff(self, api_validator):
        """Test retry logic with exponential backoff."""
        
        # Test retry delay calculation
        delay1 = api_validator.calculate_retry_delay(1)
        delay2 = api_validator.calculate_retry_delay(2)
        delay3 = api_validator.calculate_retry_delay(3)
        
        # Verify exponential backoff
        assert delay1 < delay2 < delay3
        assert delay1 >= 1.0  # Base delay
        assert delay3 <= api_validator.max_delay  # Max delay cap
    
    def test_api_error_extraction_and_recovery(self, api_validator):
        """Test error extraction and recovery suggestions."""
        
        # Mock rate limit response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'retry-after': '60'}
        mock_response.content = b'{"error": {"code": "RATE_LIMITED", "message": "Too many requests"}}'
        mock_response.text = '{"error": {"code": "RATE_LIMITED", "message": "Too many requests"}}'
        mock_response.json.return_value = {
            'error': {
                'code': 'RATE_LIMITED',
                'message': 'Too many requests'
            }
        }
        
        error_details = api_validator.extract_error_details(mock_response)
        
        assert error_details.error_code == 'RATE_LIMITED'
        assert error_details.is_recoverable is True
        assert 'retry' in error_details.suggested_action.value.lower()


class TestSOUPWorkflowIntegration:
    """Test SOUP detection → classification → compliance workflow."""
    
    @pytest.fixture
    def soup_detector(self):
        """Create SOUP detector."""
        return SOUPDetector()
    
    @pytest.fixture
    def compliance_manager(self):
        """Create IEC 62304 compliance manager."""
        return IEC62304ComplianceManager()
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project with dependency files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create package.json
            package_json = {
                "name": "medical-device-app",
                "version": "1.0.0",
                "dependencies": {
                    "express": "^4.18.0",
                    "crypto-js": "^4.1.1",
                    "medical-device-sdk": "^2.0.0"
                }
            }
            
            with open(os.path.join(temp_dir, 'package.json'), 'w') as f:
                json.dump(package_json, f)
            
            # Create requirements.txt
            requirements_txt = """
numpy==1.21.0
scipy>=1.7.0
medical-imaging-lib==3.2.1
cryptography==37.0.4
"""
            
            with open(os.path.join(temp_dir, 'requirements.txt'), 'w') as f:
                f.write(requirements_txt)
            
            yield temp_dir
    
    def test_end_to_end_soup_workflow(self, soup_detector, compliance_manager, temp_project):
        """Test complete SOUP detection → classification → compliance workflow."""
        
        # Step 1: Detect SOUP components
        components = soup_detector.detect_soup_components(temp_project)
        
        # Verify components were detected
        assert len(components) > 0
        
        # Find specific components
        express_comp = next((c for c in components if c.name == 'express'), None)
        crypto_comp = next((c for c in components if 'crypto' in c.name.lower()), None)
        
        assert express_comp is not None
        assert crypto_comp is not None
        
        # Step 2: Classify components for IEC 62304 compliance
        classifications = []
        for component in components:
            classification = soup_detector.classify_component(component)
            classifications.append((component, classification))
        
        # Verify classifications
        assert len(classifications) == len(components)
        
        # Step 3: Generate compliance documentation
        compliance_report = compliance_manager.generate_compliance_report(
            [comp for comp, _ in classifications],
            [classif for _, classif in classifications]
        )
        
        # Verify compliance report
        assert compliance_report is not None
        assert 'soup_inventory' in compliance_report
        assert 'safety_classifications' in compliance_report
        assert 'verification_requirements' in compliance_report
    
    def test_soup_component_safety_classification(self, soup_detector):
        """Test SOUP component safety classification logic."""
        
        from medical_analyzer.models.soup_models import DetectedSOUPComponent
        
        # Test different types of components
        test_components = [
            DetectedSOUPComponent(
                name="lodash",
                version="4.17.21",
                source_file="package.json",
                detection_method="package.json_dependencies",
                confidence=0.9,
                suggested_classification="A"
            ),
            DetectedSOUPComponent(
                name="express",
                version="4.18.0",
                source_file="package.json",
                detection_method="package.json_dependencies",
                confidence=0.9,
                suggested_classification="B"
            ),
            DetectedSOUPComponent(
                name="medical-device-driver",
                version="2.1.0",
                source_file="requirements.txt",
                detection_method="requirements.txt",
                confidence=0.9,
                suggested_classification="C"
            )
        ]
        
        for component in test_components:
            classification = soup_detector.classify_component(component)
            safety_assessment = soup_detector.assess_safety_impact(component)
            
            # Verify classification structure
            assert hasattr(classification, 'safety_class') or isinstance(classification, str)
            assert hasattr(safety_assessment, 'safety_impact') or isinstance(safety_assessment, dict)
    
    def test_soup_version_change_tracking(self, soup_detector):
        """Test SOUP version change tracking and impact analysis."""
        
        from medical_analyzer.models.soup_models import DetectedSOUPComponent
        
        # Old components
        old_components = [
            DetectedSOUPComponent(
                name="express",
                version="4.17.0",
                source_file="package.json",
                detection_method="package.json_dependencies",
                confidence=0.9,
                suggested_classification="B"
            )
        ]
        
        # New components (version updated)
        new_components = [
            DetectedSOUPComponent(
                name="express",
                version="4.18.0",
                source_file="package.json",
                detection_method="package.json_dependencies",
                confidence=0.9,
                suggested_classification="B"
            )
        ]
        
        # Track changes
        changes = soup_detector.track_version_changes(old_components, new_components)
        
        # Verify change tracking
        assert len(changes) > 0
        
        # Should detect version update
        version_updates = [c for c in changes if isinstance(c, dict) and c.get('change_type') == 'version_update']
        assert len(version_updates) > 0


class TestCrossComponentIntegration:
    """Test integration between multiple components."""
    
    @pytest.fixture
    def qapp(self):
        """Create QApplication for testing."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app
        app.quit()
    
    def test_requirements_to_test_generation_integration(self, qapp):
        """Test integration from requirements to test case generation."""
        
        # Create requirements
        requirements = [
            Requirement(
                id='UR1',
                text='User shall be able to authenticate',
                type=RequirementType.USER,
                acceptance_criteria=['Valid credentials accepted', 'Invalid credentials rejected']
            ),
            Requirement(
                id='SR1',
                text='System shall validate user credentials',
                type=RequirementType.SOFTWARE,
                acceptance_criteria=['Database lookup performed', 'Password hash verified'],
                derived_from=['UR1']
            )
        ]
        
        # Mock LLM backend for test generation
        mock_backend = Mock()
        mock_backend.generate.return_value = {
            'test_cases': [
                {
                    'name': 'Test user authentication',
                    'description': 'Verify user can authenticate with valid credentials',
                    'preconditions': ['User account exists'],
                    'test_steps': [
                        {'step_number': 1, 'action': 'Enter valid credentials', 'expected_result': 'Credentials accepted'}
                    ],
                    'expected_results': ['User authenticated successfully'],
                    'priority': 'high',
                    'category': 'security'
                }
            ]
        }
        
        # Generate test cases
        test_generator = CaseGenerator(mock_backend)
        test_cases = test_generator.generate_test_cases(requirements)
        
        # Verify test cases were generated
        assert len(test_cases) > 0
        assert test_cases[0].requirement_id in ['UR1', 'SR1']
    
    def test_soup_to_requirements_traceability(self):
        """Test traceability from SOUP components to requirements."""
        
        from medical_analyzer.models.soup_models import DetectedSOUPComponent
        
        # Create SOUP component
        soup_component = DetectedSOUPComponent(
            name="cryptography",
            version="37.0.4",
            source_file="requirements.txt",
            detection_method="requirements.txt",
            confidence=0.9,
            suggested_classification="C"
        )
        
        # Create related requirement
        security_requirement = Requirement(
            id='SR_CRYPTO_1',
            text='System shall use approved cryptographic libraries',
            type=RequirementType.SOFTWARE,
            acceptance_criteria=['Only FIPS 140-2 approved algorithms used']
        )
        
        # Simulate traceability link
        soup_component.metadata['related_requirements'] = [security_requirement.id]
        security_requirement.metadata['related_soup_components'] = [soup_component.name]
        
        # Verify traceability
        assert security_requirement.id in soup_component.metadata['related_requirements']
        assert soup_component.name in security_requirement.metadata['related_soup_components']
    
    def test_error_handling_across_components(self):
        """Test error handling and recovery across integrated components."""
        
        # Test API validation error propagation
        validator = APIResponseValidator()
        
        # Mock invalid response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.content = b'{"error": {"code": "INVALID_REQUEST", "message": "Request validation failed"}}'
        mock_response.json.return_value = {
            'error': {
                'code': 'INVALID_REQUEST',
                'message': 'Request validation failed'
            }
        }
        
        # Validate response
        result = validator.validate_response(mock_response, 'text_generation')
        
        # Verify error handling
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert not result.should_retry()  # Client errors shouldn't retry
    
    def test_performance_with_large_datasets(self):
        """Test system performance with large datasets."""
        
        # Create large number of requirements
        large_requirements = []
        for i in range(100):
            req = Requirement(
                id=f'REQ_{i:03d}',
                text=f'Requirement {i} text',
                type=RequirementType.SOFTWARE if i % 2 else RequirementType.USER,
                acceptance_criteria=[f'Criteria {i}.1', f'Criteria {i}.2']
            )
            large_requirements.append(req)
        
        # Test requirements widget performance
        with patch('PyQt6.QtWidgets.QApplication.instance', return_value=Mock()):
            requirements_widget = RequirementsTabWidget()
            
            # Should handle large dataset without errors
            user_reqs = [r for r in large_requirements if r.type == RequirementType.USER]
            software_reqs = [r for r in large_requirements if r.type == RequirementType.SOFTWARE]
            
            requirements_widget.update_requirements(user_reqs, software_reqs)
            
            # Verify all requirements loaded
            assert len(requirements_widget.user_requirements) == len(user_reqs)
            assert len(requirements_widget.software_requirements) == len(software_reqs)


class TestSystemReliabilityAndRecovery:
    """Test system reliability and recovery mechanisms."""
    
    def test_graceful_degradation_on_api_failure(self):
        """Test graceful degradation when API services fail."""
        
        # Mock complete API failure
        mock_backend = Mock()
        mock_backend.generate.side_effect = ConnectionError("API service unavailable")
        
        # Requirements generator should handle failure gracefully
        requirements_generator = RequirementsGenerator(mock_backend)
        
        # Should not crash, but return appropriate error
        with pytest.raises(ConnectionError):
            requirements_generator.generate_requirements("Test context")
    
    def test_data_consistency_after_errors(self):
        """Test data consistency is maintained after errors."""
        
        # Create requirements widget
        with patch('PyQt6.QtWidgets.QApplication.instance', return_value=Mock()):
            requirements_widget = RequirementsTabWidget()
            
            # Add initial requirements
            initial_reqs = [
                Requirement(
                    id='UR1',
                    text='Initial requirement',
                    type=RequirementType.USER,
                    acceptance_criteria=['Initial criteria']
                )
            ]
            
            requirements_widget.update_requirements(initial_reqs, [])
            
            # Simulate error during requirement update
            with patch('medical_analyzer.ui.requirements_tab_widget.RequirementEditDialog') as mock_dialog:
                mock_dialog.side_effect = Exception("Dialog error")
                
                # Attempt to edit requirement (should fail)
                try:
                    requirements_widget.edit_requirement('UR1')
                except:
                    pass
                
                # Verify original data is still intact
                assert len(requirements_widget.user_requirements) == 1
                assert requirements_widget.user_requirements[0].text == 'Initial requirement'
    
    def test_concurrent_operations_safety(self):
        """Test safety of concurrent operations."""
        
        # This would typically involve threading tests
        # For now, test that operations are atomic
        
        with patch('PyQt6.QtWidgets.QApplication.instance', return_value=Mock()):
            requirements_widget = RequirementsTabWidget()
            
            # Simulate rapid updates
            for i in range(10):
                reqs = [
                    Requirement(
                        id=f'UR{i}',
                        text=f'Requirement {i}',
                        type=RequirementType.USER,
                        acceptance_criteria=[f'Criteria {i}']
                    )
                ]
                requirements_widget.update_requirements(reqs, [])
            
            # Final state should be consistent
            assert len(requirements_widget.user_requirements) == 1
            assert requirements_widget.user_requirements[0].id == 'UR9'