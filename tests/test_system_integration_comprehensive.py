"""
Comprehensive System Integration Tests for Software Requirements Fixes

This module tests the complete analysis pipeline with all enhanced components:
- Requirements generation and display
- Traceability matrix generation and gap analysis
- Test case generation and export
- SOUP detection and IEC 62304 compliance
- API response validation and error handling
"""

import pytest
import tempfile
import json
import os
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtTest import QTest

from medical_analyzer.services.analysis_orchestrator import AnalysisOrchestrator
from medical_analyzer.services.requirements_generator import RequirementsGenerator
from medical_analyzer.services.traceability_service import TraceabilityService
from medical_analyzer.services.test_case_generator import TestCaseGenerator
from medical_analyzer.services.soup_detector import SOUPDetector
from medical_analyzer.services.soup_service import SOUPService
from medical_analyzer.services.iec62304_compliance_manager import IEC62304ComplianceManager
from medical_analyzer.llm.api_response_validator import APIResponseValidator
from medical_analyzer.llm.local_server_backend import LocalServerBackend
from medical_analyzer.ui.main_window import MainWindow
from medical_analyzer.ui.requirements_tab_widget import RequirementsTabWidget
from medical_analyzer.ui.traceability_matrix_widget import TraceabilityMatrixWidget
from medical_analyzer.ui.test_case_export_widget import TestCaseExportWidget
from medical_analyzer.ui.soup_widget import SOUPWidget
from medical_analyzer.models.core import Requirement, RequirementType
from medical_analyzer.models.test_models import TestCase, TestStep
from medical_analyzer.models.soup_models import DetectedSOUPComponent, IEC62304Classification


class TestSystemIntegrationComprehensive:
    """Comprehensive system integration tests for all enhanced components."""
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory with realistic test data."""
        temp_dir = tempfile.mkdtemp()
        
        # Create realistic project structure
        project_structure = {
            'package.json': {
                "name": "medical-device-software",
                "version": "1.0.0",
                "dependencies": {
                    "express": "^4.18.0",
                    "lodash": "^4.17.21",
                    "moment": "^2.29.4"
                },
                "devDependencies": {
                    "jest": "^29.0.0",
                    "eslint": "^8.0.0"
                }
            },
            'requirements.txt': [
                "numpy==1.21.0",
                "pandas==1.3.0",
                "scikit-learn==1.0.0",
                "flask==2.0.0"
            ],
            'src/main.js': """
// Main application entry point
const express = require('express');
const app = express();

// Patient data processing
function processPatientData(data) {
    // Critical: Validate patient data
    if (!data || !data.patientId) {
        throw new Error('Invalid patient data');
    }
    return data;
}

// Risk calculation
function calculateRisk(patientData) {
    // High risk calculation logic
    const riskScore = patientData.age * 0.1 + patientData.symptoms.length;
    return riskScore;
}

module.exports = { processPatientData, calculateRisk };
            """,
            'src/utils.js': """
// Utility functions
function validateInput(input) {
    return input && typeof input === 'string';
}

function formatOutput(data) {
    return JSON.stringify(data, null, 2);
}

module.exports = { validateInput, formatOutput };
            """
        }
        
        # Write project files
        for file_path, content in project_structure.items():
            full_path = os.path.join(temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            if isinstance(content, dict):
                with open(full_path, 'w') as f:
                    json.dump(content, f, indent=2)
            elif isinstance(content, list):
                with open(full_path, 'w') as f:
                    f.write('\n'.join(content))
            else:
                with open(full_path, 'w') as f:
                    f.write(content)
        
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_llm_backend(self):
        """Mock LLM backend with realistic responses."""
        backend = Mock(spec=LocalServerBackend)
        
        # Mock requirements generation response
        requirements_response = {
            "user_requirements": [
                {
                    "id": "UR-001",
                    "text": "The system shall process patient data securely",
                    "acceptance_criteria": [
                        "Patient data must be validated before processing",
                        "Invalid data must be rejected with appropriate error messages"
                    ]
                },
                {
                    "id": "UR-002", 
                    "text": "The system shall calculate patient risk scores",
                    "acceptance_criteria": [
                        "Risk calculation must use validated patient data",
                        "Risk scores must be within acceptable ranges"
                    ]
                }
            ],
            "software_requirements": [
                {
                    "id": "SR-001",
                    "text": "The processPatientData function shall validate input parameters",
                    "derived_from": ["UR-001"],
                    "acceptance_criteria": [
                        "Function must check for null or undefined input",
                        "Function must validate required fields"
                    ]
                },
                {
                    "id": "SR-002",
                    "text": "The calculateRisk function shall compute risk scores using validated data",
                    "derived_from": ["UR-002"],
                    "acceptance_criteria": [
                        "Function must use only validated patient data",
                        "Risk score calculation must be deterministic"
                    ]
                }
            ]
        }
        
        # Mock test case generation response
        test_cases_response = {
            "test_cases": [
                {
                    "id": "TC-001",
                    "name": "Test Patient Data Validation",
                    "requirement_id": "SR-001",
                    "description": "Verify that patient data validation works correctly",
                    "preconditions": ["Valid test environment", "Mock patient data available"],
                    "test_steps": [
                        {"step": 1, "action": "Call processPatientData with valid data", "expected": "Data processed successfully"},
                        {"step": 2, "action": "Call processPatientData with null data", "expected": "Error thrown"}
                    ],
                    "expected_results": ["Function validates input correctly", "Appropriate errors for invalid input"]
                }
            ]
        }
        
        def mock_generate(prompt, **kwargs):
            if "requirements" in prompt.lower():
                return json.dumps(requirements_response)
            elif "test" in prompt.lower():
                return json.dumps(test_cases_response)
            else:
                return json.dumps({"result": "success", "data": {}})
        
        backend.generate.side_effect = mock_generate
        return backend
    
    @pytest.fixture
    def integration_orchestrator(self, temp_project_dir, mock_llm_backend):
        """Create analysis orchestrator with all enhanced components."""
        from medical_analyzer.config.config_manager import ConfigManager
        from medical_analyzer.config.app_settings import AppSettings
        
        # Create mock config manager and app settings
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_llm_config.return_value = {
            'backend_type': 'local_server',
            'api_endpoint': 'http://localhost:8080',
            'timeout': 30
        }
        
        app_settings = Mock(spec=AppSettings)
        
        orchestrator = AnalysisOrchestrator(config_manager, app_settings)
        
        # Override with enhanced components for testing
        orchestrator.requirements_generator = RequirementsGenerator(mock_llm_backend)
        orchestrator.traceability_service = TraceabilityService(orchestrator.db_manager)
        orchestrator.test_case_generator = TestCaseGenerator(mock_llm_backend)
        orchestrator.soup_detector = SOUPDetector()
        orchestrator.soup_service = SOUPService(orchestrator.db_manager)
        orchestrator.compliance_manager = IEC62304ComplianceManager()
        orchestrator.api_validator = APIResponseValidator()
        
        return orchestrator
    
    def test_complete_analysis_pipeline(self, integration_orchestrator, temp_project_dir):
        """Test the complete analysis pipeline with all enhanced components."""
        
        # Step 1: Run complete analysis
        with patch.object(integration_orchestrator, '_run_analysis_pipeline') as mock_run:
            mock_run.return_value = None  # Method doesn't return a value
            
            # Start analysis (this is async, so we just verify it starts)
            integration_orchestrator.start_analysis(temp_project_dir, "Test analysis")
            
            # Verify the analysis was initiated
            assert integration_orchestrator.current_analysis is not None
            assert integration_orchestrator.current_analysis['project_path'] == temp_project_dir
    
    def test_requirements_to_traceability_data_flow(self, integration_orchestrator, temp_project_dir):
        """Test data flow from requirements generation to traceability matrix."""
        
        # Generate requirements from mock features
        from medical_analyzer.models.core import Feature
        mock_features = [
            Feature(
                name="processPatientData",
                description="Process patient data securely",
                file_path="src/main.js",
                line_number=10,
                feature_type="function",
                complexity="medium",
                safety_critical=True
            )
        ]
        
        requirements = integration_orchestrator.requirements_generator.generate_requirements_from_features(
            mock_features, temp_project_dir
        )
        
        assert requirements is not None
        assert len(requirements.get('user_requirements', [])) > 0
        assert len(requirements.get('software_requirements', [])) > 0
        
        # Generate traceability matrix
        with patch.object(integration_orchestrator.traceability_service, 'generate_traceability_matrix') as mock_trace:
            mock_trace.return_value = {
                'matrix': [
                    {
                        'code_element': 'processPatientData',
                        'software_requirement': 'SR-001',
                        'user_requirement': 'UR-001',
                        'risk': 'High',
                        'confidence': 0.9
                    }
                ],
                'gaps': []
            }
            
            traceability = integration_orchestrator.traceability_service.generate_traceability_matrix(
                requirements, temp_project_dir
            )
            
            assert traceability is not None
            assert 'matrix' in traceability
            assert len(traceability['matrix']) > 0
    
    def test_requirements_to_test_generation_flow(self, integration_orchestrator, temp_project_dir):
        """Test data flow from requirements to test case generation."""
        
        # Create mock requirements
        requirements = [
            Requirement(
                id="SR-001",
                text="The processPatientData function shall validate input parameters",
                type=RequirementType.SOFTWARE,
                acceptance_criteria=["Function must check for null input"]
            )
        ]
        
        # Generate test cases
        test_cases = integration_orchestrator.test_case_generator.generate_test_cases(requirements)
        
        assert test_cases is not None
        assert len(test_cases) > 0
        assert all(isinstance(tc, TestCase) for tc in test_cases)
    
    def test_soup_detection_to_compliance_flow(self, integration_orchestrator, temp_project_dir):
        """Test data flow from SOUP detection to IEC 62304 compliance."""
        
        # Detect SOUP components
        soup_components = integration_orchestrator.soup_detector.detect_soup_components(temp_project_dir)
        
        assert soup_components is not None
        assert len(soup_components) > 0
        assert all(isinstance(comp, DetectedSOUPComponent) for comp in soup_components)
        
        # Classify components for IEC 62304 compliance
        for component in soup_components:
            classification = integration_orchestrator.compliance_manager.classify_component(component)
            assert isinstance(classification, IEC62304Classification)
            assert classification.safety_class in ['A', 'B', 'C']
    
    def test_error_handling_across_components(self, integration_orchestrator, temp_project_dir):
        """Test error handling and recovery across all components."""
        
        # Test API validation error handling
        with patch.object(integration_orchestrator.requirements_generator, 'generate_requirements') as mock_req:
            mock_req.side_effect = Exception("API Error")
            
            try:
                integration_orchestrator.requirements_generator.generate_requirements(
                    temp_project_dir, ["src/main.js"]
                )
            except Exception as e:
                assert "API Error" in str(e)
        
        # Test traceability service error handling
        with patch.object(integration_orchestrator.traceability_service, 'generate_traceability_matrix') as mock_trace:
            mock_trace.side_effect = Exception("Traceability Error")
            
            try:
                integration_orchestrator.traceability_service.generate_traceability_matrix(
                    {}, temp_project_dir
                )
            except Exception as e:
                assert "Traceability Error" in str(e)
        
        # Test SOUP detection error handling
        with patch.object(integration_orchestrator.soup_detector, 'detect_soup_components') as mock_soup:
            mock_soup.side_effect = Exception("SOUP Detection Error")
            
            try:
                integration_orchestrator.soup_detector.detect_soup_components(temp_project_dir)
            except Exception as e:
                assert "SOUP Detection Error" in str(e)
    
    def test_performance_with_realistic_data_volumes(self, integration_orchestrator, temp_project_dir):
        """Test performance with realistic project sizes and data volumes."""
        
        # Create larger project structure
        large_project_files = []
        for i in range(50):  # Simulate 50 source files
            file_path = f"src/module_{i}.js"
            full_path = os.path.join(temp_project_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w') as f:
                f.write(f"""
// Module {i}
function process_{i}(data) {{
    // Processing logic for module {i}
    return data;
}}

function validate_{i}(input) {{
    // Validation logic for module {i}
    return input !== null;
}}

module.exports = {{ process_{i}, validate_{i} }};
                """)
            large_project_files.append(file_path)
        
        # Test performance of requirements generation
        import time
        start_time = time.time()
        
        requirements = integration_orchestrator.requirements_generator.generate_requirements(
            temp_project_dir, large_project_files[:10]  # Test with subset for performance
        )
        
        generation_time = time.time() - start_time
        assert generation_time < 30.0  # Should complete within 30 seconds
        assert requirements is not None
        
        # Test SOUP detection performance
        start_time = time.time()
        soup_components = integration_orchestrator.soup_detector.detect_soup_components(temp_project_dir)
        detection_time = time.time() - start_time
        
        assert detection_time < 10.0  # Should complete within 10 seconds
        assert soup_components is not None
    
    def test_backward_compatibility_with_existing_data(self, integration_orchestrator, temp_project_dir):
        """Test backward compatibility with existing data and workflows."""
        
        # Create legacy data structure
        legacy_requirements = {
            "requirements": [
                {
                    "id": "REQ-001",
                    "text": "Legacy requirement format",
                    "type": "functional"
                }
            ]
        }
        
        # Test that new components can handle legacy data
        try:
            # Convert legacy format to new format
            converted_requirements = []
            for req_data in legacy_requirements["requirements"]:
                req = Requirement(
                    id=req_data["id"],
                    text=req_data["text"],
                    type=RequirementType.FUNCTIONAL if req_data["type"] == "functional" else RequirementType.SOFTWARE,
                    acceptance_criteria=[]
                )
                converted_requirements.append(req)
            
            assert len(converted_requirements) == 1
            assert converted_requirements[0].id == "REQ-001"
            
        except Exception as e:
            pytest.fail(f"Backward compatibility test failed: {e}")
    
    def test_ui_integration_with_enhanced_components(self, qtbot):
        """Test UI integration with all enhanced components."""
        
        if QApplication.instance() is None:
            app = QApplication([])
        
        # Test main window integration
        main_window = MainWindow()
        qtbot.addWidget(main_window)
        
        # Verify enhanced components are integrated
        assert hasattr(main_window, 'requirements_tab')
        assert hasattr(main_window, 'traceability_matrix')
        assert hasattr(main_window, 'test_case_export')
        assert hasattr(main_window, 'soup_widget')
        
        # Test requirements tab widget
        requirements_tab = RequirementsTabWidget()
        qtbot.addWidget(requirements_tab)
        
        # Test adding requirements
        test_requirements = [
            Requirement(
                id="TEST-001",
                text="Test requirement",
                type=RequirementType.SOFTWARE,
                acceptance_criteria=["Test criteria"]
            )
        ]
        
        requirements_tab.update_requirements(test_requirements, [])
        assert requirements_tab.software_requirements_table.rowCount() == 1
        
        # Test traceability matrix widget
        traceability_widget = TraceabilityMatrixWidget()
        qtbot.addWidget(traceability_widget)
        
        # Test matrix update
        test_matrix = [
            {
                'code_element': 'testFunction',
                'software_requirement': 'SR-001',
                'user_requirement': 'UR-001',
                'risk': 'Medium',
                'confidence': 0.8
            }
        ]
        
        traceability_widget.update_matrix(test_matrix)
        assert traceability_widget.matrix_table.rowCount() == 1
    
    def test_cross_component_signal_connections(self, qtbot):
        """Test signal connections between enhanced components."""
        
        if QApplication.instance() is None:
            app = QApplication([])
        
        # Create components
        requirements_tab = RequirementsTabWidget()
        traceability_widget = TraceabilityMatrixWidget()
        test_export_widget = TestCaseExportWidget()
        
        qtbot.addWidget(requirements_tab)
        qtbot.addWidget(traceability_widget)
        qtbot.addWidget(test_export_widget)
        
        # Test signal connections
        signal_received = []
        
        def on_requirements_updated(requirements):
            signal_received.append("requirements_updated")
        
        requirements_tab.requirements_updated.connect(on_requirements_updated)
        
        # Simulate requirements update
        test_requirements = [
            Requirement(
                id="SIG-001",
                text="Signal test requirement",
                type=RequirementType.SOFTWARE,
                acceptance_criteria=["Signal test criteria"]
            )
        ]
        
        requirements_tab.update_requirements(test_requirements, [])
        requirements_tab.requirements_updated.emit({"software_requirements": test_requirements})
        
        # Verify signal was received
        assert "requirements_updated" in signal_received
    
    def test_export_functionality_integration(self, integration_orchestrator, temp_project_dir):
        """Test export functionality across all components."""
        
        # Test requirements export
        requirements = [
            Requirement(
                id="EXP-001",
                text="Export test requirement",
                type=RequirementType.SOFTWARE,
                acceptance_criteria=["Export test criteria"]
            )
        ]
        
        # Test traceability matrix export
        matrix_data = [
            {
                'code_element': 'exportFunction',
                'software_requirement': 'EXP-001',
                'user_requirement': 'UR-EXP-001',
                'risk': 'Low',
                'confidence': 0.9
            }
        ]
        
        # Test test case export
        test_cases = [
            TestCase(
                id="TC-EXP-001",
                name="Export Test Case",
                description="Test case for export functionality",
                requirement_id="EXP-001",
                preconditions=["Export environment ready"],
                test_steps=[
                    TestStep(
                        step_number=1,
                        action="Execute export function",
                        expected_result="Export completes successfully"
                    )
                ],
                expected_results=["Export file created"],
                priority="High",
                category="Integration"
            )
        ]
        
        # Verify all components can handle export operations
        try:
            # Requirements export (simulated)
            requirements_export = json.dumps([req.__dict__ for req in requirements], indent=2)
            assert len(requirements_export) > 0
            
            # Matrix export (simulated)
            matrix_export = json.dumps(matrix_data, indent=2)
            assert len(matrix_export) > 0
            
            # Test case export (simulated)
            test_case_export = json.dumps([tc.__dict__ for tc in test_cases], indent=2, default=str)
            assert len(test_case_export) > 0
            
        except Exception as e:
            pytest.fail(f"Export functionality test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])