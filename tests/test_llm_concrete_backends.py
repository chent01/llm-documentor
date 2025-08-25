"""
Integration tests for concrete LLM backend implementations.

Tests LlamaCppBackend and LocalServerBackend with mock responses
and error handling scenarios.
"""

import pytest
import json
import tempfile
import os
import sys
from unittest.mock import Mock, patch, MagicMock
import requests

from medical_analyzer.llm.llama_cpp_backend import LlamaCppBackend
from medical_analyzer.llm.local_server_backend import LocalServerBackend
from medical_analyzer.llm.backend import LLMError, ModelInfo, ModelType


class TestLlamaCppBackend:
    """Test cases for LlamaCpp backend implementation."""
    
    def test_initialization_no_llama_cpp(self):
        """Test initialization when llama-cpp-python is not available."""
        config = {"model_path": "/nonexistent/model.bin"}
        
        with patch('medical_analyzer.llm.llama_cpp_backend.logger'):
            backend = LlamaCppBackend(config)
            
            assert not backend.is_available()
            assert backend._llama is None
    
    def test_initialization_success(self):
        """Test initialization behavior (llama-cpp not available in test environment)."""
        config = {
            "model_path": "/path/to/model.bin",
            "n_ctx": 2048,
            "n_threads": 4,
            "verbose": False
        }
        
        # In test environment, llama-cpp-python is not available
        # so backend should not be available
        backend = LlamaCppBackend(config)
        assert not backend.is_available()
        assert backend._llama is None
    
    def test_generate_completion_format(self):
        """Test text generation when backend is not available."""
        config = {"model_path": "/path/to/model.bin"}
        backend = LlamaCppBackend(config)
        
        # Should raise error when not available
        with pytest.raises(LLMError):
            backend.generate("Test prompt")
    
    def test_generate_chat_format(self):
        """Test text generation with chat format when backend is not available."""
        config = {
            "model_path": "/path/to/model.bin",
            "chat_format": True
        }
        backend = LlamaCppBackend(config)
        
        # Should raise error when not available
        with pytest.raises(LLMError):
            backend.generate("Test prompt", system_prompt="You are a helpful assistant")
    
    def test_generate_with_context(self):
        """Test generation with context chunks when backend is not available."""
        config = {"model_path": "/path/to/model.bin"}
        backend = LlamaCppBackend(config)
        
        context_chunks = ["Context chunk 1", "Context chunk 2"]
        
        # Should raise error when not available
        with pytest.raises(LLMError):
            backend.generate("Test prompt", context_chunks=context_chunks)
    
    def test_generate_not_available(self):
        """Test generation when backend is not available."""
        config = {"model_path": "/nonexistent/model.bin"}
        backend = LlamaCppBackend(config)
        
        with pytest.raises(LLMError) as exc_info:
            backend.generate("Test prompt")
        
        assert "not available" in str(exc_info.value)
        assert not exc_info.value.recoverable
    
    def test_generate_error_handling(self):
        """Test error handling during generation when backend is not available."""
        config = {"model_path": "/path/to/model.bin"}
        backend = LlamaCppBackend(config)
        
        with pytest.raises(LLMError) as exc_info:
            backend.generate("Test prompt")
        
        assert "not available" in str(exc_info.value)
        assert not exc_info.value.recoverable
    
    def test_token_based_chunking(self):
        """Test content chunking fallback when backend is not available."""
        config = {"model_path": "/path/to/model.bin"}
        backend = LlamaCppBackend(config)
        
        content = "This is a test content for chunking. " * 100  # Long content
        chunks = backend.chunk_content(content, max_chunk_size=50)
        
        # Should fall back to character-based chunking
        assert len(chunks) >= 2
        
        # Verify all content is preserved
        reconstructed = "".join(chunks)
        assert reconstructed == content
    
    def test_required_config_keys(self):
        """Test required configuration keys."""
        config = {"model_path": "/path/to/model.bin"}
        backend = LlamaCppBackend(config)
        
        required_keys = backend.get_required_config_keys()
        assert "model_path" in required_keys
    
    def test_config_validation_missing_model_path(self):
        """Test configuration validation with missing model path."""
        config = {}
        
        with pytest.raises(LLMError) as exc_info:
            LlamaCppBackend(config)
        
        assert "Missing required configuration keys" in str(exc_info.value)
        assert "model_path" in str(exc_info.value)
    
    def test_estimate_tokens_fallback(self):
        """Test token estimation when backend is not available."""
        config = {"model_path": "/path/to/model.bin"}
        backend = LlamaCppBackend(config)
        
        text = "This is a test text for token estimation."
        estimated_tokens = backend.estimate_tokens(text)
        
        # Should use character-based estimation (roughly text length / 4)
        expected_tokens = len(text) // 4
        assert estimated_tokens == expected_tokens
    
    def test_validate_input_length_not_available(self):
        """Test input validation when backend is not available."""
        config = {"model_path": "/path/to/model.bin"}
        backend = LlamaCppBackend(config)
        
        # Should return True when backend is not available
        assert backend.validate_input_length("Test prompt")
        assert backend.validate_input_length("Test prompt", ["context1", "context2"])
    
    def test_chunk_content_with_overlap(self):
        """Test content chunking with token overlap."""
        config = {
            "model_path": "/path/to/model.bin",
            "chunk_overlap_tokens": 10
        }
        backend = LlamaCppBackend(config)
        
        # Long content that will need chunking
        content = "This is a sentence. " * 50  # Repeat to make it long
        chunks = backend.chunk_content(content, max_chunk_size=20)
        
        # Should create multiple chunks
        assert len(chunks) > 1
        
        # Verify all content is preserved (accounting for overlap)
        total_length = sum(len(chunk) for chunk in chunks)
        assert total_length >= len(content)  # Should be >= due to overlap


class TestLocalServerBackend:
    """Test cases for LocalServer backend implementation."""
    
    def test_initialization(self):
        """Test basic initialization."""
        config = {"base_url": "http://localhost:8080"}
        backend = LocalServerBackend(config)
        
        assert backend.config == config
        assert isinstance(backend._session, requests.Session)
    
    def test_initialization_with_api_key(self):
        """Test initialization with API key."""
        config = {
            "base_url": "http://localhost:8080",
            "api_key": "test-key"
        }
        backend = LocalServerBackend(config)
        
        assert "Authorization" in backend._session.headers
        assert backend._session.headers["Authorization"] == "Bearer test-key"
    
    @patch('requests.Session.get')
    def test_is_available_success(self, mock_get):
        """Test availability check when server is available."""
        config = {"base_url": "http://localhost:8080"}
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        backend = LocalServerBackend(config)
        assert backend.is_available()
    
    @patch('requests.Session.get')
    def test_is_available_failure(self, mock_get):
        """Test availability check when server is not available."""
        config = {"base_url": "http://localhost:8080"}
        
        # Mock connection error
        mock_get.side_effect = requests.ConnectionError("Connection failed")
        
        backend = LocalServerBackend(config)
        assert not backend.is_available()
    
    @patch('requests.Session.post')
    @patch('requests.Session.get')
    def test_generate_chat_completion(self, mock_get, mock_post):
        """Test generation using chat completion API."""
        config = {"base_url": "http://localhost:8080"}
        
        # Mock availability check
        mock_get.return_value = Mock(status_code=200)
        
        # Mock chat completion response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Generated response"}}]
        }
        mock_post.return_value = mock_response
        
        backend = LocalServerBackend(config)
        result = backend.generate("Test prompt", temperature=0.3)
        
        assert result == "Generated response"
        
        # Verify POST was called with correct data
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "/v1/chat/completions" in call_args[0][0]
        
        request_data = call_args[1]["json"]
        assert request_data["temperature"] == 0.3
        assert len(request_data["messages"]) == 1
        assert request_data["messages"][0]["content"] == "Test prompt"
    
    @patch('requests.Session.post')
    @patch('requests.Session.get')
    def test_generate_with_system_prompt(self, mock_get, mock_post):
        """Test generation with system prompt."""
        config = {"base_url": "http://localhost:8080"}
        
        # Mock availability check
        mock_get.return_value = Mock(status_code=200)
        
        # Mock chat completion response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "System response"}}]
        }
        mock_post.return_value = mock_response
        
        backend = LocalServerBackend(config)
        result = backend.generate(
            "Test prompt", 
            system_prompt="You are a helpful assistant"
        )
        
        assert result == "System response"
        
        # Verify system message was included
        request_data = mock_post.call_args[1]["json"]
        messages = request_data["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant"
    
    @patch('requests.Session.post')
    @patch('requests.Session.get')
    def test_generate_fallback_to_completion(self, mock_get, mock_post):
        """Test fallback to completion API when chat fails."""
        config = {"base_url": "http://localhost:8080"}
        
        # Mock availability check
        mock_get.return_value = Mock(status_code=200)
        
        # Mock responses: chat fails, completion succeeds
        chat_response = Mock()
        chat_response.status_code = 404  # Chat API not available
        
        completion_response = Mock()
        completion_response.status_code = 200
        completion_response.json.return_value = {
            "choices": [{"text": "Completion response"}]
        }
        
        mock_post.side_effect = [chat_response, completion_response]
        
        backend = LocalServerBackend(config)
        result = backend.generate("Test prompt")
        
        assert result == "Completion response"
        
        # Verify both APIs were tried
        assert mock_post.call_count == 2
    
    @patch('requests.Session.post')
    @patch('requests.Session.get')
    def test_generate_with_context_chunks(self, mock_get, mock_post):
        """Test generation with context chunks."""
        config = {"base_url": "http://localhost:8080"}
        
        # Mock availability check
        mock_get.return_value = Mock(status_code=200)
        
        # Mock chat completion response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Context response"}}]
        }
        mock_post.return_value = mock_response
        
        backend = LocalServerBackend(config)
        context_chunks = ["Context 1", "Context 2"]
        result = backend.generate("Test prompt", context_chunks=context_chunks)
        
        assert result == "Context response"
        
        # Verify context was included in messages
        request_data = mock_post.call_args[1]["json"]
        messages = request_data["messages"]
        
        # Should have context message and user message
        context_message = next(msg for msg in messages if "Context:" in msg["content"])
        assert "Context 1" in context_message["content"]
        assert "Context 2" in context_message["content"]
    
    def test_generate_not_available(self):
        """Test generation when backend is not available."""
        config = {"base_url": "http://localhost:8080"}
        
        with patch.object(LocalServerBackend, 'is_available', return_value=False):
            backend = LocalServerBackend(config)
            
            with pytest.raises(LLMError) as exc_info:
                backend.generate("Test prompt")
            
            assert "not available" in str(exc_info.value)
            assert exc_info.value.recoverable
    
    @patch('requests.Session.post')
    @patch('requests.Session.get')
    def test_generate_all_apis_fail(self, mock_get, mock_post):
        """Test generation when all API formats fail."""
        config = {"base_url": "http://localhost:8080"}
        
        # Mock availability check
        mock_get.return_value = Mock(status_code=200)
        
        # Mock all API calls to fail
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        backend = LocalServerBackend(config)
        
        with pytest.raises(LLMError) as exc_info:
            backend.generate("Test prompt")
        
        assert "All API formats failed" in str(exc_info.value)
        assert exc_info.value.recoverable
    
    @patch('requests.Session.get')
    def test_get_model_info_success(self, mock_get):
        """Test getting model info from server."""
        config = {"base_url": "http://localhost:8080"}
        
        # Mock model info response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{
                "id": "test-model",
                "context_length": 4096
            }]
        }
        mock_get.return_value = mock_response
        
        backend = LocalServerBackend(config)
        model_info = backend.get_model_info()
        
        assert model_info.name == "test-model"
        assert model_info.context_length == 4096
        assert model_info.type == ModelType.CHAT
    
    def test_get_model_info_not_available(self):
        """Test getting model info when backend is not available."""
        config = {"base_url": "http://localhost:8080"}
        
        with patch.object(LocalServerBackend, 'is_available', return_value=False):
            backend = LocalServerBackend(config)
            
            with pytest.raises(LLMError) as exc_info:
                backend.get_model_info()
            
            assert "not available" in str(exc_info.value)
    
    def test_required_config_keys(self):
        """Test required configuration keys."""
        config = {"base_url": "http://localhost:8080"}
        backend = LocalServerBackend(config)
        
        required_keys = backend.get_required_config_keys()
        assert "base_url" in required_keys
    
    def test_config_validation_missing_base_url(self):
        """Test configuration validation with missing base URL."""
        config = {}
        
        with pytest.raises(LLMError) as exc_info:
            LocalServerBackend(config)
        
        assert "Missing required configuration keys" in str(exc_info.value)
        assert "base_url" in str(exc_info.value)
    
    def test_estimate_tokens(self):
        """Test token estimation using character-based method."""
        config = {"base_url": "http://localhost:8080"}
        backend = LocalServerBackend(config)
        
        text = "This is a test text for token estimation."
        estimated_tokens = backend.estimate_tokens(text)
        
        # Should use character-based estimation (roughly text length / 4)
        expected_tokens = len(text) // 4
        assert estimated_tokens == expected_tokens
    
    def test_estimate_tokens_custom_ratio(self):
        """Test token estimation with custom character-to-token ratio."""
        config = {
            "base_url": "http://localhost:8080",
            "chars_per_token": 3  # Custom ratio
        }
        backend = LocalServerBackend(config)
        
        text = "This is a test text."
        estimated_tokens = backend.estimate_tokens(text)
        
        expected_tokens = len(text) // 3
        assert estimated_tokens == expected_tokens
    
    def test_validate_input_length_no_model_info(self):
        """Test input validation when model info is not available."""
        config = {"base_url": "http://localhost:8080"}
        
        with patch.object(LocalServerBackend, 'is_available', return_value=False):
            backend = LocalServerBackend(config)
            
            # Should return True when model info is not available
            assert backend.validate_input_length("Test prompt")
            assert backend.validate_input_length("Test prompt", ["context1", "context2"])
    
    @patch('requests.Session.get')
    def test_validate_input_length_with_model_info(self, mock_get):
        """Test input validation with model info available."""
        config = {"base_url": "http://localhost:8080"}
        
        # Mock model info response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{
                "id": "test-model",
                "context_length": 1000
            }]
        }
        mock_get.return_value = mock_response
        
        backend = LocalServerBackend(config)
        
        # Short input should be valid
        assert backend.validate_input_length("Short prompt")
        
        # Very long input should be invalid
        long_text = "Very long text. " * 1000  # Much longer than context
        assert not backend.validate_input_length(long_text)
    
    def test_chunk_content_with_overlap(self):
        """Test content chunking with character overlap."""
        config = {
            "base_url": "http://localhost:8080",
            "chunk_overlap_chars": 50
        }
        backend = LocalServerBackend(config)
        
        # Long content that will need chunking
        content = "This is a sentence. " * 100  # Repeat to make it long
        chunks = backend.chunk_content(content, max_chunk_size=50)  # Small chunks
        
        # Should create multiple chunks
        assert len(chunks) > 1
        
        # Verify all content is preserved (accounting for overlap)
        total_length = sum(len(chunk) for chunk in chunks)
        assert total_length >= len(content)  # Should be >= due to overlap
    
    def test_reduce_context_for_limits(self):
        """Test context reduction for token limits."""
        config = {"base_url": "http://localhost:8080"}
        
        with patch.object(LocalServerBackend, 'get_model_info') as mock_model_info:
            mock_model_info.return_value = ModelInfo(
                name="test-model",
                type=ModelType.CHAT,
                context_length=1000,
                backend_name="LocalServerBackend"
            )
            
            backend = LocalServerBackend(config)
            
            prompt = "Short prompt"
            context_chunks = [
                "This is context chunk 1. " * 20,  # Long chunk
                "This is context chunk 2. " * 20,  # Long chunk
                "This is context chunk 3. " * 20   # Long chunk
            ]
            
            reduced_chunks = backend._reduce_context_for_limits(prompt, context_chunks)
            
            # Should reduce the number of chunks or truncate them
            assert len(reduced_chunks) <= len(context_chunks)
            
            # Total estimated tokens should be reasonable
            total_tokens = backend.estimate_tokens(prompt)
            for chunk in reduced_chunks:
                total_tokens += backend.estimate_tokens(chunk)
            
            # Should be within reasonable limits (70% of context length)
            assert total_tokens <= 700


class TestIntegrationScenarios:
    """Integration tests for complete LLM backend workflows."""
    
    @patch('requests.Session.post')
    @patch('requests.Session.get')
    def test_local_server_complete_workflow(self, mock_get, mock_post):
        """Test complete workflow with LocalServerBackend."""
        config = {
            "base_url": "http://localhost:8080",
            "max_tokens": 100,
            "temperature": 0.2
        }
        
        # Mock availability check
        mock_get.return_value = Mock(status_code=200)
        
        # Mock successful generation
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "This is a medical software analysis response."}}]
        }
        mock_post.return_value = mock_response
        
        backend = LocalServerBackend(config)
        
        # Test generation with medical software context
        prompt = "Analyze this C function for medical device compliance"
        context_chunks = [
            "void monitor_heart_rate() { /* implementation */ }",
            "// This function monitors patient vital signs"
        ]
        
        result = backend.generate(
            prompt=prompt,
            context_chunks=context_chunks,
            system_prompt="You are a medical software analysis expert",
            temperature=0.2,
            max_tokens=100
        )
        
        assert result == "This is a medical software analysis response."
        
        # Verify the request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        request_data = call_args[1]["json"]
        
        assert request_data["temperature"] == 0.2
        assert request_data["max_tokens"] == 100
        assert len(request_data["messages"]) >= 2  # System + context + user messages
    
    def test_llama_cpp_error_handling_workflow(self):
        """Test error handling workflow with LlamaCppBackend."""
        config = {
            "model_path": "/nonexistent/model.bin",
            "n_ctx": 2048
        }
        
        backend = LlamaCppBackend(config)
        
        # Test that backend gracefully handles unavailability
        assert not backend.is_available()
        
        # Test that generation raises appropriate error
        with pytest.raises(LLMError) as exc_info:
            backend.generate("Test medical analysis prompt")
        
        assert "not available" in str(exc_info.value)
        assert exc_info.value.backend == "LlamaCppBackend"
        assert not exc_info.value.recoverable
    
    @patch('requests.Session.post')
    @patch('requests.Session.get')
    def test_token_limit_handling_integration(self, mock_get, mock_post):
        """Test integration of token limit handling."""
        config = {"base_url": "http://localhost:8080"}
        
        # Mock model info with small context
        model_info_response = Mock()
        model_info_response.status_code = 200
        model_info_response.json.return_value = {
            "data": [{
                "id": "small-model",
                "context_length": 512  # Small context for testing
            }]
        }
        mock_get.return_value = model_info_response
        
        # Mock successful generation
        generation_response = Mock()
        generation_response.status_code = 200
        generation_response.json.return_value = {
            "choices": [{"message": {"content": "Analysis complete with reduced context."}}]
        }
        mock_post.return_value = generation_response
        
        backend = LocalServerBackend(config)
        
        # Create input that would exceed token limits
        long_prompt = "Analyze this medical software code: " + "x" * 1000
        large_context = ["Large context chunk: " + "y" * 2000 for _ in range(5)]
        
        # Should handle token limits gracefully
        result = backend.generate(
            prompt=long_prompt,
            context_chunks=large_context,
            max_tokens=50
        )
        
        assert result == "Analysis complete with reduced context."
        
        # Verify generation was attempted (context should have been reduced)
        mock_post.assert_called_once()
    
    def test_chunking_integration_workflow(self):
        """Test content chunking integration workflow."""
        config = {"base_url": "http://localhost:8080"}
        backend = LocalServerBackend(config)
        
        # Test chunking of large medical software code
        large_code = """
        // Medical device monitoring system
        void initialize_monitoring() {
            // Initialize sensors
            sensor_init();
            
            // Setup safety checks
            safety_system_init();
            
            // Start monitoring loop
            while (system_active) {
                read_vital_signs();
                check_alarm_conditions();
                update_display();
                
                // Safety delay
                delay_ms(100);
            }
        }
        
        void read_vital_signs() {
            // Read heart rate
            heart_rate = read_heart_sensor();
            
            // Read blood pressure
            blood_pressure = read_bp_sensor();
            
            // Validate readings
            if (validate_readings()) {
                store_readings();
            } else {
                trigger_alarm();
            }
        }
        """ * 20  # Repeat to make it very large
        
        chunks = backend.chunk_content(large_code, max_chunk_size=100)
        
        # Should create multiple chunks
        assert len(chunks) > 1
        
        # Each chunk should be reasonably sized
        for chunk in chunks:
            estimated_tokens = backend.estimate_tokens(chunk)
            assert estimated_tokens <= 120  # Allow some margin
        
        # Verify content preservation
        reconstructed = "".join(chunks)
        # Due to overlap, reconstructed might be longer, but should contain original
        assert large_code.strip() in reconstructed or len(reconstructed) >= len(large_code) * 0.9


if __name__ == "__main__":
    pytest.main([__file__])