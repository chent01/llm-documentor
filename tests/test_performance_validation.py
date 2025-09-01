"""
Performance Validation Tests for Enhanced Medical Analyzer

This module tests system performance with realistic project sizes and data volumes
to ensure the enhanced components can handle production workloads.
"""

import pytest
import tempfile
import json
import os
import shutil
import time
import psutil
import threading
from pathlib import Path
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed

from medical_analyzer.services.analysis_orchestrator import AnalysisOrchestrator
from medical_analyzer.services.requirements_generator import RequirementsGenerator
from medical_analyzer.services.traceability_service import TraceabilityService
from medical_analyzer.services.test_case_generator import TestCaseGenerator
from medical_analyzer.services.soup_detector import SOUPDetector
from medical_analyzer.services.soup_service import SOUPService
from medical_analyzer.llm.api_response_validator import APIResponseValidator
from medical_analyzer.models.core import Requirement, RequirementType


class TestPerformanceValidation:
    """Performance validation tests for enhanced system components."""
    
    @pytest.fixture
    def large_project_structure(self):
        """Create a large, realistic project structure for performance testing."""
        temp_dir = tempfile.mkdtemp()
        
        # Create package.json with many dependencies
        package_json = {
            "name": "large-medical-device-software",
            "version": "2.1.0",
            "dependencies": {
                "express": "^4.18.0",
                "lodash": "^4.17.21",
                "moment": "^2.29.4",
                "axios": "^1.0.0",
                "react": "^18.0.0",
                "react-dom": "^18.0.0",
                "redux": "^4.2.0",
                "socket.io": "^4.5.0",
                "bcrypt": "^5.0.0",
                "jsonwebtoken": "^8.5.0",
                "mongoose": "^6.5.0",
                "winston": "^3.8.0",
                "helmet": "^6.0.0",
                "cors": "^2.8.0",
                "dotenv": "^16.0.0"
            },
            "devDependencies": {
                "jest": "^29.0.0",
                "eslint": "^8.0.0",
                "webpack": "^5.74.0",
                "babel-core": "^6.26.0",
                "typescript": "^4.8.0",
                "@types/node": "^18.0.0",
                "nodemon": "^2.0.0",
                "prettier": "^2.7.0"
            }
        }
        
        # Create requirements.txt with many Python dependencies
        requirements_txt = [
            "numpy==1.21.0",
            "pandas==1.3.0",
            "scikit-learn==1.0.0",
            "flask==2.0.0",
            "django==4.1.0",
            "fastapi==0.85.0",
            "sqlalchemy==1.4.0",
            "alembic==1.8.0",
            "celery==5.2.0",
            "redis==4.3.0",
            "pytest==7.1.0",
            "pytest-cov==3.0.0",
            "black==22.6.0",
            "flake8==5.0.0",
            "mypy==0.971",
            "requests==2.28.0",
            "beautifulsoup4==4.11.0",
            "selenium==4.4.0",
            "matplotlib==3.5.0",
            "seaborn==0.11.0"
        ]
        
        # Write dependency files
        with open(os.path.join(temp_dir, 'package.json'), 'w') as f:
            json.dump(package_json, f, indent=2)
        
        with open(os.path.join(temp_dir, 'requirements.txt'), 'w') as f:
            f.write('\n'.join(requirements_txt))
        
        # Create many source files
        for i in range(100):  # 100 JavaScript files
            file_content = f"""
// Module {i} - Medical Device Component
const express = require('express');
const {{ validateInput, processData }} = require('./utils');

/**
 * Patient data processor for module {i}
 * Critical safety function - handles patient medical data
 */
class PatientProcessor{i} {{
    constructor() {{
        this.processingQueue = [];
        this.errorLog = [];
    }}
    
    /**
     * Process patient medical data
     * @param {{Object}} patientData - Patient medical information
     * @returns {{Object}} Processed patient data
     */
    processPatientData(patientData) {{
        // Critical: Validate patient data before processing
        if (!patientData || !patientData.patientId) {{
            throw new Error('Invalid patient data - missing patient ID');
        }}
        
        if (!patientData.medicalHistory) {{
            throw new Error('Invalid patient data - missing medical history');
        }}
        
        // Process vital signs
        const vitalSigns = this.processVitalSigns(patientData.vitalSigns);
        
        // Calculate risk assessment
        const riskScore = this.calculateRiskScore(patientData);
        
        // Generate treatment recommendations
        const recommendations = this.generateRecommendations(patientData, riskScore);
        
        return {{
            patientId: patientData.patientId,
            processedAt: new Date().toISOString(),
            vitalSigns: vitalSigns,
            riskScore: riskScore,
            recommendations: recommendations,
            processorModule: {i}
        }};
    }}
    
    /**
     * Process vital signs data
     * @param {{Object}} vitalSigns - Patient vital signs
     * @returns {{Object}} Processed vital signs
     */
    processVitalSigns(vitalSigns) {{
        if (!vitalSigns) {{
            return {{ error: 'No vital signs data provided' }};
        }}
        
        const processed = {{
            heartRate: this.validateHeartRate(vitalSigns.heartRate),
            bloodPressure: this.validateBloodPressure(vitalSigns.bloodPressure),
            temperature: this.validateTemperature(vitalSigns.temperature),
            oxygenSaturation: this.validateOxygenSaturation(vitalSigns.oxygenSaturation)
        }};
        
        return processed;
    }}
    
    /**
     * Calculate patient risk score
     * @param {{Object}} patientData - Complete patient data
     * @returns {{number}} Risk score (0-100)
     */
    calculateRiskScore(patientData) {{
        let riskScore = 0;
        
        // Age factor
        if (patientData.age > 65) {{
            riskScore += 20;
        }} else if (patientData.age > 45) {{
            riskScore += 10;
        }}
        
        // Medical history factor
        if (patientData.medicalHistory.chronicConditions) {{
            riskScore += patientData.medicalHistory.chronicConditions.length * 5;
        }}
        
        // Vital signs factor
        if (patientData.vitalSigns) {{
            if (patientData.vitalSigns.heartRate > 100) riskScore += 15;
            if (patientData.vitalSigns.bloodPressure && patientData.vitalSigns.bloodPressure.systolic > 140) riskScore += 20;
        }}
        
        return Math.min(riskScore, 100);
    }}
    
    /**
     * Generate treatment recommendations
     * @param {{Object}} patientData - Patient data
     * @param {{number}} riskScore - Calculated risk score
     * @returns {{Array}} Treatment recommendations
     */
    generateRecommendations(patientData, riskScore) {{
        const recommendations = [];
        
        if (riskScore > 70) {{
            recommendations.push('Immediate medical attention required');
            recommendations.push('Continuous monitoring recommended');
        }} else if (riskScore > 40) {{
            recommendations.push('Regular monitoring recommended');
            recommendations.push('Follow-up appointment within 48 hours');
        }} else {{
            recommendations.push('Standard care protocol');
            recommendations.push('Routine follow-up as scheduled');
        }}
        
        return recommendations;
    }}
    
    // Validation methods
    validateHeartRate(heartRate) {{
        if (typeof heartRate !== 'number' || heartRate < 30 || heartRate > 200) {{
            return {{ value: heartRate, status: 'invalid', message: 'Heart rate out of normal range' }};
        }}
        return {{ value: heartRate, status: 'valid' }};
    }}
    
    validateBloodPressure(bp) {{
        if (!bp || typeof bp.systolic !== 'number' || typeof bp.diastolic !== 'number') {{
            return {{ status: 'invalid', message: 'Invalid blood pressure data' }};
        }}
        return {{ systolic: bp.systolic, diastolic: bp.diastolic, status: 'valid' }};
    }}
    
    validateTemperature(temp) {{
        if (typeof temp !== 'number' || temp < 95 || temp > 110) {{
            return {{ value: temp, status: 'invalid', message: 'Temperature out of normal range' }};
        }}
        return {{ value: temp, status: 'valid' }};
    }}
    
    validateOxygenSaturation(o2sat) {{
        if (typeof o2sat !== 'number' || o2sat < 70 || o2sat > 100) {{
            return {{ value: o2sat, status: 'invalid', message: 'Oxygen saturation out of normal range' }};
        }}
        return {{ value: o2sat, status: 'valid' }};
    }}
}}

module.exports = PatientProcessor{i};
            """
            
            file_path = os.path.join(temp_dir, f'src/processors/processor_{i}.js')
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(file_content)
        
        # Create Python files
        for i in range(50):  # 50 Python files
            python_content = f"""
# Medical Analysis Module {i}
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime

@dataclass
class PatientData:
    \"\"\"Patient data structure for medical analysis.\"\"\"
    patient_id: str
    age: int
    medical_history: Dict
    vital_signs: Dict
    timestamp: datetime

class MedicalAnalyzer{i}:
    \"\"\"Medical data analyzer for processing patient information.\"\"\"
    
    def __init__(self):
        self.analysis_cache = {{}}
        self.error_log = []
        
    def analyze_patient_data(self, patient_data: PatientData) -> Dict:
        \"\"\"
        Analyze patient data for medical insights.
        
        Args:
            patient_data: Patient medical data
            
        Returns:
            Analysis results dictionary
            
        Raises:
            ValueError: If patient data is invalid
        \"\"\"
        if not patient_data or not patient_data.patient_id:
            raise ValueError("Invalid patient data - missing patient ID")
            
        if not patient_data.vital_signs:
            raise ValueError("Invalid patient data - missing vital signs")
            
        # Perform medical analysis
        analysis_results = {{
            'patient_id': patient_data.patient_id,
            'analysis_timestamp': datetime.now().isoformat(),
            'vital_signs_analysis': self._analyze_vital_signs(patient_data.vital_signs),
            'risk_assessment': self._calculate_risk_assessment(patient_data),
            'recommendations': self._generate_recommendations(patient_data),
            'analyzer_module': {i}
        }}
        
        return analysis_results
    
    def _analyze_vital_signs(self, vital_signs: Dict) -> Dict:
        \"\"\"Analyze patient vital signs.\"\"\"
        analysis = {{}}
        
        # Heart rate analysis
        if 'heart_rate' in vital_signs:
            hr = vital_signs['heart_rate']
            if hr < 60:
                analysis['heart_rate_status'] = 'bradycardia'
            elif hr > 100:
                analysis['heart_rate_status'] = 'tachycardia'
            else:
                analysis['heart_rate_status'] = 'normal'
                
        # Blood pressure analysis
        if 'blood_pressure' in vital_signs:
            bp = vital_signs['blood_pressure']
            if bp.get('systolic', 0) > 140 or bp.get('diastolic', 0) > 90:
                analysis['bp_status'] = 'hypertensive'
            elif bp.get('systolic', 0) < 90 or bp.get('diastolic', 0) < 60:
                analysis['bp_status'] = 'hypotensive'
            else:
                analysis['bp_status'] = 'normal'
                
        return analysis
    
    def _calculate_risk_assessment(self, patient_data: PatientData) -> Dict:
        \"\"\"Calculate patient risk assessment.\"\"\"
        risk_score = 0
        risk_factors = []
        
        # Age-based risk
        if patient_data.age > 65:
            risk_score += 25
            risk_factors.append('advanced_age')
        elif patient_data.age > 45:
            risk_score += 10
            risk_factors.append('middle_age')
            
        # Medical history risk
        if patient_data.medical_history.get('chronic_conditions'):
            conditions = len(patient_data.medical_history['chronic_conditions'])
            risk_score += conditions * 8
            risk_factors.append('chronic_conditions')
            
        # Vital signs risk
        vital_analysis = self._analyze_vital_signs(patient_data.vital_signs)
        if vital_analysis.get('heart_rate_status') in ['bradycardia', 'tachycardia']:
            risk_score += 15
            risk_factors.append('abnormal_heart_rate')
            
        if vital_analysis.get('bp_status') in ['hypertensive', 'hypotensive']:
            risk_score += 20
            risk_factors.append('abnormal_blood_pressure')
            
        return {{
            'risk_score': min(risk_score, 100),
            'risk_level': self._categorize_risk(risk_score),
            'risk_factors': risk_factors
        }}
    
    def _categorize_risk(self, risk_score: int) -> str:
        \"\"\"Categorize risk level based on score.\"\"\"
        if risk_score >= 70:
            return 'high'
        elif risk_score >= 40:
            return 'moderate'
        else:
            return 'low'
    
    def _generate_recommendations(self, patient_data: PatientData) -> List[str]:
        \"\"\"Generate medical recommendations.\"\"\"
        recommendations = []
        risk_assessment = self._calculate_risk_assessment(patient_data)
        
        if risk_assessment['risk_level'] == 'high':
            recommendations.extend([
                'Immediate medical evaluation required',
                'Continuous monitoring recommended',
                'Consider emergency intervention'
            ])
        elif risk_assessment['risk_level'] == 'moderate':
            recommendations.extend([
                'Schedule follow-up within 24-48 hours',
                'Monitor vital signs regularly',
                'Review medication regimen'
            ])
        else:
            recommendations.extend([
                'Continue routine care',
                'Regular monitoring as scheduled',
                'Maintain current treatment plan'
            ])
            
        return recommendations

# Utility functions for module {i}
def validate_patient_data(data: Dict) -> bool:
    \"\"\"Validate patient data structure.\"\"\"
    required_fields = ['patient_id', 'age', 'medical_history', 'vital_signs']
    return all(field in data for field in required_fields)

def process_batch_analysis(patient_list: List[PatientData]) -> List[Dict]:
    \"\"\"Process multiple patients in batch.\"\"\"
    analyzer = MedicalAnalyzer{i}()
    results = []
    
    for patient in patient_list:
        try:
            result = analyzer.analyze_patient_data(patient)
            results.append(result)
        except Exception as e:
            results.append({{'error': str(e), 'patient_id': patient.patient_id}})
            
    return results
            """
            
            file_path = os.path.join(temp_dir, f'src/analyzers/analyzer_{i}.py')
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(python_content)
        
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def performance_orchestrator(self):
        """Create orchestrator optimized for performance testing."""
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
        
        # Mock LLM backend for consistent performance testing
        mock_backend = Mock()
        mock_backend.generate.return_value = json.dumps({
            "user_requirements": [{"id": f"UR-{i}", "text": f"User requirement {i}"} for i in range(10)],
            "software_requirements": [{"id": f"SR-{i}", "text": f"Software requirement {i}"} for i in range(20)]
        })
        
        orchestrator.requirements_generator = RequirementsGenerator(mock_backend)
        orchestrator.traceability_service = TraceabilityService(orchestrator.db_manager)
        orchestrator.test_case_generator = TestCaseGenerator(mock_backend)
        orchestrator.soup_detector = SOUPDetector()
        orchestrator.soup_service = SOUPService(orchestrator.db_manager)
        orchestrator.api_validator = APIResponseValidator()
        
        return orchestrator
    
    def test_requirements_generation_performance(self, performance_orchestrator, large_project_structure):
        """Test requirements generation performance with large codebases."""
        
        # Get all source files
        js_files = []
        py_files = []
        
        for root, dirs, files in os.walk(large_project_structure):
            for file in files:
                if file.endswith('.js'):
                    js_files.append(os.path.relpath(os.path.join(root, file), large_project_structure))
                elif file.endswith('.py'):
                    py_files.append(os.path.relpath(os.path.join(root, file), large_project_structure))
        
        # Test with different file counts
        test_cases = [
            ("Small batch", js_files[:10]),
            ("Medium batch", js_files[:25]),
            ("Large batch", js_files[:50])
        ]
        
        performance_results = {}
        
        for test_name, file_list in test_cases:
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            try:
                requirements = performance_orchestrator.requirements_generator.generate_requirements(
                    large_project_structure, file_list
                )
                
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                
                performance_results[test_name] = {
                    'duration': end_time - start_time,
                    'memory_delta': end_memory - start_memory,
                    'files_processed': len(file_list),
                    'requirements_generated': len(requirements.get('software_requirements', [])) if requirements else 0
                }
                
                # Performance assertions
                assert performance_results[test_name]['duration'] < 60.0  # Should complete within 60 seconds
                assert performance_results[test_name]['memory_delta'] < 500  # Should not use more than 500MB additional memory
                
            except Exception as e:
                pytest.fail(f"Requirements generation performance test failed for {test_name}: {e}")
        
        # Log performance results
        print(f"\nRequirements Generation Performance Results:")
        for test_name, results in performance_results.items():
            print(f"{test_name}: {results['duration']:.2f}s, {results['memory_delta']:.1f}MB, "
                  f"{results['files_processed']} files, {results['requirements_generated']} requirements")
    
    def test_soup_detection_performance(self, performance_orchestrator, large_project_structure):
        """Test SOUP detection performance with large dependency files."""
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        try:
            soup_components = performance_orchestrator.soup_detector.detect_soup_components(large_project_structure)
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            duration = end_time - start_time
            memory_delta = end_memory - start_memory
            
            # Performance assertions
            assert duration < 30.0  # Should complete within 30 seconds
            assert memory_delta < 200  # Should not use more than 200MB additional memory
            assert len(soup_components) > 0  # Should detect components
            
            print(f"\nSOUP Detection Performance: {duration:.2f}s, {memory_delta:.1f}MB, "
                  f"{len(soup_components)} components detected")
            
        except Exception as e:
            pytest.fail(f"SOUP detection performance test failed: {e}")
    
    def test_traceability_matrix_performance(self, performance_orchestrator, large_project_structure):
        """Test traceability matrix generation performance with large datasets."""
        
        # Create large requirements dataset
        large_requirements = {
            'user_requirements': [
                {
                    'id': f'UR-{i:03d}',
                    'text': f'User requirement {i} for medical device functionality',
                    'acceptance_criteria': [f'Criteria {j} for UR-{i:03d}' for j in range(3)]
                }
                for i in range(50)
            ],
            'software_requirements': [
                {
                    'id': f'SR-{i:03d}',
                    'text': f'Software requirement {i} implementing medical device logic',
                    'derived_from': [f'UR-{(i // 2):03d}'],
                    'acceptance_criteria': [f'Criteria {j} for SR-{i:03d}' for j in range(2)]
                }
                for i in range(100)
            ]
        }
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        try:
            with patch.object(performance_orchestrator.traceability_service, 'generate_traceability_matrix') as mock_trace:
                # Mock realistic traceability matrix
                mock_matrix = [
                    {
                        'code_element': f'function_{i}',
                        'software_requirement': f'SR-{i:03d}',
                        'user_requirement': f'UR-{(i // 2):03d}',
                        'risk': 'Medium',
                        'confidence': 0.8
                    }
                    for i in range(100)
                ]
                
                mock_trace.return_value = {
                    'matrix': mock_matrix,
                    'gaps': []
                }
                
                traceability = performance_orchestrator.traceability_service.generate_traceability_matrix(
                    large_requirements, large_project_structure
                )
                
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                
                duration = end_time - start_time
                memory_delta = end_memory - start_memory
                
                # Performance assertions
                assert duration < 45.0  # Should complete within 45 seconds
                assert memory_delta < 300  # Should not use more than 300MB additional memory
                assert len(traceability['matrix']) > 0  # Should generate matrix
                
                print(f"\nTraceability Matrix Performance: {duration:.2f}s, {memory_delta:.1f}MB, "
                      f"{len(traceability['matrix'])} matrix entries")
                
        except Exception as e:
            pytest.fail(f"Traceability matrix performance test failed: {e}")
    
    def test_concurrent_processing_performance(self, performance_orchestrator, large_project_structure):
        """Test concurrent processing performance with multiple components."""
        
        def run_requirements_generation():
            js_files = [f'src/processors/processor_{i}.js' for i in range(10)]
            return performance_orchestrator.requirements_generator.generate_requirements(
                large_project_structure, js_files
            )
        
        def run_soup_detection():
            return performance_orchestrator.soup_detector.detect_soup_components(large_project_structure)
        
        def run_test_generation():
            test_requirements = [
                Requirement(
                    id=f"PERF-{i}",
                    text=f"Performance test requirement {i}",
                    type=RequirementType.SOFTWARE,
                    acceptance_criteria=[f"Performance criteria {i}"]
                )
                for i in range(5)
            ]
            return performance_orchestrator.test_case_generator.generate_test_cases(test_requirements)
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        try:
            # Run concurrent operations
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(run_requirements_generation),
                    executor.submit(run_soup_detection),
                    executor.submit(run_test_generation)
                ]
                
                results = []
                for future in as_completed(futures):
                    try:
                        result = future.result(timeout=60)  # 60 second timeout per operation
                        results.append(result)
                    except Exception as e:
                        pytest.fail(f"Concurrent operation failed: {e}")
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            duration = end_time - start_time
            memory_delta = end_memory - start_memory
            
            # Performance assertions
            assert duration < 90.0  # All operations should complete within 90 seconds
            assert memory_delta < 800  # Should not use more than 800MB additional memory
            assert len(results) == 3  # All operations should complete
            
            print(f"\nConcurrent Processing Performance: {duration:.2f}s, {memory_delta:.1f}MB, "
                  f"{len(results)} operations completed")
            
        except Exception as e:
            pytest.fail(f"Concurrent processing performance test failed: {e}")
    
    def test_memory_usage_stability(self, performance_orchestrator, large_project_structure):
        """Test memory usage stability during extended operations."""
        
        memory_samples = []
        
        def sample_memory():
            return psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Baseline memory
        baseline_memory = sample_memory()
        memory_samples.append(baseline_memory)
        
        try:
            # Perform multiple operations and monitor memory
            for i in range(5):
                # Requirements generation
                js_files = [f'src/processors/processor_{j}.js' for j in range(i*2, (i+1)*2)]
                performance_orchestrator.requirements_generator.generate_requirements(
                    large_project_structure, js_files
                )
                memory_samples.append(sample_memory())
                
                # SOUP detection
                performance_orchestrator.soup_detector.detect_soup_components(large_project_structure)
                memory_samples.append(sample_memory())
                
                # Small delay to allow garbage collection
                time.sleep(0.1)
            
            # Check memory stability
            max_memory = max(memory_samples)
            min_memory = min(memory_samples)
            memory_variance = max_memory - min_memory
            
            # Memory stability assertions
            assert memory_variance < 1000  # Memory variance should be less than 1GB
            assert max_memory - baseline_memory < 1500  # Total memory increase should be less than 1.5GB
            
            print(f"\nMemory Usage Stability: Baseline: {baseline_memory:.1f}MB, "
                  f"Max: {max_memory:.1f}MB, Variance: {memory_variance:.1f}MB")
            
        except Exception as e:
            pytest.fail(f"Memory usage stability test failed: {e}")
    
    def test_api_response_validation_performance(self, performance_orchestrator):
        """Test API response validation performance with large responses."""
        
        # Create large mock API response
        large_response_data = {
            "user_requirements": [
                {
                    "id": f"UR-{i:04d}",
                    "text": f"User requirement {i} " + "x" * 100,  # Long text
                    "acceptance_criteria": [f"Criteria {j} for UR-{i:04d}" for j in range(5)]
                }
                for i in range(200)
            ],
            "software_requirements": [
                {
                    "id": f"SR-{i:04d}",
                    "text": f"Software requirement {i} " + "x" * 150,  # Long text
                    "derived_from": [f"UR-{(i // 3):04d}"],
                    "acceptance_criteria": [f"Criteria {j} for SR-{i:04d}" for j in range(3)]
                }
                for i in range(500)
            ]
        }
        
        large_response_json = json.dumps(large_response_data)
        
        # Mock response object
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = large_response_data
        mock_response.text = large_response_json
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        try:
            # Test validation performance
            validation_result = performance_orchestrator.api_validator.validate_response(
                mock_response, "requirements_generation"
            )
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            duration = end_time - start_time
            memory_delta = end_memory - start_memory
            
            # Performance assertions
            assert duration < 10.0  # Validation should complete within 10 seconds
            assert memory_delta < 100  # Should not use more than 100MB additional memory
            
            print(f"\nAPI Response Validation Performance: {duration:.2f}s, {memory_delta:.1f}MB, "
                  f"Response size: {len(large_response_json)} bytes")
            
        except Exception as e:
            pytest.fail(f"API response validation performance test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])