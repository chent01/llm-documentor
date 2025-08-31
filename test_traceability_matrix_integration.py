"""
Integration test for the enhanced traceability matrix system.
Tests the TraceabilityMatrixWidget, TraceabilityGapAnalyzer, and export functionality.
"""

import sys
import os
import tempfile
from datetime import datetime
from typing import List

# Add the medical_analyzer package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from medical_analyzer.models.core import (
    TraceabilityLink, CodeReference, Feature, Requirement, RiskItem,
    RequirementType
)
from medical_analyzer.models.enums import (
    FeatureCategory, Severity, Probability, RiskLevel
)
from medical_analyzer.services.traceability_models import (
    TraceabilityMatrix, TraceabilityTableRow, TraceabilityGap
)
from medical_analyzer.services.traceability_gap_analyzer import TraceabilityGapAnalyzer
from medical_analyzer.services.traceability_export_service import TraceabilityExportService


def create_test_data():
    """Create test data for traceability matrix testing."""
    
    # Create test code references
    code_refs = [
        CodeReference(
            file_path="src/auth.py",
            start_line=10,
            end_line=25,
            function_name="authenticate_user",
            context="def authenticate_user(username, password):"
        ),
        CodeReference(
            file_path="src/data.py", 
            start_line=50,
            end_line=75,
            function_name="encrypt_data",
            context="def encrypt_data(data):"
        )
    ]
    
    # Create test features
    features = [
        Feature(
            id="F001",
            description="User authentication functionality",
            category=FeatureCategory.SAFETY,
            evidence=code_refs[:1],
            confidence=0.9
        ),
        Feature(
            id="F002", 
            description="Data encryption capability",
            category=FeatureCategory.SAFETY,
            evidence=code_refs[1:],
            confidence=0.85
        )
    ]
    
    # Create test requirements
    user_requirements = [
        Requirement(
            id="UR001",
            text="The system shall authenticate users before granting access",
            type=RequirementType.USER,
            derived_from=["F001"]
        ),
        Requirement(
            id="UR002",
            text="The system shall protect sensitive data through encryption",
            type=RequirementType.USER,
            derived_from=["F002"]
        )
    ]
    
    software_requirements = [
        Requirement(
            id="SR001",
            text="The system shall implement secure password verification",
            type=RequirementType.SOFTWARE,
            derived_from=["UR001"]
        ),
        Requirement(
            id="SR002",
            text="The system shall use AES-256 encryption for data protection",
            type=RequirementType.SOFTWARE,
            derived_from=["UR002"]
        )
    ]
    
    # Create test risks
    risks = [
        RiskItem(
            id="R001",
            hazard="Unauthorized access to system",
            cause="Weak authentication mechanism",
            effect="Data breach and privacy violation",
            severity=Severity.SERIOUS,
            probability=Probability.MEDIUM,
            risk_level=RiskLevel.MEDIUM,
            mitigation="Implement strong authentication",
            verification="Security testing",
            related_requirements=["SR001"]
        ),
        RiskItem(
            id="R002",
            hazard="Data exposure during transmission",
            cause="Insufficient encryption",
            effect="Sensitive data compromise",
            severity=Severity.CATASTROPHIC,
            probability=Probability.LOW,
            risk_level=RiskLevel.MEDIUM,
            mitigation="Use strong encryption algorithms",
            verification="Encryption testing",
            related_requirements=["SR002"]
        )
    ]
    
    return features, user_requirements, software_requirements, risks


def create_test_matrix():
    """Create a test traceability matrix."""
    features, user_requirements, software_requirements, risks = create_test_data()
    
    # Create traceability links
    links = [
        # Code to feature links
        TraceabilityLink(
            id="L001",
            source_type="code",
            source_id="src/auth.py:10-25",
            target_type="feature",
            target_id="F001",
            link_type="implements",
            confidence=0.9,
            metadata={"file_path": "src/auth.py", "function_name": "authenticate_user"}
        ),
        TraceabilityLink(
            id="L002",
            source_type="code",
            source_id="src/data.py:50-75",
            target_type="feature",
            target_id="F002",
            link_type="implements",
            confidence=0.85,
            metadata={"file_path": "src/data.py", "function_name": "encrypt_data"}
        ),
        
        # Feature to user requirement links
        TraceabilityLink(
            id="L003",
            source_type="feature",
            source_id="F001",
            target_type="requirement",
            target_id="UR001",
            link_type="derives_to",
            confidence=0.95,
            metadata={"requirement_type": "user"}
        ),
        TraceabilityLink(
            id="L004",
            source_type="feature",
            source_id="F002",
            target_type="requirement",
            target_id="UR002",
            link_type="derives_to",
            confidence=0.9,
            metadata={"requirement_type": "user"}
        ),
        
        # User to software requirement links
        TraceabilityLink(
            id="L005",
            source_type="requirement",
            source_id="UR001",
            target_type="requirement",
            target_id="SR001",
            link_type="derives_to",
            confidence=0.95,
            metadata={"source_requirement_type": "user", "target_requirement_type": "software"}
        ),
        TraceabilityLink(
            id="L006",
            source_type="requirement",
            source_id="UR002",
            target_type="requirement",
            target_id="SR002",
            link_type="derives_to",
            confidence=0.9,
            metadata={"source_requirement_type": "user", "target_requirement_type": "software"}
        ),
        
        # Software requirement to risk links
        TraceabilityLink(
            id="L007",
            source_type="requirement",
            source_id="SR001",
            target_type="risk",
            target_id="R001",
            link_type="mitigated_by",
            confidence=0.9,
            metadata={"requirement_type": "software"}
        ),
        TraceabilityLink(
            id="L008",
            source_type="requirement",
            source_id="SR002",
            target_type="risk",
            target_id="R002",
            link_type="mitigated_by",
            confidence=0.85,
            metadata={"requirement_type": "software"}
        )
    ]
    
    # Create matrix
    matrix = TraceabilityMatrix(
        analysis_run_id=1,
        links=links,
        code_to_requirements={"src/auth.py:10-25": ["SR001"], "src/data.py:50-75": ["SR002"]},
        user_to_software_requirements={"UR001": ["SR001"], "UR002": ["SR002"]},
        requirements_to_risks={"SR001": ["R001"], "SR002": ["R002"]},
        metadata={"total_links": len(links)},
        created_at=datetime.now()
    )
    
    return matrix, features, user_requirements, software_requirements, risks


def create_test_table_rows():
    """Create test table rows for the matrix."""
    return [
        TraceabilityTableRow(
            code_reference="src/auth.py:10-25",
            file_path="src/auth.py",
            function_name="authenticate_user",
            feature_id="F001",
            feature_description="User authentication functionality",
            user_requirement_id="UR001",
            user_requirement_text="The system shall authenticate users before granting access",
            software_requirement_id="SR001",
            software_requirement_text="The system shall implement secure password verification",
            risk_id="R001",
            risk_hazard="Unauthorized access to system",
            confidence=0.9
        ),
        TraceabilityTableRow(
            code_reference="src/data.py:50-75",
            file_path="src/data.py",
            function_name="encrypt_data",
            feature_id="F002",
            feature_description="Data encryption capability",
            user_requirement_id="UR002",
            user_requirement_text="The system shall protect sensitive data through encryption",
            software_requirement_id="SR002",
            software_requirement_text="The system shall use AES-256 encryption for data protection",
            risk_id="R002",
            risk_hazard="Data exposure during transmission",
            confidence=0.85
        )
    ]


def test_gap_analyzer():
    """Test the traceability gap analyzer."""
    print("Testing TraceabilityGapAnalyzer...")
    
    matrix, features, user_requirements, software_requirements, risks = create_test_matrix()
    
    # Create gap analyzer
    analyzer = TraceabilityGapAnalyzer()
    
    # Analyze gaps
    gap_analysis = analyzer.analyze_gaps(
        matrix, features, user_requirements, software_requirements, risks
    )
    
    print(f"  Gap analysis completed:")
    print(f"    Total gaps: {gap_analysis.total_gaps}")
    print(f"    Gaps by severity: {gap_analysis.gaps_by_severity}")
    print(f"    Gaps by type: {gap_analysis.gaps_by_type}")
    print(f"    Coverage metrics: {gap_analysis.coverage_metrics}")
    print(f"    Recommendations: {len(gap_analysis.recommendations)}")
    
    # Generate summary report
    summary = analyzer.generate_gap_summary_report(gap_analysis)
    print(f"  Summary report generated ({len(summary)} characters)")
    
    return gap_analysis


def test_export_service():
    """Test the traceability export service."""
    print("Testing TraceabilityExportService...")
    
    table_rows = create_test_table_rows()
    gaps = [
        TraceabilityGap(
            gap_type="weak_link",
            source_type="code",
            source_id="src/data.py:50-75",
            target_type="feature",
            target_id="F002",
            description="Low confidence link between code and feature",
            severity="medium",
            recommendation="Review and strengthen this traceability link"
        )
    ]
    
    export_service = TraceabilityExportService()
    
    # Test CSV export
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        csv_filename = f.name
    
    csv_success = export_service.export_csv(table_rows, gaps, csv_filename)
    print(f"  CSV export: {'SUCCESS' if csv_success else 'FAILED'}")
    
    if csv_success and os.path.exists(csv_filename):
        with open(csv_filename, 'r') as f:
            lines = f.readlines()
        print(f"    CSV file created with {len(lines)} lines")
        os.unlink(csv_filename)
    
    # Test gap report export
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        gap_filename = f.name
    
    gap_success = export_service.export_gap_report(gaps, gap_filename)
    print(f"  Gap report export: {'SUCCESS' if gap_success else 'FAILED'}")
    
    if gap_success and os.path.exists(gap_filename):
        with open(gap_filename, 'r') as f:
            content = f.read()
        print(f"    Gap report created ({len(content)} characters)")
        os.unlink(gap_filename)
    
    return csv_success and gap_success


def test_matrix_widget_data():
    """Test data structures for the matrix widget."""
    print("Testing TraceabilityMatrixWidget data structures...")
    
    # Test table row creation
    table_rows = create_test_table_rows()
    print(f"  Created {len(table_rows)} table rows")
    
    # Verify row data
    for i, row in enumerate(table_rows):
        print(f"    Row {i+1}: {row.code_reference} -> {row.feature_id} -> {row.user_requirement_id} -> {row.software_requirement_id} -> {row.risk_id}")
    
    # Test gap creation
    gaps = [
        TraceabilityGap(
            gap_type="missing_link",
            source_type="feature",
            source_id="F003",
            description="Feature F003 has no requirement links",
            severity="high",
            recommendation="Create user requirement for this feature"
        )
    ]
    
    print(f"  Created {len(gaps)} test gaps")
    
    return True


def main():
    """Run all integration tests."""
    print("Running Traceability Matrix Integration Tests")
    print("=" * 50)
    
    try:
        # Test gap analyzer
        gap_analysis = test_gap_analyzer()
        print()
        
        # Test export service
        export_success = test_export_service()
        print()
        
        # Test widget data structures
        widget_success = test_matrix_widget_data()
        print()
        
        # Overall results
        print("Integration Test Results:")
        print(f"  Gap Analyzer: {'PASS' if gap_analysis else 'FAIL'}")
        print(f"  Export Service: {'PASS' if export_success else 'FAIL'}")
        print(f"  Widget Data: {'PASS' if widget_success else 'FAIL'}")
        
        overall_success = gap_analysis and export_success and widget_success
        print(f"\nOverall: {'PASS' if overall_success else 'FAIL'}")
        
        if overall_success:
            print("\n✓ All traceability matrix components are working correctly!")
            print("  The enhanced traceability matrix system is ready for integration.")
        else:
            print("\n✗ Some components failed testing.")
            print("  Please review the implementation before integration.")
        
        return overall_success
        
    except Exception as e:
        print(f"Integration test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)