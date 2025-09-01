"""
Unit tests for APIResponseValidator class.

Tests cover:
- JSON schema validation
- Error extraction and reporting
- Retry logic determination
- Response parsing and validation
- Edge cases and error scenarios
"""

import pytest
import json
from unittest.mock import Mock, patch
import requests
from medical_analyzer.llm.api_response_validator import (
    APIResponseValidator, ValidationResult, ErrorDetails, GenerationResult, ValidationStatus, ErrorSeverity, RecoveryAction
)


class TestAPIResponseValidator:
    """Test suite for APIResponseValidator functionality."""
    
    @pytest.fixture
    def validator(self):
        """Create APIResponseValidator with test schemas."""
        schemas = {
            'requirements': {
                'type': 'object',
                'properties': {
                    'user_requirements': {'type': 'array'},
                    'software_requirements': {'type': 'array'},
                    'status': {'type': 'string'}
                },
                'required': ['user_requirements', 'software_requirements', 'status']
            },
            'test_generation': {
                'type': 'object',
                'properties': {
                    'test_cases': {'type': 'array'},
                    'coverage': {'type': 'object'},
                    'status': {'type': 'string'}
                },
                'required': ['test_cases', 'status']
            }
        }
        return APIResponseValidator(schemas)
    
    @pytest.fixture
    def mock_response(self):
        """Create mock HTTP response."""
        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.headers = {'content-type': 'application/json'}
        response.content = b'{"test": "data"}'
        response.text = '{"test": "data"}'
        return response
    
    def test_validate_valid_response(self, validator, mock_response):
        """Test validation of valid API response."""
        # Valid text generation response
        valid_data = {
            'choices': [{
                'message': {
                    'content': 'Generated requirements content'
                }
            }]
        }
        mock_response.json.return_value = valid_data
        
        result = validator.validate_response(mock_response, 'text_generation')
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.extracted_data is not None
        assert 'content' in result.extracted_data
    
    def test_validate_invalid_json_structure(self, validator, mock_response):
        """Test validation with invalid JSON structure."""
        # Missing required field
        invalid_data = {
            'invalid_field': 'some data'
            # Missing 'choices'
        }
        mock_response.json.return_value = invalid_data
        
        result = validator.validate_response(mock_response, 'text_generation')
        
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_validate_malformed_json(self, validator, mock_response):
        """Test validation with malformed JSON."""
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        result = validator.validate_response(mock_response, 'requirements')
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert 'Invalid JSON' in str(result.errors[0])
        assert result.confidence == 0.0
    
    def test_validate_unknown_operation(self, validator, mock_response):
        """Test validation with unknown operation type."""
        mock_response.json.return_value = {'some': 'data'}
        
        result = validator.validate_response(mock_response, 'unknown_operation')
        
        # Should still validate but may have warnings
        assert result is not None
    
    def test_extract_error_details_from_response(self, validator, mock_response):
        """Test error extraction from API response."""
        error_response = {
            'error': {
                'code': 'GENERATION_FAILED',
                'message': 'Failed to generate requirements',
                'details': 'Insufficient context provided'
            }
        }
        mock_response.json.return_value = error_response
        mock_response.status_code = 400
        
        error_details = validator.extract_error_details(mock_response)
        
        assert error_details.error_code == 'GENERATION_FAILED'
        assert error_details.error_message == 'Failed to generate requirements'
        assert 'Insufficient context' in error_details.error_context['details']
        assert error_details.is_recoverable is True
    
    def test_extract_error_details_http_error(self, validator, mock_response):
        """Test error extraction from HTTP error response."""
        mock_response.status_code = 500
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "Internal Server Error"
        
        error_details = validator.extract_error_details(mock_response)
        
        assert error_details.error_code == 'HTTP_500'
        assert 'Internal Server Error' in error_details.error_message
        assert error_details.is_recoverable is True
    
    def test_should_retry_recoverable_errors(self, validator, mock_response):
        """Test retry logic for recoverable errors."""
        # Test various HTTP status codes
        recoverable_codes = [429, 500, 502, 503, 504]
        non_recoverable_codes = [400, 401, 403, 404]
        
        for code in recoverable_codes:
            mock_response.status_code = code
            assert validator.should_retry(mock_response) is True
        
        for code in non_recoverable_codes:
            mock_response.status_code = code
            assert validator.should_retry(mock_response) is False
    
    def test_should_retry_with_error_response(self, validator, mock_response):
        """Test retry logic with structured error response."""
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'error': {
                'code': 'RATE_LIMITED',
                'message': 'Too many requests'
            }
        }
        
        # Rate limiting should be retryable
        assert validator.should_retry(mock_response) is True
        
        # Change to non-retryable error
        mock_response.json.return_value = {
            'error': {
                'code': 'INVALID_INPUT',
                'message': 'Invalid request format'
            }
        }
        
        assert validator.should_retry(mock_response) is False
    
    def test_parse_generation_result_success(self, validator):
        """Test parsing successful generation result."""
        response_data = {
            'user_requirements': ['UR1: Login capability'],
            'software_requirements': ['SR1: Credential validation'],
            'status': 'success',
            'metadata': {
                'generation_time': 1.5,
                'model_used': 'gpt-4'
            }
        }
        
        result = validator.parse_generation_result(response_data)
        
        assert result.success is True
        assert len(result.data['user_requirements']) == 1
        assert len(result.data['software_requirements']) == 1
        assert result.metadata['generation_time'] == 1.5
    
    def test_parse_generation_result_failure(self, validator):
        """Test parsing failed generation result."""
        response_data = {
            'status': 'failed',
            'error': 'Generation timeout',
            'partial_results': {
                'user_requirements': ['UR1: Partial requirement']
            }
        }
        
        result = validator.parse_generation_result(response_data)
        
        assert result.success is False
        assert result.error_message == 'Generation timeout'
        assert 'user_requirements' in result.partial_data
    
    def test_validate_response_with_warnings(self, validator, mock_response):
        """Test validation that produces warnings but is still valid."""
        # Valid structure but with potential issues
        data_with_warnings = {
            'user_requirements': [],  # Empty but valid
            'software_requirements': ['SR1: Valid requirement'],
            'status': 'partial_success'
        }
        mock_response.json.return_value = data_with_warnings
        
        result = validator.validate_response(mock_response, 'requirements')
        
        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert 'empty user_requirements' in str(result.warnings[0]).lower()
        assert 0.5 < result.confidence < 0.9
    
    def test_validate_response_confidence_scoring(self, validator, mock_response):
        """Test confidence scoring based on response quality."""
        # High confidence: complete data
        complete_data = {
            'user_requirements': ['UR1', 'UR2', 'UR3'],
            'software_requirements': ['SR1', 'SR2', 'SR3', 'SR4'],
            'status': 'success'
        }
        mock_response.json.return_value = complete_data
        result = validator.validate_response(mock_response, 'requirements')
        assert result.confidence > 0.8
        
        # Medium confidence: minimal data
        minimal_data = {
            'user_requirements': ['UR1'],
            'software_requirements': ['SR1'],
            'status': 'success'
        }
        mock_response.json.return_value = minimal_data
        result = validator.validate_response(mock_response, 'requirements')
        assert 0.5 < result.confidence < 0.8
        
        # Low confidence: empty arrays
        empty_data = {
            'user_requirements': [],
            'software_requirements': [],
            'status': 'success'
        }
        mock_response.json.return_value = empty_data
        result = validator.validate_response(mock_response, 'requirements')
        assert result.confidence < 0.5
    
    def test_validate_test_generation_response(self, validator, mock_response):
        """Test validation of test generation specific response."""
        test_data = {
            'test_cases': [
                {
                    'name': 'Test Login',
                    'steps': ['Enter credentials', 'Click login'],
                    'expected': 'User logged in'
                }
            ],
            'coverage': {
                'requirements_covered': 5,
                'total_requirements': 10
            },
            'status': 'success'
        }
        mock_response.json.return_value = test_data
        
        result = validator.validate_response(mock_response, 'test_generation')
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.extracted_data['test_cases'][0]['name'] == 'Test Login'
    
    def test_error_details_suggested_actions(self, validator, mock_response):
        """Test that error details include helpful suggested actions."""
        # Test timeout error
        mock_response.status_code = 504
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "Gateway Timeout"
        
        error_details = validator.extract_error_details(mock_response)
        
        assert 'retry' in error_details.suggested_action.value
        assert error_details.is_recoverable is True
        
        # Test authentication error
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        error_details = validator.extract_error_details(mock_response)
        
        # 401 errors should suggest modifying the request (authentication)
        assert error_details.suggested_action.value == 'modify_request'
        assert error_details.is_recoverable is False
    
    def test_validation_with_nested_schema_validation(self, validator, mock_response):
        """Test validation with complex nested data structures."""
        complex_data = {
            'user_requirements': [
                {
                    'id': 'UR1',
                    'text': 'User login requirement',
                    'acceptance_criteria': ['Valid credentials accepted']
                }
            ],
            'software_requirements': [
                {
                    'id': 'SR1',
                    'text': 'Credential validation',
                    'derived_from': ['UR1']
                }
            ],
            'status': 'success'
        }
        mock_response.json.return_value = complex_data
        
        result = validator.validate_response(mock_response, 'requirements')
        
        # Should still validate even with more complex structure
        assert result.is_valid is True
        assert result.extracted_data == complex_data


class TestValidationResult:
    """Test ValidationResult data model."""
    
    def test_validation_result_creation(self):
        """Test ValidationResult object creation and properties."""
        result = ValidationResult(
            status=ValidationStatus.VALID,
            is_valid=True,
            warnings=['Minor issue'],
            extracted_data={'key': 'value'},
            confidence=0.85
        )
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 1
        assert result.extracted_data['key'] == 'value'
        assert result.confidence == 0.85
    
    def test_validation_result_defaults(self):
        """Test ValidationResult with default values."""
        error_detail = ErrorDetails(
            error_code="TEST_ERROR",
            error_message="Test error"
        )
        result = ValidationResult(
            status=ValidationStatus.INVALID,
            is_valid=False
        )
        result.add_error(error_detail)
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.warnings == []
        assert result.extracted_data is None
        assert result.confidence == 1.0  # Default confidence


class TestErrorDetails:
    """Test ErrorDetails data model."""
    
    def test_error_details_creation(self):
        """Test ErrorDetails object creation and properties."""
        details = ErrorDetails(
            error_code='TEST_ERROR',
            error_message='Test error message',
            error_context={'detail': 'Additional context'},
            suggested_action=RecoveryAction.RETRY,
            is_recoverable=True
        )
        
        assert details.error_code == 'TEST_ERROR'
        assert details.error_message == 'Test error message'
        assert details.error_context['detail'] == 'Additional context'
        assert details.suggested_action == RecoveryAction.RETRY
        assert details.is_recoverable is True


class TestGenerationResult:
    """Test GenerationResult data model."""
    
    def test_generation_result_success(self):
        """Test successful GenerationResult creation."""
        result = GenerationResult(
            success=True,
            data={'requirements': ['REQ1']},
            metadata={'time': 1.0}
        )
        
        assert result.success is True
        assert result.data['requirements'] == ['REQ1']
        assert result.metadata['time'] == 1.0
        assert result.error_message is None
        assert result.partial_data == {}
    
    def test_generation_result_failure(self):
        """Test failed GenerationResult creation."""
        result = GenerationResult(
            success=False,
            error_message='Generation failed',
            partial_data={'partial': 'data'}
        )
        
        assert result.success is False
        assert result.error_message == 'Generation failed'
        assert result.partial_data['partial'] == 'data'
        assert result.data == {}
        assert result.metadata == {}