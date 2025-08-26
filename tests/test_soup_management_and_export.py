"""
Comprehensive tests for SOUP management and export system.
Tests task 10 requirements: SOUP inventory management and comprehensive export system.
"""

import pytest
import tempfile
import os
import json
import zipfile
from datetime import datetime
from unittest.mock import Mock, patch

from medical_analyzer.models.core import SOUPComponent
from medical_analyzer.services.soup_service import SOUPService
from medical_analyzer.services.export_service import ExportService
from medical_analyzer.database.schema import DatabaseManager


class TestSOUPManagementAndExport:
    """Test cases for SOUP management and export system."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        os.unlink(path)
    
    @pytest.fixture
    def db_manager(self, temp_db):
        """Create a database manager with temporary database."""
        return DatabaseManager(temp_db)
    
    @pytest.fixture
    def soup_service(self, db_manager):
        """Create a SOUP service instance."""
        return SOUPService(db_manager)
    
    @pytest.fixture
    def export_service(self, soup_service):
        """Create an export service instance."""
        return ExportService(soup_service)
    
    @pytest.fixture
    def sample_soup_components(self):
        """Create sample SOUP components for testing."""
        return [
            SOUPComponent(
                id="sqlite-001",
                name="SQLite",
                version="3.36.0",
                usage_reason="Database storage for analysis results and project metadata",
                safety_justification="Well-tested, widely used database engine with excellent safety record and extensive testing",
                supplier="SQLite Development Team",
                license="Public Domain",
                website="https://sqlite.org",
                description="Lightweight SQL database engine",
                criticality_level="Medium",
                verification_method="Unit testing, integration testing, and extensive real-world usage",
                anomaly_list=["None known"]
            ),
            SOUPComponent(
                id="openssl-001",
                name="OpenSSL",
                version="1.1.1k",
                usage_reason="Cryptographic functions for secure data transmission",
                safety_justification="Industry standard cryptographic library with comprehensive security audits",
                supplier="OpenSSL Software Foundation",
                license="Apache License 2.0",
                website="https://www.openssl.org",
                description="Cryptographic library for SSL/TLS protocols",
                criticality_level="High",
                verification_method="Security audits, penetration testing, and compliance validation",
                anomaly_list=["CVE-2021-3711", "CVE-2021-3712"]
            ),
            SOUPComponent(
                id="jquery-001",
                name="jQuery",
                version="3.6.0",
                usage_reason="DOM manipulation and AJAX functionality for web interface",
                safety_justification="Mature JavaScript library with extensive testing and wide adoption",
                supplier="jQuery Foundation",
                license="MIT License",
                website="https://jquery.com",
                description="JavaScript library for DOM manipulation",
                criticality_level="Low",
                verification_method="Unit testing and integration testing",
                anomaly_list=["None known"]
            )
        ]
    
    @pytest.fixture
    def sample_analysis_results(self):
        """Create sample analysis results for testing export."""
        return {
            "timestamp": datetime.now().isoformat(),
            "file_count": 25,
            "lines_of_code": 15000,
            "summary": {
                "software_class": "Class B",
                "confidence": 85,
                "features": ["Patient monitoring", "Data logging", "Alarm system"]
            },
            "requirements": {
                "user_requirements": [
                    {
                        "id": "UR-001",
                        "description": "The system shall monitor patient vital signs",
                        "acceptance_criteria": ["Heart rate monitoring", "Blood pressure monitoring"],
                        "derived_from": [],
                        "code_references": [{"file": "monitor.c", "line": 45}]
                    },
                    {
                        "id": "UR-002",
                        "description": "The system shall log all patient data",
                        "acceptance_criteria": ["Data persistence", "Audit trail"],
                        "derived_from": [],
                        "code_references": [{"file": "logger.c", "line": 23}]
                    }
                ],
                "software_requirements": [
                    {
                        "id": "SR-001",
                        "description": "The software shall acquire heart rate data every 5 seconds",
                        "acceptance_criteria": ["5-second intervals", "Accuracy ±2 BPM"],
                        "derived_from": ["UR-001"],
                        "code_references": [{"file": "heart_rate.c", "line": 67}]
                    }
                ]
            },
            "risks": [
                {
                    "id": "RISK-001",
                    "hazard": "Incorrect heart rate reading",
                    "cause": "Sensor malfunction or calibration error",
                    "effect": "Incorrect patient assessment",
                    "severity": "SERIOUS",
                    "probability": "MEDIUM",
                    "risk_level": "MEDIUM",
                    "mitigation": "Regular sensor calibration and validation",
                    "verification": "Unit tests and integration tests",
                    "related_requirements": ["SR-001"]
                }
            ],
            "traceability": {
                "links": [
                    {
                        "source_type": "code",
                        "source_id": "heart_rate.c:67",
                        "target_type": "requirement",
                        "target_id": "SR-001",
                        "link_type": "implements",
                        "evidence": "Function implements heart rate acquisition"
                    }
                ],
                "gaps": [
                    {
                        "type": "missing_verification",
                        "description": "No test coverage for sensor calibration",
                        "severity": "MEDIUM",
                        "recommendation": "Add unit tests for calibration functions"
                    }
                ]
            },
            "tests": {
                "total_tests": 150,
                "passed_tests": 145,
                "failed_tests": 3,
                "skipped_tests": 2,
                "coverage": 87,
                "execution_time": 45.2,
                "test_suites": [
                    {
                        "name": "Unit Tests",
                        "total_tests": 100,
                        "passed_tests": 98,
                        "failed_tests": 2,
                        "status": "completed"
                    }
                ],
                "generated_files": {
                    "tests/unit/test_heart_rate.c": "#include <unity.h>\nvoid test_heart_rate_acquisition() {\n    // Test implementation\n}"
                }
            }
        }
    
    def test_soup_component_validation(self, sample_soup_components):
        """Test SOUP component data validation."""
        # Test valid components
        for component in sample_soup_components:
            assert component.is_valid()
            assert len(component.validate()) == 0
        
        # Test invalid component (missing required fields)
        invalid_component = SOUPComponent(
            id="",  # Empty ID
            name="",  # Empty name
            version="",  # Empty version
            usage_reason="",  # Empty usage reason
            safety_justification=""  # Empty safety justification
        )
        
        assert not invalid_component.is_valid()
        validation_errors = invalid_component.validate()
        assert len(validation_errors) > 0
        assert "id cannot be empty" in validation_errors
        assert "name cannot be empty" in validation_errors
        assert "version cannot be empty" in validation_errors
        assert "usage_reason cannot be empty" in validation_errors
        assert "safety_justification cannot be empty" in validation_errors
    
    def test_soup_service_crud_operations(self, soup_service, sample_soup_components):
        """Test SOUP service CRUD operations."""
        # Test adding components
        for component in sample_soup_components:
            component_id = soup_service.add_component(component)
            assert component_id == component.id
        
        # Test retrieving all components
        all_components = soup_service.get_all_components()
        assert len(all_components) == 3
        
        # Test retrieving specific component
        sqlite_component = soup_service.get_component("sqlite-001")
        assert sqlite_component is not None
        assert sqlite_component.name == "SQLite"
        assert sqlite_component.version == "3.36.0"
        
        # Test updating component
        sqlite_component.version = "3.37.0"
        success = soup_service.update_component(sqlite_component)
        assert success
        
        updated_component = soup_service.get_component("sqlite-001")
        assert updated_component.version == "3.37.0"
        
        # Test deleting component
        success = soup_service.delete_component("jquery-001")
        assert success
        
        remaining_components = soup_service.get_all_components()
        assert len(remaining_components) == 2
    
    def test_soup_service_search_and_filter(self, soup_service, sample_soup_components):
        """Test SOUP service search and filtering capabilities."""
        # Add components
        for component in sample_soup_components:
            soup_service.add_component(component)
        
        # Test search functionality
        search_results = soup_service.search_components("SQLite")
        assert len(search_results) == 1
        assert search_results[0].name == "SQLite"
        
        # Test criticality filtering
        high_criticality = soup_service.get_components_by_criticality("High")
        assert len(high_criticality) == 1
        assert high_criticality[0].name == "OpenSSL"
        
        medium_criticality = soup_service.get_components_by_criticality("Medium")
        assert len(medium_criticality) == 1
        assert medium_criticality[0].name == "SQLite"
        
        low_criticality = soup_service.get_components_by_criticality("Low")
        assert len(low_criticality) == 1
        assert low_criticality[0].name == "jQuery"
    
    def test_soup_inventory_export(self, soup_service, sample_soup_components):
        """Test SOUP inventory export functionality."""
        # Add components
        for component in sample_soup_components:
            soup_service.add_component(component)
        
        # Export inventory
        inventory_data = soup_service.export_inventory()
        
        # Verify export structure
        assert "soup_inventory" in inventory_data
        assert "export_timestamp" in inventory_data["soup_inventory"]
        assert "component_count" in inventory_data["soup_inventory"]
        assert "components" in inventory_data["soup_inventory"]
        
        # Verify component count
        assert inventory_data["soup_inventory"]["component_count"] == 3
        
        # Verify component data
        components = inventory_data["soup_inventory"]["components"]
        assert len(components) == 3
        
        # Check specific component data
        sqlite_data = next(c for c in components if c["name"] == "SQLite")
        assert sqlite_data["version"] == "3.36.0"
        assert sqlite_data["supplier"] == "SQLite Development Team"
        assert sqlite_data["criticality_level"] == "Medium"
    
    def test_export_service_audit_logging(self, export_service):
        """Test export service audit logging functionality."""
        # Test logging actions
        export_service.log_action("test_action", "Test details", "test_user")
        
        # Verify log entry
        assert len(export_service.audit_log) == 1
        log_entry = export_service.audit_log[0]
        assert log_entry["action"] == "test_action"
        assert log_entry["details"] == "Test details"
        assert log_entry["user"] == "test_user"
        assert "timestamp" in log_entry
        
        # Test multiple log entries
        export_service.log_action("another_action", "More details")
        assert len(export_service.audit_log) == 2
    
    def test_comprehensive_export_creation(self, export_service, sample_soup_components, 
                                         sample_analysis_results, temp_db):
        """Test comprehensive export bundle creation."""
        # Add SOUP components
        for component in sample_soup_components:
            export_service.soup_service.add_component(component)
        
        # Create export bundle
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_path = export_service.create_comprehensive_export(
                analysis_results=sample_analysis_results,
                project_name="Test Medical Device",
                project_path="/path/to/project",
                output_dir=temp_dir
            )
            
            # Verify bundle was created
            assert os.path.exists(bundle_path)
            assert bundle_path.endswith('.zip')
            
            # Verify zip file structure
            with zipfile.ZipFile(bundle_path, 'r') as zipf:
                file_list = zipf.namelist()
                
                # Check for required directories and files
                assert any('requirements/' in f for f in file_list)
                assert any('risk_register/' in f for f in file_list)
                assert any('traceability/' in f for f in file_list)
                assert any('tests/' in f for f in file_list)
                assert any('soup_inventory/' in f for f in file_list)
                assert any('audit/' in f for f in file_list)
                assert any('metadata/' in f for f in file_list)
                assert any('summary_report.txt' in f for f in file_list)
                
                # Verify specific files
                assert any('requirements/user_requirements.csv' in f for f in file_list)
                assert any('requirements/software_requirements.csv' in f for f in file_list)
                assert any('risk_register/risk_register.csv' in f for f in file_list)
                assert any('traceability/traceability_matrix.csv' in f for f in file_list)
                assert any('soup_inventory/soup_inventory.csv' in f for f in file_list)
                assert any('audit/audit_log.json' in f for f in file_list)
                assert any('metadata/project_metadata.json' in f for f in file_list)
    
    def test_export_content_validation(self, export_service, sample_soup_components, 
                                     sample_analysis_results):
        """Test that exported content is correct and complete."""
        # Add SOUP components
        for component in sample_soup_components:
            export_service.soup_service.add_component(component)
        
        # Create export bundle
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_path = export_service.create_comprehensive_export(
                analysis_results=sample_analysis_results,
                project_name="Test Medical Device",
                project_path="/path/to/project",
                output_dir=temp_dir
            )
            
            # Extract and verify content
            with zipfile.ZipFile(bundle_path, 'r') as zipf:
                # Verify requirements export
                with zipf.open('requirements/user_requirements.csv') as f:
                    content = f.read().decode('utf-8')
                    assert 'UR-001' in content
                    assert 'monitor patient vital signs' in content
                
                # Verify risk register export
                with zipf.open('risk_register/risk_register.csv') as f:
                    content = f.read().decode('utf-8')
                    assert 'RISK-001' in content
                    assert 'Incorrect heart rate reading' in content
                
                # Verify SOUP inventory export
                with zipf.open('soup_inventory/soup_inventory.csv') as f:
                    content = f.read().decode('utf-8')
                    assert 'SQLite' in content
                    assert 'OpenSSL' in content
                    assert 'jQuery' in content
                
                # Verify audit log
                with zipf.open('audit/audit_log.json') as f:
                    audit_data = json.load(f)
                    assert len(audit_data) > 0
                    # Check for export-related actions in the audit log
                    export_actions = [entry['action'] for entry in audit_data]
                    assert 'export_started' in export_actions
                    assert 'export_completed' in export_actions
                
                # Verify summary report
                with zipf.open('summary_report.txt') as f:
                    content = f.read().decode('utf-8')
                    assert 'MEDICAL SOFTWARE ANALYSIS' in content
                    assert 'Test Medical Device' in content
                    assert 'User Requirements: 2' in content
                    assert 'Software Requirements: 1' in content
                    assert 'Total Risks: 1' in content
                    assert 'Total SOUP Components: 3' in content
    
    def test_export_error_handling(self, export_service):
        """Test export service error handling."""
        # Test with empty analysis results
        with pytest.raises(ValueError, match="Analysis results cannot be empty"):
            export_service.create_comprehensive_export(
                analysis_results={},
                project_name="Test",
                project_path="/path/to/project"
            )
        
        # Test with None analysis results
        with pytest.raises(ValueError, match="Analysis results cannot be empty"):
            export_service.create_comprehensive_export(
                analysis_results=None,
                project_name="Test",
                project_path="/path/to/project"
            )
    
    def test_export_service_summary(self, export_service):
        """Test export service summary functionality."""
        # Add some audit log entries
        export_service.log_action("test_action", "Test details")
        export_service.log_action("another_action", "More details")
        
        # Get summary
        summary = export_service.get_export_summary()
        
        # Verify summary structure
        assert "audit_log_entries" in summary
        assert "last_export_timestamp" in summary
        assert "export_actions" in summary
        
        # Verify summary values
        assert summary["audit_log_entries"] == 2
        assert len(summary["export_actions"]) == 2
        assert "test_action" in summary["export_actions"]
        assert "another_action" in summary["export_actions"]
    
    def test_soup_component_anomaly_handling(self, soup_service):
        """Test SOUP component anomaly list handling."""
        # Create component with anomalies
        component = SOUPComponent(
            id="test-anomaly",
            name="Test Component",
            version="1.0.0",
            usage_reason="Testing anomaly handling",
            safety_justification="Safe for testing",
            anomaly_list=["CVE-2021-1234", "CVE-2021-5678", "Known bug in v1.0.0"]
        )
        
        # Add component
        soup_service.add_component(component)
        
        # Retrieve and verify
        retrieved = soup_service.get_component("test-anomaly")
        assert retrieved is not None
        assert len(retrieved.anomaly_list) == 3
        assert "CVE-2021-1234" in retrieved.anomaly_list
        assert "CVE-2021-5678" in retrieved.anomaly_list
        assert "Known bug in v1.0.0" in retrieved.anomaly_list
    
    def test_export_with_empty_soup_inventory(self, export_service, sample_analysis_results):
        """Test export functionality when SOUP inventory is empty."""
        # Create export bundle with empty SOUP inventory
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_path = export_service.create_comprehensive_export(
                analysis_results=sample_analysis_results,
                project_name="Test Medical Device",
                project_path="/path/to/project",
                output_dir=temp_dir
            )
            
            # Verify bundle was created
            assert os.path.exists(bundle_path)
            
            # Check that empty SOUP inventory file was created
            with zipfile.ZipFile(bundle_path, 'r') as zipf:
                file_list = zipf.namelist()
                assert any('soup_inventory/soup_inventory_empty.txt' in f for f in file_list)
                
                # Verify empty inventory file content
                with zipf.open('soup_inventory/soup_inventory_empty.txt') as f:
                    content = f.read().decode('utf-8')
                    assert 'No SOUP components have been added' in content
                    assert 'SOUP inventory was checked but found empty' in content
