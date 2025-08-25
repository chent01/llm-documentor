"""
LLM response parsing utilities.

This module provides utilities for parsing and cleaning LLM responses,
particularly JSON responses that may contain markdown formatting or
other artifacts.
"""

import re
import json
from typing import List, Dict, Any


class LLMResponseParser:
    """Parser for LLM responses with robust JSON extraction."""
    
    @staticmethod
    def parse_json_response(response: str) -> List[Dict[str, Any]]:
        """
        Parse LLM response to extract JSON data.
        
        Args:
            response: Raw LLM response
            
        Returns:
            List of data dictionaries
        """
        # Clean up response - remove markdown code blocks if present
        response = response.strip()
        if response.startswith('```json'):
            response = response[7:]
        if response.startswith('```'):
            response = response[3:]
        if response.endswith('```'):
            response = response[:-3]
        
        response = response.strip()
        
        try:
            # Try to parse as JSON
            data = json.loads(response)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
            else:
                return []
        except json.JSONDecodeError:
            # Try to extract JSON from text
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            # Fallback: try to parse individual objects
            object_matches = re.findall(r'\{[^}]*\}', response, re.DOTALL)
            objects = []
            for match in object_matches:
                try:
                    obj = json.loads(match)
                    objects.append(obj)
                except json.JSONDecodeError:
                    continue
            
            return objects
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> bool:
        """
        Validate that required fields are present in data.
        
        Args:
            data: Dictionary to validate
            required_fields: List of required field names
            
        Returns:
            True if all required fields are present and non-empty
        """
        for field in required_fields:
            if field not in data:
                return False
            
            value = data[field]
            if isinstance(value, str) and not value.strip():
                return False
        
        return True
    
    @staticmethod
    def clamp_confidence(confidence: Any) -> float:
        """
        Clamp confidence value to [0, 1] range.
        
        Args:
            confidence: Confidence value to clamp
            
        Returns:
            Confidence value clamped to [0, 1]
        """
        try:
            conf = float(confidence)
            return max(0.0, min(1.0, conf))
        except (ValueError, TypeError):
            return 0.5  # Default confidence