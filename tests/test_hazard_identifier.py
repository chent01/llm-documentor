"""
Unit tests for the HazardIdentifier service.

Tests hazard identification functionality from Software Requirements.
"""

import pytest
import json
from unittest.mock import Mock
from datetime import datetime

from medical_analyzer.services.hazard_identifier import HazardIdentifier
from medical_analyzer.models.result_models import HazardIdentificationResult
from medical_analyzer.models.core import Requirement, RiskItem
from medical_analyzer.models.enums import RequirementType, Severity, Probability, RiskLevel
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


class TestHazardIdentifier:
    """Test cases for HazardIdentifier."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm = MockLLMBackend()
        self.identifier = HazardIdentifier(self.mock_llm)
    
    def create_sample_requirement(self, req_id, text, req_type=RequirementType.SOFTWARE):
        """Create a sample requirement for testing."""
        return Requirement(
            id=req_id,
            text=text,
            type=req_type,
            acceptance_criteria=["Acceptance criteria 1", "Acceptance criteria 2"],
            metadata={'source': 'test'}
        )
    
    def test_init(self):
        """Test hazard identifier initialization."""
        assert self.identifier.llm_backend == self.mock_llm
        assert self.identifier.risk_counter == 0
    
    def test_identify_hazards_empty_requirements(self):
        """Test hazard identification with empty requirements list."""
        result = self.identifier.identify_hazards([])
        
        assert isinstance(result, HazardIdentificationResult)
        assert result.risk_items == []
        assert result.confidence_score == 0.0
        assert result.requirements_processed == 0
        assert result.errors == []
        assert result.metadata['total_requirements'] == 0
    
    def test_identify_hazards_single_requirement(self):
        """Test hazard identification with a single requirement."""
        # Set up mock response
        mock_response = json.dumps([
            {
                "hazard": "Incorrect data processing",
                "cause": "Invalid input validation",
                "effect": "Patient receives incorrect treatment",
                "severity": "Serious",
                "probability": "Medium",
                "confidence": 0.8,
                "related_requirement_id": "SR_001"
            }
        ])
        self.mock_llm.responses = {"SR_001": mock_response}
        
        requirements = [self.create_sample_requirement("SR_001", "The system shall validate all input data")]
        result = self.identifier.identify_hazards(requirements, "Medical device project")
        
        assert len(result.risk_items) == 1
        risk = result.risk_items[0]
        assert risk.hazard == "Incorrect data processing"
        assert risk.cause == "Invalid input validation"
        assert risk.effect == "Patient receives incorrect treatment"
        assert risk.severity == Severity.SERIOUS
        assert risk.probability == Probability.MEDIUM
        assert risk.risk_level == RiskLevel.UNDESIRABLE
        assert "SR_001" in risk.related_requirements
        assert result.requirements_processed == 1
        assert len(result.errors) == 0
    
    def test_identify_hazards_multiple_requirements(self):
        """Test hazard identification with multiple requirements."""
        # Set up mock responses
        validation_response = json.dumps([{
            "hazard": "Data validation failure",
            "cause": "Insufficient input checking",
            "effect": "System processes invalid data",
            "severity": "Minor",
            "probability": "Low",
            "confidence": 0.7,
            "related_requirement_id": "SR_001"
        }])
        
        ui_response = json.dumps([{
            "hazard": "User interface confusion",
            "cause": "Unclear display information",
            "effect": "User makes incorrect decisions",
            "severity": "Serious",
            "probability": "Medium",
            "confidence": 0.6,
            "related_requirement_id": "SR_002"
        }])
        
        # Both requirements will be processed in the same batch, so use a combined response
        combined_response = json.dumps([
            {
                "hazard": "Data validation failure",
                "cause": "Insufficient input checking",
                "effect": "System processes invalid data",
                "severity": "Minor",
                "probability": "Low",
                "confidence": 0.7,
                "related_requirement_id": "SR_001"
            },
            {
                "hazard": "User interface confusion",
                "cause": "Unclear display information",
                "effect": "User makes incorrect decisions",
                "severity": "Serious",
                "probability": "Medium",
                "confidence": 0.6,
                "related_requirement_id": "SR_002"
            }
        ])
        
        self.mock_llm.responses = {
            "SR_001": combined_response,
            "SR_002": combined_response
        }
        
        requirements = [
            self.create_sample_requirement("SR_001", "The system shall validate user input"),
            self.create_sample_requirement("SR_002", "The system shall display patient information clearly")
        ]
        
        result = self.identifier.identify_hazards(requirements)
        
        assert len(result.risk_items) == 2
        assert result.requirements_processed == 2
        assert result.confidence_score > 0.0
        assert len(result.errors) == 0
    
    def test_create_risk_item_from_data_valid(self):
        """Test creating risk item from valid data."""
        hazard_data = {
            "hazard": "System malfunction",
            "cause": "Software bug",
            "effect": "Device stops working",
            "severity": "Catastrophic",
            "probability": "Low",
            "confidence": 0.9,
            "related_requirement_id": "SR_001"
        }
        
        requirements = [self.create_sample_requirement("SR_001", "Test requirement")]
        risk_item = self.identifier._create_risk_item_from_data(hazard_data, requirements)
        
        assert risk_item is not None
        assert risk_item.hazard == "System malfunction"
        assert risk_item.cause == "Software bug"
        assert risk_item.effect == "Device stops working"
        assert risk_item.severity == Severity.CATASTROPHIC
        assert risk_item.probability == Probability.LOW
        assert risk_item.risk_level == RiskLevel.UNDESIRABLE
        assert risk_item.metadata['confidence'] == 0.9
    
    def test_create_risk_item_from_data_missing_fields(self):
        """Test creating risk item with missing required fields."""
        hazard_data = {
            "hazard": "Test hazard",
            "cause": "Test cause"
            # Missing effect, severity, probability
        }
        
        requirements = [self.create_sample_requirement("SR_001", "Test requirement")]
        risk_item = self.identifier._create_risk_item_from_data(hazard_data, requirements)
        
        assert risk_item is None
    
    def test_parse_severity_valid(self):
        """Test parsing valid severity values."""
        assert self.identifier._parse_severity("Catastrophic") == Severity.CATASTROPHIC
        assert self.identifier._parse_severity("SERIOUS") == Severity.SERIOUS
        assert self.identifier._parse_severity("minor") == Severity.MINOR
        assert self.identifier._parse_severity("Negligible") == Severity.NEGLIGIBLE
    
    def test_parse_severity_invalid(self):
        """Test parsing invalid severity defaults to MINOR."""
        assert self.identifier._parse_severity("invalid") == Severity.MINOR
    
    def test_parse_probability_valid(self):
        """Test parsing valid probability values."""
        assert self.identifier._parse_probability("High") == Probability.HIGH
        assert self.identifier._parse_probability("MEDIUM") == Probability.MEDIUM
        assert self.identifier._parse_probability("low") == Probability.LOW
        assert self.identifier._parse_probability("Remote") == Probability.REMOTE
    
    def test_parse_probability_invalid(self):
        """Test parsing invalid probability defaults to LOW."""
        assert self.identifier._parse_probability("invalid") == Probability.LOW
    
    def test_calculate_risk_level_matrix(self):
        """Test risk level calculation using ISO 14971 risk matrix."""
        # Catastrophic risks
        assert self.identifier._calculate_risk_level(Severity.CATASTROPHIC, Probability.HIGH) == RiskLevel.UNACCEPTABLE
        assert self.identifier._calculate_risk_level(Severity.CATASTROPHIC, Probability.MEDIUM) == RiskLevel.UNACCEPTABLE
        assert self.identifier._calculate_risk_level(Severity.CATASTROPHIC, Probability.LOW) == RiskLevel.UNDESIRABLE
        assert self.identifier._calculate_risk_level(Severity.CATASTROPHIC, Probability.REMOTE) == RiskLevel.UNDESIRABLE
        
        # Serious risks
        assert self.identifier._calculate_risk_level(Severity.SERIOUS, Probability.HIGH) == RiskLevel.UNACCEPTABLE
        assert self.identifier._calculate_risk_level(Severity.SERIOUS, Probability.MEDIUM) == RiskLevel.UNDESIRABLE
        assert self.identifier._calculate_risk_level(Severity.SERIOUS, Probability.LOW) == RiskLevel.ACCEPTABLE
        assert self.identifier._calculate_risk_level(Severity.SERIOUS, Probability.REMOTE) == RiskLevel.ACCEPTABLE
        
        # Minor risks
        assert self.identifier._calculate_risk_level(Severity.MINOR, Probability.HIGH) == RiskLevel.UNDESIRABLE
        assert self.identifier._calculate_risk_level(Severity.MINOR, Probability.MEDIUM) == RiskLevel.UNDESIRABLE
        assert self.identifier._calculate_risk_level(Severity.MINOR, Probability.LOW) == RiskLevel.ACCEPTABLE
        assert self.identifier._calculate_risk_level(Severity.MINOR, Probability.REMOTE) == RiskLevel.ACCEPTABLE
        
        # Negligible risks
        assert self.identifier._calculate_risk_level(Severity.NEGLIGIBLE, Probability.HIGH) == RiskLevel.NEGLIGIBLE
        assert self.identifier._calculate_risk_level(Severity.NEGLIGIBLE, Probability.LOW) == RiskLevel.NEGLIGIBLE
    
    def test_calculate_risk_score(self):
        """Test numerical risk score calculation."""
        # Highest risk
        score = self.identifier._calculate_risk_score(Severity.CATASTROPHIC, Probability.HIGH)
        assert score == 16  # 4 * 4
        
        # Medium risk
        score = self.identifier._calculate_risk_score(Severity.SERIOUS, Probability.MEDIUM)
        assert score == 9  # 3 * 3
        
        # Lowest risk
        score = self.identifier._calculate_risk_score(Severity.NEGLIGIBLE, Probability.REMOTE)
        assert score == 1  # 1 * 1
    
    def test_generate_mitigation_strategy(self):
        """Test mitigation strategy generation."""
        # Software-related hazard
        mitigation = self.identifier._generate_mitigation_strategy(
            "Software algorithm error", "Incorrect calculation", "Wrong diagnosis", Severity.CATASTROPHIC
        )
        assert "redundant validation" in mitigation.lower()
        assert "testing" in mitigation.lower()
        
        # Data-related hazard
        mitigation = self.identifier._generate_mitigation_strategy(
            "Data corruption", "Storage failure", "Lost patient data", Severity.SERIOUS
        )
        assert "data integrity" in mitigation.lower()
        assert "backup" in mitigation.lower()
        
        # User interface hazard
        mitigation = self.identifier._generate_mitigation_strategy(
            "User interface confusion", "Unclear display", "Wrong action", Severity.MINOR
        )
        assert "user interface" in mitigation.lower()
        assert "confirmation" in mitigation.lower()
    
    def test_generate_verification_method(self):
        """Test verification method generation."""
        # High severity verification
        verification = self.identifier._generate_verification_method(
            "Critical system failure", "Test mitigation", Severity.CATASTROPHIC
        )
        assert "comprehensive testing" in verification.lower()
        
        # Lower severity verification
        verification = self.identifier._generate_verification_method(
            "Minor display issue", "Test mitigation", Severity.MINOR
        )
        assert "testing" in verification.lower()
    
    def test_fallback_hazard_identification(self):
        """Test fallback hazard identification using heuristics."""
        requirements = [
            self.create_sample_requirement("SR_001", "The system shall validate input data"),
            self.create_sample_requirement("SR_002", "The system shall display user interface"),
            self.create_sample_requirement("SR_003", "The system shall store patient information")
        ]
        
        risk_items = self.identifier._fallback_hazard_identification(requirements)
        
        # Should identify at least 2 risks (some requirements may match multiple patterns)
        assert len(risk_items) >= 2
        
        # Check that different hazard types are identified
        hazards = [r.hazard for r in risk_items]
        assert any("data processing" in h.lower() or "data" in h.lower() for h in hazards)
        assert any("user interface" in h.lower() or "interface" in h.lower() for h in hazards)
    
    def test_get_statistics_empty(self):
        """Test risk statistics with empty risk list."""
        stats = self.identifier.get_statistics([])
        
        assert stats['total_risks'] == 0
        assert stats['average_confidence'] == 0.0
        assert stats['severity_distribution'] == {}
        assert stats['high_risk_count'] == 0
    
    def test_get_statistics_with_risks(self):
        """Test risk statistics with actual risks."""
        risk_items = [
            RiskItem(
                id="RISK_001",
                hazard="High risk hazard",
                cause="Test cause",
                effect="Test effect",
                severity=Severity.CATASTROPHIC,
                probability=Probability.HIGH,
                risk_level=RiskLevel.UNACCEPTABLE,
                mitigation="Test mitigation",
                verification="Test verification",
                related_requirements=["SR_001"],
                metadata={'confidence': 0.9, 'risk_score': 16}
            ),
            RiskItem(
                id="RISK_002",
                hazard="Medium risk hazard",
                cause="Test cause",
                effect="Test effect",
                severity=Severity.SERIOUS,
                probability=Probability.MEDIUM,
                risk_level=RiskLevel.UNDESIRABLE,
                mitigation="Test mitigation",
                verification="Test verification",
                related_requirements=["SR_002"],
                metadata={'confidence': 0.7, 'risk_score': 9}
            ),
            RiskItem(
                id="RISK_003",
                hazard="Low risk hazard",
                cause="Test cause",
                effect="Test effect",
                severity=Severity.MINOR,
                probability=Probability.LOW,
                risk_level=RiskLevel.ACCEPTABLE,
                mitigation="Test mitigation",
                verification="Test verification",
                related_requirements=["SR_003"],
                metadata={'confidence': 0.5, 'risk_score': 4}
            )
        ]
        
        stats = self.identifier.get_statistics(risk_items)
        
        assert stats['total_risks'] == 3
        assert abs(stats['average_confidence'] - 0.7) < 0.01  # (0.9 + 0.7 + 0.5) / 3
        assert stats['severity_distribution']['Catastrophic'] == 1
        assert stats['severity_distribution']['Serious'] == 1
        assert stats['severity_distribution']['Minor'] == 1
        assert stats['high_risk_count'] == 1  # Unacceptable
        assert stats['medium_risk_count'] == 1  # Undesirable
        assert stats['low_risk_count'] == 1  # Acceptable
        assert abs(stats['average_risk_score'] - 9.67) < 0.1  # (16 + 9 + 4) / 3
    
    def test_filter_by_level(self):
        """Test filtering risks by minimum risk level."""
        risk_items = [
            RiskItem(
                id="1", hazard="High", cause="", effect="", severity=Severity.CATASTROPHIC,
                probability=Probability.HIGH, risk_level=RiskLevel.UNACCEPTABLE,
                mitigation="", verification="", related_requirements=[]
            ),
            RiskItem(
                id="2", hazard="Medium", cause="", effect="", severity=Severity.SERIOUS,
                probability=Probability.MEDIUM, risk_level=RiskLevel.UNDESIRABLE,
                mitigation="", verification="", related_requirements=[]
            ),
            RiskItem(
                id="3", hazard="Low", cause="", effect="", severity=Severity.MINOR,
                probability=Probability.LOW, risk_level=RiskLevel.ACCEPTABLE,
                mitigation="", verification="", related_requirements=[]
            )
        ]
        
        filtered = self.identifier.filter_by_level(risk_items, RiskLevel.UNDESIRABLE)
        assert len(filtered) == 2  # Unacceptable and Undesirable
        assert all(r.risk_level in [RiskLevel.UNACCEPTABLE, RiskLevel.UNDESIRABLE] for r in filtered)
    
    def test_group_by_severity(self):
        """Test grouping risks by severity level."""
        risk_items = [
            RiskItem(
                id="1", hazard="Catastrophic risk", cause="", effect="", severity=Severity.CATASTROPHIC,
                probability=Probability.HIGH, risk_level=RiskLevel.UNACCEPTABLE,
                mitigation="", verification="", related_requirements=[]
            ),
            RiskItem(
                id="2", hazard="Another catastrophic risk", cause="", effect="", severity=Severity.CATASTROPHIC,
                probability=Probability.MEDIUM, risk_level=RiskLevel.UNACCEPTABLE,
                mitigation="", verification="", related_requirements=[]
            ),
            RiskItem(
                id="3", hazard="Serious risk", cause="", effect="", severity=Severity.SERIOUS,
                probability=Probability.LOW, risk_level=RiskLevel.ACCEPTABLE,
                mitigation="", verification="", related_requirements=[]
            )
        ]
        
        grouped = self.identifier.group_by_severity(risk_items)
        
        assert len(grouped) == 2
        assert len(grouped[Severity.CATASTROPHIC]) == 2
        assert len(grouped[Severity.SERIOUS]) == 1
    
    def test_llm_error_handling_recoverable(self):
        """Test handling of recoverable LLM errors."""
        # Create a mock that raises recoverable LLM error
        error_llm = Mock(spec=LLMBackend)
        error_llm.generate.side_effect = LLMError("Temporary error", recoverable=True)
        
        identifier = HazardIdentifier(error_llm)
        requirements = [self.create_sample_requirement("SR_001", "Test requirement")]
        
        # Should fall back to heuristic identification
        risk_items = identifier._identify_hazards_for_batch(requirements, "Test project")
        assert isinstance(risk_items, list)
    
    def test_llm_error_handling_non_recoverable(self):
        """Test handling of non-recoverable LLM errors."""
        error_llm = Mock(spec=LLMBackend)
        error_llm.generate.side_effect = LLMError("Fatal error", recoverable=False)
        
        identifier = HazardIdentifier(error_llm)
        requirements = [self.create_sample_requirement("SR_001", "Test requirement")]
        
        with pytest.raises(LLMError):
            identifier._identify_hazards_for_batch(requirements, "Test project")