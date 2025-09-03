#!/usr/bin/env python3
"""
Test script to verify that all LLM-dependent services are using cached backends.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from medical_analyzer.services.analysis_orchestrator import AnalysisOrchestrator
from medical_analyzer.config.config_manager import ConfigManager
from medical_analyzer.config.app_settings import AppSettings
from medical_analyzer.llm.cached_backend import CachedLLMBackend


def test_all_services_caching():
    """Test that all LLM-dependent services are using cached backends."""
    print("=== All Services LLM Caching Test ===\n")
    
    try:
        # Initialize configuration and orchestrator
        config_manager = ConfigManager()
        config_manager.load_default_config()
        app_settings = AppSettings(config_manager)
        
        orchestrator = AnalysisOrchestrator(config_manager, app_settings)
        
        services_to_check = [
            ("Analysis Orchestrator", orchestrator.llm_backend),
            ("Feature Extractor", getattr(orchestrator.feature_extractor, 'llm_backend', None) if orchestrator.feature_extractor else None),
            ("Requirements Generator", getattr(orchestrator.requirements_generator, 'llm_backend', None) if orchestrator.requirements_generator else None),
            ("Hazard Identifier", getattr(orchestrator.hazard_identifier, 'llm_backend', None) if orchestrator.hazard_identifier else None),
            ("Test Case Generator", getattr(orchestrator.test_case_generator, 'llm_backend', None) if hasattr(orchestrator.test_case_generator, 'llm_backend') else None),
        ]
        
        print("Checking LLM backend caching for all services:\n")
        
        cached_count = 0
        total_count = 0
        
        for service_name, backend in services_to_check:
            if backend is None:
                print(f"❓ {service_name}: No LLM backend (service disabled or not available)")
                continue
            
            total_count += 1
            backend_type = type(backend).__name__
            
            if isinstance(backend, CachedLLMBackend):
                print(f"✅ {service_name}: Using CachedLLMBackend")
                cached_count += 1
            else:
                print(f"❌ {service_name}: Using {backend_type} (NOT cached)")
        
        print(f"\n--- Summary ---")
        print(f"Services with LLM backends: {total_count}")
        print(f"Services using cached backends: {cached_count}")
        
        if cached_count == total_count and total_count > 0:
            print("✅ ALL services are using cached LLM backends!")
        elif cached_count > 0:
            print(f"⚠️  {cached_count}/{total_count} services are using cached backends")
        else:
            print("❌ NO services are using cached backends")
        
        # Test that they're all using the same cache instance
        print(f"\n--- Cache Instance Check ---")
        cache_instances = set()
        
        for service_name, backend in services_to_check:
            if isinstance(backend, CachedLLMBackend):
                cache_id = id(backend.cache)
                cache_instances.add(cache_id)
                print(f"{service_name}: Cache instance ID {cache_id}")
        
        if len(cache_instances) == 1:
            print("✅ All services are using the same cache instance (efficient)")
        elif len(cache_instances) > 1:
            print(f"⚠️  Services are using {len(cache_instances)} different cache instances")
        else:
            print("❓ No cached backends found")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_all_services_caching()