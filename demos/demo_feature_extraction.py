#!/usr/bin/env python3
"""
Demo script for feature extraction functionality.

This script demonstrates how to use the AnalysisOrchestrator to extract
features from code chunks using local LLMs.
"""

import json
from medical_analyzer.services.feature_extractor import FeatureExtractor
from medical_analyzer.models.core import CodeChunk
from medical_analyzer.models.enums import ChunkType
from medical_analyzer.llm.backend import FallbackLLMBackend


def create_sample_chunks():
    """Create sample code chunks for demonstration."""
    
    # C code sample - medical device sensor validation
    c_code = """
int validate_sensor_reading(float reading, float min_val, float max_val) {
    // Input validation
    if (reading < min_val || reading > max_val) {
        log_error("Sensor reading %.2f out of range [%.2f, %.2f]", 
                  reading, min_val, max_val);
        trigger_alarm(ALARM_SENSOR_OUT_OF_RANGE);
        return ERROR_INVALID_READING;
    }
    
    // Additional safety checks
    if (isnan(reading) || isinf(reading)) {
        log_error("Invalid sensor reading: NaN or Inf detected");
        trigger_alarm(ALARM_SENSOR_MALFUNCTION);
        return ERROR_SENSOR_MALFUNCTION;
    }
    
    return SUCCESS;
}
"""
    
    # JavaScript code sample - patient data display
    js_code = """
class PatientDataDisplay {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.patientData = null;
        this.updateInterval = null;
    }
    
    async loadPatientData(patientId) {
        try {
            const response = await fetch(`/api/patients/${patientId}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            this.patientData = await response.json();
            this.validatePatientData();
            this.renderPatientInfo();
            this.startRealTimeUpdates();
            
        } catch (error) {
            console.error('Failed to load patient data:', error);
            this.showErrorMessage('Unable to load patient data. Please try again.');
        }
    }
    
    validatePatientData() {
        if (!this.patientData || !this.patientData.id) {
            throw new Error('Invalid patient data structure');
        }
        
        // Validate vital signs ranges
        const vitals = this.patientData.vitals;
        if (vitals) {
            if (vitals.heartRate < 30 || vitals.heartRate > 200) {
                console.warn('Heart rate out of normal range:', vitals.heartRate);
            }
            if (vitals.bloodPressure && 
                (vitals.bloodPressure.systolic < 70 || vitals.bloodPressure.systolic > 200)) {
                console.warn('Blood pressure out of normal range:', vitals.bloodPressure);
            }
        }
    }
}
"""
    
    chunks = [
        CodeChunk(
            file_path="sensor_validation.c",
            start_line=1,
            end_line=20,
            content=c_code,
            function_name="validate_sensor_reading",
            chunk_type=ChunkType.FUNCTION,
            metadata={'language': 'c', 'module': 'sensor_management'}
        ),
        CodeChunk(
            file_path="patient_display.js", 
            start_line=1,
            end_line=35,
            content=js_code,
            function_name="PatientDataDisplay",
            chunk_type=ChunkType.CLASS,
            metadata={'language': 'javascript', 'framework': 'electron'}
        )
    ]
    
    return chunks


def demo_with_mock_llm():
    """Demonstrate feature extraction with mock LLM responses."""
    print("=== Feature Extraction Demo with Mock LLM ===\n")
    
    # Create mock LLM backend with predefined responses
    class MockLLMBackend(FallbackLLMBackend):
        def generate(self, prompt, context_chunks=None, temperature=0.1, max_tokens=None, system_prompt=None):
            # Simulate realistic LLM responses based on code content
            if "validate_sensor_reading" in prompt:
                return json.dumps([
                    {
                        "description": "Sensor data validation with range checking and safety alarms",
                        "category": "validation",
                        "confidence": 0.95,
                        "evidence": [
                            "Range validation (min_val, max_val)",
                            "NaN/Inf detection",
                            "Error logging with log_error()",
                            "Safety alarm triggering",
                            "Multiple return codes for different error types"
                        ]
                    },
                    {
                        "description": "Safety-critical alarm system integration",
                        "category": "safety",
                        "confidence": 0.90,
                        "evidence": [
                            "trigger_alarm() function calls",
                            "ALARM_SENSOR_OUT_OF_RANGE constant",
                            "ALARM_SENSOR_MALFUNCTION constant",
                            "Error classification and reporting"
                        ]
                    },
                    {
                        "description": "Error logging and diagnostic functionality",
                        "category": "monitoring",
                        "confidence": 0.85,
                        "evidence": [
                            "log_error() function calls",
                            "Formatted error messages with sensor values",
                            "Diagnostic information capture"
                        ]
                    }
                ])
            elif "PatientDataDisplay" in prompt:
                return json.dumps([
                    {
                        "description": "Patient data retrieval and management system",
                        "category": "data_processing",
                        "confidence": 0.90,
                        "evidence": [
                            "Async data fetching with fetch() API",
                            "JSON data parsing",
                            "Patient data structure management",
                            "Data validation methods"
                        ]
                    },
                    {
                        "description": "Real-time patient data display interface",
                        "category": "user_interface",
                        "confidence": 0.88,
                        "evidence": [
                            "DOM manipulation with getElementById",
                            "Patient information rendering",
                            "Real-time updates with intervals",
                            "Error message display to users"
                        ]
                    },
                    {
                        "description": "Medical data validation with vital signs checking",
                        "category": "validation",
                        "confidence": 0.85,
                        "evidence": [
                            "Heart rate range validation (30-200 bpm)",
                            "Blood pressure range checking",
                            "Patient data structure validation",
                            "Warning messages for out-of-range values"
                        ]
                    },
                    {
                        "description": "Error handling and user feedback system",
                        "category": "safety",
                        "confidence": 0.80,
                        "evidence": [
                            "Try-catch error handling",
                            "HTTP error status checking",
                            "User-friendly error messages",
                            "Console error logging"
                        ]
                    }
                ])
            else:
                return "[]"
    
    # Initialize feature extractor with mock LLM
    mock_llm = MockLLMBackend({})
    extractor = FeatureExtractor(mock_llm, min_confidence=0.3)
    
    # Create sample chunks
    chunks = create_sample_chunks()
    
    print(f"Processing {len(chunks)} code chunks...")
    print()
    
    # Run feature extraction
    result = extractor.extract_features(chunks)
    
    # Display results
    print(f"Feature Extraction Results:")
    print(f"- Total features extracted: {len(result.features)}")
    print(f"- Chunks processed: {result.chunks_processed}/{len(chunks)}")
    print(f"- Overall confidence: {result.confidence_score:.2f}")
    print(f"- Processing time: {result.processing_time:.2f} seconds")
    print(f"- Errors: {len(result.errors)}")
    print()
    
    # Display individual features
    print("Extracted Features:")
    print("-" * 80)
    
    for i, feature in enumerate(result.features, 1):
        print(f"{i}. {feature.description}")
        print(f"   Category: {feature.category.name}")
        print(f"   Confidence: {feature.confidence:.2f}")
        print(f"   Source: {feature.evidence[0].file_path}:{feature.evidence[0].start_line}-{feature.evidence[0].end_line}")
        if feature.evidence[0].function_name:
            print(f"   Function: {feature.evidence[0].function_name}")
        
        # Show evidence details if available
        evidence_details = feature.metadata.get('evidence_details', [])
        if evidence_details:
            print(f"   Evidence: {', '.join(evidence_details[:3])}")
            if len(evidence_details) > 3:
                print(f"             ... and {len(evidence_details) - 3} more")
        print()
    
    # Display statistics
    stats = extractor.get_statistics(result.features)
    print("Feature Statistics:")
    print("-" * 40)
    print(f"Total features: {stats['total_features']}")
    print(f"Average confidence: {stats['average_confidence']:.2f}")
    print(f"High confidence (≥0.7): {stats['high_confidence_features']}")
    print(f"Medium confidence (0.4-0.7): {stats['medium_confidence_features']}")
    print(f"Low confidence (<0.4): {stats['low_confidence_features']}")
    print()
    
    print("Features by category:")
    for category, count in stats['categories'].items():
        print(f"  {category}: {count}")
    print()
    
    print("Features by extraction method:")
    for method, count in stats['extraction_methods'].items():
        print(f"  {method}: {count}")


def demo_with_fallback():
    """Demonstrate fallback feature extraction when no LLM is available."""
    print("\n=== Feature Extraction Demo with Fallback (No LLM) ===\n")
    
    # Use fallback LLM backend
    fallback_llm = FallbackLLMBackend({})
    extractor = FeatureExtractor(fallback_llm, min_confidence=0.2)
    
    # Create sample chunks with heuristic-detectable patterns
    heuristic_code = """
void process_patient_data() {
    FILE* data_file = fopen("patient_data.txt", "r");
    if (!data_file) {
        printf("Error: Cannot open patient data file\\n");
        return;
    }
    
    char buffer[256];
    while (fgets(buffer, sizeof(buffer), data_file)) {
        if (validate_data_format(buffer)) {
            printf("Processing: %s", buffer);
        } else {
            printf("Invalid data format detected\\n");
        }
    }
    
    fclose(data_file);
}
"""
    
    chunk = CodeChunk(
        file_path="data_processor.c",
        start_line=1,
        end_line=18,
        content=heuristic_code,
        function_name="process_patient_data",
        chunk_type=ChunkType.FUNCTION,
        metadata={'language': 'c'}
    )
    
    result = extractor.extract_features([chunk])
    
    print(f"Fallback Feature Extraction Results:")
    print(f"- Features extracted: {len(result.features)}")
    print(f"- Processing method: Heuristic-based")
    print()
    
    if result.features:
        print("Features detected by heuristics:")
        for feature in result.features:
            print(f"- {feature.description} (confidence: {feature.confidence:.2f})")
            matched_keywords = feature.metadata.get('matched_keywords', [])
            if matched_keywords:
                print(f"  Matched keywords: {', '.join(matched_keywords)}")
    else:
        print("No features detected by heuristics in this code sample.")


if __name__ == "__main__":
    # Run both demos
    demo_with_mock_llm()
    demo_with_fallback()
    
    print("\n=== Demo Complete ===")
    print("\nThis demonstrates the feature extraction capabilities of the FeatureExtractor service.")
    print("In a real deployment, you would configure a local LLM backend (like llama.cpp)")
    print("to get more sophisticated feature analysis.")