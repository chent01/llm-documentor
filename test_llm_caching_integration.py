#!/usr/bin/env python3
"""
Test script to verify that LLM backends are properly using the caching layer.
"""

import sys
import tempfile
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from medical_analyzer.services.analysis_orchestrator import AnalysisOrchestrator
from medical_analyzer.config.config_manager import ConfigManager
from medical_analyzer.config.app_settings import AppSettings
from medical_analyzer.llm.cached_backend import CachedLLMBackend
from medical_analyzer.llm.query_cache import get_global_cache


def test_llm_caching_integration():
    """Test that LLM backends are properly wrapped with caching."""
    print("=== LLM Caching Integration Test ===\n")
    
    try:
        # Initialize configuration and orchestrator
        config_manager = ConfigManager()
        config_manager.load_default_config()
        app_settings = AppSettings(config_manager)
        
        orchestrator = AnalysisOrchestrator(config_manager, app_settings)
        
        # Check if LLM backend is wrapped with caching
        print("--- LLM Backend Analysis ---")
        if orchestrator.llm_backend is None:
            print("❌ No LLM backend initialized")
            print("This is expected if no LLM service is configured/available")
            return
        
        print(f"LLM Backend Type: {type(orchestrator.llm_backend).__name__}")
        
        if isinstance(orchestrator.llm_backend, CachedLLMBackend):
            print("✅ LLM backend is properly wrapped with CachedLLMBackend")
            
            # Check cache configuration
            cache_stats = orchestrator.llm_backend.get_cache_statistics()
            print(f"Cache Enabled: {orchestrator.llm_backend.cache_enabled}")
            print(f"Cache Hit Rate: {cache_stats.get('hit_rate_percent', 0):.1f}%")
            print(f"Total Queries: {cache_stats.get('total_queries', 0)}")
            
            # Test a simple LLM call to see if caching works
            print("\n--- Testing LLM Caching ---")
            test_prompt = "What is the capital of France?"
            
            print("Making first LLM call...")
            start_time = time.time()
            try:
                response1 = orchestrator.llm_backend.generate(test_prompt, temperature=0.1)
                first_call_time = time.time() - start_time
                print(f"First call completed in {first_call_time:.3f}s")
                print(f"Response length: {len(response1)} characters")
            except Exception as e:
                print(f"First call failed: {e}")
                return
            
            print("Making second identical LLM call...")
            start_time = time.time()
            try:
                response2 = orchestrator.llm_backend.generate(test_prompt, temperature=0.1)
                second_call_time = time.time() - start_time
                print(f"Second call completed in {second_call_time:.3f}s")
                print(f"Response length: {len(response2)} characters")
                
                # Check if second call was faster (indicating cache hit)
                if second_call_time < first_call_time * 0.1:  # 10x faster
                    print("✅ Second call was significantly faster - cache likely used!")
                else:
                    print("⚠️  Second call wasn't much faster - cache might not be working")
                
                # Check if responses are identical
                if response1 == response2:
                    print("✅ Responses are identical - consistent caching")
                else:
                    print("⚠️  Responses differ - might indicate cache miss")
                    
            except Exception as e:
                print(f"Second call failed: {e}")
            
            # Check updated cache statistics
            updated_stats = orchestrator.llm_backend.get_cache_statistics()
            print(f"\nUpdated Cache Stats:")
            print(f"Total Queries: {updated_stats.get('total_queries', 0)}")
            print(f"Cache Hits: {updated_stats.get('cache_hits', 0)}")
            print(f"Cache Misses: {updated_stats.get('cache_misses', 0)}")
            print(f"Hit Rate: {updated_stats.get('hit_rate_percent', 0):.1f}%")
            
        else:
            print("❌ LLM backend is NOT wrapped with CachedLLMBackend")
            print(f"   Actual type: {type(orchestrator.llm_backend)}")
            print("   This means LLM queries are not being cached!")
        
        # Check global cache state
        print("\n--- Global Cache Analysis ---")
        global_cache = get_global_cache()
        global_stats = global_cache.get_statistics()
        print(f"Global Cache Entries: {global_stats.get('entry_count', 0)}")
        print(f"Global Cache Size: {global_stats.get('total_size_mb', 0):.2f} MB")
        print(f"Global Hit Rate: {global_stats.get('hit_rate_percent', 0):.1f}%")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()


def test_feature_extractor_caching():
    """Test that feature extractor uses cached LLM backend."""
    print("\n=== Feature Extractor Caching Test ===\n")
    
    try:
        # Initialize configuration and orchestrator
        config_manager = ConfigManager()
        config_manager.load_default_config()
        app_settings = AppSettings(config_manager)
        
        orchestrator = AnalysisOrchestrator(config_manager, app_settings)
        
        if not orchestrator.feature_extractor:
            print("❌ No feature extractor available (LLM backend not initialized)")
            return
        
        # Check if feature extractor's LLM backend is cached
        fe_backend = orchestrator.feature_extractor.llm_backend
        print(f"Feature Extractor LLM Backend Type: {type(fe_backend).__name__}")
        
        if isinstance(fe_backend, CachedLLMBackend):
            print("✅ Feature extractor is using cached LLM backend")
        else:
            print("❌ Feature extractor is NOT using cached LLM backend")
            print("   This means feature extraction queries are not being cached!")
        
    except Exception as e:
        print(f"Error during feature extractor test: {e}")


if __name__ == "__main__":
    test_llm_caching_integration()
    test_feature_extractor_caching()
    
    print("\n=== Test Summary ===")
    print("If LLM backends are properly wrapped with CachedLLMBackend,")
    print("then LLM queries will be automatically cached, providing:")
    print("- Faster response times for repeated queries")
    print("- Reduced API costs")
    print("- Better reliability")
    print("\nIf not wrapped, LLM caching is not active and should be fixed.")