#!/usr/bin/env python3
"""
Integration test for embedding service functionality.

This script demonstrates the complete embedding service workflow:
1. Initialize the service
2. Create code chunks
3. Build FAISS index
4. Perform similarity search
5. Save and load index
"""

import os
import tempfile
from medical_analyzer.llm.embedding_service import EmbeddingService
from medical_analyzer.models.core import CodeChunk
from medical_analyzer.models.enums import ChunkType


def main():
    """Run embedding service integration test."""
    print("=== Embedding Service Integration Test ===\n")
    
    # Initialize service
    print("1. Initializing embedding service...")
    service = EmbeddingService()
    
    if not service.is_available():
        print("❌ Embedding service not available. Please install sentence-transformers and faiss-cpu.")
        return
    
    print("✅ Embedding service initialized successfully")
    print(f"   Model: {service.model_name}")
    print(f"   Cache dir: {service.cache_dir}")
    
    # Create sample code chunks
    print("\n2. Creating sample code chunks...")
    chunks = [
        CodeChunk(
            file_path="main.c",
            start_line=1,
            end_line=10,
            content="""
int main(int argc, char* argv[]) {
    printf("Hello, Medical Device!\\n");
    initialize_device();
    run_main_loop();
    cleanup_device();
    return 0;
}
            """.strip(),
            function_name="main",
            chunk_type=ChunkType.FUNCTION
        ),
        CodeChunk(
            file_path="device.c",
            start_line=15,
            end_line=25,
            content="""
void initialize_device() {
    setup_sensors();
    calibrate_hardware();
    enable_safety_systems();
    log_startup_event();
}
            """.strip(),
            function_name="initialize_device",
            chunk_type=ChunkType.FUNCTION
        ),
        CodeChunk(
            file_path="safety.c",
            start_line=30,
            end_line=40,
            content="""
bool check_safety_conditions() {
    if (!sensor_readings_valid()) {
        trigger_alarm();
        return false;
    }
    return temperature_within_limits() && pressure_normal();
}
            """.strip(),
            function_name="check_safety_conditions",
            chunk_type=ChunkType.FUNCTION
        ),
        CodeChunk(
            file_path="ui.js",
            start_line=1,
            end_line=15,
            content="""
function displayPatientData(patientId) {
    const data = fetchPatientData(patientId);
    if (data.isValid) {
        updateUI(data);
        logAccess(patientId);
    } else {
        showError("Invalid patient data");
    }
}
            """.strip(),
            function_name="displayPatientData",
            chunk_type=ChunkType.FUNCTION
        )
    ]
    
    print(f"✅ Created {len(chunks)} code chunks")
    
    # Build FAISS index
    print("\n3. Building FAISS index...")
    success = service.build_index(chunks)
    
    if not success:
        print("❌ Failed to build FAISS index")
        return
    
    print("✅ FAISS index built successfully")
    
    # Get service statistics
    stats = service.get_stats()
    print(f"   Chunks indexed: {stats['num_chunks']}")
    print(f"   Embedding dimension: {stats['embedding_dimension']}")
    
    # Perform similarity searches
    print("\n4. Performing similarity searches...")
    
    queries = [
        "device initialization and setup",
        "safety checks and validation",
        "patient data display",
        "main program entry point"
    ]
    
    for query in queries:
        print(f"\n   Query: '{query}'")
        results = service.search(query, k=2, min_similarity=0.1)
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"   {i}. {result.chunk.function_name} (similarity: {result.similarity:.3f})")
                print(f"      File: {result.chunk.file_path}")
        else:
            print("   No results found")
    
    # Test save and load functionality
    print("\n5. Testing save/load functionality...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        index_path = os.path.join(temp_dir, "test_index")
        
        # Save index
        print("   Saving index...")
        save_success = service.save_index(index_path)
        
        if not save_success:
            print("   ❌ Failed to save index")
            return
        
        print("   ✅ Index saved successfully")
        
        # Create new service and load index
        print("   Loading index in new service...")
        new_service = EmbeddingService()
        load_success = new_service.load_index(index_path)
        
        if not load_success:
            print("   ❌ Failed to load index")
            return
        
        print("   ✅ Index loaded successfully")
        
        # Verify loaded index works
        test_results = new_service.search("safety validation", k=1)
        if test_results:
            print(f"   ✅ Loaded index working - found: {test_results[0].chunk.function_name}")
        else:
            print("   ❌ Loaded index not working properly")
    
    # Test similar chunks functionality
    print("\n6. Testing similar chunks functionality...")
    reference_chunk = chunks[0]  # main function
    similar = service.get_similar_chunks(reference_chunk, k=2, exclude_self=True)
    
    print(f"   Similar to '{reference_chunk.function_name}':")
    for result in similar:
        print(f"   - {result.chunk.function_name} (similarity: {result.similarity:.3f})")
    
    print("\n=== Integration Test Complete ===")
    print("✅ All embedding service functionality working correctly!")


if __name__ == "__main__":
    main()