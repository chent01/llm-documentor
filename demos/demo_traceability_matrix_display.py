#!/usr/bin/env python3
"""
Demo script for traceability matrix display and export functionality.

This script demonstrates the tabular display and CSV export capabilities
of the TraceabilityService, including gap detection and reporting.
"""

import tempfile
import os
from datetime import datetime

from medical_analyzer.services.traceability_service import TraceabilityService
from medical_analyzer.models.core import (
    CodeReference, Feature, Requirement, RiskItem,
    RequirementType, FeatureCategory, Severity, Probability, RiskLevel
)
from medical_analyzer.database.schema import DatabaseManager


def create_comprehensive_sample_data():
    """Create comprehensive sample data including some gaps for demonstration."""
    
    # Sample features with code references
    features = [
        Feature(
            id="feature_auth",
            description="User authentication and authorization system",
            confidence=0.92,
            evidence=[
                CodeReference(
                    file_path="src/auth/login.c",
                    start_line=45,
                    end_line=78,
                    function_name="authenticate_user",
                    context="Main authentication function"
                ),
                CodeReference(
                    file_path="src/auth/session.c",
                    start_line=12,
                    end_line=35,
                    function_name="create_session",
                    context="Session management"
                )
            ],
            category=FeatureCategory.SAFETY
        ),
        Feature(
            id="feature_data_proc",
            description="Medical data processing and validation",
            confidence=0.88,
            evidence=[
                CodeReference(
                    file_path="src/data/processor.js",
                    start_line=120,
                    end_line=180,
                    function_name="processPatientData",
                    context="Main data processing pipeline"
                ),
                CodeReference(
                    file_path="src/data/validator.js",
                    start_line=25,
                    end_line=60,
                    function_name="validateMedicalData",
                    context="Data validation logic"
                )
            ],
            category=FeatureCategory.DATA_PROCESSING
        ),
        # Orphaned feature (no requirements will be created for this)
        Feature(
            id="feature_orphan",
            description="Orphaned feature with no requirements",
            confidence=0.75,
            evidence=[
                CodeReference(
                    file_path="src/utils/helper.c",
                    start_line=10,
                    end_line=25,
                    function_name="helper_function",
                    context="Utility function"
                )
            ],
            category=FeatureCategory.UTILITY
        )
    ]
    
    # Sample user requirements (missing one for orphaned feature)
    user_requirements = [
        Requirement(
            id="UR_001",
            type=RequirementType.USER,
            text="The system shall authenticate healthcare providers before allowing access to patient data",
            acceptance_criteria=[
                "User must provide valid credentials",
                "System must verify credentials against secure database",
                "Failed authentication attempts must be logged"
            ],
            derived_from=["feature_auth"]
        ),
        Requirement(
            id="UR_002", 
            type=RequirementType.USER,
            text="The system shall process and validate medical data according to healthcare standards",
            acceptance_criteria=[
                "Data must conform to HL7 FHIR standards",
                "Invalid data must be rejected with clear error messages",
                "Processing must maintain data integrity"
            ],
            derived_from=["feature_data_proc"]
        ),
        # Orphaned user requirement (no software requirements will be created)
        Requirement(
            id="UR_003",
            type=RequirementType.USER,
            text="Orphaned user requirement with no software requirements",
            acceptance_criteria=[
                "This requirement has no implementation"
            ],
            derived_from=["nonexistent_feature"]  # References non-existent feature
        )
    ]
    
    # Sample software requirements (missing one for UR_003)
    software_requirements = [
        Requirement(
            id="SR_001",
            type=RequirementType.SOFTWARE,
            text="The authentication module shall implement secure password hashing using SHA-256",
            acceptance_criteria=[
                "Use SHA-256 with salt for password hashing",
                "Implement rate limiting for failed login attempts",
                "Store session tokens securely"
            ],
            derived_from=["UR_001"]
        ),
        Requirement(
            id="SR_002",
            type=RequirementType.SOFTWARE,
            text="The data processing module shall validate input against HL7 FHIR schema",
            acceptance_criteria=[
                "Parse and validate JSON against FHIR schema",
                "Reject malformed data with specific error codes",
                "Log all validation failures for audit"
            ],
            derived_from=["UR_002"]
        ),
        # Orphaned software requirement (no risks will be created)
        Requirement(
            id="SR_003",
            type=RequirementType.SOFTWARE,
            text="Orphaned software requirement with no associated risks",
            acceptance_criteria=[
                "This requirement has no risk analysis"
            ],
            derived_from=["UR_001"]  # Valid derivation but no risks
        )
    ]
    
    # Sample risk items (missing one for SR_003)
    risk_items = [
        RiskItem(
            id="RISK_001",
            hazard="Unauthorized access to patient data",
            cause="Weak authentication or session management",
            effect="Privacy breach and regulatory non-compliance",
            severity=Severity.SERIOUS,
            probability=Probability.MEDIUM,
            risk_level=RiskLevel.UNDESIRABLE,
            mitigation="Implement strong authentication, secure session management, and access logging",
            verification="Security testing, penetration testing, and code review",
            related_requirements=["SR_001"]
        ),
        RiskItem(
            id="RISK_002",
            hazard="Incorrect processing of medical data",
            cause="Invalid or malformed input data not properly validated",
            effect="Incorrect medical decisions leading to patient harm",
            severity=Severity.CATASTROPHIC,
            probability=Probability.LOW,
            risk_level=RiskLevel.UNDESIRABLE,
            mitigation="Comprehensive input validation, schema compliance checking, and error handling",
            verification="Unit testing, integration testing, and clinical validation",
            related_requirements=["SR_002"]
        ),
        # Orphaned risk (no related requirements)
        RiskItem(
            id="RISK_003",
            hazard="Orphaned risk with no linked requirements",
            cause="System design oversight",
            effect="Unmitigated risk in system",
            severity=Severity.MINOR,
            probability=Probability.HIGH,
            risk_level=RiskLevel.ACCEPTABLE,
            mitigation="Link to appropriate requirements",
            verification="Traceability review",
            related_requirements=[]  # No related requirements
        )
    ]
    
    return features, user_requirements, software_requirements, risk_items


def display_tabular_matrix(rows):
    """Display traceability matrix in a formatted table."""
    print("\n" + "="*150)
    print("TRACEABILITY MATRIX - TABULAR VIEW")
    print("="*150)
    
    # Print header
    header = f"{'Code Reference':<25} {'File':<20} {'Function':<15} {'Feature':<12} {'UR':<8} {'SR':<8} {'Risk':<8} {'Conf':<6}"
    print(header)
    print("-" * 150)
    
    # Print rows
    for i, row in enumerate(rows, 1):
        # Truncate long descriptions for display
        feature_desc = row.feature_description[:30] + "..." if len(row.feature_description) > 30 else row.feature_description
        ur_text = row.user_requirement_text[:25] + "..." if len(row.user_requirement_text) > 25 else row.user_requirement_text
        sr_text = row.software_requirement_text[:25] + "..." if len(row.software_requirement_text) > 25 else row.software_requirement_text
        risk_hazard = row.risk_hazard[:20] + "..." if len(row.risk_hazard) > 20 else row.risk_hazard
        
        row_str = (f"{row.code_reference:<25} "
                  f"{os.path.basename(row.file_path):<20} "
                  f"{row.function_name:<15} "
                  f"{row.feature_id:<12} "
                  f"{row.user_requirement_id:<8} "
                  f"{row.software_requirement_id:<8} "
                  f"{row.risk_id:<8} "
                  f"{row.confidence:<6.3f}")
        print(row_str)
        
        # Print descriptions on next line for better readability
        if i <= 5:  # Only show details for first 5 rows to avoid clutter
            desc_str = (f"{'  └─ Feature:':<25} {feature_desc}")
            print(desc_str)
            if row.user_requirement_text:
                ur_str = f"{'  └─ UR:':<25} {ur_text}"
                print(ur_str)
            if row.software_requirement_text:
                sr_str = f"{'  └─ SR:':<25} {sr_text}"
                print(sr_str)
            if row.risk_hazard:
                risk_str = f"{'  └─ Risk:':<25} {risk_hazard}"
                print(risk_str)
            print()
    
    print(f"\nTotal rows: {len(rows)}")
    print("="*150)


def main():
    """Main demonstration function."""
    print("=== Traceability Matrix Display and Export Demo ===\n")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # Initialize database and traceability service
        print("1. Initializing database and traceability service...")
        db_manager = DatabaseManager(db_path)
        traceability_service = TraceabilityService(db_manager)
        
        # Create project and analysis run
        project_id = db_manager.create_project(
            name="Medical Device Software - Display Demo",
            root_path="/path/to/medical/device/project",
            description="Cardiac monitoring device software with comprehensive traceability"
        )
        
        analysis_run_id = db_manager.create_analysis_run(
            project_id=project_id,
            artifacts_path="/path/to/analysis/artifacts"
        )
        
        print(f"   Created project {project_id} and analysis run {analysis_run_id}")
        
        # Create comprehensive sample data (including gaps)
        print("\n2. Creating comprehensive sample data with intentional gaps...")
        features, user_requirements, software_requirements, risk_items = create_comprehensive_sample_data()
        
        print(f"   Created {len(features)} features (including 1 orphaned)")
        print(f"   Created {len(user_requirements)} user requirements (including 1 orphaned)")
        print(f"   Created {len(software_requirements)} software requirements (including 1 orphaned)")
        print(f"   Created {len(risk_items)} risk items (including 1 orphaned)")
        
        # Create traceability matrix
        print("\n3. Creating traceability matrix...")
        matrix = traceability_service.create_traceability_matrix(
            analysis_run_id=analysis_run_id,
            features=features,
            user_requirements=user_requirements,
            software_requirements=software_requirements,
            risk_items=risk_items
        )
        
        print(f"   Created traceability matrix with {len(matrix.links)} total links")
        
        # Generate tabular matrix
        print("\n4. Generating tabular traceability matrix...")
        tabular_rows = traceability_service.generate_tabular_matrix(
            matrix, features, user_requirements, software_requirements, risk_items
        )
        
        print(f"   Generated {len(tabular_rows)} tabular rows")
        
        # Display tabular matrix
        display_tabular_matrix(tabular_rows)
        
        # Export to CSV (basic)
        print("\n5. Exporting to CSV (basic format)...")
        csv_content_basic = traceability_service.export_to_csv(
            matrix, features, user_requirements, software_requirements, risk_items,
            include_metadata=False
        )
        
        # Save basic CSV
        basic_csv_path = "traceability_matrix_basic.csv"
        with open(basic_csv_path, 'w', newline='', encoding='utf-8') as f:
            f.write(csv_content_basic)
        
        print(f"   ✓ Basic CSV exported to: {basic_csv_path}")
        print(f"   CSV size: {len(csv_content_basic)} characters")
        
        # Export to CSV (with metadata)
        print("\n6. Exporting to CSV (with metadata)...")
        csv_content_metadata = traceability_service.export_to_csv(
            matrix, features, user_requirements, software_requirements, risk_items,
            include_metadata=True
        )
        
        # Save metadata CSV
        metadata_csv_path = "traceability_matrix_with_metadata.csv"
        with open(metadata_csv_path, 'w', newline='', encoding='utf-8') as f:
            f.write(csv_content_metadata)
        
        print(f"   ✓ Metadata CSV exported to: {metadata_csv_path}")
        print(f"   CSV size: {len(csv_content_metadata)} characters")
        
        # Show CSV preview
        print("\n   CSV Preview (first 3 lines):")
        csv_lines = csv_content_basic.split('\n')
        for i, line in enumerate(csv_lines[:3]):
            print(f"   {i+1}: {line[:100]}{'...' if len(line) > 100 else ''}")
        
        # Detect traceability gaps
        print("\n7. Detecting traceability gaps...")
        gaps = traceability_service.detect_traceability_gaps(
            matrix, features, user_requirements, software_requirements, risk_items
        )
        
        print(f"   Detected {len(gaps)} traceability gaps")
        
        # Group gaps by severity
        high_gaps = [g for g in gaps if g.severity == "high"]
        medium_gaps = [g for g in gaps if g.severity == "medium"]
        low_gaps = [g for g in gaps if g.severity == "low"]
        
        print(f"   - High severity: {len(high_gaps)}")
        print(f"   - Medium severity: {len(medium_gaps)}")
        print(f"   - Low severity: {len(low_gaps)}")
        
        # Show example gaps
        print("\n   Example gaps:")
        for i, gap in enumerate(gaps[:3]):  # Show first 3 gaps
            print(f"   Gap {i+1}: [{gap.severity.upper()}] {gap.gap_type}")
            print(f"           {gap.description}")
            print(f"           Recommendation: {gap.recommendation}")
            print()
        
        # Generate gap report
        print("\n8. Generating gap analysis report...")
        gap_report = traceability_service.generate_gap_report(gaps)
        
        # Save gap report
        gap_report_path = "traceability_gap_report.txt"
        with open(gap_report_path, 'w', encoding='utf-8') as f:
            f.write(gap_report)
        
        print(f"   ✓ Gap report saved to: {gap_report_path}")
        
        # Show gap report preview
        print("\n   Gap Report Preview:")
        report_lines = gap_report.split('\n')
        for line in report_lines[:15]:  # Show first 15 lines
            print(f"   {line}")
        if len(report_lines) > 15:
            print(f"   ... ({len(report_lines) - 15} more lines)")
        
        # Validate traceability matrix
        print("\n9. Validating traceability matrix...")
        validation_issues = traceability_service.validate_traceability_matrix(matrix)
        
        if validation_issues:
            print("   Validation issues found:")
            for issue in validation_issues:
                print(f"     - {issue}")
        else:
            print("   ✓ Traceability matrix structure is valid!")
        
        # Summary statistics
        print("\n10. Summary Statistics:")
        print(f"    - Total traceability links: {len(matrix.links)}")
        print(f"    - Code references: {len(set(link.source_id for link in matrix.links if link.source_type == 'code'))}")
        print(f"    - Features with traceability: {len(set(link.source_id for link in matrix.links if link.source_type == 'feature'))}")
        print(f"    - Requirements with traceability: {len(set(link.source_id for link in matrix.links if link.source_type == 'requirement'))}")
        print(f"    - Risks with traceability: {len(set(link.target_id for link in matrix.links if link.target_type == 'risk'))}")
        print(f"    - Average link confidence: {sum(link.confidence for link in matrix.links) / len(matrix.links):.3f}")
        
        # File outputs summary
        print(f"\n11. Generated Files:")
        print(f"    - {basic_csv_path} ({os.path.getsize(basic_csv_path)} bytes)")
        print(f"    - {metadata_csv_path} ({os.path.getsize(metadata_csv_path)} bytes)")
        print(f"    - {gap_report_path} ({os.path.getsize(gap_report_path)} bytes)")
 