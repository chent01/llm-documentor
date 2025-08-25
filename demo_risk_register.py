#!/usr/bin/env python3
"""
Demo script for the Risk Register functionality.

This script demonstrates how to use the RiskRegister service to generate
ISO 14971 compliant risk registers from Software Requirements.
"""

print("Demo script starting...")

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from medical_analyzer.services.risk_register import RiskRegister
from medical_analyzer.services.hazard_identifier import HazardIdentifier
from medical_analyzer.models.core import Requirement
from medical_analyzer.models.enums import RequirementType, Severity, RiskLevel
from medical_analyzer.llm.backend import LLMBackend


def create_sample_requirements():
    """Create sample Software Requirements for demonstration."""
    return [
        Requirement(
            id="SR_001",
            type=RequirementType.SOFTWARE,
            text="The system shall validate all patient data input before processing to ensure data integrity and prevent corruption",
            acceptance_criteria=[
                "Input validation must reject invalid data formats",
                "System must log all validation failures with timestamps",
                "Invalid data must not be processed or stored"
            ],
            derived_from=["UR_001"]
        ),
        Requirement(
            id="SR_002",
            type=RequirementType.SOFTWARE,
            text="The system shall display patient vital signs with real-time updates every 2 seconds",
            acceptance_criteria=[
                "Display must show current patient information accurately",
                "Data must be refreshed every 2 seconds maximum",
                "Display must indicate when data is stale or unavailable"
            ],
            derived_from=["UR_002"]
        ),
        Requirement(
            id="SR_003",
            type=RequirementType.SOFTWARE,
            text="The system shall implement automatic backup and recovery mechanisms for critical patient data",
            acceptance_criteria=[
                "Automatic backup must occur every 5 minutes",
                "Recovery must be possible within 30 seconds",
                "Data integrity must be verified after recovery"
            ],
            derived_from=["UR_003"]
        ),
        Requirement(
            id="SR_004",
            type=RequirementType.SOFTWARE,
            text="The system shall provide user authentication and access control for medical personnel",
            acceptance_criteria=[
                "Users must authenticate with username and password",
                "Access levels must be enforced based on user roles",
                "Failed authentication attempts must be logged"
            ],
            derived_from=["UR_004"]
        )
    ]


class MockLLMBackend(LLMBackend):
    """Mock LLM backend for testing."""
    
    def __init__(self):
        super().__init__({})  # Initialize with empty config
        self.responses = []
        self.response_index = 0
    
    def generate(self, prompt, context_chunks=None, temperature=0.7, max_tokens=1000, system_prompt=None):
        if self.response_index < len(self.responses):
            response = self.responses[self.response_index]
            self.response_index += 1
            return response
        else:
            # Return a generic response if we run out of predefined responses
            return '''[
                {
                    "hazard": "Generic system malfunction",
                    "cause": "Software or hardware failure",
                    "effect": "Potential impact on patient care",
                    "severity": "Minor",
                    "probability": "Low",
                    "confidence": 0.6,
                    "related_requirement_id": "SR_001"
                }
            ]'''
    
    def is_available(self):
        return True
    
    def get_model_info(self):
        from medical_analyzer.llm.backend import ModelInfo, ModelType
        return ModelInfo(
            name="Mock LLM",
            type=ModelType.CHAT,
            context_length=4096,
            supports_system_prompt=True,
            backend_name="mock"
        )
    
    def get_required_config_keys(self):
        return []  # No config required for mock


def create_mock_llm_backend():
    """Create a mock LLM backend with realistic medical device hazard responses."""
    mock_backend = MockLLMBackend()
    
    # Configure realistic hazard identification responses
    mock_responses = [
        '''[
            {
                "hazard": "Incorrect patient data processing",
                "cause": "Invalid input data bypassing validation or processing errors in data handling logic",
                "effect": "Incorrect patient information leading to misdiagnosis, wrong treatment decisions, or medication errors",
                "severity": "Serious",
                "probability": "Medium",
                "confidence": 0.85,
                "related_requirement_id": "SR_001"
            }
        ]''',
        '''[
            {
                "hazard": "Delayed or missing vital signs display",
                "cause": "System performance issues, network delays, or display refresh failures",
                "effect": "Healthcare providers may miss critical changes in patient condition, leading to delayed intervention",
                "severity": "Serious",
                "probability": "Low",
                "confidence": 0.78,
                "related_requirement_id": "SR_002"
            }
        ]''',
        '''[
            {
                "hazard": "Loss of critical patient data",
                "cause": "Backup system failure, storage corruption, or recovery mechanism malfunction",
                "effect": "Permanent loss of patient medical history and treatment records, compromising patient safety",
                "severity": "Catastrophic",
                "probability": "Low",
                "confidence": 0.92,
                "related_requirement_id": "SR_003"
            }
        ]''',
        '''[
            {
                "hazard": "Unauthorized access to patient data",
                "cause": "Authentication bypass, privilege escalation, or access control failures",
                "effect": "Breach of patient confidentiality and potential data manipulation by unauthorized personnel",
                "severity": "Serious",
                "probability": "Medium",
                "confidence": 0.88,
                "related_requirement_id": "SR_004"
            }
        ]'''
    ]
    
    # Set up the mock to return different responses for different calls
    mock_backend.responses = mock_responses
    mock_backend.response_index = 0
    return mock_backend


def demonstrate_risk_register_generation():
    """Demonstrate the complete risk register generation process."""
    print("=" * 80)
    print("Medical Software Analysis Tool - Risk Register Demo")
    print("=" * 80)
    print()
    
    # Create sample requirements
    print("1. Creating sample Software Requirements...")
    requirements = create_sample_requirements()
    print(f"   Created {len(requirements)} Software Requirements")
    for req in requirements:
        print(f"   - {req.id}: {req.text[:60]}...")
    print()
    
    # Create mock LLM backend and hazard identifier
    print("2. Setting up hazard identification service...")
    mock_llm = create_mock_llm_backend()
    hazard_identifier = HazardIdentifier(mock_llm)
    print("   ✓ Mock LLM backend configured")
    print("   ✓ Hazard identifier initialized")
    print()
    
    # Create risk register service
    print("3. Creating risk register service...")
    risk_register = RiskRegister(hazard_identifier)
    print("   ✓ Risk register service initialized")
    print()
    
    # Generate risk register
    print("4. Generating ISO 14971 compliant risk register...")
    project_description = """
    Medical Device Patient Monitoring System
    
    This is a critical care patient monitoring system used in hospital ICUs.
    The system monitors vital signs, displays patient data, and alerts medical
    staff to critical conditions. The device is used by nurses, doctors, and
    medical technicians to make life-critical decisions about patient care.
    
    Key safety considerations:
    - Patient data accuracy is critical for diagnosis and treatment
    - System availability must be maintained during patient monitoring
    - Data security and privacy must be protected
    - User interface must be clear and prevent user errors
    """
    
    try:
        result = risk_register.generate_risk_register(
            requirements, 
            project_description.strip(),
            include_mitigation_strategies=True
        )
        
        print(f"   ✓ Generated {result.total_risks} risk items")
        print(f"   ✓ High priority risks: {len(result.high_priority_risks)}")
        print(f"   ✓ Medium priority risks: {len(result.medium_priority_risks)}")
        print(f"   ✓ Low priority risks: {len(result.low_priority_risks)}")
        print(f"   ✓ ISO 14971 compliance: {result.metadata.get('iso_14971_compliant', False)}")
        print()
        
    except Exception as e:
        print(f"   ✗ Error generating risk register: {e}")
        return
    
    # Display risk details
    print("5. Risk Register Details:")
    print("-" * 80)
    
    # Sort risks by priority for display
    sorted_risks = risk_register.sort_by_priority(result.risk_items)
    
    for i, risk in enumerate(sorted_risks, 1):
        score_data = risk.metadata.get('risk_score', {})
        residual_data = risk.metadata.get('residual_risk_assessment', {})
        acceptability_data = risk.metadata.get('risk_acceptability', {})
        
        print(f"\nRisk #{i}: {risk.id}")
        print(f"Hazard: {risk.hazard}")
        print(f"Cause: {risk.cause}")
        print(f"Effect: {risk.effect}")
        print(f"Severity: {risk.severity.value} | Probability: {risk.probability.value}")
        print(f"Risk Level: {risk.risk_level.value}")
        print(f"Risk Score: {score_data.get('raw_score', 'N/A')} | Priority: {score_data.get('risk_priority', 'N/A')}")
        print(f"Acceptable: {'Yes' if acceptability_data.get('acceptable', False) else 'No'}")
        
        if risk.mitigation:
            print(f"Mitigation: {risk.mitigation[:100]}...")
        
        if residual_data:
            print(f"Residual Risk: {residual_data.get('residual_severity', 'N/A')} / {residual_data.get('residual_probability', 'N/A')}")
        
        print(f"Related Requirements: {', '.join(risk.related_requirements)}")
        print("-" * 40)
    
    print()
    
    # Demonstrate filtering capabilities
    print("6. Demonstrating filtering capabilities:")
    print("-" * 50)
    
    # Filter by severity
    serious_risks = risk_register.filter_by_severity(result.risk_items, Severity.SERIOUS)
    print(f"Serious or higher severity risks: {len(serious_risks)}")
    
    # Filter by risk level
    undesirable_risks = risk_register.filter_by_risk_level(result.risk_items, RiskLevel.UNDESIRABLE)
    print(f"Undesirable or higher risk level: {len(undesirable_risks)}")
    print()
    
    # Demonstrate export capabilities
    print("7. Demonstrating export capabilities:")
    print("-" * 50)
    
    output_dir = Path("demo_output")
    output_dir.mkdir(exist_ok=True)
    
    # Export to CSV
    csv_path = output_dir / "risk_register.csv"
    csv_success = risk_register.export_to_csv(result.risk_items, str(csv_path))
    print(f"CSV export: {'✓ Success' if csv_success else '✗ Failed'} -> {csv_path}")
    
    # Export to JSON
    json_path = output_dir / "risk_register.json"
    json_success = risk_register.export_to_json(result.risk_items, str(json_path))
    print(f"JSON export: {'✓ Success' if json_success else '✗ Failed'} -> {json_path}")
    
    # Generate ISO 14971 report
    report_path = output_dir / "iso_14971_report.md"
    project_info = {
        'name': 'Patient Monitoring System',
        'version': '2.1.0',
        'manufacturer': 'Demo Medical Devices Inc.',
        'classification': 'Class IIb Medical Device'
    }
    
    report_success = risk_register.generate_iso_14971_report(
        result.risk_items, str(report_path), project_info
    )
    print(f"ISO 14971 report: {'✓ Success' if report_success else '✗ Failed'} -> {report_path}")
    print()
    
    # Display statistics
    print("8. Risk Register Statistics:")
    print("-" * 50)
    stats = result.metadata.get('risk_statistics', {})
    
    print(f"Total Risks: {stats.get('total_risks', 0)}")
    print(f"Average Risk Score: {stats.get('average_risk_score', 0):.2f}")
    print(f"Max Risk Score: {stats.get('max_risk_score', 0)}")
    print(f"Min Risk Score: {stats.get('min_risk_score', 0)}")
    
    print("\nSeverity Distribution:")
    for severity, count in stats.get('severity_distribution', {}).items():
        print(f"  {severity}: {count}")
    
    print("\nRisk Level Distribution:")
    for level, count in stats.get('risk_level_distribution', {}).items():
        print(f"  {level}: {count}")
    
    print()
    print("=" * 80)
    print("Demo completed successfully!")
    print(f"Output files saved to: {output_dir.absolute()}")
    print("=" * 80)


if __name__ == "__main__":
    try:
        print("Starting demo...")
        demonstrate_risk_register_generation()
    except KeyboardInterrupt:
        print("\nDemo interrupted by user.")
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()