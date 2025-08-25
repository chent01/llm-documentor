"""
Unit tests for the LLMResponseParser utility.

Tests JSON parsing and response cleaning functionality.
"""

import pytest
import json

from medical_analyzer.services.llm_response_parser import LLMResponseParser


class TestLLMResponseParser:
    """Test cases for LLMResponseParser."""
    
    def test_parse_json_response_valid_array(self):
        """Test parsing valid JSON array response."""
        response = json.dumps([
            {"description": "Feature 1", "confidence": 0.8},
            {"description": "Feature 2", "confidence": 0.6}
        ])
        
        result = LLMResponseParser.parse_json_response(response)
        
        assert len(result) == 2
        assert result[0]["description"] == "Feature 1"
        assert result[1]["description"] == "Feature 2"
    
    def test_parse_json_response_valid_object(self):
        """Test parsing valid JSON object (single item)."""
        response = json.dumps({"description": "Single feature", "confidence": 0.7})
        
        result = LLMResponseParser.parse_json_response(response)
        
        assert len(result) == 1
        assert result[0]["description"] == "Single feature"
    
    def test_parse_json_response_markdown_wrapped(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        data = [{"description": "Test feature", "confidence": 0.5}]
        response = "```json\n" + json.dumps(data) + "\n```"
        
        result = LLMResponseParser.parse_json_response(response)
        
        assert len(result) == 1
        assert result[0]["description"] == "Test feature"
    
    def test_parse_json_response_code_block_without_json(self):
        """Test parsing JSON wrapped in generic code blocks."""
        data = [{"description": "Test feature", "confidence": 0.5}]
        response = "```\n" + json.dumps(data) + "\n```"
        
        result = LLMResponseParser.parse_json_response(response)
        
        assert len(result) == 1
        assert result[0]["description"] == "Test feature"
    
    def test_parse_json_response_with_extra_text(self):
        """Test parsing JSON with extra text around it."""
        data = [{"description": "Test feature", "confidence": 0.5}]
        response = f"Here is the analysis:\n{json.dumps(data)}\nThat's the result."
        
        result = LLMResponseParser.parse_json_response(response)
        
        assert len(result) == 1
        assert result[0]["description"] == "Test feature"
    
    def test_parse_json_response_multiple_objects(self):
        """Test parsing multiple JSON objects in text."""
        response = """
        Here are the results:
        {"description": "Feature 1", "confidence": 0.8}
        {"description": "Feature 2", "confidence": 0.6}
        End of results.
        """
        
        result = LLMResponseParser.parse_json_response(response)
        
        assert len(result) == 2
        assert result[0]["description"] == "Feature 1"
        assert result[1]["description"] == "Feature 2"
    
    def test_parse_json_response_invalid_json(self):
        """Test parsing completely invalid JSON."""
        response = "This is not JSON at all"
        
        result = LLMResponseParser.parse_json_response(response)
        
        assert result == []
    
    def test_parse_json_response_malformed_json(self):
        """Test parsing malformed JSON."""
        response = '{"description": "Test", "confidence": 0.5'  # Missing closing brace
        
        result = LLMResponseParser.parse_json_response(response)
        
        assert result == []
    
    def test_parse_json_response_empty_string(self):
        """Test parsing empty string."""
        response = ""
        
        result = LLMResponseParser.parse_json_response(response)
        
        assert result == []
    
    def test_parse_json_response_whitespace_only(self):
        """Test parsing whitespace-only string."""
        response = "   \n\t  "
        
        result = LLMResponseParser.parse_json_response(response)
        
        assert result == []
    
    def test_parse_json_response_non_dict_array_items(self):
        """Test parsing array with non-dictionary items."""
        response = json.dumps(["string1", "string2", 123])
        
        result = LLMResponseParser.parse_json_response(response)
        
        assert result == ["string1", "string2", 123]
    
    def test_validate_required_fields_all_present(self):
        """Test validation when all required fields are present."""
        data = {
            "description": "Test feature",
            "confidence": 0.8,
            "category": "validation"
        }
        required_fields = ["description", "confidence", "category"]
        
        result = LLMResponseParser.validate_required_fields(data, required_fields)
        
        assert result is True
    
    def test_validate_required_fields_missing_field(self):
        """Test validation when a required field is missing."""
        data = {
            "description": "Test feature",
            "confidence": 0.8
            # Missing "category"
        }
        required_fields = ["description", "confidence", "category"]
        
        result = LLMResponseParser.validate_required_fields(data, required_fields)
        
        assert result is False
    
    def test_validate_required_fields_empty_string(self):
        """Test validation when a required field is empty string."""
        data = {
            "description": "",  # Empty string
            "confidence": 0.8,
            "category": "validation"
        }
        required_fields = ["description", "confidence", "category"]
        
        result = LLMResponseParser.validate_required_fields(data, required_fields)
        
        assert result is False
    
    def test_validate_required_fields_whitespace_only(self):
        """Test validation when a required field is whitespace only."""
        data = {
            "description": "   \n\t  ",  # Whitespace only
            "confidence": 0.8,
            "category": "validation"
        }
        required_fields = ["description", "confidence", "category"]
        
        result = LLMResponseParser.validate_required_fields(data, required_fields)
        
        assert result is False
    
    def test_validate_required_fields_non_string_values(self):
        """Test validation with non-string values (should pass)."""
        data = {
            "description": "Test feature",
            "confidence": 0.8,  # Number
            "enabled": True,    # Boolean
            "count": 0         # Zero (should be valid)
        }
        required_fields = ["description", "confidence", "enabled", "count"]
        
        result = LLMResponseParser.validate_required_fields(data, required_fields)
        
        assert result is True
    
    def test_validate_required_fields_empty_list(self):
        """Test validation with empty required fields list."""
        data = {"description": "Test feature"}
        required_fields = []
        
        result = LLMResponseParser.validate_required_fields(data, required_fields)
        
        assert result is True
    
    def test_clamp_confidence_valid_range(self):
        """Test confidence clamping with values in valid range."""
        assert LLMResponseParser.clamp_confidence(0.5) == 0.5
        assert LLMResponseParser.clamp_confidence(0.0) == 0.0
        assert LLMResponseParser.clamp_confidence(1.0) == 1.0
    
    def test_clamp_confidence_above_range(self):
        """Test confidence clamping with values above valid range."""
        assert LLMResponseParser.clamp_confidence(1.5) == 1.0
        assert LLMResponseParser.clamp_confidence(100.0) == 1.0
    
    def test_clamp_confidence_below_range(self):
        """Test confidence clamping with values below valid range."""
        assert LLMResponseParser.clamp_confidence(-0.5) == 0.0
        assert LLMResponseParser.clamp_confidence(-100.0) == 0.0
    
    def test_clamp_confidence_string_number(self):
        """Test confidence clamping with string numbers."""
        assert LLMResponseParser.clamp_confidence("0.7") == 0.7
        assert LLMResponseParser.clamp_confidence("1.5") == 1.0
        assert LLMResponseParser.clamp_confidence("-0.3") == 0.0
    
    def test_clamp_confidence_invalid_string(self):
        """Test confidence clamping with invalid string."""
        assert LLMResponseParser.clamp_confidence("invalid") == 0.5
        assert LLMResponseParser.clamp_confidence("") == 0.5
    
    def test_clamp_confidence_none(self):
        """Test confidence clamping with None value."""
        assert LLMResponseParser.clamp_confidence(None) == 0.5
    
    def test_clamp_confidence_other_types(self):
        """Test confidence clamping with other data types."""
        assert LLMResponseParser.clamp_confidence([]) == 0.5
        assert LLMResponseParser.clamp_confidence({}) == 0.5
        assert LLMResponseParser.clamp_confidence(object()) == 0.5