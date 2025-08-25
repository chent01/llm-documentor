#!/usr/bin/env python3
"""
Demo script for the traceability service.

This script demonstrates how to use the TraceabilityService to create
traceability links between code references, features, requirements, and risks.
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


def create_sample_data():
    """Create sample data for demonstration."""
    
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
        )
    ]
    
    # Sample user requirements
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
        )
    ]
    
    # Sample software requirements
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
        )
    ]
    
    # Sample risk items
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
        )
    ]
    
    return features, user_requirements, software_requirements, risk_items


def main():
    """Main demonstration function."""
    print("=== Medical Software Traceability Service Demo ===\n")
    
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
            name="Medical Device Software",
            root_path="/path/to/medical/device/project",
            description="Cardiac monitoring device software with patient data processing"
        )
        
        analysis_run_id = db_manager.create_analysis_run(
            project_id=project_id,
            artifacts_path="/path/to/analysis/artifacts"
        )
        
        print(f"   Created project {project_id} and analysis run {analysis_run_id}")
        
        # Create sample data
        print("\n2. Creating sample analysis data...")
        features, user_requirements, software_requirements, risk_items = create_sample_data()
        
        print(f"   Created {len(features)} features")
        print(f"   Created {len(user_requirements)} user requirements")
        print(f"   Created {len(software_requirements)} software requirements")
        print(f"   Created {len(risk_items)} risk items")
        
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
        print(f"   Link breakdown:")
        print(f"     - Code-to-feature links: {matrix.metadata['code_feature_links']}")
        print(f"     - Feature-to-UR links: {matrix.metadata['feature_ur_links']}")
        print(f"     - UR-to-SR links: {matrix.metadata['ur_sr_links']}")
        print(f"     - SR-to-risk links: {matrix.metadata['sr_risk_links']}")
        print(f"     - Code-to-SR links (transitive): {matrix.metadata['code_sr_links']}")
        
        # Display traceability mappings
        print("\n4. Traceability mappings:")
        
        print("\n   Code-to-Requirements mapping:")
        for code_ref, req_ids in matrix.code_to_requirements.items():
            print(f"     {code_ref} -> {req_ids}")
        
        print("\n   User-to-Software Requirements mapping:")
        for ur_id, sr_ids in matrix.user_to_software_requirements.items():
            print(f"     {ur_id} -> {sr_ids}")
        
        print("\n   Requirements-to-Risks mapping:")
        for req_id, risk_ids in matrix.requirements_to_risks.items():
            print(f"     {req_id} -> {risk_ids}")
        
        # Validate traceability matrix
        print("\n5. Validating traceability matrix...")
        issues = traceability_service.validate_traceability_matrix(matrix)
        
        if issues:
            print("   Validation issues found:")
            for issue in issues:
                print(f"     - {issue}")
        else:
            print("   ✓ Traceability matrix is valid!")
        
        # Test retrieval from database
        print("\n6. Testing database retrieval...")
        retrieved_matrix = traceability_service.get_traceability_matrix(analysis_run_id)
        
        if retrieved_matrix:
            print(f"   ✓ Successfully retrieved matrix with {len(retrieved_matrix.links)} links")
        else:
            print("   ✗ Failed to retrieve matrix from database")
        
        # Display some example links
        print("\n7. Example traceability links:")
        for i, link in enumerate(matrix.links[:5]):  # Show first 5 links
            print(f"   Link {i+1}: {link.source_type}:{link.source_id} --{link.link_type}--> {link.target_type}:{link.target_id}")
            print(f"            Confidence: {link.confidence:.2f}")
            if link.metadata:
                key_metadata = {k: v for k, v in link.metadata.items() if k in ['file_path', 'function_name', 'hazard']}
                if key_metadata:
                    print(f"            Metadata: {key_metadata}")
            print()
        
        print("=== Demo completed successfully! ===")
        
    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == "__main__":
    main()