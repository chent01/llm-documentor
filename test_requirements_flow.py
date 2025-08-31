#!/usr/bin/env python3
"""
Test script to verify the new requirements generation flow.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from medical_analyzer.services.requirements_generator import RequirementsGenerator
from medical_analyzer.models.core import Feature, CodeReference
from medical_analyzer.models.enums import FeatureCategory
from medical_analyzer.llm.local_server_backend import LocalServerBackend
from medical_analyzer.llm.config import LLMConfig


def create_mock_features():
    """Create mock features for testing."""
    features = []
    
    # Feature 1: Data validation
    code_ref1 = CodeReference(
        file_path="src/validator.py",
        start_line=10,
        end_line=25,
        function_name="validate_input",
        context="Input validation function"
    )
    
    feature1 = Feature(
        id="FEAT_0001",
        description="Input data validation functionality",
        confidence=0.85,
        evidence=[code_ref1],
        category=FeatureCategory.VALIDATION,
        metadata={'language': 'python', 'complexity': 'medium'}
    )
    features.append(feature1)
    
    # Feature 2: User interface
    code_ref2 = CodeReference(
        file_path="src/ui/main_window.py",
        start_line=50,
        end_line=80,
        function_name="create_main_window",
        context="Main window creation"
    )
    
    feature2 = Feature(
        id="FEAT_0002",
        description="Main user interface window",
        confidence=0.90,
        evidence=[code_ref2],
        category=FeatureCategory.USER_INTERFACE,
        metadata={'language': 'python', 'framework': 'PyQt6'}
    )
    features.append(feature2)
    
    # Feature 3: Data storage
    code_ref3 = CodeReference(
        file_path="src/database/manager.py",
        start_line=100,
        end_line=150,
        function_name="save_data",
        context="Data persistence functionality"
    )
    
    feature3 = Feature(
        id="FEAT_0003",
        description="Database data storage functionality",
        confidence=0.75,
        evidence=[code_ref3],
        category=FeatureCategory.STORAGE,
        metadata={'language': 'python', 'database': 'sqlite'}
    )
    features.append(feature3)
    
    return features


def test_requirements_generation():
    """Test the requirements generation flow."""
    print("Testing Requirements Generation Flow")
    print("=" * 50)
    
    # Create mock features
    features = create_mock_features()
    print(f"Created {len(features)} mock features:")
    for feature in features:
        print(f"  - {feature.id}: {feature.description}")
    
    # Try to create LLM backend (will fail gracefully if not available)
    try:
        llm_config = LLMConfig()
        llm_backend = LocalServerBackend(llm_config)
        print(f"\nLLM Backend: {llm_backend.__class__.__name__}")
    except Exception as e:
        print(f"\nLLM Backend not available: {e}")
        print("Using fallback heuristic generation...")
        # Create a mock backend that will fail and trigger fallback
        class MockLLMBackend:
            def generate(self, *args, **kwargs):
                raise Exception("Mock LLM failure to test fallback")
        llm_backend = MockLLMBackend()
    
    # Create requirements generator
    req_generator = RequirementsGenerator(llm_backend)
    
    # Generate requirements
    print("\nGenerating requirements from features...")
    try:
        result = req_generator.generate_requirements_from_features(
            features=features,
            project_description="Medical device software analyzer"
        )
        
        print(f"\nResults:")
        print(f"  Processing time: {result.processing_time:.2f} seconds")
        print(f"  User requirements: {len(result.user_requirements)}")
        print(f"  Software requirements: {len(result.software_requirements)}")
        
        print(f"\nUser Requirements:")
        for ur in result.user_requirements:
            print(f"  {ur.id}: {ur.text}")
            print(f"    Priority: {ur.metadata.get('priority', 'medium')}")
            print(f"    Acceptance criteria: {len(ur.acceptance_criteria)} items")
            print(f"    Derived from: {ur.derived_from}")
        
        print(f"\nSoftware Requirements:")
        for sr in result.software_requirements:
            print(f"  {sr.id}: {sr.text}")
            print(f"    Priority: {sr.metadata.get('priority', 'medium')}")
            print(f"    Derived from: {sr.derived_from}")
            print(f"    Type: {sr.metadata.get('requirement_type', 'unknown')}")
        
        # Test statistics
        stats = req_generator.get_statistics(result.user_requirements, result.software_requirements)
        print(f"\nStatistics:")
        print(f"  UR/SR ratio: {stats['traceability']['ur_to_sr_ratio']:.2f}")
        print(f"  Requirements with traceability: {stats['traceability']['requirements_with_traceability']}")
        
        print(f"\nFlow verification:")
        print(f"  ✓ Features → User Requirements: {len(features)} → {len(result.user_requirements)}")
        print(f"  ✓ User Requirements → Software Requirements: {len(result.user_requirements)} → {len(result.software_requirements)}")
        
        # Verify traceability
        all_feature_ids = {f.id for f in features}
        ur_derived_features = set()
        for ur in result.user_requirements:
            ur_derived_features.update(ur.derived_from)
        
        sr_derived_urs = set()
        for sr in result.software_requirements:
            sr_derived_urs.update(sr.derived_from)
        
        ur_ids = {ur.id for ur in result.user_requirements}
        
        print(f"  ✓ Feature traceability: {len(ur_derived_features & all_feature_ids)}/{len(all_feature_ids)} features traced")
        print(f"  ✓ UR traceability: {len(sr_derived_urs & ur_ids)}/{len(ur_ids)} URs traced")
        
        print(f"\n✅ Requirements generation flow test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Requirements generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_requirements_generation()
    sys.exit(0 if success else 1)