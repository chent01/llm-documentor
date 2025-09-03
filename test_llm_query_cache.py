#!/usr/bin/env python3
"""
Test script to demonstrate LLM query-level caching functionality.
"""

import os
import sys
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from medical_analyzer.llm.backend import LLMBackend
from medical_analyzer.llm.query_cache import LLMQueryCache
from medical_analyzer.llm.cached_backend import CachedLLMBackend


def test_query_cache():
    """Test the query-level caching functionality."""
    print("=== LLM Query-Level Caching Test ===\n")
    
    # Create a test cache
    cache = LLMQueryCache(
        cache_dir="test_llm_cache",
        max_entries=100,
        default_ttl=300,  # 5 minutes
        max_cache_size_mb=10
    )
    
    print("1. Testing cache key generation...")
    
    # Test cache key generation
    prompt1 = "Analyze this code for security vulnerabilities"
    prompt2 = "Analyze this code for security vulnerabilities"  # Same
    prompt3 = "Generate test cases for this function"  # Different
    
    key1 = cache._generate_cache_key(prompt1, temperature=0.1)
    key2 = cache._generate_cache_key(prompt2, temperature=0.1)
    key3 = cache._generate_cache_key(prompt3, temperature=0.1)
    key4 = cache._generate_cache_key(prompt1, temperature=0.2)  # Different temp
    
    print(f"  Key 1: {key1[:16]}...")
    print(f"  Key 2: {key2[:16]}...")
    print(f"  Key 3: {key3[:16]}...")
    print(f"  Key 4: {key4[:16]}...")
    
    assert key1 == key2, "Same prompts should generate same keys"
    assert key1 != key3, "Different prompts should generate different keys"
    assert key1 != key4, "Different temperatures should generate different keys"
    print("  ✓ Cache key generation working correctly")
    
    print("\n2. Testing cache storage and retrieval...")
    
    # Test cache miss
    result = cache.get(prompt1, temperature=0.1)
    assert result is None, "Should be cache miss for new query"
    print("  ✓ Cache miss for new query")
    
    # Store response
    test_response = "This code has potential SQL injection vulnerabilities in lines 15-20."
    cache.put(
        prompt=prompt1,
        response=test_response,
        response_time=2.5,
        temperature=0.1,
        backend_name="TestBackend",
        model_name="test-model"
    )
    print("  ✓ Response stored in cache")
    
    # Test cache hit
    result = cache.get(prompt1, temperature=0.1)
    assert result == test_response, "Should get cached response"
    print("  ✓ Cache hit for stored query")
    
    print("\n3. Testing cached backend wrapper...")
    
    # Create a mock backend for testing
    class MockLLMBackend(LLMBackend):
        def __init__(self):
            super().__init__({})
            self.call_count = 0
            self.responses = [
                "First response - analyzing code structure...",
                "Second response - identifying patterns...",
                "Third response - generating recommendations..."
            ]
        
        def generate(self, prompt, context_chunks=None, temperature=0.1, max_tokens=None, system_prompt=None):
            self.call_count += 1
            time.sleep(0.1)  # Simulate processing time
            response_idx = (self.call_count - 1) % len(self.responses)
            return self.responses[response_idx]
        
        def is_available(self):
            return True
        
        def get_model_info(self):
            from medical_analyzer.llm.backend import ModelInfo, ModelType
            return ModelInfo(
                name="mock-model",
                type=ModelType.CHAT,
                context_length=4096,
                backend_name="MockLLMBackend"
            )
        
        def get_required_config_keys(self):
            return []
    
    # Create mock backend and wrap with cache
    mock_backend = MockLLMBackend()
    cached_backend = CachedLLMBackend(mock_backend, cache)
    
    test_prompt = "Analyze this function for potential bugs"
    
    print("  First call (should hit backend)...")
    start_time = time.time()
    response1 = cached_backend.generate(test_prompt, temperature=0.1)
    time1 = time.time() - start_time
    print(f"    Response: {response1[:50]}...")
    print(f"    Time: {time1:.3f}s")
    print(f"    Backend calls: {mock_backend.call_count}")
    
    print("  Second call (should hit cache)...")
    start_time = time.time()
    response2 = cached_backend.generate(test_prompt, temperature=0.1)
    time2 = time.time() - start_time
    print(f"    Response: {response2[:50]}...")
    print(f"    Time: {time2:.3f}s")
    print(f"    Backend calls: {mock_backend.call_count}")
    
    assert response1 == response2, "Cached response should match original"
    assert time2 < time1, "Cached response should be faster"
    assert mock_backend.call_count == 1, "Backend should only be called once"
    print("  ✓ Caching working correctly")
    
    print("\n4. Testing cache statistics...")
    
    stats = cache.get_statistics()
    print(f"  Cache statistics:")
    print(f"    Hit rate: {stats['hit_rate_percent']}%")
    print(f"    Total queries: {stats['total_queries']}")
    print(f"    Cache hits: {stats['cache_hits']}")
    print(f"    Cache misses: {stats['cache_misses']}")
    print(f"    Entry count: {stats['entry_count']}")
    print(f"    Cache size: {stats['total_size_mb']} MB")
    print(f"    Avg response time saved: {stats['avg_response_time_saved']:.3f}s")
    
    print("\n5. Testing different parameters...")
    
    # Test with different temperature (should miss cache)
    print("  Call with different temperature (should miss cache)...")
    start_time = time.time()
    response3 = cached_backend.generate(test_prompt, temperature=0.5)
    time3 = time.time() - start_time
    print(f"    Time: {time3:.3f}s")
    print(f"    Backend calls: {mock_backend.call_count}")
    
    assert mock_backend.call_count == 2, "Should call backend for different parameters"
    print("  ✓ Different parameters correctly bypass cache")
    
    print("\n6. Testing cache health check...")
    
    health = cached_backend.health_check()
    print(f"  Backend available: {health['available']}")
    print(f"  Cache enabled: {health['cache_enabled']}")
    print(f"  Cache hit rate: {health['cache_stats']['hit_rate_percent']}%")
    
    print("\n7. Testing cache configuration...")
    
    # Test creating backend with cache config
    config = {
        'backend': 'fallback',
        'cache': {
            'enabled': True,
            'max_entries': 50,
            'default_ttl': 600,
            'max_cache_size_mb': 5
        }
    }
    
    backend_with_cache = LLMBackend.create_from_config(config)
    print(f"  Created backend: {backend_with_cache.__class__.__name__}")
    
    if hasattr(backend_with_cache, 'cache_enabled'):
        print(f"  Cache enabled: {backend_with_cache.cache_enabled}")
    
    print("\n=== Summary ===")
    print("✓ Query-level caching implemented successfully!")
    print("✓ Cache keys generated based on prompt content and parameters")
    print("✓ Responses cached and retrieved correctly")
    print("✓ Performance improvement demonstrated")
    print("✓ Cache statistics and monitoring available")
    print("✓ Configurable cache settings")
    
    print("\nBenefits:")
    print("- Eliminates redundant LLM API calls")
    print("- Significant performance improvement for repeated queries")
    print("- Intelligent cache invalidation based on TTL")
    print("- Memory and size limits to prevent unbounded growth")
    print("- Detailed statistics for monitoring and optimization")
    
    # Clean up test cache
    cache.clear()
    print(f"\nTest cache cleared.")


if __name__ == "__main__":
    test_query_cache()