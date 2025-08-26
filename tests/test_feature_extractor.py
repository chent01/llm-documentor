"""
Unit tests for the FeatureExtractor service.

Tests feature extraction functionality with known code samples and expected features.
"""

import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime

from medical_analyzer.services.feature_extractor import FeatureExtractor
from medical_analyzer.models.result_models import FeatureExtractionResult
from medical_analyzer.models.core import CodeChunk, Feature, CodeReference
from medical_analyzer.models.enums import ChunkType, FeatureCategory
from medical_analyzer.llm.backend import LLMBackend, LLMError, ModelInfo, ModelType


class MockLLMBackend(LLMBackend):
    """Mock LLM backend for testing."""
    
    def __init__(self, config=None, responses=None):
        super().__init__(config or {})
        self.responses = responses or {}
        self.call_count = 0
        self.last_prompt = None
        self.last_system_prompt = None
        
    def generate(self, prompt, context_chunks=None, temperature=0.1, max_tokens=None, system_prompt=None):
        self.call_count += 1
        self.last_prompt = prompt
        self.last_system_prompt = system_prompt
        
        # Return predefined response based on prompt content
        for key, response in self.responses.items():
            if key in prompt:
                return response
        
        # Default response
        return '[]'
    
    def is_available(self):
        return True
    
    def get_model_info(self):
        return ModelInfo(
            name="mock-model",
            type=ModelType.CHAT,
            context_length=4096,
            backend_name="MockLLMBackend"
        )
    
    def get_required_config_keys(self):
        return []


class TestFeatureExtractor:
    """Test cases for FeatureExtractor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm = MockLLMBackend()
        self.extractor = FeatureExtractor(self.mock_llm, min_confidence=0.3)
    
    def create_sample_chunk(self, content, file_path="test.c", function_name="test_func", language="c"):
        """Create a sample code chunk for testing."""
        return CodeChunk(
            file_path=file_path,
            start_line=1,
            end_line=10,
            content=content,
            function_name=function_name,
            chunk_type=ChunkType.FUNCTION,
            metadata={'language': language}
        )
    
    def test_init(self):
        """Test feature extractor initialization."""
        assert self.extractor.llm_backend == self.mock_llm
        assert self.extractor.min_confidence == 0.3
        assert self.extractor.feature_counter == 0
    
    def test_extract_features_empty_chunks(self):
        """Test feature extraction with empty chunk list."""
        result = self.extractor.extract_features([])
        
        assert isinstance(result, FeatureExtractionResult)
        assert result.features == []
        assert result.confidence_score == 0.0
        assert result.chunks_processed == 0
        assert result.errors == []
        assert result.metadata['total_chunks'] == 0
    
    def test_extract_features_single_chunk(self):
        """Test feature extraction with a single chunk."""
        # Set up mock response
        mock_response = json.dumps([
            {
                "description": "Data validation functionality",
                "category": "validation",
                "confidence": 0.8,
                "evidence": ["validate_input function", "error checking"]
            }
        ])
        self.mock_llm.responses = {"validate_input": mock_response}
        
        chunk = self.create_sample_chunk(
            "int validate_input(char* input) { if (!input) return -1; return 0; }",
            function_name="validate_input"
        )
        
        result = self.extractor.extract_features([chunk])
        
        assert len(result.features) == 1
        assert result.features[0].description == "Data validation functionality"
        assert result.features[0].category == FeatureCategory.VALIDATION
        assert result.features[0].confidence == 0.8
        assert result.chunks_processed == 1
        assert len(result.errors) == 0
    
    def test_extract_features_multiple_chunks(self):
        """Test feature extraction with multiple chunks."""
        # Set up mock responses
        self.mock_llm.responses = {
            "validate": json.dumps([{
                "description": "Input validation",
                "category": "validation",
                "confidence": 0.7,
                "evidence": ["input checking"]
            }]),
            "display": json.dumps([{
                "description": "User display functionality",
                "category": "user_interface",
                "confidence": 0.9,
                "evidence": ["printf statement"]
            }])
        }
        
        chunks = [
            self.create_sample_chunk("int validate(char* input) { return input != NULL; }", function_name="validate"),
            self.create_sample_chunk("void display(char* msg) { printf('%s', msg); }", function_name="display")
        ]
        
        result = self.extractor.extract_features(chunks)
        
        assert len(result.features) == 2
        assert result.chunks_processed == 2
        assert result.confidence_score > 0.0
        assert len(result.errors) == 0
    
    def test_extract_features_from_chunk_valid_json(self):
        """Test feature extraction from chunk with valid JSON response."""
        mock_response = json.dumps([
            {
                "description": "Memory allocation functionality",
                "category": "data_processing",
                "confidence": 0.6,
                "evidence": ["malloc call", "memory management"]
            }
        ])
        self.mock_llm.responses = {"malloc": mock_response}
        
        chunk = self.create_sample_chunk("void* ptr = malloc(100);")
        features = self.extractor._extract_features_from_chunk(chunk)
        
        assert len(features) == 1
        assert features[0].description == "Memory allocation functionality"
        assert features[0].category == FeatureCategory.DATA_PROCESSING
        assert features[0].confidence == 0.6
    
    def test_extract_features_from_chunk_invalid_json(self):
        """Test feature extraction with invalid JSON response."""
        self.mock_llm.responses = {"test": "invalid json response"}
        
        chunk = self.create_sample_chunk("int test() { return 0; }")
        features = self.extractor._extract_features_from_chunk(chunk)
        
        # Should fall back to heuristic extraction
        assert isinstance(features, list)
    
    def test_create_feature_from_data_valid(self):
        """Test creating feature from valid data."""
        chunk = self.create_sample_chunk("test code")
        feature_data = {
            "description": "Test feature description",
            "category": "validation",
            "confidence": 0.8,
            "evidence": ["test evidence 1", "test evidence 2"]
        }
        
        feature = self.extractor._create_feature_from_data(feature_data, chunk)
        
        assert feature is not None
        assert feature.description == "Test feature description"
        assert feature.category == FeatureCategory.VALIDATION
        assert feature.confidence == 0.8
        assert len(feature.evidence) == 1
        assert feature.evidence[0].file_path == chunk.file_path
    
    def test_create_feature_from_data_missing_description(self):
        """Test creating feature with missing description."""
        chunk = self.create_sample_chunk("test code")
        feature_data = {
            "category": "validation",
            "confidence": 0.8
        }
        
        feature = self.extractor._create_feature_from_data(feature_data, chunk)
        assert feature is None
    
    def test_create_feature_from_data_invalid_confidence(self):
        """Test creating feature with invalid confidence value."""
        chunk = self.create_sample_chunk("test code")
        feature_data = {
            "description": "Test feature",
            "confidence": "invalid",
            "category": "validation"
        }
        
        feature = self.extractor._create_feature_from_data(feature_data, chunk)
        # Invalid confidence should be clamped to default 0.5, so feature should still be created
        assert feature is not None
        assert feature.confidence == 0.5
    
    def test_parse_feature_category_valid(self):
        """Test parsing valid feature categories."""
        assert self.extractor._parse_feature_category("data_processing") == FeatureCategory.DATA_PROCESSING
        assert self.extractor._parse_feature_category("user_interface") == FeatureCategory.USER_INTERFACE
        assert self.extractor._parse_feature_category("safety") == FeatureCategory.SAFETY
    
    def test_parse_feature_category_invalid(self):
        """Test parsing invalid feature category defaults to DATA_PROCESSING."""
        assert self.extractor._parse_feature_category("invalid_category") == FeatureCategory.DATA_PROCESSING
    
    def test_fallback_feature_extraction_printf(self):
        """Test fallback extraction with printf function."""
        chunk = self.create_sample_chunk('printf("Hello World");')
        features = self.extractor._fallback_feature_extraction(chunk)
        
        assert len(features) >= 1
        # Should detect user interface feature
        ui_features = [f for f in features if f.category == FeatureCategory.USER_INTERFACE]
        assert len(ui_features) >= 1
        assert "output" in ui_features[0].description.lower() or "display" in ui_features[0].description.lower()
    
    def test_fallback_feature_extraction_file_operations(self):
        """Test fallback extraction with file operations."""
        chunk = self.create_sample_chunk('FILE* fp = fopen("test.txt", "r");')
        features = self.extractor._fallback_feature_extraction(chunk)
        
        storage_features = [f for f in features if f.category == FeatureCategory.STORAGE]
        assert len(storage_features) >= 1
        assert "file" in storage_features[0].description.lower()
    
    def test_fallback_feature_extraction_validation(self):
        """Test fallback extraction with validation code."""
        chunk = self.create_sample_chunk('if (validate(input)) { /* process */ }')
        features = self.extractor._fallback_feature_extraction(chunk)
        
        validation_features = [f for f in features if f.category == FeatureCategory.VALIDATION]
        assert len(validation_features) >= 1
        assert "validation" in validation_features[0].description.lower()
    
    def test_fallback_feature_extraction_no_matches(self):
        """Test fallback extraction with code that matches no heuristics."""
        chunk = self.create_sample_chunk('int x = 42;')
        features = self.extractor._fallback_feature_extraction(chunk)
        
        assert features == []
    
    def test_get_statistics_empty(self):
        """Test feature statistics with empty feature list."""
        stats = self.extractor.get_statistics([])
        
        assert stats['total_features'] == 0
        assert stats['average_confidence'] == 0.0
        assert stats['categories'] == {}
        assert stats['high_confidence_features'] == 0
    
    def test_get_statistics_with_features(self):
        """Test feature statistics with actual features."""
        features = [
            Feature(
                id="FEAT_0001",
                description="High confidence feature",
                confidence=0.9,
                category=FeatureCategory.VALIDATION,
                metadata={'extraction_method': 'llm'}
            ),
            Feature(
                id="FEAT_0002", 
                description="Medium confidence feature",
                confidence=0.5,
                category=FeatureCategory.USER_INTERFACE,
                metadata={'extraction_method': 'heuristic'}
            ),
            Feature(
                id="FEAT_0003",
                description="Low confidence feature", 
                confidence=0.2,
                category=FeatureCategory.VALIDATION,
                metadata={'extraction_method': 'llm'}
            )
        ]
        
        stats = self.extractor.get_statistics(features)
        
        assert stats['total_features'] == 3
        assert abs(stats['average_confidence'] - 0.533) < 0.01  # (0.9 + 0.5 + 0.2) / 3
        assert stats['categories']['VALIDATION'] == 2
        assert stats['categories']['USER_INTERFACE'] == 1
        assert stats['high_confidence_features'] == 1  # >= 0.7
        assert stats['medium_confidence_features'] == 1  # 0.4 <= x < 0.7
        assert stats['low_confidence_features'] == 1  # < 0.4
        assert stats['extraction_methods']['llm'] == 2
        assert stats['extraction_methods']['heuristic'] == 1
    
    def test_filter_by_confidence(self):
        """Test filtering features by confidence threshold."""
        features = [
            Feature(id="1", description="High", confidence=0.8, category=FeatureCategory.VALIDATION),
            Feature(id="2", description="Medium", confidence=0.5, category=FeatureCategory.VALIDATION),
            Feature(id="3", description="Low", confidence=0.2, category=FeatureCategory.VALIDATION)
        ]
        
        filtered = self.extractor.filter_by_confidence(features, 0.4)
        assert len(filtered) == 2
        assert all(f.confidence >= 0.4 for f in filtered)
    
    def test_group_by_file(self):
        """Test grouping features by source file."""
        features = [
            Feature(
                id="1", 
                description="Feature 1", 
                confidence=0.8,
                category=FeatureCategory.VALIDATION,
                evidence=[CodeReference(file_path="file1.c", start_line=1, end_line=10)]
            ),
            Feature(
                id="2",
                description="Feature 2",
                confidence=0.7,
                category=FeatureCategory.VALIDATION,
                evidence=[CodeReference(file_path="file1.c", start_line=20, end_line=30)]
            ),
            Feature(
                id="3",
                description="Feature 3", 
                confidence=0.6,
                category=FeatureCategory.VALIDATION,
                evidence=[CodeReference(file_path="file2.c", start_line=1, end_line=15)]
            )
        ]
        
        grouped = self.extractor.group_by_file(features)
        
        assert len(grouped) == 2
        assert len(grouped["file1.c"]) == 2
        assert len(grouped["file2.c"]) == 1
    
    def test_llm_error_handling_recoverable(self):
        """Test handling of recoverable LLM errors."""
        # Create a mock that raises recoverable LLM error
        error_llm = Mock(spec=LLMBackend)
        error_llm.generate.side_effect = LLMError("Temporary error", recoverable=True)
        
        extractor = FeatureExtractor(error_llm)
        chunk = self.create_sample_chunk('printf("test");')
        
        # Should fall back to heuristic extraction
        features = extractor._extract_features_from_chunk(chunk)
        assert isinstance(features, list)
    
    def test_llm_error_handling_non_recoverable(self):
        """Test handling of non-recoverable LLM errors."""
        error_llm = Mock(spec=LLMBackend)
        error_llm.generate.side_effect = LLMError("Fatal error", recoverable=False)
        
        extractor = FeatureExtractor(error_llm)
        chunk = self.create_sample_chunk("test code")
        
        with pytest.raises(LLMError):
            extractor._extract_features_from_chunk(chunk)
    
    def test_confidence_threshold_filtering(self):
        """Test that features below confidence threshold are filtered out."""
        mock_response = json.dumps([
            {
                "description": "High confidence feature",
                "category": "validation",
                "confidence": 0.8,
                "evidence": ["strong evidence"]
            },
            {
                "description": "Low confidence feature",
                "category": "validation", 
                "confidence": 0.1,
                "evidence": ["weak evidence"]
            }
        ])
        self.mock_llm.responses = {"test": mock_response}
        
        chunk = self.create_sample_chunk("test code")
        features = self.extractor._extract_features_from_chunk(chunk)
        
        # Only high confidence feature should be included (min_confidence = 0.3)
        assert len(features) == 1
        assert features[0].confidence == 0.8
    
    def test_javascript_chunk_processing(self):
        """Test processing JavaScript code chunks."""
        mock_response = json.dumps([{
            "description": "JavaScript function",
            "category": "data_processing",
            "confidence": 0.7,
            "evidence": ["function definition"]
        }])
        self.mock_llm.responses = {"function": mock_response}
        
        chunk = self.create_sample_chunk(
            "function processData(data) { return data.filter(x => x > 0); }",
            file_path="test.js",
            function_name="processData",
            language="javascript"
        )
        
        features = self.extractor._extract_features_from_chunk(chunk)
        
        assert len(features) == 1
        assert features[0].metadata['language'] == 'javascript'
    
    def test_feature_id_generation(self):
        """Test that feature IDs are generated uniquely."""
        mock_response = json.dumps([{
            "description": "Test feature",
            "category": "validation",
            "confidence": 0.5,
            "evidence": ["test"]
        }])
        self.mock_llm.responses = {"test": mock_response}
        
        chunk1 = self.create_sample_chunk("test code 1")
        chunk2 = self.create_sample_chunk("test code 2")
        
        features1 = self.extractor._extract_features_from_chunk(chunk1)
        features2 = self.extractor._extract_features_from_chunk(chunk2)
        
        assert features1[0].id != features2[0].id
        assert features1[0].id == "FEAT_0001"
        assert features2[0].id == "FEAT_0002"


class TestFeatureExtractionIntegration:
    """Integration tests for feature extraction with realistic code samples."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm = MockLLMBackend()
        self.extractor = FeatureExtractor(self.mock_llm, min_confidence=0.3)
    
    def test_c_medical_device_code(self):
        """Test feature extraction from realistic C medical device code."""
        c_code = """
        int validate_sensor_reading(float reading) {
            if (reading < 0.0 || reading > 100.0) {
                log_error("Invalid sensor reading: %f", reading);
                return -1;
            }
            return 0;
        }
        
        void display_patient_data(patient_data_t* data) {
            if (!data) return;
            printf("Patient ID: %d\\n", data->id);
            printf("Heart Rate: %d bpm\\n", data->heart_rate);
        }
        """
        
        # Set up realistic LLM response
        mock_response = json.dumps([
            {
                "description": "Sensor data validation with range checking",
                "category": "validation",
                "confidence": 0.9,
                "evidence": ["Range checking (0.0 to 100.0)", "Error logging", "Input validation"]
            },
            {
                "description": "Patient data display functionality",
                "category": "user_interface", 
                "confidence": 0.8,
                "evidence": ["printf statements", "Patient data formatting", "Null pointer check"]
            },
            {
                "description": "Error logging for safety",
                "category": "safety",
                "confidence": 0.7,
                "evidence": ["log_error function call", "Error message formatting"]
            }
        ])
        self.mock_llm.responses = {"validate_sensor_reading": mock_response}
        
        chunk = CodeChunk(
            file_path="medical_device.c",
            start_line=1,
            end_line=15,
            content=c_code,
            function_name="validate_sensor_reading",
            chunk_type=ChunkType.FUNCTION,
            metadata={'language': 'c'}
        )
        
        result = self.extractor.extract_features([chunk])
        
        assert len(result.features) == 3
        assert result.chunks_processed == 1
        assert len(result.errors) == 0
        
        # Check that we have validation, UI, and safety features
        categories = [f.category for f in result.features]
        assert FeatureCategory.VALIDATION in categories
        assert FeatureCategory.USER_INTERFACE in categories
        assert FeatureCategory.SAFETY in categories
    
    def test_javascript_electron_code(self):
        """Test feature extraction from JavaScript/Electron code."""
        js_code = """
        const { ipcRenderer } = require('electron');
        
        class DeviceController {
            constructor() {
                this.deviceStatus = 'disconnected';
            }
            
            async connectToDevice() {
                try {
                    const result = await ipcRenderer.invoke('connect-device');
                    if (result.success) {
                        this.deviceStatus = 'connected';
                        this.updateUI();
                    }
                } catch (error) {
                    console.error('Device connection failed:', error);
                    this.showErrorDialog(error.message);
                }
            }
            
            updateUI() {
                document.getElementById('status').textContent = this.deviceStatus;
            }
        }
        """
        
        mock_response = json.dumps([
            {
                "description": "Device connection management with async communication",
                "category": "device_control",
                "confidence": 0.9,
                "evidence": ["ipcRenderer.invoke", "Device status tracking", "Async/await pattern"]
            },
            {
                "description": "User interface updates for device status",
                "category": "user_interface",
                "confidence": 0.8,
                "evidence": ["DOM manipulation", "Status display", "UI update method"]
            },
            {
                "description": "Error handling and user notification",
                "category": "safety",
                "confidence": 0.7,
                "evidence": ["try-catch block", "Error logging", "Error dialog display"]
            }
        ])
        self.mock_llm.responses = {"DeviceController": mock_response}
        
        chunk = CodeChunk(
            file_path="device_controller.js",
            start_line=1,
            end_line=25,
            content=js_code,
            function_name="DeviceController",
            chunk_type=ChunkType.CLASS,
            metadata={'language': 'javascript'}
        )
        
        result = self.extractor.extract_features([chunk])
        
        assert len(result.features) == 3
        assert result.chunks_processed == 1
        
        # Verify feature categories
        categories = [f.category for f in result.features]
        assert FeatureCategory.DEVICE_CONTROL in categories
        assert FeatureCategory.USER_INTERFACE in categories
        assert FeatureCategory.SAFETY in categories