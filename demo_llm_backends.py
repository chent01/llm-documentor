#!/usr/bin/env python3
"""
Demonstration script for enhanced LLM backends with token limit handling.

This script shows how the LlamaCppBackend and LocalServerBackend handle
token limits, content chunking, and error scenarios for medical software analysis.
"""

import logging
from typing import List
from medical_analyzer.llm.llama_cpp_backend import LlamaCppBackend
from medical_analyzer.llm.local_server_backend import LocalServerBackend
from medical_analyzer.llm.backend import LLMError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def demo_llama_cpp_backend():
    """Demonstrate LlamaCpp backend capabilities."""
    print("\n" + "="*60)
    print("LLAMA.CPP BACKEND DEMONSTRATION")
    print("="*60)
    
    # Configuration for LlamaCpp backend
    config = {
        "model_path": "/path/to/your/model.gguf",  # Update with actual path
        "n_ctx": 4096,
        "n_threads": 4,
        "verbose": False,
        "chunk_overlap_tokens": 50
    }
    
    try:
        backend = LlamaCppBackend(config)
        
        print(f"Backend available: {backend.is_available()}")
        
        if not backend.is_available():
            print("LlamaCpp backend not available (llama-cpp-python not installed or model not found)")
            print("This is expected in the test environment.")
            return
        
        # Get model info
        model_info = backend.get_model_info()
        print(f"Model: {model_info.name}")
        print(f"Context length: {model_info.context_length}")
        print(f"Type: {model_info.type}")
        
        # Test token estimation
        test_text = "This is a medical device monitoring function that checks vital signs."
        estimated_tokens = backend.estimate_tokens(test_text)
        print(f"Estimated tokens for test text: {estimated_tokens}")
        
        # Test content chunking
        large_code = """
        // Medical device heart rate monitor
        void monitor_heart_rate() {
            int heart_rate = 0;
            
            while (system_active) {
                // Read sensor data
                heart_rate = read_heart_sensor();
                
                // Validate reading
                if (heart_rate < 40 || heart_rate > 200) {
                    trigger_alarm("Heart rate out of range");
                    continue;
                }
                
                // Store reading
                store_heart_rate(heart_rate);
                
                // Check for arrhythmia
                if (detect_arrhythmia(heart_rate)) {
                    alert_medical_staff();
                }
                
                // Update display
                update_heart_rate_display(heart_rate);
                
                // Wait for next reading
                delay_ms(1000);
            }
        }
        """ * 10  # Repeat to make it large
        
        chunks = backend.chunk_content(large_code, max_chunk_size=100)
        print(f"Large code chunked into {len(chunks)} pieces")
        
        # Test input validation
        is_valid = backend.validate_input_length("Short prompt", ["Context chunk"])
        print(f"Input validation result: {is_valid}")
        
        # Test generation (will fail since model is not actually available)
        try:
            result = backend.generate(
                "Analyze this medical device code for safety requirements",
                context_chunks=chunks[:2],  # Use first 2 chunks
                temperature=0.1
            )
            print(f"Generation result: {result[:100]}...")
        except LLMError as e:
            print(f"Generation failed as expected: {e}")
            
    except Exception as e:
        print(f"Error with LlamaCpp backend: {e}")


def demo_local_server_backend():
    """Demonstrate LocalServer backend capabilities."""
    print("\n" + "="*60)
    print("LOCAL SERVER BACKEND DEMONSTRATION")
    print("="*60)
    
    # Configuration for LocalServer backend
    config = {
        "base_url": "http://localhost:8080",
        "api_key": "",  # Optional
        "timeout": 30,
        "max_tokens": 512,
        "chars_per_token": 4,
        "chunk_overlap_chars": 100
    }
    
    try:
        backend = LocalServerBackend(config)
        
        print(f"Backend available: {backend.is_available()}")
        
        if not backend.is_available():
            print("Local server not available (no server running on localhost:8080)")
            print("This is expected if you don't have a local LLM server running.")
        
        # Test token estimation
        test_text = "This is a medical device monitoring function that checks vital signs."
        estimated_tokens = backend.estimate_tokens(test_text)
        print(f"Estimated tokens for test text: {estimated_tokens}")
        
        # Test content chunking with custom parameters
        large_medical_text = """
        Medical Device Software Requirements:
        
        1. The system SHALL monitor patient vital signs continuously
        2. The system SHALL alert medical staff when readings are abnormal
        3. The system SHALL store all readings with timestamps
        4. The system SHALL have redundant safety mechanisms
        5. The system SHALL comply with IEC 62304 standards
        
        Risk Analysis:
        - Heart rate sensor failure could lead to missed critical events
        - Software bugs could cause false alarms or missed alarms
        - Network connectivity issues could prevent alerts
        - Power failure could interrupt monitoring
        
        Mitigation Strategies:
        - Implement dual sensor redundancy
        - Use watchdog timers for software reliability
        - Provide battery backup for power failures
        - Include offline alert mechanisms
        """ * 20  # Repeat to make it large
        
        chunks = backend.chunk_content(large_medical_text, max_chunk_size=200)
        print(f"Large medical text chunked into {len(chunks)} pieces")
        
        # Show chunk sizes
        for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
            tokens = backend.estimate_tokens(chunk)
            print(f"Chunk {i+1}: {tokens} estimated tokens, {len(chunk)} characters")
        
        # Test input validation
        is_valid = backend.validate_input_length("Analyze medical requirements", chunks[:5])
        print(f"Input validation with 5 chunks: {is_valid}")
        
        # Test context reduction
        long_prompt = "Analyze this medical device software for compliance with FDA regulations"
        reduced_chunks = backend._reduce_context_for_limits(long_prompt, chunks)
        print(f"Context reduced from {len(chunks)} to {len(reduced_chunks)} chunks")
        
        # Test generation (will fail since server is not running)
        try:
            result = backend.generate(
                "Generate software requirements for a heart rate monitor",
                context_chunks=reduced_chunks[:3],
                system_prompt="You are a medical device software expert",
                temperature=0.1
            )
            print(f"Generation result: {result[:100]}...")
        except LLMError as e:
            print(f"Generation failed as expected: {e}")
            
    except Exception as e:
        print(f"Error with LocalServer backend: {e}")


def demo_error_handling():
    """Demonstrate error handling capabilities."""
    print("\n" + "="*60)
    print("ERROR HANDLING DEMONSTRATION")
    print("="*60)
    
    # Test with invalid configurations
    invalid_configs = [
        {},  # Missing required keys
        {"model_path": ""},  # Empty model path for LlamaCpp
        {"base_url": ""},  # Empty base URL for LocalServer
    ]
    
    for i, config in enumerate(invalid_configs):
        print(f"\nTesting invalid config {i+1}: {config}")
        
        try:
            if i == 0:
                # Test both backends with empty config
                try:
                    LlamaCppBackend(config)
                except LLMError as e:
                    print(f"LlamaCpp validation error: {e}")
                
                try:
                    LocalServerBackend(config)
                except LLMError as e:
                    print(f"LocalServer validation error: {e}")
            
            elif i == 1:
                # Test LlamaCpp with empty model path
                try:
                    backend = LlamaCppBackend({"model_path": ""})
                    print(f"Backend created, available: {backend.is_available()}")
                except LLMError as e:
                    print(f"LlamaCpp error: {e}")
            
            elif i == 2:
                # Test LocalServer with empty base URL
                try:
                    backend = LocalServerBackend({"base_url": ""})
                    print(f"Backend created, available: {backend.is_available()}")
                except LLMError as e:
                    print(f"LocalServer error: {e}")
                    
        except Exception as e:
            print(f"Unexpected error: {e}")


def main():
    """Run all demonstrations."""
    print("LLM BACKENDS DEMONSTRATION")
    print("This script demonstrates the enhanced LLM backends with token limit handling")
    print("and content chunking for medical software analysis.")
    
    # Run demonstrations
    demo_llama_cpp_backend()
    demo_local_server_backend()
    demo_error_handling()
    
    print("\n" + "="*60)
    print("DEMONSTRATION COMPLETE")
    print("="*60)
    print("\nKey features demonstrated:")
    print("- Token limit validation and handling")
    print("- Intelligent content chunking with overlap")
    print("- Context reduction for large inputs")
    print("- Robust error handling and graceful degradation")
    print("- Medical software analysis context support")
    print("\nTo use these backends in production:")
    print("1. Install llama-cpp-python for LlamaCpp backend")
    print("2. Set up a local LLM server for LocalServer backend")
    print("3. Configure appropriate model paths and URLs")
    print("4. Adjust token limits and chunking parameters as needed")


if __name__ == "__main__":
    main()