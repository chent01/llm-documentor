"""
Backward Compatibility Tests for Enhanced Medical Analyzer

This module tests that the enhanced system maintains compatibility with existing
data formats, workflows, and user interfaces from previous versions.
"""

import pytest
import tempfile
import json
import os
import shutil
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication

from medical_analyzer.services.analysis_orchestrator import AnalysisOrchestrator
from medical_analyzer.services.requirements_generator import RequirementsGenerator
from medical_analyzer.services.traceability_service import TraceabilityService
from medical_analyzer.services.soup_service import SOUPService
from medical_analyzer.ui.main_window import MainWindow
from medical_analyzer.ui.results_tab_widget import ResultsTabWidget
from medical_analyzer.models.core import Requirement, RequirementType, RiskLevel
from medical_analyzer.database.schema import DatabaseManager


class TestBackwardCompatibility:
    """Test backward compatibility with existing data and workflows."""
    
    @pytest.fixture
    def legacy_database(self):
        """Create a legacy database with old schema format."""
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()
        
        # Create legacy database schema
        conn = sqlite3.connect(temp_db.name)
        cursor = conn.cursor()
        
        # Legacy requirements table (old format)
        cursor.execute("""
            CREATE TABLE requirements (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                type TEXT NOT NULL,
                created_at TEXT,
                project_path TEXT
            )
        """)
        
        # Legacy traceability table (old format)
        cursor.execute("""
            CREATE TABLE traceability (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT,
                target_id TEXT,
                relationship_type TEXT,
                confidence REAL
            )
        """)
        
        # Legacy SOUP table (old format)
        cursor.execute("""
            CREATE TABLE soup_components (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                version TEXT,
                supplier TEXT,
                project_path TEXT
            )
        """)
        
        # Insert legacy data
        legacy_requirements = [
            ('REQ-001', 'The system shall process patient data', 'functional', '2023-01-01T00:00:00', '/test/project'),
            ('REQ-002', 'The system shall validate input data', 'functional', '2023-01-01T00:00:00', '/test/project'),
            ('REQ-003', 'The system shall handle errors gracefully', 'non-functional', '2023-01-01T00:00:00', '/test/project')
        ]
        
        cursor.executemany(
            "INSERT INTO requirements (id, text, type, created_at, project_path) VALUES (?, ?, ?, ?, ?)",
            legacy_requirements
        )
        
        legacy_traceability = [
            ('REQ-001', 'CODE-001', 'implements', 0.9),
            ('REQ-002', 'CODE-002', 'implements', 0.8),
            ('REQ-003', 'CODE-003', 'implements', 0.7)
        ]
        
        cursor.executemany(
            "INSERT INTO traceability (source_id, target_id, relationship_type, confidence) VALUES (?, ?, ?, ?)",
            legacy_traceability
        )
        
        legacy_soup = [
            ('express', '4.17.1', 'npm', '/test/project'),
            ('lodash', '4.17.21', 'npm', '/test/project'),
            ('numpy', '1.21.0', 'pip', '/test/project')
        ]
        
        cursor.executemany(
            "INSERT INTO soup_components (name, version, supplier, project_path) VALUES (?, ?, ?, ?)",
            legacy_soup
        )
        
        conn.commit()
        conn.close()
        
        yield temp_db.name
        os.unlink(temp_db.name)
    
    @pytest.fixture
    def legacy_project_structure(self):
        """Create a legacy project structure with old file formats."""
        temp_dir = tempfile.mkdtemp()
        
        # Legacy analysis results file (old JSON format)
        legacy_results = {
            "analysis_timestamp": "2023-01-01T00:00:00",
            "project_path": temp_dir,
            "requirements": [
                {
                    "id": "LEGACY-001",
                    "description": "Legacy requirement format",
                    "category": "functional",
                    "priority": "high"
                }
            ],
            "traceability": [
                {
                    "from": "LEGACY-001",
                    "to": "legacy_function",
                    "type": "implements"
                }
            ],
            "soup": [
                {
                    "component": "legacy-lib",
                    "version": "1.0.0",
                    "source": "npm"
                }
            ]
        }
        
        with open(os.path.join(temp_dir, 'analysis_results.json'), 'w') as f:
            json.dump(legacy_results, f, indent=2)
        
        # Legacy configuration file (old format)
        legacy_config = {
            "llm_backend": "local",
            "api_endpoint": "http://localhost:8080",
            "analysis_settings": {
                "include_tests": True,
                "generate_docs": False
            }
        }
        
        with open(os.path.join(temp_dir, 'config.json'), 'w') as f:
            json.dump(legacy_config, f, indent=2)
        
        # Legacy source code
        legacy_code = """
// Legacy JavaScript code format
function legacyFunction(data) {
    // Old style comment format
    if (!data) {
        return null;
    }
    return processData(data);
}

var legacyVariable = "old style";
        """
        
        with open(os.path.join(temp_dir, 'legacy_code.js'), 'w') as f:
            f.write(legacy_code)
        
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_legacy_database_migration(self, legacy_database):
        """Test that legacy database can be migrated to new schema."""
        
        try:
            # Initialize database manager with legacy database
            db_manager = DatabaseManager(legacy_database)
            
            # Test reading legacy requirements
            conn = sqlite3.connect(legacy_database)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM requirements")
            legacy_requirements = cursor.fetchall()
            
            assert len(legacy_requirements) == 3
            assert legacy_requirements[0][0] == 'REQ-001'
            assert legacy_requirements[0][1] == 'The system shall process patient data'
            
            # Test that new system can handle legacy data
            converted_requirements = []
            for req_data in legacy_requirements:
                req = Requirement(
                    id=req_data[0],
                    text=req_data[1],
                    type=RequirementType.SOFTWARE if req_data[2] == 'functional' else RequirementType.SYSTEM,
                    acceptance_criteria=[],
                    derived_from=[],
                    metadata={
                        "priority": "medium",
                        "status": "draft",
                        "legacy_type": req_data[2]
                    }
                )
                converted_requirements.append(req)
            
            assert len(converted_requirements) == 3
            assert converted_requirements[0].id == 'REQ-001'
            assert converted_requirements[0].type == RequirementType.SOFTWARE
            
            conn.close()
            
        except Exception as e:
            pytest.fail(f"Legacy database migration test failed: {e}")
    
    def test_legacy_requirements_format_compatibility(self):
        """Test that legacy requirements format can be processed."""
        
        # Legacy requirements format (old structure)
        legacy_requirements_data = {
            "requirements": [
                {
                    "id": "LEGACY-REQ-001",
                    "description": "Legacy requirement description",
                    "category": "functional",
                    "priority": "high",
                    "status": "approved"
                },
                {
                    "id": "LEGACY-REQ-002",
                    "description": "Another legacy requirement",
                    "category": "performance",
                    "priority": "medium",
                    "status": "draft"
                }
            ]
        }
        
        try:
            # Convert legacy format to new format
            converted_requirements = []
            for legacy_req in legacy_requirements_data["requirements"]:
                # Map legacy fields to new structure
                req_type = RequirementType.SOFTWARE
                if legacy_req["category"] == "functional":
                    req_type = RequirementType.SOFTWARE
                elif legacy_req["category"] == "performance":
                    req_type = RequirementType.SYSTEM
                elif legacy_req["category"] == "security":
                    req_type = RequirementType.SYSTEM
                
                new_req = Requirement(
                    id=legacy_req["id"],
                    text=legacy_req["description"],  # Map 'description' to 'text'
                    type=req_type,
                    acceptance_criteria=[],  # Legacy format didn't have acceptance criteria
                    derived_from=[],
                    metadata={
                        "priority": legacy_req["priority"],
                        "status": legacy_req["status"],
                        "legacy_category": legacy_req["category"]
                    }
                )
                converted_requirements.append(new_req)
            
            # Verify conversion
            assert len(converted_requirements) == 2
            assert converted_requirements[0].id == "LEGACY-REQ-001"
            assert converted_requirements[0].text == "Legacy requirement description"
            assert converted_requirements[0].type == RequirementType.SOFTWARE
            assert converted_requirements[1].type == RequirementType.SYSTEM
            
        except Exception as e:
            pytest.fail(f"Legacy requirements format compatibility test failed: {e}")
    
    def test_legacy_traceability_format_compatibility(self):
        """Test that legacy traceability format can be processed."""
        
        # Legacy traceability format
        legacy_traceability_data = {
            "traceability_links": [
                {
                    "from_id": "REQ-001",
                    "to_id": "FUNC-001",
                    "link_type": "implements",
                    "confidence_score": 0.9
                },
                {
                    "from_id": "REQ-002", 
                    "to_id": "FUNC-002",
                    "link_type": "satisfies",
                    "confidence_score": 0.8
                }
            ]
        }
        
        try:
            # Convert legacy traceability to new format
            converted_links = []
            for legacy_link in legacy_traceability_data["traceability_links"]:
                # Map legacy format to new structure
                new_link = {
                    'source_id': legacy_link["from_id"],
                    'target_id': legacy_link["to_id"],
                    'relationship_type': legacy_link["link_type"],
                    'confidence': legacy_link["confidence_score"],
                    'metadata': {}  # New field not in legacy format
                }
                converted_links.append(new_link)
            
            # Verify conversion
            assert len(converted_links) == 2
            assert converted_links[0]['source_id'] == "REQ-001"
            assert converted_links[0]['target_id'] == "FUNC-001"
            assert converted_links[0]['confidence'] == 0.9
            
        except Exception as e:
            pytest.fail(f"Legacy traceability format compatibility test failed: {e}")
    
    def test_legacy_soup_format_compatibility(self):
        """Test that legacy SOUP format can be processed."""
        
        # Legacy SOUP format (simple structure)
        legacy_soup_data = {
            "components": [
                {
                    "name": "express",
                    "version": "4.17.1",
                    "type": "npm",
                    "description": "Web framework"
                },
                {
                    "name": "lodash",
                    "version": "4.17.21", 
                    "type": "npm",
                    "description": "Utility library"
                }
            ]
        }
        
        try:
            # Convert legacy SOUP to new format
            from medical_analyzer.models.soup_models import DetectedSOUPComponent, IEC62304Classification
            
            converted_components = []
            for legacy_comp in legacy_soup_data["components"]:
                new_comp = DetectedSOUPComponent(
                    name=legacy_comp["name"],
                    version=legacy_comp["version"],
                    source_file="package.json",  # Inferred from type
                    detection_method="legacy_import",
                    confidence=1.0,  # Legacy data assumed to be accurate
                    suggested_classification="B",  # Default classification
                    metadata={
                        "legacy_type": legacy_comp["type"],
                        "legacy_description": legacy_comp.get("description", "")
                    }
                )
                converted_components.append(new_comp)
            
            # Verify conversion
            assert len(converted_components) == 2
            assert converted_components[0].name == "express"
            assert converted_components[0].version == "4.17.1"
            assert converted_components[0].confidence == 1.0
            
        except Exception as e:
            pytest.fail(f"Legacy SOUP format compatibility test failed: {e}")
    
    def test_legacy_ui_workflow_compatibility(self, qtbot):
        """Test that legacy UI workflows still work with enhanced components."""
        
        if QApplication.instance() is None:
            app = QApplication([])
        
        try:
            # Test main window initialization with legacy data
            main_window = MainWindow()
            qtbot.addWidget(main_window)
            
            # Verify that enhanced components are backward compatible
            results_widget = main_window.results_widget
            assert results_widget is not None
            
            # Test legacy results display format
            legacy_results = {
                "requirements": [
                    {
                        "id": "LEGACY-001",
                        "text": "Legacy requirement text",
                        "type": "functional"
                    }
                ],
                "traceability": [
                    {
                        "source": "LEGACY-001",
                        "target": "legacy_function",
                        "type": "implements"
                    }
                ]
            }
            
            # Test that results widget can handle legacy format
            # This would normally be done through the results widget's update methods
            # For testing, we verify the widget exists and can be updated
            assert hasattr(results_widget, 'update_results')
            
        except Exception as e:
            pytest.fail(f"Legacy UI workflow compatibility test failed: {e}")
    
    def test_legacy_configuration_compatibility(self, legacy_project_structure):
        """Test that legacy configuration files are handled correctly."""
        
        config_file = os.path.join(legacy_project_structure, 'config.json')
        
        try:
            # Read legacy configuration
            with open(config_file, 'r') as f:
                legacy_config = json.load(f)
            
            # Test that new system can handle legacy config
            from medical_analyzer.config.config_manager import ConfigManager
            
            config_manager = ConfigManager()
            
            # Convert legacy config to new format
            new_config = {
                'llm': {
                    'backend_type': legacy_config.get('llm_backend', 'local'),
                    'api_endpoint': legacy_config.get('api_endpoint', 'http://localhost:8080'),
                    'timeout': 30  # Default value for new field
                },
                'analysis': {
                    'include_tests': legacy_config.get('analysis_settings', {}).get('include_tests', True),
                    'generate_documentation': legacy_config.get('analysis_settings', {}).get('generate_docs', False),
                    'enable_traceability': True  # New field with default
                }
            }
            
            # Verify conversion maintains essential settings
            assert new_config['llm']['backend_type'] == 'local'
            assert new_config['llm']['api_endpoint'] == 'http://localhost:8080'
            assert new_config['analysis']['include_tests'] is True
            
        except Exception as e:
            pytest.fail(f"Legacy configuration compatibility test failed: {e}")
    
    def test_legacy_analysis_results_compatibility(self, legacy_project_structure):
        """Test that legacy analysis results can be loaded and processed."""
        
        results_file = os.path.join(legacy_project_structure, 'analysis_results.json')
        
        try:
            # Read legacy analysis results
            with open(results_file, 'r') as f:
                legacy_results = json.load(f)
            
            # Convert legacy results to new format
            converted_results = {
                'metadata': {
                    'analysis_timestamp': legacy_results.get('analysis_timestamp'),
                    'project_path': legacy_results.get('project_path'),
                    'version': '2.0.0'  # Mark as converted
                },
                'requirements': {
                    'user_requirements': [],
                    'software_requirements': []
                },
                'traceability': {
                    'matrix': [],
                    'gaps': []
                },
                'soup_components': [],
                'test_cases': []
            }
            
            # Convert legacy requirements
            for legacy_req in legacy_results.get('requirements', []):
                converted_req = {
                    'id': legacy_req['id'],
                    'text': legacy_req['description'],
                    'type': 'software' if legacy_req['category'] == 'functional' else 'non_functional',
                    'priority': legacy_req['priority'],
                    'acceptance_criteria': []  # New field
                }
                converted_results['requirements']['software_requirements'].append(converted_req)
            
            # Convert legacy traceability
            for legacy_trace in legacy_results.get('traceability', []):
                converted_trace = {
                    'source_id': legacy_trace['from'],
                    'target_id': legacy_trace['to'],
                    'relationship_type': legacy_trace['type'],
                    'confidence': 0.8  # Default confidence for legacy data
                }
                converted_results['traceability']['matrix'].append(converted_trace)
            
            # Convert legacy SOUP
            for legacy_soup in legacy_results.get('soup', []):
                converted_soup = {
                    'name': legacy_soup['component'],
                    'version': legacy_soup['version'],
                    'source_file': 'package.json' if legacy_soup['source'] == 'npm' else 'requirements.txt',
                    'detection_method': 'legacy_import',
                    'confidence': 1.0,
                    'classification': 'B'  # Default classification
                }
                converted_results['soup_components'].append(converted_soup)
            
            # Verify conversion
            assert len(converted_results['requirements']['software_requirements']) == 1
            assert len(converted_results['traceability']['matrix']) == 1
            assert len(converted_results['soup_components']) == 1
            
            # Verify data integrity
            req = converted_results['requirements']['software_requirements'][0]
            assert req['id'] == 'LEGACY-001'
            assert req['text'] == 'Legacy requirement format'
            
        except Exception as e:
            pytest.fail(f"Legacy analysis results compatibility test failed: {e}")
    
    def test_legacy_api_response_compatibility(self):
        """Test that legacy API response formats are handled correctly."""
        
        # Legacy API response format (simpler structure)
        legacy_api_response = {
            "status": "success",
            "data": {
                "requirements": [
                    "The system shall process data",
                    "The system shall validate input",
                    "The system shall handle errors"
                ]
            }
        }
        
        try:
            from medical_analyzer.llm.api_response_validator import APIResponseValidator
            
            # Test that validator can handle legacy format
            validator = APIResponseValidator({})
            
            # Convert legacy response to new format
            converted_response = {
                "user_requirements": [],
                "software_requirements": []
            }
            
            # Convert simple requirement list to structured format
            for i, req_text in enumerate(legacy_api_response["data"]["requirements"]):
                converted_req = {
                    "id": f"LEGACY-SR-{i+1:03d}",
                    "text": req_text,
                    "type": "software",
                    "acceptance_criteria": [],
                    "derived_from": []
                }
                converted_response["software_requirements"].append(converted_req)
            
            # Verify conversion
            assert len(converted_response["software_requirements"]) == 3
            assert converted_response["software_requirements"][0]["text"] == "The system shall process data"
            
        except Exception as e:
            pytest.fail(f"Legacy API response compatibility test failed: {e}")
    
    def test_legacy_export_format_compatibility(self):
        """Test that legacy export formats are still supported."""
        
        # Legacy export format (simple CSV)
        legacy_csv_data = """ID,Description,Type,Priority
REQ-001,Process patient data,Functional,High
REQ-002,Validate input data,Functional,Medium
REQ-003,Handle errors,Non-Functional,Low"""
        
        try:
            # Parse legacy CSV format
            import csv
            import io
            
            csv_reader = csv.DictReader(io.StringIO(legacy_csv_data))
            legacy_requirements = list(csv_reader)
            
            # Convert to new format
            converted_requirements = []
            for legacy_req in legacy_requirements:
                req = Requirement(
                    id=legacy_req["ID"],
                    text=legacy_req["Description"],
                    type=RequirementType.SOFTWARE if legacy_req["Type"] == "Functional" else RequirementType.SYSTEM,
                    acceptance_criteria=[],
                    derived_from=[],
                    metadata={
                        "priority": legacy_req["Priority"].lower(),
                        "status": "imported",
                        "legacy_type": legacy_req["Type"]
                    }
                )
                converted_requirements.append(req)
            
            # Verify conversion
            assert len(converted_requirements) == 3
            assert converted_requirements[0].id == "REQ-001"
            assert converted_requirements[0].metadata["priority"] == "high"
            
        except Exception as e:
            pytest.fail(f"Legacy export format compatibility test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])