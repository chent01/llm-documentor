"""
Unit tests for the risk register service.

Tests the generation, filtering, and export of ISO 14971 compliant risk registers.
"""

import pytest
import tempfile
import json
import csv
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

from medical_analyzer.services.risk_register import RiskRegister, RiskRegisterResult
from medical_analyzer.services.hazard_identifier import HazardIdentifier
from medical_analyzer.models.result_models import HazardIdentificationResult
from medical_analyzer.models.core import RiskItem, Requirement
from medical_analyzer.models.enums import (
    Severity, Probability, RiskLevel, RequirementType
)


class TestRiskRegister:
    """Test cases for RiskRegister class."""
    
    @pytest.fixture
    def mock_hazard_identifier(self):
        """Create a mock hazard identifier."""
        mock_identifier = Mock(spec=HazardIdentifier)
        return mock_identifier
    
    @pytest.fixture
    def risk_register(self, mock_hazard_identifier):
        """Create a RiskRegister instance with mock hazard identifier."""
        return RiskRegister(mock_hazard_identifier)
    
    @pytest.fixture
    def sample_requirements(self):
        """Create sample Software Requirements for testing."""
        return [
            Requirement(
                id="SR_001",
                type=RequirementType.SOFTWARE,
                text="The system shall validate all input data before processing",
                acceptance_criteria=["Input validation must reject invalid data", "System must log validation failures"],
                derived_from=["UR_001"]
            ),
            Requirement(
                id="SR_002", 
                type=RequirementType.SOFTWARE,
                text="The system shall display patient data accurately",
                acceptance_criteria=["Display must show current patient information", "Data must be refreshed every 5 seconds"],
                derived_from=["UR_002"]
            )
        ]
    
    @pytest.fixture
    def sample_risk_items(self):
        """Create sample risk items for testing."""
        return [
            RiskItem(
                id="RISK_0001",
                hazard="Incorrect data processing",
                cause="Invalid input data or processing errors",
                effect="Incorrect results leading to potential misdiagnosis",
                severity=Severity.SERIOUS,
                probability=Probability.MEDIUM,
                risk_level=RiskLevel.UNDESIRABLE,
                mitigation="Implement comprehensive input validation and error checking",
                verification="Unit testing and integration testing with invalid data scenarios",
                related_requirements=["SR_001"],
                metadata={
                    'confidence': 0.8,
                    'identification_method': 'llm',
                    'risk_score': 9
                }
            ),
            RiskItem(
                id="RISK_0002",
                hazard="Misleading user interface",
                cause="Unclear or incorrect information display",
                effect="User confusion leading to incorrect device operation",
                severity=Severity.MINOR,
                probability=Probability.LOW,
                risk_level=RiskLevel.ACCEPTABLE,
                mitigation="Improve user interface design and add confirmation dialogs",
                verification="Usability testing and user training validation",
                related_requirements=["SR_002"],
                metadata={
                    'confidence': 0.7,
                    'identification_method': 'llm',
                    'risk_score': 4
                }
            ),
            RiskItem(
                id="RISK_0003",
                hazard="System failure during critical operation",
                cause="Software crash or hardware malfunction",
                effect="Complete loss of device functionality during patient treatment",
                severity=Severity.CATASTROPHIC,
                probability=Probability.LOW,
                risk_level=RiskLevel.UNDESIRABLE,
                mitigation="Implement redundant systems and automatic failover mechanisms",
                verification="Comprehensive testing including unit, integration, and system tests",
                related_requirements=["SR_001", "SR_002"],
                metadata={
                    'confidence': 0.9,
                    'identification_method': 'llm',
                    'risk_score': 8
                }
            )
        ]
    
    def test_init_without_hazard_identifier(self):
        """Test RiskRegister initialization without hazard identifier."""
        risk_register = RiskRegister()
        assert risk_register.hazard_identifier is None
    
    def test_init_with_hazard_identifier(self, mock_hazard_identifier):
        """Test RiskRegister initialization with hazard identifier."""
        risk_register = RiskRegister(mock_hazard_identifier)
        assert risk_register.hazard_identifier == mock_hazard_identifier
    
    def test_generate_risk_register_without_hazard_identifier(self, sample_requirements):
        """Test risk register generation without hazard identifier raises error."""
        risk_register = RiskRegister()
        
        with pytest.raises(ValueError, match="HazardIdentifier is required"):
            risk_register.generate_risk_register(sample_requirements)
    
    def test_generate_risk_register_success(self, risk_register, sample_requirements, sample_risk_items):
        """Test successful risk register generation."""
        # Mock hazard identification result
        hazard_result = HazardIdentificationResult(
            risk_items=sample_risk_items,
            confidence_score=0.8,
            processing_time=2.5,
            requirements_processed=2,
            errors=[],
            metadata={'test': 'data'}
        )
        
        risk_register.hazard_identifier.identify_hazards.return_value = hazard_result
        
        # Generate risk register
        result = risk_register.generate_risk_register(
            sample_requirements, 
            "Test medical device project"
        )
        
        # Verify result
        assert isinstance(result, RiskRegisterResult)
        assert len(result.risk_items) == 3
        assert result.total_risks == 3
        assert result.metadata['iso_14971_compliant'] is True
        assert result.metadata['total_requirements_analyzed'] == 2
        assert result.metadata['hazard_identification_confidence'] == 0.8
        
        # Verify enhanced risk items have additional metadata
        for risk in result.risk_items:
            assert 'iso_14971_compliant' in risk.metadata
            assert 'risk_score' in risk.metadata
            assert 'residual_risk_assessment' in risk.metadata
            assert 'risk_acceptability' in risk.metadata
    
    def test_generate_risk_register_with_errors(self, risk_register, sample_requirements, sample_risk_items):
        """Test risk register generation with hazard identification errors."""
        # Mock hazard identification result with errors
        hazard_result = HazardIdentificationResult(
            risk_items=sample_risk_items,
            confidence_score=0.6,
            processing_time=3.0,
            requirements_processed=1,
            errors=["Error processing requirement SR_002"],
            metadata={'test': 'data'}
        )
        
        risk_register.hazard_identifier.identify_hazards.return_value = hazard_result
        
        # Generate risk register
        result = risk_register.generate_risk_register(sample_requirements)
        
        # Verify errors are propagated
        assert len(result.metadata['errors']) == 1
        assert "Error processing requirement SR_002" in result.metadata['errors']
    
    def test_filter_by_severity(self, risk_register, sample_risk_items):
        """Test filtering risks by severity level."""
        # Filter by SERIOUS or higher
        filtered = risk_register.filter_by_severity(sample_risk_items, Severity.SERIOUS)
        assert len(filtered) == 2  # SERIOUS and CATASTROPHIC
        
        # Filter by CATASTROPHIC only
        filtered = risk_register.filter_by_severity(sample_risk_items, Severity.CATASTROPHIC)
        assert len(filtered) == 1
        assert filtered[0].severity == Severity.CATASTROPHIC
        
        # Filter by MINOR or higher (should include all)
        filtered = risk_register.filter_by_severity(sample_risk_items, Severity.MINOR)
        assert len(filtered) == 3
    
    def test_filter_by_risk_level(self, risk_register, sample_risk_items):
        """Test filtering risks by risk level."""
        # Filter by UNDESIRABLE or higher
        filtered = risk_register.filter_by_risk_level(sample_risk_items, RiskLevel.UNDESIRABLE)
        assert len(filtered) == 2  # Two UNDESIRABLE risks
        
        # Filter by UNACCEPTABLE only
        filtered = risk_register.filter_by_risk_level(sample_risk_items, RiskLevel.UNACCEPTABLE)
        assert len(filtered) == 0  # No UNACCEPTABLE risks in sample
        
        # Filter by ACCEPTABLE or higher (should include all)
        filtered = risk_register.filter_by_risk_level(sample_risk_items, RiskLevel.ACCEPTABLE)
        assert len(filtered) == 3
    
    def test_sort_by_priority(self, risk_register, sample_risk_items):
        """Test sorting risks by priority."""
        # First enhance the risk items to add priority metadata
        enhanced_risks = risk_register._enhance_risk_items(sample_risk_items, True)
        
        # Sort by priority
        sorted_risks = risk_register.sort_by_priority(enhanced_risks)
        
        # Verify sorting (highest priority first)
        assert len(sorted_risks) == 3
        
        # Get priority values for verification
        priorities = [r.metadata['risk_score']['risk_priority'] for r in sorted_risks]
        
        # Should be sorted by priority (lower number = higher priority)
        for i in range(len(priorities) - 1):
            assert priorities[i] <= priorities[i + 1]
    
    def test_export_to_csv(self, risk_register, sample_risk_items):
        """Test exporting risk register to CSV format."""
        # Enhance risk items first
        enhanced_risks = risk_register._enhance_risk_items(sample_risk_items, True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "risk_register.csv"
            
            # Export to CSV
            success = risk_register.export_to_csv(enhanced_risks, str(output_path))
            assert success is True
            assert output_path.exists()
            
            # Verify CSV content
            with open(output_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)
                
                assert len(rows) == 3
                
                # Check required columns exist
                expected_columns = [
                    'Risk_ID', 'Hazard', 'Cause', 'Effect', 'Severity', 'Probability',
                    'Risk_Level', 'Risk_Score', 'Priority', 'Mitigation', 'Verification'
                ]
                
                for column in expected_columns:
                    assert column in reader.fieldnames
                
                # Verify first row data
                first_row = rows[0]
                assert first_row['Risk_ID'] == 'RISK_0001'
                assert first_row['Hazard'] == 'Incorrect data processing'
                assert first_row['Severity'] == 'Serious'
                assert first_row['Probability'] == 'Medium'
    
    def test_export_to_json(self, risk_register, sample_risk_items):
        """Test exporting risk register to JSON format."""
        # Enhance risk items first
        enhanced_risks = risk_register._enhance_risk_items(sample_risk_items, True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "risk_register.json"
            
            # Export to JSON
            success = risk_register.export_to_json(enhanced_risks, str(output_path))
            assert success is True
            assert output_path.exists()
            
            # Verify JSON content
            with open(output_path, 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
                
                assert 'risk_register' in data
                register = data['risk_register']
                
                assert register['total_risks'] == 3
                assert register['iso_14971_compliant'] is True
                assert len(register['risks']) == 3
                
                # Verify first risk data
                first_risk = register['risks'][0]
                assert first_risk['id'] == 'RISK_0001'
                assert first_risk['hazard'] == 'Incorrect data processing'
                assert first_risk['severity'] == 'Serious'
                assert 'metadata' in first_risk
    
    def test_export_to_json_without_metadata(self, risk_register, sample_risk_items):
        """Test exporting risk register to JSON without metadata."""
        enhanced_risks = risk_register._enhance_risk_items(sample_risk_items, True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "risk_register_no_meta.json"
            
            # Export to JSON without metadata
            success = risk_register.export_to_json(enhanced_risks, str(output_path), include_metadata=False)
            assert success is True
            
            # Verify metadata is not included
            with open(output_path, 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
                first_risk = data['risk_register']['risks'][0]
                assert 'metadata' not in first_risk
    
    def test_generate_iso_14971_report(self, risk_register, sample_risk_items):
        """Test generating ISO 14971 compliant report."""
        enhanced_risks = risk_register._enhance_risk_items(sample_risk_items, True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "iso_14971_report.md"
            project_info = {
                'name': 'Test Medical Device',
                'version': '1.0.0'
            }
            
            # Generate report
            success = risk_register.generate_iso_14971_report(
                enhanced_risks, str(output_path), project_info
            )
            assert success is True
            assert output_path.exists()
            
            # Verify report content
            with open(output_path, 'r', encoding='utf-8') as report_file:
                content = report_file.read()
                
                # Check for required sections
                assert "# ISO 14971 Risk Management Report" in content
                assert "## Project Information" in content
                assert "## Executive Summary" in content
                assert "## Detailed Risk Analysis" in content
                assert "Test Medical Device" in content
                assert "RISK_0001" in content
                assert "Incorrect data processing" in content
    
    def test_calculate_detailed_risk_score(self, risk_register):
        """Test detailed risk score calculation."""
        risk = RiskItem(
            id="TEST_001",
            hazard="Test hazard",
            cause="Test cause", 
            effect="Test effect",
            severity=Severity.SERIOUS,
            probability=Probability.HIGH,
            risk_level=RiskLevel.UNACCEPTABLE,
            mitigation="Test mitigation",
            verification="Test verification"
        )
        
        score_data = risk_register._calculate_detailed_risk_score(risk)
        
        assert score_data['severity_score'] == 3  # SERIOUS = 3
        assert score_data['probability_score'] == 4  # HIGH = 4
        assert score_data['raw_score'] == 12  # 3 * 4
        assert score_data['normalized_score'] == 0.75  # 12/16
        assert score_data['risk_priority'] == 1  # Highest priority
    
    def test_estimate_mitigation_effectiveness(self, risk_register):
        """Test mitigation effectiveness estimation."""
        # High effectiveness mitigation
        high_mitigation = "Implement redundant validation and automatic monitoring with independent verification"
        high_effectiveness = risk_register._estimate_mitigation_effectiveness(high_mitigation)
        assert high_effectiveness > 0.7
        
        # Medium effectiveness mitigation
        medium_mitigation = "Add input validation and error checking with user notification"
        medium_effectiveness = risk_register._estimate_mitigation_effectiveness(medium_mitigation)
        assert 0.3 < medium_effectiveness <= 0.7
        
        # Low effectiveness mitigation
        low_mitigation = "Document the issue"
        low_effectiveness = risk_register._estimate_mitigation_effectiveness(low_mitigation)
        assert low_effectiveness <= 0.4
        
        # Empty mitigation
        empty_effectiveness = risk_register._estimate_mitigation_effectiveness("")
        assert empty_effectiveness == 0.0
    
    def test_reduce_severity_and_probability(self, risk_register):
        """Test severity and probability reduction based on mitigation effectiveness."""
        # High effectiveness should reduce by 2 levels
        reduced_severity = risk_register._reduce_severity(Severity.CATASTROPHIC, 0.8)
        assert reduced_severity == Severity.MINOR
        
        reduced_probability = risk_register._reduce_probability(Probability.HIGH, 0.8)
        assert reduced_probability == Probability.LOW
        
        # Medium effectiveness should reduce by 1 level
        reduced_severity = risk_register._reduce_severity(Severity.SERIOUS, 0.6)
        assert reduced_severity == Severity.MINOR
        
        # Low effectiveness should not reduce
        reduced_severity = risk_register._reduce_severity(Severity.SERIOUS, 0.2)
        assert reduced_severity == Severity.SERIOUS
        
        # Test boundary conditions
        reduced_severity = risk_register._reduce_severity(Severity.NEGLIGIBLE, 0.9)
        assert reduced_severity == Severity.NEGLIGIBLE  # Can't reduce below NEGLIGIBLE
    
    def test_assess_residual_risk(self, risk_register):
        """Test residual risk assessment."""
        risk = RiskItem(
            id="TEST_001",
            hazard="Test hazard",
            cause="Test cause",
            effect="Test effect", 
            severity=Severity.SERIOUS,
            probability=Probability.HIGH,
            risk_level=RiskLevel.UNACCEPTABLE,
            mitigation="Implement comprehensive validation and monitoring with automatic detection",
            verification="Test verification"
        )
        
        residual_data = risk_register._assess_residual_risk(risk)
        
        assert 'residual_severity' in residual_data
        assert 'residual_probability' in residual_data
        assert 'mitigation_effectiveness' in residual_data
        assert 'residual_risk_level' in residual_data
        
        # With good mitigation, residual risk should be lower
        assert residual_data['mitigation_effectiveness'] > 0.5
    
    def test_determine_risk_acceptability(self, risk_register):
        """Test risk acceptability determination."""
        # Test UNACCEPTABLE risk
        unacceptable_risk = RiskItem(
            id="TEST_001", hazard="Test", cause="Test", effect="Test",
            severity=Severity.CATASTROPHIC, probability=Probability.HIGH,
            risk_level=RiskLevel.UNACCEPTABLE, mitigation="", verification=""
        )
        
        acceptability = risk_register._determine_risk_acceptability(unacceptable_risk)
        assert acceptability['acceptable'] is False
        assert acceptability['approval_needed'] is True
        assert "Immediate risk control" in acceptability['action_required']
        
        # Test ACCEPTABLE risk
        acceptable_risk = RiskItem(
            id="TEST_002", hazard="Test", cause="Test", effect="Test",
            severity=Severity.MINOR, probability=Probability.LOW,
            risk_level=RiskLevel.ACCEPTABLE, mitigation="", verification=""
        )
        
        acceptability = risk_register._determine_risk_acceptability(acceptable_risk)
        assert acceptability['acceptable'] is True
        assert acceptability['approval_needed'] is False
    
    def test_extract_risk_control_measures(self, risk_register):
        """Test extraction of individual risk control measures."""
        # Test with semicolon-separated measures
        mitigation_text = "Implement input validation; Add error checking; Create backup systems"
        measures = risk_register._extract_risk_control_measures(mitigation_text)
        assert len(measures) == 3
        assert "Implement input validation" in measures
        assert "Add error checking" in measures
        assert "Create backup systems" in measures
        
        # Test with bullet points
        mitigation_text = "• Implement redundant validation\n• Add automatic monitoring\n• Create failsafe mechanisms"
        measures = risk_register._extract_risk_control_measures(mitigation_text)
        assert len(measures) == 3
        assert "Implement redundant validation" in measures
        
        # Test with single measure
        mitigation_text = "Implement comprehensive input validation with error handling"
        measures = risk_register._extract_risk_control_measures(mitigation_text)
        assert len(measures) == 1
        assert measures[0] == mitigation_text
        
        # Test with empty mitigation
        measures = risk_register._extract_risk_control_measures("")
        assert len(measures) == 0
    
    def test_generate_surveillance_plan(self, risk_register):
        """Test post-market surveillance plan generation."""
        # Test high-risk item
        high_risk = RiskItem(
            id="TEST_001", hazard="Test", cause="Test", effect="Test",
            severity=Severity.CATASTROPHIC, probability=Probability.HIGH,
            risk_level=RiskLevel.UNACCEPTABLE, mitigation="", verification=""
        )
        
        plan = risk_register._generate_surveillance_plan(high_risk)
        assert "Continuous monitoring" in plan
        assert "immediate reporting" in plan
        
        # Test medium-risk item
        medium_risk = RiskItem(
            id="TEST_002", hazard="Test", cause="Test", effect="Test",
            severity=Severity.SERIOUS, probability=Probability.MEDIUM,
            risk_level=RiskLevel.UNDESIRABLE, mitigation="", verification=""
        )
        
        plan = risk_register._generate_surveillance_plan(medium_risk)
        assert "Quarterly monitoring" in plan
        
        # Test low-risk item
        low_risk = RiskItem(
            id="TEST_003", hazard="Test", cause="Test", effect="Test",
            severity=Severity.MINOR, probability=Probability.LOW,
            risk_level=RiskLevel.ACCEPTABLE, mitigation="", verification=""
        )
        
        plan = risk_register._generate_surveillance_plan(low_risk)
        assert "Annual review" in plan
    
    def test_generate_risk_benefit_analysis(self, risk_register):
        """Test risk-benefit analysis generation."""
        # Test unacceptable risk
        unacceptable_risk = RiskItem(
            id="TEST_001", hazard="Test", cause="Test", effect="Test",
            severity=Severity.CATASTROPHIC, probability=Probability.HIGH,
            risk_level=RiskLevel.UNACCEPTABLE, mitigation="", verification=""
        )
        
        analysis = risk_register._generate_risk_benefit_analysis(unacceptable_risk)
        assert "not acceptable" in analysis
        assert "additional risk control" in analysis
        
        # Test acceptable risk
        acceptable_risk = RiskItem(
            id="TEST_002", hazard="Test", cause="Test", effect="Test",
            severity=Severity.MINOR, probability=Probability.LOW,
            risk_level=RiskLevel.ACCEPTABLE, mitigation="", verification=""
        )
        
        analysis = risk_register._generate_risk_benefit_analysis(acceptable_risk)
        assert "acceptable" in analysis
        assert "outweigh" in analysis
    
    def test_enhanced_risk_items_iso_fields(self, risk_register, sample_risk_items):
        """Test that enhanced risk items include new ISO 14971 fields."""
        enhanced_risks = risk_register._enhance_risk_items(sample_risk_items, True)
        
        for risk in enhanced_risks:
            # Check that new ISO 14971 fields are populated
            assert risk.risk_control_measures is not None
            assert risk.residual_risk_severity is not None
            assert risk.residual_risk_probability is not None
            assert risk.residual_risk_level is not None
            assert risk.risk_acceptability is not None
            assert risk.risk_control_effectiveness is not None
            assert risk.post_market_surveillance is not None
            assert risk.risk_benefit_analysis is not None
            
            # Check that risk acceptability is properly set
            assert risk.risk_acceptability in ["Acceptable", "Not Acceptable"]
            
            # Check that control effectiveness is in valid range
            assert 0.0 <= risk.risk_control_effectiveness <= 1.0
    
    def test_calculate_risk_statistics(self, risk_register, sample_risk_items):
        """Test risk statistics calculation."""
        stats = risk_register._calculate_risk_statistics(sample_risk_items)
        
        assert stats['total_risks'] == 3
        assert 'severity_distribution' in stats
        assert 'probability_distribution' in stats
        assert 'risk_level_distribution' in stats
        assert 'average_risk_score' in stats
        
        # Verify severity distribution
        assert stats['severity_distribution']['Serious'] == 1
        assert stats['severity_distribution']['Minor'] == 1
        assert stats['severity_distribution']['Catastrophic'] == 1
        
        # Verify probability distribution
        assert stats['probability_distribution']['Medium'] == 1
        assert stats['probability_distribution']['Low'] == 2
    
    def test_calculate_risk_statistics_empty_list(self, risk_register):
        """Test risk statistics calculation with empty risk list."""
        stats = risk_register._calculate_risk_statistics([])
        
        assert stats['total_risks'] == 0
        assert stats['average_risk_score'] == 0.0
        assert stats['severity_distribution'] == {}
        assert stats['probability_distribution'] == {}
        assert stats['risk_level_distribution'] == {}


class TestRiskRegisterResult:
    """Test cases for RiskRegisterResult class."""
    
    @pytest.fixture
    def sample_risk_items(self):
        """Create sample risk items for testing."""
        return [
            RiskItem(
                id="RISK_001", hazard="High risk", cause="Cause", effect="Effect",
                severity=Severity.CATASTROPHIC, probability=Probability.HIGH,
                risk_level=RiskLevel.UNACCEPTABLE, mitigation="", verification=""
            ),
            RiskItem(
                id="RISK_002", hazard="Medium risk", cause="Cause", effect="Effect",
                severity=Severity.SERIOUS, probability=Probability.MEDIUM,
                risk_level=RiskLevel.UNDESIRABLE, mitigation="", verification=""
            ),
            RiskItem(
                id="RISK_003", hazard="Low risk", cause="Cause", effect="Effect",
                severity=Severity.MINOR, probability=Probability.LOW,
                risk_level=RiskLevel.ACCEPTABLE, mitigation="", verification=""
            )
        ]
    
    def test_risk_register_result_properties(self, sample_risk_items):
        """Test RiskRegisterResult properties."""
        metadata = {'test': 'data'}
        result = RiskRegisterResult(sample_risk_items, metadata)
        
        assert result.total_risks == 3
        assert len(result.high_priority_risks) == 1
        assert len(result.medium_priority_risks) == 1
        assert len(result.low_priority_risks) == 1
        
        # Verify risk categorization
        assert result.high_priority_risks[0].risk_level == RiskLevel.UNACCEPTABLE
        assert result.medium_priority_risks[0].risk_level == RiskLevel.UNDESIRABLE
        assert result.low_priority_risks[0].risk_level == RiskLevel.ACCEPTABLE
    
    def test_risk_register_result_empty(self):
        """Test RiskRegisterResult with empty risk list."""
        result = RiskRegisterResult([], {})
        
        assert result.total_risks == 0
        assert len(result.high_priority_risks) == 0
        assert len(result.medium_priority_risks) == 0
        assert len(result.low_priority_risks) == 0


class TestRiskRegisterIntegration:
    """Integration tests for risk register functionality."""
    
    @pytest.fixture
    def mock_llm_backend(self):
        """Create a mock LLM backend."""
        mock_backend = Mock()
        mock_backend.generate.return_value = '''[
            {
                "hazard": "Data corruption during processing",
                "cause": "Memory overflow or invalid pointer access",
                "effect": "Incorrect patient data leading to misdiagnosis",
                "severity": "Serious",
                "probability": "Medium",
                "confidence": 0.8,
                "related_requirement_id": "SR_001"
            }
        ]'''
        return mock_backend
    
    def test_end_to_end_risk_register_generation(self, mock_llm_backend):
        """Test complete end-to-end risk register generation."""
        # Create hazard identifier with mock LLM
        hazard_identifier = HazardIdentifier(mock_llm_backend)
        
        # Create risk register
        risk_register = RiskRegister(hazard_identifier)
        
        # Create sample requirements
        requirements = [
            Requirement(
                id="SR_001",
                type=RequirementType.SOFTWARE,
                text="The system shall process patient data securely",
                acceptance_criteria=["Data must be encrypted", "Access must be logged"]
            )
        ]
        
        # Generate risk register
        result = risk_register.generate_risk_register(
            requirements, 
            "Medical device for patient monitoring"
        )
        
        # Verify result
        assert isinstance(result, RiskRegisterResult)
        assert result.total_risks > 0
        assert result.metadata['iso_14971_compliant'] is True
        
        # Verify risk items have enhanced metadata
        for risk in result.risk_items:
            assert 'iso_14971_compliant' in risk.metadata
            assert 'risk_score' in risk.metadata
            assert 'residual_risk_assessment' in risk.metadata
    
    def test_export_integration(self, mock_llm_backend):
        """Test integration of risk register generation and export."""
        # Setup
        hazard_identifier = HazardIdentifier(mock_llm_backend)
        risk_register = RiskRegister(hazard_identifier)
        
        requirements = [
            Requirement(
                id="SR_001",
                type=RequirementType.SOFTWARE,
                text="System shall validate input data",
                acceptance_criteria=["Reject invalid input"]
            )
        ]
        
        # Generate risk register
        result = risk_register.generate_risk_register(requirements)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test CSV export
            csv_path = Path(temp_dir) / "risks.csv"
            csv_success = risk_register.export_to_csv(result.risk_items, str(csv_path))
            assert csv_success is True
            assert csv_path.exists()
            
            # Test JSON export
            json_path = Path(temp_dir) / "risks.json"
            json_success = risk_register.export_to_json(result.risk_items, str(json_path))
            assert json_success is True
            assert json_path.exists()
            
            # Test ISO report export
            report_path = Path(temp_dir) / "iso_report.md"
            report_success = risk_register.generate_iso_14971_report(
                result.risk_items, str(report_path), {'name': 'Test Device'}
            )
            assert report_success is True
            assert report_path.exists()