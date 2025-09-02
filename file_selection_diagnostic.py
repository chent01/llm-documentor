#!/usr/bin/env python3
"""
Diagnostic script to trace file selection through the analysis pipeline.
This will help identify where the file selection constraint is being lost.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from medical_analyzer.services.ingestion import IngestionService
from medical_analyzer.parsers.parser_service import ParserService
from medical_analyzer.services.feature_extractor import FeatureExtractor
from medical_analyzer.services.requirements_generator import RequirementsGenerator
from medical_analyzer.config.config_manager import ConfigManager
from medical_analyzer.llm.backend import LLMBackend


def trace_file_selection(project_path: str, selected_files: list):
    """
    Trace how file selection flows through the analysis pipeline.
    
    Args:
        project_path: Path to the project to analyze
        selected_files: List of specific files to analyze
    """
    print("=" * 80)
    print("FILE SELECTION DIAGNOSTIC")
    print("=" * 80)
    print(f"Project Path: {project_path}")
    print(f"Selected Files: {selected_files}")
    print()
    
    # Stage 1: Project Ingestion
    print("STAGE 1: PROJECT INGESTION")
    print("-" * 40)
    
    ingestion_service = IngestionService()
    project_structure = ingestion_service.scan_project(
        project_path, 
        description="Diagnostic test", 
        selected_files=selected_files
    )
    
    print(f"Files in project_structure.selected_files: {len(project_structure.selected_files)}")
    for i, file_path in enumerate(project_structure.selected_files):
        print(f"  {i+1}. {file_path}")
    print()
    
    # Stage 2: Code Parsing
    print("STAGE 2: CODE PARSING")
    print("-" * 40)
    
    parser_service = ParserService()
    parsed_files = parser_service.parse_project(project_structure)
    
    print(f"Number of parsed files: {len(parsed_files)}")
    all_chunks = []
    for parsed_file in parsed_files:
        print(f"  File: {parsed_file.file_path}")
        print(f"    Chunks: {len(parsed_file.chunks)}")
        all_chunks.extend(parsed_file.chunks)
        for j, chunk in enumerate(parsed_file.chunks):
            print(f"      Chunk {j+1}: {chunk.file_path}:{chunk.start_line}-{chunk.end_line}")
    
    print(f"Total chunks from selected files: {len(all_chunks)}")
    print()
    
    # Stage 3: Feature Extraction (if LLM available)
    print("STAGE 3: FEATURE EXTRACTION")
    print("-" * 40)
    
    try:
        config_manager = ConfigManager()
        llm_config = config_manager.get_llm_config()
        
        # Try to initialize LLM backend
        if llm_config and llm_config.get('backend_type'):
            from medical_analyzer.llm.local_server_backend import LocalServerBackend
            llm_backend = LocalServerBackend(llm_config)
            
            feature_extractor = FeatureExtractor(llm_backend)
            feature_result = feature_extractor.extract_features(all_chunks)
            
            print(f"Features extracted: {len(feature_result.features)}")
            for i, feature in enumerate(feature_result.features):
                print(f"  Feature {i+1}: {feature.id} - {feature.description}")
                if feature.evidence:
                    for evidence in feature.evidence:
                        print(f"    Evidence: {evidence.file_path}:{evidence.start_line}")
            print()
            
            # Stage 4: Requirements Generation
            print("STAGE 4: REQUIREMENTS GENERATION")
            print("-" * 40)
            
            requirements_generator = RequirementsGenerator(llm_backend)
            requirements_result = requirements_generator.generate_requirements_from_features(
                feature_result.features, 
                "Diagnostic test project"
            )
            
            print(f"User requirements generated: {len(requirements_result.user_requirements)}")
            for i, ur in enumerate(requirements_result.user_requirements):
                print(f"  UR {i+1}: {ur.id} - {ur.text}")
                print(f"    Derived from features: {ur.derived_from}")
            
            print(f"Software requirements generated: {len(requirements_result.software_requirements)}")
            for i, sr in enumerate(requirements_result.software_requirements):
                print(f"  SR {i+1}: {sr.id} - {sr.text}")
                print(f"    Derived from: {sr.derived_from}")
            print()
            
        else:
            print("LLM backend not configured - skipping feature extraction and requirements generation")
            print()
            
    except Exception as e:
        print(f"Error in LLM-based stages: {e}")
        print()
    
    # Check for any other file scanning
    print("STAGE 5: OTHER FILE SCANNING CHECKS")
    print("-" * 40)
    
    # Check if SOUP detector would scan additional files
    from medical_analyzer.services.soup_detector import SOUPDetector
    soup_detector = SOUPDetector(use_llm_classification=False)
    
    print("SOUP detector would scan for these dependency files:")
    project_root = Path(project_path)
    for filename in soup_detector.parsers.keys():
        dependency_files = list(project_root.rglob(filename))
        if dependency_files:
            print(f"  {filename}: {len(dependency_files)} files found")
            for dep_file in dependency_files:
                print(f"    - {dep_file}")
                # Check if this file is in selected_files
                if str(dep_file) in selected_files:
                    print(f"      ✓ This file IS in selected_files")
                else:
                    print(f"      ✗ This file is NOT in selected_files")
    print()
    
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    # Example usage - you can modify these paths
    current_dir = os.getcwd()
    
    # Test with a few selected files
    selected_files = [
        os.path.join(current_dir, "main.py"),
        os.path.join(current_dir, "medical_analyzer", "services", "requirements_generator.py")
    ]
    
    trace_file_selection(current_dir, selected_files)