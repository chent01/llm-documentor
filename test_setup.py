#!/usr/bin/env python3
"""
Test script to verify the project setup and core interfaces.
"""

import sys
import tempfile
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from medical_analyzer.models import (
    ProjectStructure, CodeChunk, Feature, Requirement, RiskItem,
    ChunkType, FeatureCategory, RequirementType, Severity, Probability, RiskLevel
)
from medical_analyzer.database import DatabaseManager
from datetime import datetime


def test_data_models():
    """Test that all data models can be instantiated."""
    print("Testing data models...")
    
    # Test ProjectStructure
    project = ProjectStructure(
        root_path="/test/project",
        selected_files=["main.c", "utils.js"],
        description="Test medical device project"
    )
    assert project.root_path == "/test/project"
    print("✓ ProjectStructure model works")
    
    # Test CodeChunk
    chunk = CodeChunk(
        file_path="main.c",
        start_line=10,
        end_line=25,
        content="int main() { return 0; }",
        function_name="main",
        chunk_type=ChunkType.FUNCTION
    )
    assert chunk.chunk_type == ChunkType.FUNCTION
    print("✓ CodeChunk model works")
    
    # Test Feature
    feature = Feature(
        id="F001",
        description="User authentication system",
        confidence=0.85,
        category=FeatureCategory.SAFETY
    )
    assert feature.category == FeatureCategory.SAFETY
    print("✓ Feature model works")
    
    # Test Requirement
    requirement = Requirement(
        id="UR001",
        type=RequirementType.USER,
        text="The system shall authenticate users before access"
    )
    assert requirement.type == RequirementType.USER
    print("✓ Requirement model works")
    
    # Test RiskItem
    risk = RiskItem(
        id="R001",
        hazard="Unauthorized access",
        cause="Weak authentication",
        effect="Data breach",
        severity=Severity.SERIOUS,
        probability=Probability.MEDIUM,
        risk_level=RiskLevel.UNDESIRABLE,
        mitigation="Implement strong authentication",
        verification="Security testing"
    )
    assert risk.severity == Severity.SERIOUS
    print("✓ RiskItem model works")


def test_database_schema():
    """Test that the database schema works correctly."""
    print("\nTesting database schema...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        # Initialize database
        db_manager = DatabaseManager(db_path)
        print("✓ Database initialization works")
        
        # Test project creation
        project_id = db_manager.create_project(
            name="Test Project",
            root_path="/test/path",
            description="Test medical device project",
            metadata={"version": "1.0", "type": "medical_device"}
        )
        assert project_id > 0
        print("✓ Project creation works")
        
        # Test project retrieval
        project = db_manager.get_project(project_id)
        assert project is not None
        assert project['name'] == "Test Project"
        assert project['metadata']['version'] == "1.0"
        print("✓ Project retrieval works")
        
        # Test analysis run creation
        run_id = db_manager.create_analysis_run(
            project_id=project_id,
            artifacts_path="/test/artifacts",
            metadata={"stage": "requirements"}
        )
        assert run_id > 0
        print("✓ Analysis run creation works")
        
        # Test traceability link creation
        link_id = db_manager.create_traceability_link(
            analysis_run_id=run_id,
            source_type="code",
            source_id="main.c:10-25",
            target_type="requirement",
            target_id="UR001",
            link_type="implements",
            confidence=0.9
        )
        assert link_id > 0
        print("✓ Traceability link creation works")
        
        # Test traceability link retrieval
        links = db_manager.get_traceability_links(run_id)
        assert len(links) == 1
        assert links[0]['source_type'] == "code"
        assert links[0]['confidence'] == 0.9
        print("✓ Traceability link retrieval works")
        
    finally:
        # Clean up temporary database
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_enums():
    """Test that all enums are properly defined."""
    print("\nTesting enums...")
    
    # Test all enum values are accessible
    assert ChunkType.FUNCTION
    assert FeatureCategory.SAFETY
    assert RequirementType.USER
    assert Severity.SERIOUS
    assert Probability.MEDIUM
    assert RiskLevel.UNDESIRABLE
    print("✓ All enums are properly defined")


def main():
    """Run all tests."""
    print("Medical Software Analysis Tool - Setup Verification")
    print("=" * 50)
    
    try:
        test_enums()
        test_data_models()
        test_database_schema()
        
        print("\n" + "=" * 50)
        print("✓ All tests passed! Project setup is complete.")
        print("\nCore interfaces created:")
        print("- ProjectStructure, CodeChunk, Feature, Requirement, RiskItem")
        print("- Database schema with projects, analysis_runs, traceability_links tables")
        print("- Directory structure: models/, services/, parsers/, ui/, database/")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())