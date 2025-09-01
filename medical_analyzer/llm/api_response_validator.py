"""
API Response Validation System for LLM backends.

This module provides comprehensive validation of LLM API responses,
including JSON schema validation, error extraction, and recovery suggestions.
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Status of validation result."""
    VALID = "valid"
    INVALID = "invalid"
    PARTIAL = "partial"
    ERROR = "error"


class ErrorSeverity(Enum):
    """Severity levels for validation errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryAction(Enum):
    """Recommended recovery actions for errors."""
    RETRY = "retry"
    FALLBACK = "fallback"
    ABORT = "abort"
    MODIFY_REQUEST = "modify_request"
    WAIT_AND_RETRY = "wait_and_retry"


@dataclass
class ErrorDetails:
    """Detailed information about a validation error."""
    error_code: str
    error_message: str
    error_context: Dict[str, Any] = field(default_factory=dict)
    suggested_action: RecoveryAction = RecoveryAction.RETRY
    is_recoverable: bool = True
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            'error_code': self.error_code,
            'error_message': self.error_message,
            'error_context': self.error_context,
            'suggested_action': self.suggested_action.value,
            'is_recoverable': self.is_recoverable,
            'severity': self.severity.value,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class GenerationResult:
    """Result of content generation parsing."""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    partial_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of API response validation."""
    status: ValidationStatus
    is_valid: bool
    errors: List[ErrorDetails] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    extracted_data: Optional[Dict[str, Any]] = None
    confidence: float = 1.0
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, error: ErrorDetails) -> None:
        """Add an error to the validation result."""
        self.errors.append(error)
        self.is_valid = False
        if self.status == ValidationStatus.VALID:
            self.status = ValidationStatus.INVALID
    
    def add_warning(self, warning: str) -> None:
        """Add a warning to the validation result."""
        self.warnings.append(warning)
        if self.status == ValidationStatus.VALID and self.warnings:
            self.status = ValidationStatus.PARTIAL
    
    def get_highest_severity(self) -> Optional[ErrorSeverity]:
        """Get the highest severity error."""
        if not self.errors:
            return None
        
        severity_order = [ErrorSeverity.LOW, ErrorSeverity.MEDIUM, ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
        return max((error.severity for error in self.errors), key=lambda s: severity_order.index(s))
    
    def should_retry(self) -> bool:
        """Determine if the request should be retried based on errors."""
        if not self.errors:
            return False
        
        # Don't retry if any error is not recoverable
        if any(not error.is_recoverable for error in self.errors):
            return False
        
        # Don't retry critical errors
        if any(error.severity == ErrorSeverity.CRITICAL for error in self.errors):
            return False
        
        # Check if any error suggests retry
        return any(error.suggested_action in [RecoveryAction.RETRY, RecoveryAction.WAIT_AND_RETRY] 
                  for error in self.errors)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            'status': self.status.value,
            'is_valid': self.is_valid,
            'errors': [error.to_dict() for error in self.errors],
            'warnings': self.warnings,
            'extracted_data': self.extracted_data,
            'confidence': self.confidence,
            'processing_time': self.processing_time,
            'metadata': self.metadata
        }


class APIResponseValidator:
    """
    Comprehensive validator for LLM API responses.
    
    Provides JSON schema validation, content completeness checking,
    error extraction, and recovery suggestions.
    """
    
    def __init__(self, expected_schemas: Optional[Dict[str, Dict]] = None):
        """
        Initialize the API response validator.
        
        Args:
            expected_schemas: Dictionary mapping operation names to JSON schemas
        """
        self.expected_schemas = expected_schemas or {}
        self._setup_default_schemas()
        
        # Retry configuration
        self.max_retries = 3
        self.base_delay = 1.0  # Base delay for exponential backoff
        self.max_delay = 30.0  # Maximum delay between retries
        
        # Response caching
        self._response_cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
    
    def _setup_default_schemas(self) -> None:
        """Setup default JSON schemas for common operations."""
        
        # Schema for text generation responses
        self.expected_schemas['text_generation'] = {
            "type": "object",
            "properties": {
                "choices": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "message": {
                                "type": "object",
                                "properties": {
                                    "content": {"type": "string"}
                                },
                                "required": ["content"]
                            }
                        }
                    },
                    "minItems": 1
                }
            },
            "required": ["choices"]
        }
        
        # Schema for requirements generation responses
        self.expected_schemas['requirements_generation'] = {
            "type": "object",
            "properties": {
                "choices": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "object",
                                "properties": {
                                    "content": {"type": "string"}
                                },
                                "required": ["content"]
                            }
                        },
                        "required": ["message"]
                    },
                    "minItems": 1
                }
            },
            "required": ["choices"]
        }
        
        # Schema for model info responses
        self.expected_schemas['model_info'] = {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "context_length": {"type": "number"}
                        },
                        "required": ["id"]
                    }
                }
            }
        }
    
    def validate_response(
        self, 
        response: requests.Response, 
        operation: str = "text_generation",
        expected_content_type: str = "application/json"
    ) -> ValidationResult:
        """
        Validate an API response comprehensively.
        
        Args:
            response: The HTTP response to validate
            operation: The operation type for schema validation
            expected_content_type: Expected content type
            
        Returns:
            ValidationResult with detailed validation information
        """
        start_time = time.time()
        result = ValidationResult(
            status=ValidationStatus.VALID,
            is_valid=True,
            metadata={
                'operation': operation,
                'status_code': response.status_code,
                'content_type': response.headers.get('content-type', ''),
                'response_size': len(response.content) if response.content else 0
            }
        )
        
        try:
            # Step 1: Validate HTTP status
            self._validate_http_status(response, result)
            
            # Step 2: Validate content type
            self._validate_content_type(response, expected_content_type, result)
            
            # Step 3: Validate JSON structure
            json_data = self._validate_json_structure(response, result)
            
            # Step 4: Validate against schema
            if json_data and operation in self.expected_schemas:
                self._validate_json_schema(json_data, operation, result)
            
            # Step 5: Extract and validate content
            if json_data:
                self._extract_and_validate_content(json_data, operation, result)
            
            # Step 6: Perform semantic validation
            if result.extracted_data:
                self._perform_semantic_validation(result.extracted_data, operation, result)
            
        except Exception as e:
            logger.error(f"Validation failed with exception: {e}")
            result.add_error(ErrorDetails(
                error_code="VALIDATION_EXCEPTION",
                error_message=f"Validation process failed: {str(e)}",
                severity=ErrorSeverity.HIGH,
                is_recoverable=False,
                suggested_action=RecoveryAction.ABORT
            ))
        
        result.processing_time = time.time() - start_time
        return result
    
    def _validate_http_status(self, response: requests.Response, result: ValidationResult) -> None:
        """Validate HTTP status code."""
        if response.status_code == 200:
            return
        elif response.status_code in [400, 422]:
            # Client error - extract error details from response
            error_details = self._extract_client_error_details(response)
            result.add_error(ErrorDetails(
                error_code=f"HTTP_{response.status_code}",
                error_message=error_details.get('message', f"Client error: {response.status_code}"),
                error_context=error_details,
                severity=ErrorSeverity.HIGH,
                is_recoverable=False,
                suggested_action=RecoveryAction.MODIFY_REQUEST
            ))
        elif response.status_code in [429]:
            # Rate limiting
            retry_after = response.headers.get('retry-after', '60')
            result.add_error(ErrorDetails(
                error_code="RATE_LIMITED",
                error_message="API rate limit exceeded",
                error_context={'retry_after': retry_after},
                severity=ErrorSeverity.MEDIUM,
                is_recoverable=True,
                suggested_action=RecoveryAction.WAIT_AND_RETRY
            ))
        elif response.status_code >= 500:
            # Server error - recoverable
            result.add_error(ErrorDetails(
                error_code=f"HTTP_{response.status_code}",
                error_message=f"Server error: {response.status_code}",
                severity=ErrorSeverity.MEDIUM,
                is_recoverable=True,
                suggested_action=RecoveryAction.RETRY
            ))
        else:
            # Other status codes
            result.add_error(ErrorDetails(
                error_code=f"HTTP_{response.status_code}",
                error_message=f"Unexpected status code: {response.status_code}",
                severity=ErrorSeverity.MEDIUM,
                is_recoverable=True,
                suggested_action=RecoveryAction.RETRY
            ))
    
    def _validate_content_type(
        self, 
        response: requests.Response, 
        expected_content_type: str, 
        result: ValidationResult
    ) -> None:
        """Validate response content type."""
        content_type = response.headers.get('content-type', '').lower()
        
        if expected_content_type.lower() not in content_type:
            result.add_warning(
                f"Unexpected content type: {content_type}, expected: {expected_content_type}"
            )
    
    def _validate_json_structure(
        self, 
        response: requests.Response, 
        result: ValidationResult
    ) -> Optional[Dict[str, Any]]:
        """Validate JSON structure and parse response."""
        try:
            if not response.content:
                result.add_error(ErrorDetails(
                    error_code="EMPTY_RESPONSE",
                    error_message="Response body is empty",
                    severity=ErrorSeverity.HIGH,
                    is_recoverable=True,
                    suggested_action=RecoveryAction.RETRY
                ))
                return None
            
            json_data = response.json()
            return json_data
            
        except json.JSONDecodeError as e:
            result.add_error(ErrorDetails(
                error_code="INVALID_JSON",
                error_message=f"Invalid JSON response: {str(e)}",
                error_context={'response_text': response.text[:500]},
                severity=ErrorSeverity.HIGH,
                is_recoverable=True,
                suggested_action=RecoveryAction.RETRY
            ))
            return None
        except Exception as e:
            result.add_error(ErrorDetails(
                error_code="JSON_PARSE_ERROR",
                error_message=f"Failed to parse JSON: {str(e)}",
                severity=ErrorSeverity.HIGH,
                is_recoverable=True,
                suggested_action=RecoveryAction.RETRY
            ))
            return None
    
    def _validate_json_schema(
        self, 
        json_data: Dict[str, Any], 
        operation: str, 
        result: ValidationResult
    ) -> None:
        """Validate JSON data against expected schema."""
        try:
            schema = self.expected_schemas[operation]
            
            # Basic schema validation (simplified - could use jsonschema library)
            if not self._validate_schema_structure(json_data, schema):
                result.add_error(ErrorDetails(
                    error_code="SCHEMA_VALIDATION_FAILED",
                    error_message=f"Response does not match expected schema for {operation}",
                    error_context={'schema': schema, 'data_keys': list(json_data.keys())},
                    severity=ErrorSeverity.MEDIUM,
                    is_recoverable=True,
                    suggested_action=RecoveryAction.RETRY
                ))
        except Exception as e:
            result.add_warning(f"Schema validation failed: {str(e)}")
    
    def _validate_schema_structure(self, data: Any, schema: Dict[str, Any]) -> bool:
        """Simple schema structure validation."""
        if schema.get('type') == 'object':
            if not isinstance(data, dict):
                return False
            
            # Check required fields
            required = schema.get('required', [])
            for field in required:
                if field not in data:
                    return False
            
            # Check properties
            properties = schema.get('properties', {})
            for prop, prop_schema in properties.items():
                if prop in data:
                    if not self._validate_schema_structure(data[prop], prop_schema):
                        return False
        
        elif schema.get('type') == 'array':
            if not isinstance(data, list):
                return False
            
            min_items = schema.get('minItems', 0)
            if len(data) < min_items:
                return False
            
            items_schema = schema.get('items')
            if items_schema:
                for item in data:
                    if not self._validate_schema_structure(item, items_schema):
                        return False
        
        elif schema.get('type') == 'string':
            return isinstance(data, str)
        elif schema.get('type') == 'number':
            return isinstance(data, (int, float))
        
        return True
    
    def _extract_and_validate_content(
        self, 
        json_data: Dict[str, Any], 
        operation: str, 
        result: ValidationResult
    ) -> None:
        """Extract and validate content from JSON response."""
        try:
            extracted_data = {}
            
            if operation in ['text_generation', 'requirements_generation']:
                # Extract text content from choices
                choices = json_data.get('choices', [])
                if not choices:
                    result.add_error(ErrorDetails(
                        error_code="NO_CHOICES",
                        error_message="No choices found in response",
                        severity=ErrorSeverity.HIGH,
                        is_recoverable=True,
                        suggested_action=RecoveryAction.RETRY
                    ))
                    return
                
                # Extract content from first choice
                choice = choices[0]
                content = None
                
                # Try different content extraction methods
                if 'message' in choice and 'content' in choice['message']:
                    content = choice['message']['content']
                elif 'text' in choice:
                    content = choice['text']
                
                if not content:
                    result.add_error(ErrorDetails(
                        error_code="NO_CONTENT",
                        error_message="No content found in response choice",
                        error_context={'choice_keys': list(choice.keys())},
                        severity=ErrorSeverity.HIGH,
                        is_recoverable=True,
                        suggested_action=RecoveryAction.RETRY
                    ))
                    return
                
                if not content.strip():
                    result.add_error(ErrorDetails(
                        error_code="EMPTY_CONTENT",
                        error_message="Generated content is empty",
                        severity=ErrorSeverity.MEDIUM,
                        is_recoverable=True,
                        suggested_action=RecoveryAction.RETRY
                    ))
                    return
                
                extracted_data['content'] = content.strip()
                extracted_data['choice_count'] = len(choices)
                
            elif operation == 'model_info':
                # Extract model information
                data = json_data.get('data', [])
                if data:
                    model_info = data[0]
                    extracted_data['model_id'] = model_info.get('id', 'unknown')
                    extracted_data['context_length'] = model_info.get('context_length', 4096)
            
            result.extracted_data = extracted_data
            
        except Exception as e:
            result.add_error(ErrorDetails(
                error_code="CONTENT_EXTRACTION_FAILED",
                error_message=f"Failed to extract content: {str(e)}",
                severity=ErrorSeverity.MEDIUM,
                is_recoverable=True,
                suggested_action=RecoveryAction.RETRY
            ))
    
    def _perform_semantic_validation(
        self, 
        extracted_data: Dict[str, Any], 
        operation: str, 
        result: ValidationResult
    ) -> None:
        """Perform semantic validation on extracted content."""
        try:
            if operation in ['text_generation', 'requirements_generation']:
                content = extracted_data.get('content', '')
                
                # Check content length
                if len(content) < 10:
                    result.add_warning("Generated content is very short")
                    result.confidence *= 0.8
                
                # Check for common error patterns
                error_patterns = [
                    'error', 'failed', 'unable to', 'cannot', 'invalid',
                    'sorry', 'apologize', 'i cannot', 'i am unable'
                ]
                
                content_lower = content.lower()
                for pattern in error_patterns:
                    if pattern in content_lower:
                        result.add_warning(f"Content may contain error indication: '{pattern}'")
                        result.confidence *= 0.9
                        break
                
                # For requirements generation, check for JSON structure
                if operation == 'requirements_generation':
                    if not self._validate_requirements_content(content, result):
                        result.confidence *= 0.7
                        
        except Exception as e:
            result.add_warning(f"Semantic validation failed: {str(e)}")
    
    def _validate_requirements_content(self, content: str, result: ValidationResult) -> bool:
        """Validate requirements generation content."""
        try:
            # Try to parse as JSON
            json.loads(content)
            return True
        except json.JSONDecodeError:
            # Check if it looks like it should be JSON
            if content.strip().startswith('[') or content.strip().startswith('{'):
                result.add_warning("Content appears to be malformed JSON")
                return False
            else:
                # Might be plain text response
                result.add_warning("Content is not in JSON format")
                return True
    
    def _extract_client_error_details(self, response: requests.Response) -> Dict[str, Any]:
        """Extract error details from client error responses."""
        try:
            error_data = response.json()
            return {
                'message': error_data.get('error', {}).get('message', 'Client error'),
                'type': error_data.get('error', {}).get('type', 'unknown'),
                'code': error_data.get('error', {}).get('code', 'unknown'),
                'raw_response': response.text[:500]
            }
        except:
            return {
                'message': f"HTTP {response.status_code} error",
                'raw_response': response.text[:500]
            }
    
    def extract_error_details(self, response: requests.Response) -> ErrorDetails:
        """
        Extract detailed error information from API response.
        
        Args:
            response: The HTTP response containing error information
            
        Returns:
            ErrorDetails with comprehensive error information
        """
        try:
            if response.status_code == 200:
                # Check for application-level errors in successful HTTP response
                try:
                    json_data = response.json()
                    if 'error' in json_data:
                        error_info = json_data['error']
                        return ErrorDetails(
                            error_code=error_info.get('code', 'APPLICATION_ERROR'),
                            error_message=error_info.get('message', 'Application error occurred'),
                            error_context=error_info,
                            severity=ErrorSeverity.MEDIUM,
                            is_recoverable=True,
                            suggested_action=RecoveryAction.RETRY
                        )
                except:
                    pass
                
                return ErrorDetails(
                    error_code="SUCCESS",
                    error_message="No error detected",
                    severity=ErrorSeverity.LOW,
                    is_recoverable=True,
                    suggested_action=RecoveryAction.RETRY
                )
            
            # Extract error details based on status code
            client_error_details = self._extract_client_error_details(response)
            
            if response.status_code == 429:
                return ErrorDetails(
                    error_code="RATE_LIMITED",
                    error_message="API rate limit exceeded",
                    error_context=client_error_details,
                    severity=ErrorSeverity.MEDIUM,
                    is_recoverable=True,
                    suggested_action=RecoveryAction.WAIT_AND_RETRY
                )
            elif response.status_code in [400, 422]:
                return ErrorDetails(
                    error_code=f"CLIENT_ERROR_{response.status_code}",
                    error_message=client_error_details.get('message', f"Client error: {response.status_code}"),
                    error_context=client_error_details,
                    severity=ErrorSeverity.HIGH,
                    is_recoverable=False,
                    suggested_action=RecoveryAction.MODIFY_REQUEST
                )
            elif response.status_code >= 500:
                return ErrorDetails(
                    error_code=f"SERVER_ERROR_{response.status_code}",
                    error_message=f"Server error: {response.status_code}",
                    error_context=client_error_details,
                    severity=ErrorSeverity.MEDIUM,
                    is_recoverable=True,
                    suggested_action=RecoveryAction.RETRY
                )
            else:
                return ErrorDetails(
                    error_code=f"HTTP_ERROR_{response.status_code}",
                    error_message=f"HTTP error: {response.status_code}",
                    error_context=client_error_details,
                    severity=ErrorSeverity.MEDIUM,
                    is_recoverable=True,
                    suggested_action=RecoveryAction.RETRY
                )
                
        except Exception as e:
            return ErrorDetails(
                error_code="ERROR_EXTRACTION_FAILED",
                error_message=f"Failed to extract error details: {str(e)}",
                error_context={'original_status': response.status_code},
                severity=ErrorSeverity.HIGH,
                is_recoverable=True,
                suggested_action=RecoveryAction.RETRY
            )
    
    def should_retry(self, response: requests.Response, attempt: int = 1) -> bool:
        """
        Determine if a request should be retried based on response.
        
        Args:
            response: The HTTP response to evaluate
            attempt: Current attempt number
            
        Returns:
            True if request should be retried, False otherwise
        """
        if attempt >= self.max_retries:
            return False
        
        # Don't retry client errors (except rate limiting)
        if 400 <= response.status_code < 500 and response.status_code != 429:
            return False
        
        # Retry server errors and rate limiting
        if response.status_code >= 500 or response.status_code == 429:
            return True
        
        # For 200 responses, check if there are application-level errors
        if response.status_code == 200:
            try:
                json_data = response.json()
                if 'error' in json_data:
                    error_info = json_data['error']
                    error_type = error_info.get('type', '').lower()
                    # Retry on temporary errors
                    return error_type in ['temporary', 'timeout', 'overloaded']
            except:
                pass
        
        return False
    
    def calculate_retry_delay(self, attempt: int, base_delay: Optional[float] = None) -> float:
        """
        Calculate delay for exponential backoff retry.
        
        Args:
            attempt: Current attempt number (1-based)
            base_delay: Base delay in seconds
            
        Returns:
            Delay in seconds before next retry
        """
        if base_delay is None:
            base_delay = self.base_delay
        
        # Exponential backoff with jitter
        import random
        delay = min(base_delay * (2 ** (attempt - 1)), self.max_delay)
        jitter = random.uniform(0.1, 0.3) * delay
        return delay + jitter
    
    def parse_generation_result(self, response_json: Dict[str, Any]) -> Optional[str]:
        """
        Parse generation result from validated JSON response.
        
        Args:
            response_json: Validated JSON response data
            
        Returns:
            Generated text content or None if not found
        """
        try:
            choices = response_json.get('choices', [])
            if not choices:
                return None
            
            choice = choices[0]
            
            # Try different content extraction methods
            if 'message' in choice and 'content' in choice['message']:
                return choice['message']['content'].strip()
            elif 'text' in choice:
                return choice['text'].strip()
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to parse generation result: {e}")
            return None
    
    def add_schema(self, operation: str, schema: Dict[str, Any]) -> None:
        """
        Add or update a JSON schema for an operation.
        
        Args:
            operation: Operation name
            schema: JSON schema definition
        """
        self.expected_schemas[operation] = schema
    
    def get_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """
        Get JSON schema for an operation.
        
        Args:
            operation: Operation name
            
        Returns:
            JSON schema or None if not found
        """
        return self.expected_schemas.get(operation)