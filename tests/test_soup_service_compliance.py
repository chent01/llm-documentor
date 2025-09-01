"""
Tests for enhanced SOUP service compliance features.
Tests automatic classification, version change tracking, compliance validation, and audit trail.
"""

import pytest
import tempfile
import os
import json
from datetime import datetime
from unittest.mock import Mock, patch

from medical_analyzer.database.schema import DatabaseManager
from medical_analyzer.services.soup_service import SOUPService
from medical_analyzer.models.soup_models import (
    DetectedSOUPComponent, DetectionMethod, IEC62304SafetyClass,
    IEC62304Classification, VersionChange, SafetyAssessment, 
    ComplianceValidation, SOUPAuditEntry
)
from medical_analyzer.models.core import SOUPComponent


class TestSOUPServiceCompliance:
    """Test enhanced SOUP service compliance features."""
    
    @pytest.fixture
    def db_manager(self):
        """Create temporary database manager for testing."""
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()
        
        db_manager = DatabaseManager(temp_db.name)
        yield db_manager
        
        # Cleanup
        try:
            os.unlink(temp_db.name)
        except:
            pass
    
    @pytest.fixture
    def soup_service(self, db_manager):
        """Create SOUP service instance."""
        return SOUPService(db_manager)
    
    @pytest.fixture
    def sample_detected_component(self):
        """Create sample detected SOUP component."""
        return DetectedSOUPComponent(
            name="openssl",
            version="1.1.1k",
            source_file="requirements.txt",
            detection_method=DetectionMethod.REQUIREMENTS_TXT,
            confidence=0.95,
            description="Cryptographic library",
            license="Apache-2.0",
            homepage="https://openssl.org",
            metadata={"supplier": "OpenSSL Foundation"}
        )
    
    def test_add_component_with_classification(self, soup_service, sample_detected_component):
        """Test adding component with automatic classification."""
        # Add component with classification
        component_id = soup_service.add_component_with_classification(
            sample_detected_component, "test_user"
        )
        
        assert component_id is not None
        assert len(component_id) > 0
        
        # Verify component was added
        component = soup_service.get_component(component_id)
        assert component is not None
        assert component.name == "openssl"
        assert component.version == "1.1.1k"
        
        # Verify classification was created
        classification = soup_service.get_component_classification(component_id)
        assert classification is not None
        assert isinstance(classification.safety_class, IEC62304SafetyClass)
        assert len(classification.justification) > 0
        assert len(classification.risk_assessment) > 0
    
    def test_classify_existing_component(self, soup_service):
        """Test classifying an existing component."""
        # Add regular component first
        component = SOUPComponent(
            id="test-component-123",
            name="test-library",
            version="1.0.0",
            usage_reason="Testing",
            safety_justification="Test component"
        )
        
        component_id = soup_service.add_component(component)
        
        # Classify the component
        classification = soup_service.classify_existing_component(component_id, "test_user")
        
        assert classification is not None
        assert isinstance(classification.safety_class, IEC62304SafetyClass)
        assert len(classification.justification) > 0
        
        # Verify classification was stored
        stored_classification = soup_service.get_component_classification(component_id)
        assert stored_classification is not None
        assert stored_classification.safety_class == classification.safety_class
    
    def test_track_version_change(self, soup_service, sample_detected_component):
        """Test version change tracking."""
        # Add component
        component_id = soup_service.add_component_with_classification(
            sample_detected_component, "test_user"
        )
        
        # Track version change
        version_change = soup_service.track_version_change(
            component_id=component_id,
            new_version="1.1.1l",
            impact_analysis="Security update with vulnerability fixes",
            change_reason="Critical security patch",
            user="test_user"
        )
        
        assert version_change.old_version == "1.1.1k"
        assert version_change.new_version == "1.1.1l"
        assert version_change.approval_status == "pending"
        assert version_change.impact_analysis == "Security update with vulnerability fixes"
        
        # Verify component version was updated
        component = soup_service.get_component(component_id)
        assert component.version == "1.1.1l"
        
        # Verify version history
        history = soup_service.get_component_version_history(component_id)
        assert len(history) == 1
        assert history[0].old_version == "1.1.1k"
        assert history[0].new_version == "1.1.1l"
    
    def test_validate_component_compliance(self, soup_service, sample_detected_component):
        """Test compliance validation."""
        # Add component with classification
        component_id = soup_service.add_component_with_classification(
            sample_detected_component, "test_user"
        )
        
        # Validate compliance
        validation = soup_service.validate_component_compliance(component_id)
        
        assert validation is not None
        assert isinstance(validation.is_compliant, bool)
        assert isinstance(validation.missing_requirements, list)
        assert isinstance(validation.warnings, list)
        assert isinstance(validation.recommendations, list)
        assert validation.component_id == component_id
    
    def test_audit_trail_creation(self, soup_service, sample_detected_component):
        """Test audit trail creation."""
        # Add component (creates audit entry)
        component_id = soup_service.add_component_with_classification(
            sample_detected_component, "test_user"
        )
        
        # Track version change (creates another audit entry)
        soup_service.track_version_change(
            component_id=component_id,
            new_version="1.1.1l",
            impact_analysis="Test change",
            user="test_user"
        )
        
        # Get audit trail
        audit_entries = soup_service.get_component_audit_trail(component_id)
        
        assert len(audit_entries) >= 2
        
        # Check audit entry structure
        for entry in audit_entries:
            assert entry.component_id == component_id
            assert len(entry.action) > 0
            assert len(entry.user) > 0
            assert isinstance(entry.timestamp, datetime)
            assert isinstance(entry.details, dict)
    
    def test_approve_version_change(self, soup_service, sample_detected_component):
        """Test version change approval."""
        # Add component and track version change
        component_id = soup_service.add_component_with_classification(
            sample_detected_component, "test_user"
        )
        
        soup_service.track_version_change(
            component_id=component_id,
            new_version="1.1.1l",
            impact_analysis="Test change",
            user="test_user"
        )
        
        # Approve the change
        approved = soup_service.approve_version_change(
            component_id=component_id,
            version_change_id="1.1.1k",  # old version
            approver="manager_user"
        )
        
        assert approved is True
        
        # Verify approval in history
        history = soup_service.get_component_version_history(component_id)
        assert len(history) == 1
        assert history[0].approval_status == "approved"
        assert history[0].approver == "manager_user"
    
    def test_safety_assessment(self, soup_service, sample_detected_component):
        """Test safety assessment creation."""
        # Add component
        component_id = soup_service.add_component_with_classification(
            sample_detected_component, "test_user"
        )
        
        # Create safety assessment
        assessment = soup_service.assess_component_safety(
            component_id=component_id,
            safety_impact="Critical security component",
            failure_modes=["Certificate bypass", "Weak encryption"],
            mitigation_measures=["Regular updates", "Security testing"],
            verification_methods=["Penetration testing", "Code review"],
            assessor="security_team"
        )
        
        assert assessment.component_id == component_id
        assert assessment.safety_impact == "Critical security component"
        assert len(assessment.failure_modes) == 2
        assert len(assessment.mitigation_measures) == 2
        assert len(assessment.verification_methods) == 2
        assert assessment.assessor == "security_team"
    
    def test_compliance_summary(self, soup_service):
        """Test compliance summary generation."""
        # Add multiple components with different classifications
        components_data = [
            ("openssl", "1.1.1k"),  # Should be classified as CLASS_C (crypto)
            ("jquery", "3.6.0"),    # Should be classified as CLASS_B (UI)
            ("numpy", "1.21.0")     # Should be classified as CLASS_B (math)
        ]
        
        component_ids = []
        for name, version in components_data:
            detected_component = DetectedSOUPComponent(
                name=name,
                version=version,
                source_file="requirements.txt",
                detection_method=DetectionMethod.REQUIREMENTS_TXT,
                confidence=0.9
            )
            component_id = soup_service.add_component_with_classification(detected_component, "test_user")
            component_ids.append(component_id)
        
        # Get compliance summary
        summary = soup_service.get_compliance_summary()
        
        assert summary["total_components"] == 3
        assert "by_safety_class" in summary
        assert "compliance_status" in summary
        assert "pending_approvals" in summary
        assert "recent_changes" in summary
        
        # Check that components were classified (total should equal sum of classes)
        total_classified = (summary["by_safety_class"]["A"] + 
                          summary["by_safety_class"]["B"] + 
                          summary["by_safety_class"]["C"])
        assert total_classified == 3, f"Expected 3 classified components, got {total_classified}"
        
        # Verify at least one component was classified as CLASS_C (openssl)
        assert summary["by_safety_class"]["C"] >= 1, "Expected at least one Class C component (openssl)"
    
    def test_get_component_classification_not_found(self, soup_service):
        """Test getting classification for non-existent component."""
        classification = soup_service.get_component_classification("non-existent-id")
        assert classification is None
    
    def test_track_version_change_component_not_found(self, soup_service):
        """Test version change tracking for non-existent component."""
        with pytest.raises(ValueError, match="Component .* not found"):
            soup_service.track_version_change(
                component_id="non-existent-id",
                new_version="2.0.0",
                impact_analysis="Test",
                user="test_user"
            )
    
    def test_validate_compliance_component_not_found(self, soup_service):
        """Test compliance validation for non-existent component."""
        with pytest.raises(ValueError, match="Component .* not found"):
            soup_service.validate_component_compliance("non-existent-id")
    
    def test_safety_class_to_criticality_mapping(self, soup_service):
        """Test safety class to criticality mapping."""
        # Test the mapping function
        assert soup_service._map_safety_class_to_criticality(IEC62304SafetyClass.CLASS_A) == "Low"
        assert soup_service._map_safety_class_to_criticality(IEC62304SafetyClass.CLASS_B) == "Medium"
        assert soup_service._map_safety_class_to_criticality(IEC62304SafetyClass.CLASS_C) == "High"
    
    def test_detected_component_validation_error(self, soup_service):
        """Test validation error for invalid detected component."""
        invalid_component = DetectedSOUPComponent(
            name="",  # Invalid: empty name
            version="1.0.0",
            source_file="test.txt",
            detection_method=DetectionMethod.MANUAL,
            confidence=0.5
        )
        
        with pytest.raises(ValueError, match="Detected component validation failed"):
            soup_service.add_component_with_classification(invalid_component, "test_user")
    
    def test_version_change_validation_error(self, soup_service, sample_detected_component):
        """Test validation error for invalid version change."""
        # Add component first
        component_id = soup_service.add_component_with_classification(
            sample_detected_component, "test_user"
        )
        
        # Try to track version change with empty impact analysis
        with pytest.raises(ValueError, match="Version change validation failed"):
            soup_service.track_version_change(
                component_id=component_id,
                new_version="1.1.1l",
                impact_analysis="",  # Invalid: empty impact analysis
                user="test_user"
            )
    
    def test_database_tables_creation(self, soup_service):
        """Test that all required database tables are created."""
        with soup_service.db_manager.get_connection() as conn:
            # Check that all tables exist
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name LIKE 'soup_%'
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = [
                'soup_components',
                'soup_classifications', 
                'soup_version_changes',
                'soup_audit_trail'
            ]
            
            for table in expected_tables:
                assert table in tables, f"Table {table} not found"
    
    def test_classification_persistence(self, soup_service, sample_detected_component):
        """Test that classifications are properly persisted and retrieved."""
        # Add component with classification
        component_id = soup_service.add_component_with_classification(
            sample_detected_component, "test_user"
        )
        
        # Get classification
        classification = soup_service.get_component_classification(component_id)
        
        # Verify all fields are properly stored and retrieved
        assert classification is not None
        assert isinstance(classification.safety_class, IEC62304SafetyClass)
        assert len(classification.justification) > 0
        assert len(classification.risk_assessment) > 0
        assert isinstance(classification.verification_requirements, list)
        assert isinstance(classification.documentation_requirements, list)
        assert isinstance(classification.change_control_requirements, list)
        assert isinstance(classification.created_at, datetime)
        assert isinstance(classification.updated_at, datetime)