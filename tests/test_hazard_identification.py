"""
Unit tests for hazard identification functionality.

Tests cover:
- Hazard identification from Software Requirements
- Risk level calculation using ISO 14971 principles
- Severity and probability assignment heuristics
- Mitigation strategy generation
- Verification method generation
- Risk statistics and filtering
"""

import pytest
from unittest.mock import Mock
from datetime import datetime

from medical_analyzer.services.hazard_identifier import HazardIdentifier
from medical_analyzer.models.result_models import HazardIdentificationResult
from medical_analyzer.models.core import Requirement, RiskItem, CodeReference
from medical_analyzer.models.enums import RequirementType, Severity, Probability, RiskLevel
from medical_analyzer.llm.backend import LLMError


class TestHazardIdentification:
    """Test hazard identification functionality."""
    
    @pytest.fixture
    def mock_llm_backend(self):
        """Create a mock LLM backend."""
        backend = Mock()
        backend.__class__.__name__ = "MockLLMBackend"
        return backend
    

    
    @pytest.fixture
    def hazard_identifier(self, mock_llm_backend):
        """Create a HazardIdentifier instance."""
        return HazardIdentifier(mock_llm_backend)
    
    @pytest.fixture
    def sample_software_requirements(self):
        """Create sample Software Requirements for testing."""
        return [
            Requirement(
                id="SR_0001",
                type=RequirementType.SOFTWARE,
                text="The software shall validate patient data input before processing",
                acceptance_criteria=[
                    "Input validation shall check data format and ranges",
                    "Invalid data shall be rejected with appropriate error messages"
                ],
                derived_from=["UR_0001"],
                code_references=[
                    CodeReference(
                        file_path="src/validation.c",
                        start_line=10,
                        end_line=25,
                        function_name="validate_patient_data"
                    )
                ],
                metadata={'confidence': 0.8}
            ),
            Requirement(
                id="SR_0002",
                type=RequirementType.SOFTWARE,
                text="The software shall display treatment recommendations to healthcare providers",
                acceptance_criteria=[
                    "Recommendations shall be clearly formatted and readable",
                    "Display shall include confidence levels and supporting data"
                ],
                derived_from=["UR_0002"],
                code_references=[
                    CodeReference(
                        file_path="src/ui/display.js",
                        start_line=50,
                        end_line=75,
                        function_name="displayRecommendations"
                    )
                ],
                metadata={'confidence': 0.9}
            )
        ]
    
    def test_identify_hazards_success(self, hazard_identifier, mock_llm_backend, sample_software_requirements):
        """Test successful hazard identification from Software Requirements."""
        # Mock LLM response
        mock_response = '''[
            {
                "hazard": "Incorrect data validation",
                "cause": "Invalid input data bypassing validation checks",
                "effect": "Incorrect patient data leading to misdiagnosis",
                "severity": "Serious",
                "probability": "Medium",
                "confidence": 0.8,
                "related_requirement_id": "SR_0001"
            }
        ]'''
        
        mock_llm_backend.generate.return_value = mock_response
        
        # Test hazard identification
        result = hazard_identifier.identify_hazards(
            sample_software_requirements,
            "Medical device for patient diagnosis and treatment recommendations"
        )
        
        # Verify result structure
        assert isinstance(result, HazardIdentificationResult)
        assert len(result.risk_items) == 1
        assert result.confidence_score > 0.0
        assert result.processing_time >= 0.0
        assert result.requirements_processed == 2
        assert len(result.errors) == 0
        
        # Verify risk item
        risk = result.risk_items[0]
        assert risk.hazard == "Incorrect data validation"
        assert risk.cause == "Invalid input data bypassing validation checks"
        assert risk.effect == "Incorrect patient data leading to misdiagnosis"
        assert risk.severity == Severity.SERIOUS
        assert risk.probability == Probability.MEDIUM
        assert risk.risk_level == RiskLevel.UNDESIRABLE
        assert "SR_0001" in risk.related_requirements
        assert risk.metadata['confidence'] == 0.8
        assert risk.metadata['identification_method'] == 'llm'
        
        # Verify mitigation and verification are generated
        assert len(risk.mitigation) > 0
        assert len(risk.verification) > 0
    
    def test_identify_hazards_empty_requirements(self, hazard_identifier):
        """Test hazard identification with empty requirements list."""
        result = hazard_identifier.identify_hazards([])
        
        assert isinstance(result, HazardIdentificationResult)
        assert len(result.risk_items) == 0
        assert result.confidence_score == 0.0
        assert result.processing_time >= 0.0
        assert result.requirements_processed == 0
        assert len(result.errors) == 0
        assert result.metadata['total_requirements'] == 0
        assert result.metadata['identification_method'] == 'none'
    
    def test_identify_hazards_llm_error_fallback(self, hazard_identifier, mock_llm_backend, sample_software_requirements):
        """Test fallback hazard identification when LLM fails."""
        # Mock LLM to raise recoverable error
        mock_llm_backend.generate.side_effect = LLMError("Connection timeout", recoverable=True)
        
        result = hazard_identifier.identify_hazards(sample_software_requirements)
        
        # Should use fallback heuristic method
        assert isinstance(result, HazardIdentificationResult)
        assert len(result.risk_items) > 0  # Should identify some risks using heuristics
        assert result.requirements_processed == 2
        
        # Check that heuristic method was used
        for risk in result.risk_items:
            assert risk.metadata['identification_method'] == 'heuristic'
            assert risk.metadata['confidence'] == 0.3  # Lower confidence for heuristic
    
    def test_parse_severity_levels(self, hazard_identifier):
        """Test severity parsing from strings."""
        assert hazard_identifier._parse_severity("Catastrophic") == Severity.CATASTROPHIC
        assert hazard_identifier._parse_severity("SERIOUS") == Severity.SERIOUS
        assert hazard_identifier._parse_severity("minor") == Severity.MINOR
        assert hazard_identifier._parse_severity("Negligible") == Severity.NEGLIGIBLE
        assert hazard_identifier._parse_severity("invalid") == Severity.MINOR  # Default
    
    def test_parse_probability_levels(self, hazard_identifier):
        """Test probability parsing from strings."""
        assert hazard_identifier._parse_probability("High") == Probability.HIGH
        assert hazard_identifier._parse_probability("MEDIUM") == Probability.MEDIUM
        assert hazard_identifier._parse_probability("low") == Probability.LOW
        assert hazard_identifier._parse_probability("Remote") == Probability.REMOTE
        assert hazard_identifier._parse_probability("invalid") == Probability.LOW  # Default
    
    def test_calculate_risk_level_matrix(self, hazard_identifier):
        """Test risk level calculation using ISO 14971 risk matrix."""
        # Test Catastrophic combinations
        assert hazard_identifier._calculate_risk_level(Severity.CATASTROPHIC, Probability.HIGH) == RiskLevel.UNACCEPTABLE
        assert hazard_identifier._calculate_risk_level(Severity.CATASTROPHIC, Probability.MEDIUM) == RiskLevel.UNACCEPTABLE
        assert hazard_identifier._calculate_risk_level(Severity.CATASTROPHIC, Probability.LOW) == RiskLevel.UNDESIRABLE
        assert hazard_identifier._calculate_risk_level(Severity.CATASTROPHIC, Probability.REMOTE) == RiskLevel.UNDESIRABLE
        
        # Test Serious combinations
        assert hazard_identifier._calculate_risk_level(Severity.SERIOUS, Probability.HIGH) == RiskLevel.UNACCEPTABLE
        assert hazard_identifier._calculate_risk_level(Severity.SERIOUS, Probability.MEDIUM) == RiskLevel.UNDESIRABLE
        assert hazard_identifier._calculate_risk_level(Severity.SERIOUS, Probability.LOW) == RiskLevel.ACCEPTABLE
        assert hazard_identifier._calculate_risk_level(Severity.SERIOUS, Probability.REMOTE) == RiskLevel.ACCEPTABLE
        
        # Test Minor combinations
        assert hazard_identifier._calculate_risk_level(Severity.MINOR, Probability.HIGH) == RiskLevel.UNDESIRABLE
        assert hazard_identifier._calculate_risk_level(Severity.MINOR, Probability.MEDIUM) == RiskLevel.UNDESIRABLE
        assert hazard_identifier._calculate_risk_level(Severity.MINOR, Probability.LOW) == RiskLevel.ACCEPTABLE
        assert hazard_identifier._calculate_risk_level(Severity.MINOR, Probability.REMOTE) == RiskLevel.ACCEPTABLE
        
        # Test Negligible (always negligible)
        assert hazard_identifier._calculate_risk_level(Severity.NEGLIGIBLE, Probability.HIGH) == RiskLevel.NEGLIGIBLE
        assert hazard_identifier._calculate_risk_level(Severity.NEGLIGIBLE, Probability.LOW) == RiskLevel.NEGLIGIBLE
    
    def test_calculate_risk_score(self, hazard_identifier):
        """Test numerical risk score calculation."""
        # Test various combinations
        assert hazard_identifier._calculate_risk_score(Severity.CATASTROPHIC, Probability.HIGH) == 16  # 4 * 4
        assert hazard_identifier._calculate_risk_score(Severity.SERIOUS, Probability.MEDIUM) == 9    # 3 * 3
        assert hazard_identifier._calculate_risk_score(Severity.MINOR, Probability.LOW) == 4        # 2 * 2
        assert hazard_identifier._calculate_risk_score(Severity.NEGLIGIBLE, Probability.REMOTE) == 1 # 1 * 1
    
    def test_fallback_hazard_identification(self, hazard_identifier, sample_software_requirements):
        """Test heuristic-based fallback hazard identification."""
        risk_items = hazard_identifier._fallback_hazard_identification(sample_software_requirements)
        
        assert len(risk_items) > 0
        
        # Check that risks were identified based on keywords
        risk_ids = [r.id for r in risk_items]
        assert len(set(risk_ids)) == len(risk_ids)  # All IDs should be unique
        
        # Verify heuristic metadata
        for risk in risk_items:
            assert risk.metadata['identification_method'] == 'heuristic'
            assert risk.metadata['confidence'] == 0.3
            assert 'matched_keywords' in risk.metadata
            assert len(risk.metadata['matched_keywords']) > 0
            assert risk.metadata['source_requirements'] == 1
            assert 'risk_score' in risk.metadata
    
    def test_get_risk_statistics_empty(self, hazard_identifier):
        """Test risk statistics with empty risk list."""
        stats = hazard_identifier.get_statistics([])
        
        assert stats['total_risks'] == 0
        assert stats['average_confidence'] == 0.0
        assert stats['severity_distribution'] == {}
        assert stats['probability_distribution'] == {}
        assert stats['risk_level_distribution'] == {}
        assert stats['high_risk_count'] == 0
        assert stats['medium_risk_count'] == 0
        assert stats['low_risk_count'] == 0
    
    def test_get_risk_statistics_with_risks(self, hazard_identifier):
        """Test risk statistics with actual risk items."""
        # Create sample risk items
        risk_items = [
            RiskItem(
                id="RISK_0001",
                hazard="Test hazard 1",
                cause="Test cause 1",
                effect="Test effect 1",
                severity=Severity.CATASTROPHIC,
                probability=Probability.HIGH,
                risk_level=RiskLevel.UNACCEPTABLE,
                mitigation="Test mitigation 1",
                verification="Test verification 1",
                related_requirements=["SR_0001"],
                metadata={'confidence': 0.8, 'identification_method': 'llm', 'risk_score': 16}
            ),
            RiskItem(
                id="RISK_0002",
                hazard="Test hazard 2",
                cause="Test cause 2",
                effect="Test effect 2",
                severity=Severity.MINOR,
                probability=Probability.LOW,
                risk_level=RiskLevel.ACCEPTABLE,
                mitigation="Test mitigation 2",
                verification="Test verification 2",
                related_requirements=["SR_0002"],
                metadata={'confidence': 0.6, 'identification_method': 'heuristic', 'risk_score': 4}
            )
        ]
        
        stats = hazard_identifier.get_statistics(risk_items)
        
        assert stats['total_risks'] == 2
        assert stats['average_confidence'] == 0.7  # (0.8 + 0.6) / 2
        assert stats['max_confidence'] == 0.8
        assert stats['min_confidence'] == 0.6
        assert stats['severity_distribution']['Catastrophic'] == 1
        assert stats['severity_distribution']['Minor'] == 1
        assert stats['probability_distribution']['High'] == 1
        assert stats['probability_distribution']['Low'] == 1
        assert stats['risk_level_distribution']['Unacceptable'] == 1
        assert stats['risk_level_distribution']['Acceptable'] == 1
        assert stats['high_risk_count'] == 1  # Unacceptable
        assert stats['medium_risk_count'] == 0  # Undesirable
        assert stats['low_risk_count'] == 1   # Acceptable + Negligible
        assert stats['identification_methods']['llm'] == 1
        assert stats['identification_methods']['heuristic'] == 1
        assert stats['average_risk_score'] == 10.0  # (16 + 4) / 2
    
    def test_filter_risks_by_level(self, hazard_identifier):
        """Test filtering risks by minimum risk level."""
        # Create sample risk items with different levels
        risk_items = [
            RiskItem(
                id="RISK_0001", hazard="H1", cause="C1", effect="E1",
                severity=Severity.CATASTROPHIC, probability=Probability.HIGH,
                risk_level=RiskLevel.UNACCEPTABLE, mitigation="M1", verification="V1"
            ),
            RiskItem(
                id="RISK_0002", hazard="H2", cause="C2", effect="E2",
                severity=Severity.SERIOUS, probability=Probability.MEDIUM,
                risk_level=RiskLevel.UNDESIRABLE, mitigation="M2", verification="V2"
            ),
            RiskItem(
                id="RISK_0003", hazard="H3", cause="C3", effect="E3",
                severity=Severity.MINOR, probability=Probability.LOW,
                risk_level=RiskLevel.ACCEPTABLE, mitigation="M3", verification="V3"
            ),
            RiskItem(
                id="RISK_0004", hazard="H4", cause="C4", effect="E4",
                severity=Severity.NEGLIGIBLE, probability=Probability.REMOTE,
                risk_level=RiskLevel.NEGLIGIBLE, mitigation="M4", verification="V4"
            )
        ]
        
        # Filter by Undesirable and above
        filtered = hazard_identifier.filter_by_level(risk_items, RiskLevel.UNDESIRABLE)
        assert len(filtered) == 2  # Unacceptable + Undesirable
        assert filtered[0].risk_level == RiskLevel.UNACCEPTABLE
        assert filtered[1].risk_level == RiskLevel.UNDESIRABLE
        
        # Filter by Acceptable and above
        filtered = hazard_identifier.filter_by_level(risk_items, RiskLevel.ACCEPTABLE)
        assert len(filtered) == 3  # All except Negligible
        
        # Filter by Negligible (should include all)
        filtered = hazard_identifier.filter_by_level(risk_items, RiskLevel.NEGLIGIBLE)
        assert len(filtered) == 4
    
    def test_group_risks_by_severity(self, hazard_identifier):
        """Test grouping risks by severity level."""
        # Create sample risk items with different severities
        risk_items = [
            RiskItem(
                id="RISK_0001", hazard="H1", cause="C1", effect="E1",
                severity=Severity.CATASTROPHIC, probability=Probability.HIGH,
                risk_level=RiskLevel.UNACCEPTABLE, mitigation="M1", verification="V1"
            ),
            RiskItem(
                id="RISK_0002", hazard="H2", cause="C2", effect="E2",
                severity=Severity.SERIOUS, probability=Probability.MEDIUM,
                risk_level=RiskLevel.UNDESIRABLE, mitigation="M2", verification="V2"
            ),
            RiskItem(
                id="RISK_0003", hazard="H3", cause="C3", effect="E3",
                severity=Severity.SERIOUS, probability=Probability.LOW,
                risk_level=RiskLevel.ACCEPTABLE, mitigation="M3", verification="V3"
            )
        ]
        
        grouped = hazard_identifier.group_by_severity(risk_items)
        
        assert len(grouped) == 2  # Catastrophic and Serious
        assert len(grouped[Severity.CATASTROPHIC]) == 1
        assert len(grouped[Severity.SERIOUS]) == 2
        assert grouped[Severity.CATASTROPHIC][0].id == "RISK_0001"
        assert len([r for r in grouped[Severity.SERIOUS] if r.id in ["RISK_0002", "RISK_0003"]]) == 2


if __name__ == '__main__':
    pytest.main([__file__])