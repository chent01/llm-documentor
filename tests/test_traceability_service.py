"""
Unit tests for the traceability service.
"""

import pytest
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, patch

from medical_analyzer.services.traceability_service import (
    TraceabilityService, TraceabilityMatrix, TraceabilityGap, TraceabilityTableRow
)
from medical_analyzer.models.core import (
    TraceabilityLink, CodeReference, Feature, Requirement, RiskItem,
    RequirementType, FeatureCategory, Severity, Probability, RiskLevel
)
from medical_analyzer.database.schema import DatabaseManager


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    db_manager = DatabaseManager(db_path)
    yield db_manager
    
    # Cleanup
    os.unlink(db_path)


@pytest.fixture
def traceability_service(temp_db):
    """Create a traceability service with temporary database."""
    return TraceabilityService(temp_db)


@pytest.fixture
def sample_features():
    """Create sample features for testing."""
    return [
        Feature(
            id="feature_1",
            description="User authentication system",
            confidence=0.9,
            evidence=[
                CodeReference(
                    file_path="src/auth.c",
                    start_line=10,
                    end_line=25,
                    function_name="authenticate_user",
                    context="User login validation"
                ),
                CodeReference(
                    file_path="src/auth.c",
                    start_line=30,
                    end_line=45,
                    function_name="validate_password",
                    context="Password validation"
                )
            ],
            category=FeatureCategory.SAFETY
        ),
        Feature(
            id="feature_2",
            description="Data processing pipeline",
            confidence=0.85,
            evidence=[
                CodeReference(
                    file_path="src/data.js",
                    start_line=50,
                    end_line=80,
                    function_name="processData",
                    context="Main data processing function"
                )
            ],
            category=FeatureCategory.DATA_PROCESSING
        )
    ]


@pytest.fixture
def sample_user_requirements():
    """Create sample user requirements for testing."""
    return [
        Requirement(
            id="UR_001",
            type=RequirementType.USER,
            text="The system shall authenticate users before granting access",
            acceptance_criteria=[
                "User must provide valid credentials",
                "System must verify credentials against database"
            ],
            derived_from=["feature_1"]
        ),
        Requirement(
            id="UR_002",
            type=RequirementType.USER,
            text="The system shall process medical data accurately",
            acceptance_criteria=[
                "Data must be validated before processing",
                "Processing must follow medical standards"
            ],
            derived_from=["feature_2"]
        )
    ]


@pytest.fixture
def sample_software_requirements():
    """Create sample software requirements for testing."""
    return [
        Requirement(
            id="SR_001",
            type=RequirementType.SOFTWARE,
            text="The authentication module shall validate user credentials using secure hash comparison",
            acceptance_criteria=[
                "Use SHA-256 for password hashing",
                "Implement rate limiting for failed attempts"
            ],
            derived_from=["UR_001"]
        ),
        Requirement(
            id="SR_002",
            type=RequirementType.SOFTWARE,
            text="The data processing module shall validate input data format",
            acceptance_criteria=[
                "Check data schema compliance",
                "Reject malformed data with error message"
            ],
            derived_from=["UR_002"]
        )
    ]


@pytest.fixture
def sample_risk_items():
    """Create sample risk items for testing."""
    return [
        RiskItem(
            id="RISK_001",
            hazard="Unauthorized access to patient data",
            cause="Weak authentication mechanism",
            effect="Data breach and privacy violation",
            severity=Severity.SERIOUS,
            probability=Probability.MEDIUM,
            risk_level=RiskLevel.UNDESIRABLE,
            mitigation="Implement strong authentication and access controls",
            verification="Security testing and penetration testing",
            related_requirements=["SR_001"]
        ),
        RiskItem(
            id="RISK_002",
            hazard="Incorrect data processing",
            cause="Invalid input data not properly validated",
            effect="Incorrect medical analysis results",
            severity=Severity.CATASTROPHIC,
            probability=Probability.LOW,
            risk_level=RiskLevel.UNDESIRABLE,
            mitigation="Implement comprehensive input validation",
            verification="Unit testing and integration testing",
            related_requirements=["SR_002"]
        )
    ]


class TestTraceabilityService:
    """Test cases for TraceabilityService."""
    
    def test_init(self, temp_db):
        """Test traceability service initialization."""
        service = TraceabilityService(temp_db)
        assert service.db_manager == temp_db
        assert service.logger is not None
    
    def test_generate_code_reference_id(self, traceability_service):
        """Test code reference ID generation."""
        code_ref = CodeReference(
            file_path="src/test.c",
            start_line=10,
            end_line=20,
            function_name="test_func"
        )
        
        expected_id = "src/test.c:10-20"
        actual_id = traceability_service._generate_code_reference_id(code_ref)
        
        assert actual_id == expected_id
    
    def test_create_code_to_feature_links(self, traceability_service, sample_features):
        """Test creation of code-to-feature traceability links."""
        links = traceability_service._create_code_to_feature_links(1, sample_features)
        
        # Should have 3 links total (2 from feature_1, 1 from feature_2)
        assert len(links) == 3
        
        # Check first link
        link = links[0]
        assert link.source_type == "code"
        assert link.source_id == "src/auth.c:10-25"
        assert link.target_type == "feature"
        assert link.target_id == "feature_1"
        assert link.link_type == "implements"
        assert link.confidence == 0.9
        assert link.metadata["file_path"] == "src/auth.c"
        assert link.metadata["function_name"] == "authenticate_user"
    
    def test_create_feature_to_user_requirement_links(
        self, traceability_service, sample_features, sample_user_requirements
    ):
        """Test creation of feature-to-user-requirement traceability links."""
        links = traceability_service._create_feature_to_user_requirement_links(
            1, sample_features, sample_user_requirements
        )
        
        # Should have 2 links (one for each user requirement)
        assert len(links) == 2
        
        # Check first link
        link = links[0]
        assert link.source_type == "feature"
        assert link.source_id == "feature_1"
        assert link.target_type == "requirement"
        assert link.target_id == "UR_001"
        assert link.link_type == "derives_to"
        assert link.confidence == 0.9  # min(0.9, 0.9)
        assert link.metadata["requirement_type"] == "user"
    
    def test_create_user_to_software_requirement_links(
        self, traceability_service, sample_user_requirements, sample_software_requirements
    ):
        """Test creation of user-to-software-requirement traceability links."""
        links = traceability_service._create_user_to_software_requirement_links(
            1, sample_user_requirements, sample_software_requirements
        )
        
        # Should have 2 links (one for each software requirement)
        assert len(links) == 2
        
        # Check first link
        link = links[0]
        assert link.source_type == "requirement"
        assert link.source_id == "UR_001"
        assert link.target_type == "requirement"
        assert link.target_id == "SR_001"
        assert link.link_type == "derives_to"
        assert link.confidence == 0.95
        assert link.metadata["source_requirement_type"] == "user"
        assert link.metadata["target_requirement_type"] == "software"
    
    def test_create_software_requirement_to_risk_links(
        self, traceability_service, sample_software_requirements, sample_risk_items
    ):
        """Test creation of software-requirement-to-risk traceability links."""
        links = traceability_service._create_software_requirement_to_risk_links(
            1, sample_software_requirements, sample_risk_items
        )
        
        # Should have 2 links (one for each risk item)
        assert len(links) == 2
        
        # Check first link
        link = links[0]
        assert link.source_type == "requirement"
        assert link.source_id == "SR_001"
        assert link.target_type == "risk"
        assert link.target_id == "RISK_001"
        assert link.link_type == "mitigated_by"
        assert link.confidence == 0.9
        assert link.metadata["requirement_type"] == "software"
        assert link.metadata["hazard"] == "Unauthorized access to patient data"
    
    def test_create_transitive_code_to_requirement_links(
        self, traceability_service, sample_features, sample_software_requirements
    ):
        """Test creation of transitive code-to-software-requirement links."""
        # Create mock feature-to-UR and UR-to-SR links
        feature_ur_links = [
            TraceabilityLink(
                id="test_1",
                source_type="feature",
                source_id="feature_1",
                target_type="requirement",
                target_id="UR_001",
                link_type="derives_to",
                confidence=0.9
            )
        ]
        
        ur_sr_links = [
            TraceabilityLink(
                id="test_2",
                source_type="requirement",
                source_id="UR_001",
                target_type="requirement",
                target_id="SR_001",
                link_type="derives_to",
                confidence=0.95
            )
        ]
        
        links = traceability_service._create_transitive_code_to_requirement_links(
            1, sample_features, sample_software_requirements, feature_ur_links, ur_sr_links
        )
        
        # Should have 2 links (2 code references from feature_1)
        assert len(links) == 2
        
        # Check first link
        link = links[0]
        assert link.source_type == "code"
        assert link.source_id == "src/auth.c:10-25"
        assert link.target_type == "requirement"
        assert link.target_id == "SR_001"
        assert link.link_type == "implements"
        assert abs(link.confidence - 0.72) < 0.001  # 0.9 * 0.8 (with floating point tolerance)
        assert link.metadata["via_feature"] == "feature_1"
        assert link.metadata["via_user_requirement"] == "UR_001"
        assert link.metadata["link_type"] == "transitive"
    
    def test_build_mappings(self, traceability_service):
        """Test building of various traceability mappings."""
        # Test code-to-requirement mapping
        code_sr_links = [
            TraceabilityLink(
                id="test_1",
                source_type="code",
                source_id="src/test.c:10-20",
                target_type="requirement",
                target_id="SR_001",
                link_type="implements",
                confidence=0.8
            ),
            TraceabilityLink(
                id="test_2",
                source_type="code",
                source_id="src/test.c:10-20",
                target_type="requirement",
                target_id="SR_002",
                link_type="implements",
                confidence=0.7
            )
        ]
        
        mapping = traceability_service._build_code_to_requirement_mapping(code_sr_links)
        assert "src/test.c:10-20" in mapping
        assert len(mapping["src/test.c:10-20"]) == 2
        assert "SR_001" in mapping["src/test.c:10-20"]
        assert "SR_002" in mapping["src/test.c:10-20"]
        
        # Test UR-to-SR mapping
        ur_sr_links = [
            TraceabilityLink(
                id="test_3",
                source_type="requirement",
                source_id="UR_001",
                target_type="requirement",
                target_id="SR_001",
                link_type="derives_to",
                confidence=0.95
            )
        ]
        
        ur_mapping = traceability_service._build_ur_to_sr_mapping(ur_sr_links)
        assert "UR_001" in ur_mapping
        assert "SR_001" in ur_mapping["UR_001"]
        
        # Test requirement-to-risk mapping
        sr_risk_links = [
            TraceabilityLink(
                id="test_4",
                source_type="requirement",
                source_id="SR_001",
                target_type="risk",
                target_id="RISK_001",
                link_type="mitigated_by",
                confidence=0.9
            )
        ]
        
        risk_mapping = traceability_service._build_requirement_to_risk_mapping(sr_risk_links)
        assert "SR_001" in risk_mapping
        assert "RISK_001" in risk_mapping["SR_001"]
    
    @patch('medical_analyzer.services.traceability_service.datetime')
    def test_create_traceability_matrix(
        self, mock_datetime, traceability_service, sample_features, 
        sample_user_requirements, sample_software_requirements, sample_risk_items
    ):
        """Test complete traceability matrix creation."""
        # Mock datetime.now()
        mock_now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        matrix = traceability_service.create_traceability_matrix(
            analysis_run_id=1,
            features=sample_features,
            user_requirements=sample_user_requirements,
            software_requirements=sample_software_requirements,
            risk_items=sample_risk_items
        )
        
        assert matrix.analysis_run_id == 1
        assert len(matrix.links) > 0
        assert matrix.created_at == mock_now
        
        # Check that all mapping dictionaries are populated
        assert len(matrix.code_to_requirements) > 0
        assert len(matrix.user_to_software_requirements) > 0
        assert len(matrix.requirements_to_risks) > 0
        
        # Check metadata
        assert "total_links" in matrix.metadata
        assert "code_feature_links" in matrix.metadata
        assert "feature_ur_links" in matrix.metadata
        assert "ur_sr_links" in matrix.metadata
        assert "sr_risk_links" in matrix.metadata
        assert "code_sr_links" in matrix.metadata
    
    def test_validate_traceability_matrix(self, traceability_service):
        """Test traceability matrix validation."""
        # Create a valid matrix
        valid_links = [
            TraceabilityLink(
                id="test_1",
                source_type="feature",
                source_id="feature_1",
                target_type="requirement",
                target_id="UR_001",
                link_type="derives_to",
                confidence=0.9
            ),
            TraceabilityLink(
                id="test_2",
                source_type="requirement",
                source_id="UR_001",
                target_type="requirement",
                target_id="SR_001",
                link_type="derives_to",
                confidence=0.95
            )
        ]
        
        valid_matrix = TraceabilityMatrix(
            analysis_run_id=1,
            links=valid_links,
            code_to_requirements={},
            user_to_software_requirements={"UR_001": ["SR_001"]},
            requirements_to_risks={},
            metadata={"total_links": 2},
            created_at=datetime.now()
        )
        
        issues = traceability_service.validate_traceability_matrix(valid_matrix)
        assert len(issues) == 0
        
        # Create a matrix with issues
        low_confidence_links = [
            TraceabilityLink(
                id="test_3",
                source_type="feature",
                source_id="feature_1",
                target_type="requirement",
                target_id="UR_001",
                link_type="derives_to",
                confidence=0.3  # Low confidence
            )
        ]
        
        problematic_matrix = TraceabilityMatrix(
            analysis_run_id=1,
            links=low_confidence_links,
            code_to_requirements={},
            user_to_software_requirements={},
            requirements_to_risks={},
            metadata={"total_links": 1},
            created_at=datetime.now()
        )
        
        issues = traceability_service.validate_traceability_matrix(problematic_matrix)
        assert len(issues) > 0
        assert any("low confidence" in issue.lower() for issue in issues)
    
    def test_get_traceability_matrix_empty(self, traceability_service):
        """Test retrieving traceability matrix when no links exist."""
        matrix = traceability_service.get_traceability_matrix(999)
        assert matrix is None
    
    def test_database_integration(self, traceability_service, temp_db):
        """Test integration with database for storing and retrieving links."""
        # Create a project and analysis run
        project_id = temp_db.create_project("Test Project", "/test/path", "Test description")
        analysis_run_id = temp_db.create_analysis_run(project_id, "/test/artifacts")
        
        # Create a simple traceability link
        link_id = temp_db.create_traceability_link(
            analysis_run_id=analysis_run_id,
            source_type="code",
            source_id="test.c:10-20",
            target_type="requirement",
            target_id="SR_001",
            link_type="implements",
            confidence=0.8,
            metadata={"test": "data"}
        )
        
        assert link_id > 0
        
        # Retrieve the matrix
        matrix = traceability_service.get_traceability_matrix(analysis_run_id)
        assert matrix is not None
        assert len(matrix.links) == 1
        
        link = matrix.links[0]
        assert link.source_type == "code"
        assert link.source_id == "test.c:10-20"
        assert link.target_type == "requirement"
        assert link.target_id == "SR_001"
        assert link.link_type == "implements"
        assert link.confidence == 0.8
        assert link.metadata["test"] == "data"


class TestTraceabilityMatrix:
    """Test cases for TraceabilityMatrix dataclass."""
    
    def test_traceability_matrix_creation(self):
        """Test TraceabilityMatrix creation and attributes."""
        links = [
            TraceabilityLink(
                id="test_1",
                source_type="code",
                source_id="test.c:10-20",
                target_type="requirement",
                target_id="SR_001",
                link_type="implements",
                confidence=0.8
            )
        ]
        
        matrix = TraceabilityMatrix(
            analysis_run_id=1,
            links=links,
            code_to_requirements={"test.c:10-20": ["SR_001"]},
            user_to_software_requirements={"UR_001": ["SR_001"]},
            requirements_to_risks={"SR_001": ["RISK_001"]},
            metadata={"total_links": 1},
            created_at=datetime.now()
        )
        
        assert matrix.analysis_run_id == 1
        assert len(matrix.links) == 1
        assert "test.c:10-20" in matrix.code_to_requirements
        assert "UR_001" in matrix.user_to_software_requirements
        assert "SR_001" in matrix.requirements_to_risks
        assert matrix.metadata["total_links"] == 1
        assert isinstance(matrix.created_at, datetime)


class TestTraceabilityMatrixDisplay:
    """Test cases for traceability matrix display functionality."""
    
    def test_generate_tabular_matrix(
        self, traceability_service, sample_features, sample_user_requirements,
        sample_software_requirements, sample_risk_items
    ):
        """Test generation of tabular traceability matrix."""
        # Create a complete traceability matrix
        matrix = traceability_service.create_traceability_matrix(
            analysis_run_id=1,
            features=sample_features,
            user_requirements=sample_user_requirements,
            software_requirements=sample_software_requirements,
            risk_items=sample_risk_items
        )
        
        # Generate tabular representation
        rows = traceability_service.generate_tabular_matrix(
            matrix, sample_features, sample_user_requirements,
            sample_software_requirements, sample_risk_items
        )
        
        assert len(rows) > 0
        
        # Check first row structure
        row = rows[0]
        assert hasattr(row, 'code_reference')
        assert hasattr(row, 'file_path')
        assert hasattr(row, 'function_name')
        assert hasattr(row, 'feature_id')
        assert hasattr(row, 'feature_description')
        assert hasattr(row, 'user_requirement_id')
        assert hasattr(row, 'software_requirement_id')
        assert hasattr(row, 'risk_id')
        assert hasattr(row, 'confidence')
        
        # Verify data integrity
        assert row.code_reference != ""
        assert row.file_path != ""
        assert row.feature_id != ""
        assert 0.0 <= row.confidence <= 1.0
    
    def test_export_to_csv_basic(
        self, traceability_service, sample_features, sample_user_requirements,
        sample_software_requirements, sample_risk_items
    ):
        """Test basic CSV export functionality."""
        matrix = traceability_service.create_traceability_matrix(
            analysis_run_id=1,
            features=sample_features,
            user_requirements=sample_user_requirements,
            software_requirements=sample_software_requirements,
            risk_items=sample_risk_items
        )
        
        csv_content = traceability_service.export_to_csv(
            matrix, sample_features, sample_user_requirements,
            sample_software_requirements, sample_risk_items
        )
        
        assert isinstance(csv_content, str)
        assert len(csv_content) > 0
        
        # Check CSV structure
        lines = csv_content.strip().split('\n')
        assert len(lines) > 1  # At least header + one data row
        
        # Check header
        header = lines[0]
        expected_columns = [
            "Code Reference", "File Path", "Function Name", "Feature ID",
            "Feature Description", "User Requirement ID", "User Requirement Text",
            "Software Requirement ID", "Software Requirement Text", 
            "Risk ID", "Risk Hazard", "Confidence"
        ]
        
        for column in expected_columns:
            assert column in header
    
    def test_export_to_csv_with_metadata(
        self, traceability_service, sample_features, sample_user_requirements,
        sample_software_requirements, sample_risk_items
    ):
        """Test CSV export with metadata columns."""
        matrix = traceability_service.create_traceability_matrix(
            analysis_run_id=1,
            features=sample_features,
            user_requirements=sample_user_requirements,
            software_requirements=sample_software_requirements,
            risk_items=sample_risk_items
        )
        
        csv_content = traceability_service.export_to_csv(
            matrix, sample_features, sample_user_requirements,
            sample_software_requirements, sample_risk_items,
            include_metadata=True
        )
        
        lines = csv_content.strip().split('\n')
        header = lines[0]
        
        # Check for metadata columns
        assert "Analysis Run ID" in header
        assert "Export Timestamp" in header
        assert "Total Links" in header
        assert "Link Types" in header
    
    def test_detect_traceability_gaps_complete_matrix(
        self, traceability_service, sample_features, sample_user_requirements,
        sample_software_requirements, sample_risk_items
    ):
        """Test gap detection with complete traceability matrix."""
        matrix = traceability_service.create_traceability_matrix(
            analysis_run_id=1,
            features=sample_features,
            user_requirements=sample_user_requirements,
            software_requirements=sample_software_requirements,
            risk_items=sample_risk_items
        )
        
        gaps = traceability_service.detect_traceability_gaps(
            matrix, sample_features, sample_user_requirements,
            sample_software_requirements, sample_risk_items
        )
        
        # Should have minimal gaps in a well-formed matrix
        assert isinstance(gaps, list)
        
        # Check gap structure
        if gaps:
            gap = gaps[0]
            assert hasattr(gap, 'gap_type')
            assert hasattr(gap, 'source_type')
            assert hasattr(gap, 'source_id')
            assert hasattr(gap, 'description')
            assert hasattr(gap, 'severity')
            assert hasattr(gap, 'recommendation')
            
            assert gap.severity in ['low', 'medium', 'high']
    
    def test_detect_traceability_gaps_with_orphans(self, traceability_service):
        """Test gap detection with orphaned elements."""
        # Create incomplete data with orphans
        orphaned_feature = Feature(
            id="orphan_feature",
            description="Orphaned feature with no requirements",
            confidence=0.8,
            evidence=[
                CodeReference(
                    file_path="src/orphan.c",
                    start_line=1,
                    end_line=10,
                    function_name="orphan_func"
                )
            ]
        )
        
        orphaned_ur = Requirement(
            id="UR_ORPHAN",
            type=RequirementType.USER,
            text="Orphaned user requirement",
            derived_from=["nonexistent_feature"]
        )
        
        orphaned_risk = RiskItem(
            id="RISK_ORPHAN",
            hazard="Orphaned risk",
            cause="No linked requirements",
            effect="Unmitigated risk",
            severity=Severity.SERIOUS,
            probability=Probability.MEDIUM,
            risk_level=RiskLevel.UNDESIRABLE,
            mitigation="Link to requirements",
            verification="Review traceability",
            related_requirements=[]  # No related requirements
        )
        
        # Create empty matrix
        empty_matrix = TraceabilityMatrix(
            analysis_run_id=1,
            links=[],
            code_to_requirements={},
            user_to_software_requirements={},
            requirements_to_risks={},
            metadata={},
            created_at=datetime.now()
        )
        
        gaps = traceability_service.detect_traceability_gaps(
            empty_matrix, [orphaned_feature], [orphaned_ur], [], [orphaned_risk]
        )
        
        assert len(gaps) > 0
        
        # Check for specific gap types
        gap_types = [gap.gap_type for gap in gaps]
        assert "orphaned_code" in gap_types
        assert "orphaned_feature" in gap_types
        assert "orphaned_requirement" in gap_types
        assert "orphaned_risk" in gap_types
    
    def test_generate_gap_report(self, traceability_service):
        """Test gap report generation."""
        # Create sample gaps
        gaps = [
            TraceabilityGap(
                gap_type="orphaned_feature",
                source_type="feature",
                source_id="feature_1",
                description="Feature has no requirements",
                severity="high",
                recommendation="Create user requirement"
            ),
            TraceabilityGap(
                gap_type="weak_link",
                source_type="code",
                source_id="test.c:10-20",
                target_type="requirement",
                target_id="SR_001",
                description="Low confidence link",
                severity="low",
                recommendation="Review evidence"
            )
        ]
        
        report = traceability_service.generate_gap_report(gaps)
        
        assert isinstance(report, str)
        assert "TRACEABILITY GAP ANALYSIS REPORT" in report
        assert "Total gaps detected: 2" in report
        assert "High severity: 1" in report
        assert "Low severity: 1" in report
        assert "Feature has no requirements" in report
        assert "Low confidence link" in report
    
    def test_generate_gap_report_no_gaps(self, traceability_service):
        """Test gap report generation with no gaps."""
        report = traceability_service.generate_gap_report([])
        
        assert "No traceability gaps detected" in report
        assert "Traceability matrix is complete" in report


class TestTraceabilityIntegration:
    """Integration tests for complete traceability pipeline."""
    
    def test_end_to_end_traceability_pipeline(
        self, traceability_service, temp_db, sample_features,
        sample_user_requirements, sample_software_requirements, sample_risk_items
    ):
        """Test complete end-to-end traceability pipeline."""
        # 1. Create project and analysis run
        project_id = temp_db.create_project(
            "Integration Test Project", 
            "/test/path", 
            "Test project for integration testing"
        )
        analysis_run_id = temp_db.create_analysis_run(project_id, "/test/artifacts")
        
        # 2. Create traceability matrix
        matrix = traceability_service.create_traceability_matrix(
            analysis_run_id=analysis_run_id,
            features=sample_features,
            user_requirements=sample_user_requirements,
            software_requirements=sample_software_requirements,
            risk_items=sample_risk_items
        )
        
        # 3. Verify matrix creation
        assert matrix.analysis_run_id == analysis_run_id
        assert len(matrix.links) > 0
        assert len(matrix.code_to_requirements) > 0
        assert len(matrix.user_to_software_requirements) > 0
        assert len(matrix.requirements_to_risks) > 0
        
        # 4. Generate tabular display
        rows = traceability_service.generate_tabular_matrix(
            matrix, sample_features, sample_user_requirements,
            sample_software_requirements, sample_risk_items
        )
        assert len(rows) > 0
        
        # 5. Export to CSV
        csv_content = traceability_service.export_to_csv(
            matrix, sample_features, sample_user_requirements,
            sample_software_requirements, sample_risk_items
        )
        assert len(csv_content) > 0
        
        # 6. Detect gaps
        gaps = traceability_service.detect_traceability_gaps(
            matrix, sample_features, sample_user_requirements,
            sample_software_requirements, sample_risk_items
        )
        assert isinstance(gaps, list)
        
        # 7. Generate gap report
        gap_report = traceability_service.generate_gap_report(gaps)
        assert isinstance(gap_report, str)
        
        # 8. Validate matrix
        validation_issues = traceability_service.validate_traceability_matrix(matrix)
        assert isinstance(validation_issues, list)
        
        # 9. Retrieve matrix from database
        retrieved_matrix = traceability_service.get_traceability_matrix(analysis_run_id)
        assert retrieved_matrix is not None
        assert retrieved_matrix.analysis_run_id == analysis_run_id
        assert len(retrieved_matrix.links) == len(matrix.links)
    
    def test_large_scale_traceability_performance(self, traceability_service, temp_db):
        """Test traceability performance with larger datasets."""
        import time
        
        # Create larger dataset
        large_features = []
        large_urs = []
        large_srs = []
        large_risks = []
        
        # Generate 50 features with multiple code references each
        for i in range(50):
            feature = Feature(
                id=f"feature_{i:03d}",
                description=f"Feature {i} description",
                confidence=0.8 + (i % 3) * 0.05,
                evidence=[
                    CodeReference(
                        file_path=f"src/module_{i//10}.c",
                        start_line=i * 10 + 1,
                        end_line=i * 10 + 15,
                        function_name=f"function_{i}"
                    ),
                    CodeReference(
                        file_path=f"src/module_{i//10}.c", 
                        start_line=i * 10 + 20,
                        end_line=i * 10 + 30,
                        function_name=f"helper_{i}"
                    )
                ]
            )
            large_features.append(feature)
            
            # Create corresponding UR
            ur = Requirement(
                id=f"UR_{i:03d}",
                type=RequirementType.USER,
                text=f"User requirement {i} text",
                derived_from=[f"feature_{i:03d}"]
            )
            large_urs.append(ur)
            
            # Create 2 SRs per UR
            for j in range(2):
                sr = Requirement(
                    id=f"SR_{i:03d}_{j}",
                    type=RequirementType.SOFTWARE,
                    text=f"Software requirement {i}.{j} text",
                    derived_from=[f"UR_{i:03d}"]
                )
                large_srs.append(sr)
                
                # Create risk for each SR
                risk = RiskItem(
                    id=f"RISK_{i:03d}_{j}",
                    hazard=f"Hazard for requirement {i}.{j}",
                    cause=f"Cause {i}.{j}",
                    effect=f"Effect {i}.{j}",
                    severity=Severity.SERIOUS if i % 3 == 0 else Severity.MINOR,
                    probability=Probability.MEDIUM,
                    risk_level=RiskLevel.UNDESIRABLE,
                    mitigation=f"Mitigation {i}.{j}",
                    verification=f"Verification {i}.{j}",
                    related_requirements=[f"SR_{i:03d}_{j}"]
                )
                large_risks.append(risk)
        
        # Create project
        project_id = temp_db.create_project(
            "Large Scale Test", "/test/large", "Performance test"
        )
        analysis_run_id = temp_db.create_analysis_run(project_id, "/test/artifacts")
        
        # Time the matrix creation
        start_time = time.time()
        matrix = traceability_service.create_traceability_matrix(
            analysis_run_id=analysis_run_id,
            features=large_features,
            user_requirements=large_urs,
            software_requirements=large_srs,
            risk_items=large_risks
        )
        matrix_time = time.time() - start_time
        
        # Time the tabular generation
        start_time = time.time()
        rows = traceability_service.generate_tabular_matrix(
            matrix, large_features, large_urs, large_srs, large_risks
        )
        tabular_time = time.time() - start_time
        
        # Time the CSV export
        start_time = time.time()
        csv_content = traceability_service.export_to_csv(
            matrix, large_features, large_urs, large_srs, large_risks
        )
        csv_time = time.time() - start_time
        
        # Time gap detection
        start_time = time.time()
        gaps = traceability_service.detect_traceability_gaps(
            matrix, large_features, large_urs, large_srs, large_risks
        )
        gap_time = time.time() - start_time
        
        # Verify results
        assert len(matrix.links) > 0
        assert len(rows) > 0
        assert len(csv_content) > 0
        
        # Performance assertions (should complete within reasonable time)
        assert matrix_time < 30.0  # Matrix creation should take < 30 seconds
        assert tabular_time < 10.0  # Tabular generation should take < 10 seconds
        assert csv_time < 10.0      # CSV export should take < 10 seconds
        assert gap_time < 10.0      # Gap detection should take < 10 seconds
        
        print(f"Performance metrics for {len(large_features)} features:")
        print(f"  Matrix creation: {matrix_time:.3f}s")
        print(f"  Tabular generation: {tabular_time:.3f}s")
        print(f"  CSV export: {csv_time:.3f}s")
        print(f"  Gap detection: {gap_time:.3f}s")
        print(f"  Total links: {len(matrix.links)}")
        print(f"  Total rows: {len(rows)}")
        print(f"  Detected gaps: {len(gaps)}")
    
    def test_traceability_data_consistency(
        self, traceability_service, temp_db, sample_features,
        sample_user_requirements, sample_software_requirements, sample_risk_items
    ):
        """Test data consistency across different traceability operations."""
        # Create matrix
        project_id = temp_db.create_project("Consistency Test", "/test", "Test")
        analysis_run_id = temp_db.create_analysis_run(project_id, "/test/artifacts")
        
        matrix = traceability_service.create_traceability_matrix(
            analysis_run_id=analysis_run_id,
            features=sample_features,
            user_requirements=sample_user_requirements,
            software_requirements=sample_software_requirements,
            risk_items=sample_risk_items
        )
        
        # Generate tabular representation
        rows = traceability_service.generate_tabular_matrix(
            matrix, sample_features, sample_user_requirements,
            sample_software_requirements, sample_risk_items
        )
        
        # Verify consistency between matrix and tabular representation
        # Count unique entities in matrix
        matrix_features = set()
        matrix_urs = set()
        matrix_srs = set()
        matrix_risks = set()
        
        for link in matrix.links:
            if link.source_type == "feature":
                matrix_features.add(link.source_id)
            elif link.target_type == "feature":
                matrix_features.add(link.target_id)
            
            if (link.source_type == "requirement" and 
                link.metadata.get("source_requirement_type") == "user"):
                matrix_urs.add(link.source_id)
            elif (link.target_type == "requirement" and
                  link.metadata.get("target_requirement_type") == "software"):
                matrix_srs.add(link.target_id)
            elif link.target_type == "risk":
                matrix_risks.add(link.target_id)
        
        # Count unique entities in tabular representation
        table_features = set(row.feature_id for row in rows if row.feature_id)
        table_urs = set(row.user_requirement_id for row in rows if row.user_requirement_id)
        table_srs = set(row.software_requirement_id for row in rows if row.software_requirement_id)
        table_risks = set(row.risk_id for row in rows if row.risk_id)
        
        # Verify consistency (tabular should be subset of matrix due to filtering)
        assert table_features.issubset(matrix_features) or len(table_features) >= len(matrix_features)
        assert table_urs.issubset(matrix_urs) or len(table_urs) >= len(matrix_urs)
        assert table_srs.issubset(matrix_srs) or len(table_srs) >= len(matrix_srs)
        assert table_risks.issubset(matrix_risks) or len(table_risks) >= len(matrix_risks)


if __name__ == "__main__":
    pytest.main([__file__])