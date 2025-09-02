"""
Unified JSON response handling for LLM operations.

This module provides consistent JSON response parsing and validation
across all LLM operations to eliminate maintenance issues.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ResponseFormat(Enum):
    """Supported response formats."""
    JSON_OBJECT = "json_object"
    JSON_ARRAY = "json_array"
    PLAIN_TEXT = "plain_text"
    STRUCTURED_TEXT = "structured_text"


@dataclass
class ParseResult(Generic[T]):
    """Result of parsing an LLM response."""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    raw_response: Optional[str] = None
    format_detected: Optional[ResponseFormat] = None
    
    @property
    def is_valid(self) -> bool:
        """Check if parsing was successful."""
        return self.success and self.data is not None


class UnifiedResponseHandler:
    """Unified handler for all LLM response parsing."""
    
    def __init__(self):
        """Initialize the response handler."""
        self._parsers = {
            ResponseFormat.JSON_OBJECT: self._parse_json_object,
            ResponseFormat.JSON_ARRAY: self._parse_json_array,
            ResponseFormat.PLAIN_TEXT: self._parse_plain_text,
            ResponseFormat.STRUCTURED_TEXT: self._parse_structured_text
        }
    
    def parse_response(
        self, 
        response: str, 
        expected_format: ResponseFormat = ResponseFormat.JSON_OBJECT,
        schema_validator: Optional[callable] = None
    ) -> ParseResult[Any]:
        """
        Parse LLM response with unified error handling.
        
        Args:
            response: Raw LLM response text
            expected_format: Expected response format
            schema_validator: Optional function to validate parsed data
            
        Returns:
            ParseResult with parsed data or error information
        """
        if not response or not response.strip():
            return ParseResult(
                success=False,
                error="Empty response",
                raw_response=response
            )
        
        # Clean the response
        cleaned_response = self._clean_response(response)
        
        # Try to detect format if not specified
        if expected_format == ResponseFormat.JSON_OBJECT:
            detected_format = self._detect_format(cleaned_response)
        else:
            detected_format = expected_format
        
        # Parse using appropriate parser
        try:
            parser = self._parsers.get(detected_format, self._parse_json_object)
            result = parser(cleaned_response)
            
            if result.success and schema_validator:
                # Validate against schema if provided
                try:
                    if not schema_validator(result.data):
                        return ParseResult(
                            success=False,
                            error="Schema validation failed",
                            raw_response=response,
                            format_detected=detected_format
                        )
                except Exception as e:
                    return ParseResult(
                        success=False,
                        error=f"Schema validation error: {str(e)}",
                        raw_response=response,
                        format_detected=detected_format
                    )
            
            result.raw_response = response
            result.format_detected = detected_format
            return result
            
        except Exception as e:
            logger.error(f"Response parsing failed: {str(e)}")
            return ParseResult(
                success=False,
                error=f"Parsing error: {str(e)}",
                raw_response=response,
                format_detected=detected_format
            )
    
    def _clean_response(self, response: str) -> str:
        """
        Clean response text for parsing.
        
        Args:
            response: Raw response text
            
        Returns:
            Cleaned response text
        """
        # Remove common LLM artifacts
        cleaned = response.strip()
        
        # Remove markdown code blocks
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        elif cleaned.startswith('```'):
            cleaned = cleaned[3:]
        
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        
        # Remove leading/trailing whitespace again
        cleaned = cleaned.strip()
        
        # Handle common prefixes
        prefixes_to_remove = [
            "Here's the JSON response:",
            "Here is the JSON:",
            "JSON response:",
            "Response:",
            "Result:",
        ]
        
        for prefix in prefixes_to_remove:
            if cleaned.lower().startswith(prefix.lower()):
                cleaned = cleaned[len(prefix):].strip()
        
        return cleaned
    
    def _detect_format(self, response: str) -> ResponseFormat:
        """
        Detect the format of the response.
        
        Args:
            response: Cleaned response text
            
        Returns:
            Detected ResponseFormat
        """
        response = response.strip()
        
        if response.startswith('{') and response.endswith('}'):
            return ResponseFormat.JSON_OBJECT
        elif response.startswith('[') and response.endswith(']'):
            return ResponseFormat.JSON_ARRAY
        elif any(marker in response for marker in ['```', '---', '##', '**']):
            return ResponseFormat.STRUCTURED_TEXT
        else:
            return ResponseFormat.PLAIN_TEXT
    
    def _parse_json_object(self, response: str) -> ParseResult[Dict[str, Any]]:
        """Parse JSON object response."""
        try:
            data = json.loads(response)
            if isinstance(data, dict):
                return ParseResult(success=True, data=data)
            else:
                return ParseResult(
                    success=False,
                    error=f"Expected JSON object, got {type(data).__name__}"
                )
        except json.JSONDecodeError as e:
            return ParseResult(
                success=False,
                error=f"JSON decode error: {str(e)}"
            )
    
    def _parse_json_array(self, response: str) -> ParseResult[List[Any]]:
        """Parse JSON array response."""
        try:
            data = json.loads(response)
            if isinstance(data, list):
                return ParseResult(success=True, data=data)
            else:
                return ParseResult(
                    success=False,
                    error=f"Expected JSON array, got {type(data).__name__}"
                )
        except json.JSONDecodeError as e:
            return ParseResult(
                success=False,
                error=f"JSON decode error: {str(e)}"
            )
    
    def _parse_plain_text(self, response: str) -> ParseResult[str]:
        """Parse plain text response."""
        return ParseResult(success=True, data=response)
    
    def _parse_structured_text(self, response: str) -> ParseResult[Dict[str, str]]:
        """Parse structured text response (markdown-like)."""
        # Simple structured text parser
        sections = {}
        current_section = "content"
        current_content = []
        
        for line in response.split('\n'):
            line = line.strip()
            if line.startswith('##'):
                # Save previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                # Start new section
                current_section = line[2:].strip().lower().replace(' ', '_')
                current_content = []
            elif line.startswith('**') and line.endswith('**'):
                # Bold text as section header
                if current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = line[2:-2].strip().lower().replace(' ', '_')
                current_content = []
            else:
                current_content.append(line)
        
        # Save final section
        if current_content:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return ParseResult(success=True, data=sections)
    
    def parse_json_list(self, response: str) -> ParseResult[List[Dict[str, Any]]]:
        """
        Parse response expecting a list of JSON objects.
        
        Args:
            response: Raw LLM response
            
        Returns:
            ParseResult with list of dictionaries
        """
        result = self.parse_response(response, ResponseFormat.JSON_ARRAY)
        
        if not result.success:
            return result
        
        # Ensure all items are dictionaries
        if not isinstance(result.data, list):
            return ParseResult(
                success=False,
                error="Expected list of objects",
                raw_response=response
            )
        
        for i, item in enumerate(result.data):
            if not isinstance(item, dict):
                return ParseResult(
                    success=False,
                    error=f"Item {i} is not a JSON object",
                    raw_response=response
                )
        
        return result
    
    def parse_requirements_response(self, response: str) -> ParseResult[List[Dict[str, Any]]]:
        """
        Parse requirements generation response.
        
        Args:
            response: Raw LLM response
            
        Returns:
            ParseResult with requirements list
        """
        def validate_requirement(req: Dict[str, Any]) -> bool:
            """Validate requirement structure."""
            required_fields = ['id', 'description', 'priority']
            return all(field in req for field in required_fields)
        
        result = self.parse_json_list(response)
        
        if result.success:
            # Validate each requirement
            for req in result.data:
                if not validate_requirement(req):
                    return ParseResult(
                        success=False,
                        error="Invalid requirement structure",
                        raw_response=response
                    )
        
        return result
    
    def parse_soup_classification_response(self, response: str) -> ParseResult[Dict[str, Any]]:
        """
        Parse SOUP classification response.
        
        Args:
            response: Raw LLM response
            
        Returns:
            ParseResult with classification data
        """
        def validate_classification(data: Dict[str, Any]) -> bool:
            """Validate classification structure."""
            required_fields = ['is_soup', 'confidence', 'reasoning']
            return all(field in data for field in required_fields)
        
        result = self.parse_response(response, ResponseFormat.JSON_OBJECT, validate_classification)
        return result


# Global instance for easy access
_global_handler = None

def get_response_handler() -> UnifiedResponseHandler:
    """
    Get global response handler instance.
    
    Returns:
        UnifiedResponseHandler instance
    """
    global _global_handler
    if _global_handler is None:
        _global_handler = UnifiedResponseHandler()
    return _global_handler


def parse_llm_response(
    response: str, 
    expected_format: ResponseFormat = ResponseFormat.JSON_OBJECT,
    schema_validator: Optional[callable] = None
) -> ParseResult[Any]:
    """
    Convenience function to parse LLM response.
    
    Args:
        response: Raw LLM response
        expected_format: Expected response format
        schema_validator: Optional schema validator
        
    Returns:
        ParseResult with parsed data
    """
    return get_response_handler().parse_response(response, expected_format, schema_validator)