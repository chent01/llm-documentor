"""
IEC 62304 Compliance Manager for SOUP components.
Handles automatic safety classification and compliance validation.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

from ..models.soup_models import (
    DetectedSOUPComponent, IEC62304Classification, IEC62304SafetyClass,
    SafetyAssessment, ComplianceValidation, VersionChange
)
from ..models.core import SOUPComponent


class IEC62304ComplianceManager:
    """Manager for IEC 62304 compliance of SOUP components."""
    
    def __init__(self):
        """Initialize compliance manager."""
        self.classification_templates = self._load_classification_templates()
        self.verification_requirements = self._load_verification_requirements()
        self.documentation_templates = self._load_documentation_templates()
    
    def classify_component_automatically(self, component: DetectedSOUPComponent) -> IEC62304Classification:
        """
        Automatically classify a SOUP component according to IEC 62304.
        
        Args:
            component: Detected SOUP component
            
        Returns:
            IEC 62304 classification
        """
        # Determine safety class based on component analysis
        safety_class = self._determine_safety_class(component)
        
        # Generate justification
        justification = self._generate_classification_justification(component, safety_class)
        
        # Generate risk assessment
        risk_assessment = self._generate_risk_assessment(component, safety_class)
        
        # Get requirements for this class
        verification_reqs = self.verification_requirements.get(safety_class.value, [])
        documentation_reqs = self._get_documentation_requirements(safety_class)
        change_control_reqs = self._get_change_control_requirements(safety_class)
        
        return IEC62304Classification(
            safety_class=safety_class,
            justification=justification,
            risk_assessment=risk_assessment,
            verification_requirements=verification_reqs.copy(),
            documentation_requirements=documentation_reqs,
            change_control_requirements=change_control_reqs
        )
    
    def _determine_safety_class(self, component: DetectedSOUPComponent) -> IEC62304SafetyClass:
        """
        Determine safety class based on component characteristics.
        
        Args:
            component: Component to classify
            
        Returns:
            Safety class
        """
        name_lower = component.name.lower()
        
        # Class C (highest risk) - life-supporting or life-sustaining
        class_c_indicators = [
            'database', 'db', 'sql', 'mongo', 'redis',  # Data persistence
            'crypto', 'encryption', 'ssl', 'tls', 'openssl',  # Security/crypto
            'auth', 'authentication', 'oauth', 'jwt',  # Authentication
            'network', 'http', 'https', 'socket', 'tcp',  # Network communication
            'kernel', 'driver', 'system', 'os',  # System-level
            'medical', 'patient', 'clinical', 'device'  # Medical-specific
        ]
        
        # Class B (medium risk) - non-life-supporting but injury possible
        class_b_indicators = [
            'ui', 'gui', 'interface', 'widget', 'qt', 'gtk',  # User interface
            'parser', 'json', 'xml', 'yaml', 'csv',  # Data parsing
            'validation', 'schema', 'format',  # Data validation
            'image', 'graphics', 'render', 'display',  # Graphics/display
            'file', 'io', 'stream', 'buffer',  # File I/O
            'math', 'calculation', 'algorithm'  # Mathematical operations
        ]
        
        # Class A (lowest risk) - no safety impact
        class_a_indicators = [
            'test', 'mock', 'stub', 'fake',  # Testing utilities
            'debug', 'log', 'trace', 'profil',  # Debugging/logging
            'util', 'helper', 'tool', 'common',  # Utilities
            'doc', 'documentation', 'comment',  # Documentation
            'style', 'theme', 'color', 'font'  # Styling/appearance
        ]
        
        # Check for Class C indicators first (highest priority)
        for indicator in class_c_indicators:
            if indicator in name_lower:
                return IEC62304SafetyClass.CLASS_C
        
        # Check for Class A indicators (lowest risk)
        for indicator in class_a_indicators:
            if indicator in name_lower:
                return IEC62304SafetyClass.CLASS_A
        
        # Check for Class B indicators
        for indicator in class_b_indicators:
            if indicator in name_lower:
                return IEC62304SafetyClass.CLASS_B
        
        # Default to Class B for unknown components (conservative approach)
        return IEC62304SafetyClass.CLASS_B
    
    def _generate_classification_justification(self, component: DetectedSOUPComponent, 
                                            safety_class: IEC62304SafetyClass) -> str:
        """Generate justification text for the classification."""
        template = self.classification_templates.get(safety_class.value, {})
        
        base_justification = template.get('justification', 
            f"Component classified as Class {safety_class.value} based on analysis.")
        
        # Add component-specific details
        details = []
        
        if component.description:
            details.append(f"Component description: {component.description}")
        
        if component.package_manager:
            details.append(f"Package manager: {component.package_manager}")
        
        details.append(f"Detection confidence: {component.confidence:.1%}")
        details.append(f"Source file: {component.source_file}")
        
        if details:
            return f"{base_justification}\n\nComponent Details:\n" + "\n".join(f"• {detail}" for detail in details)
        
        return base_justification
    
    def _generate_risk_assessment(self, component: DetectedSOUPComponent, 
                                safety_class: IEC62304SafetyClass) -> str:
        """Generate risk assessment for the component."""
        template = self.classification_templates.get(safety_class.value, {})
        
        risk_template = template.get('risk_assessment', 
            f"Risk assessment for Class {safety_class.value} component.")
        
        # Add specific risks based on component type
        risks = []
        name_lower = component.name.lower()
        
        if any(term in name_lower for term in ['database', 'db', 'sql']):
            risks.append("Data integrity and availability risks")
            risks.append("Potential for data corruption or loss")
        
        if any(term in name_lower for term in ['crypto', 'ssl', 'auth']):
            risks.append("Security vulnerabilities could compromise patient data")
            risks.append("Authentication failures could allow unauthorized access")
        
        if any(term in name_lower for term in ['network', 'http', 'socket']):
            risks.append("Network communication failures could disrupt device operation")
            risks.append("Potential for man-in-the-middle attacks")
        
        if any(term in name_lower for term in ['ui', 'gui', 'interface']):
            risks.append("User interface errors could lead to incorrect operation")
            risks.append("Display issues could cause misinterpretation of data")
        
        if risks:
            return f"{risk_template}\n\nSpecific Risks Identified:\n" + "\n".join(f"• {risk}" for risk in risks)
        
        return risk_template
    
    def _get_documentation_requirements(self, safety_class: IEC62304SafetyClass) -> List[str]:
        """Get documentation requirements for safety class."""
        base_requirements = [
            "SOUP component identification and version",
            "Intended use and functional requirements",
            "Hardware and software requirements",
            "Known anomalies and their impact"
        ]
        
        if safety_class == IEC62304SafetyClass.CLASS_C:
            base_requirements.extend([
                "Detailed safety analysis and risk assessment",
                "Verification and validation evidence",
                "Supplier audit documentation",
                "Change control procedures and history",
                "Security assessment documentation"
            ])
        elif safety_class == IEC62304SafetyClass.CLASS_B:
            base_requirements.extend([
                "Safety analysis and risk assessment",
                "Verification evidence",
                "Change impact analysis",
                "Basic security review"
            ])
        else:  # CLASS_A
            base_requirements.extend([
                "Basic functional verification",
                "Change notification procedures"
            ])
        
        return base_requirements
    
    def _get_change_control_requirements(self, safety_class: IEC62304SafetyClass) -> List[str]:
        """Get change control requirements for safety class."""
        base_requirements = [
            "Version identification and tracking",
            "Change notification to development team"
        ]
        
        if safety_class == IEC62304SafetyClass.CLASS_C:
            base_requirements.extend([
                "Formal change impact analysis required",
                "Safety assessment for all changes",
                "Verification and validation of changes",
                "Regulatory notification if required",
                "Supplier notification and approval"
            ])
        elif safety_class == IEC62304SafetyClass.CLASS_B:
            base_requirements.extend([
                "Change impact analysis required",
                "Safety review for significant changes",
                "Verification of changes",
                "Supplier notification for major changes"
            ])
        else:  # CLASS_A
            base_requirements.extend([
                "Basic change impact assessment",
                "Functional verification of changes"
            ])
        
        return base_requirements
    
    def generate_verification_requirements(self, classification: IEC62304Classification) -> List[str]:
        """
        Generate verification requirements based on safety classification.
        
        Args:
            classification: IEC 62304 classification
            
        Returns:
            List of verification requirements
        """
        safety_class = classification.safety_class
        
        base_requirements = [
            "Verify SOUP component identification and version",
            "Confirm functional requirements are met",
            "Validate integration with medical device software"
        ]
        
        if safety_class == IEC62304SafetyClass.CLASS_C:
            base_requirements.extend([
                "Perform comprehensive testing of all safety-related functions",
                "Conduct security vulnerability assessment",
                "Verify error handling and fault tolerance",
                "Validate data integrity mechanisms",
                "Test failure modes and recovery procedures",
                "Perform stress and boundary testing",
                "Conduct code review or static analysis",
                "Verify supplier quality management system"
            ])
        elif safety_class == IEC62304SafetyClass.CLASS_B:
            base_requirements.extend([
                "Test safety-related functions",
                "Basic security review",
                "Verify error handling",
                "Test integration points",
                "Validate data handling",
                "Review supplier documentation"
            ])
        else:  # CLASS_A
            base_requirements.extend([
                "Basic functional testing",
                "Integration testing",
                "Review supplier documentation"
            ])
        
        return base_requirements
    
    def validate_compliance(self, component: SOUPComponent, 
                          classification: IEC62304Classification) -> ComplianceValidation:
        """
        Validate IEC 62304 compliance for a SOUP component.
        
        Args:
            component: SOUP component to validate
            classification: IEC 62304 classification
            
        Returns:
            Compliance validation result
        """
        missing_requirements = []
        warnings = []
        recommendations = []
        
        # Check required fields
        if not component.name:
            missing_requirements.append("Component name is required")
        
        if not component.version:
            missing_requirements.append("Component version is required")
        
        if not component.usage_reason:
            missing_requirements.append("Usage reason is required")
        
        if not component.safety_justification:
            missing_requirements.append("Safety justification is required")
        
        # Check classification-specific requirements
        safety_class = classification.safety_class
        
        if safety_class == IEC62304SafetyClass.CLASS_C:
            if not component.supplier:
                missing_requirements.append("Supplier information is required for Class C components")
            
            if not component.verification_method:
                missing_requirements.append("Verification method is required for Class C components")
            
            if not component.anomaly_list:
                warnings.append("Known anomalies list is empty - verify if this is correct")
            
            recommendations.extend([
                "Consider conducting supplier audit",
                "Implement comprehensive testing strategy",
                "Establish formal change control procedures"
            ])
        
        elif safety_class == IEC62304SafetyClass.CLASS_B:
            if not component.verification_method:
                warnings.append("Verification method should be specified for Class B components")
            
            recommendations.extend([
                "Consider security review",
                "Implement change impact analysis procedures"
            ])
        
        else:  # CLASS_A
            recommendations.extend([
                "Basic functional testing recommended",
                "Monitor for version changes"
            ])
        
        # General recommendations
        if not component.license:
            warnings.append("License information not specified")
        
        if not component.website:
            recommendations.append("Consider adding component website/documentation link")
        
        is_compliant = len(missing_requirements) == 0
        
        return ComplianceValidation(
            component_id=component.id,
            is_compliant=is_compliant,
            validation_date=datetime.now(),
            missing_requirements=missing_requirements,
            warnings=warnings,
            recommendations=recommendations,
            validator="IEC62304ComplianceManager"
        )
    
    def _load_classification_templates(self) -> Dict[str, Dict[str, str]]:
        """Load classification templates."""
        return {
            "A": {
                "justification": "Component classified as Class A - no safety impact. "
                              "Failure or malfunction of this component cannot result in death, "
                              "serious injury, or damage to health, either to patients, operators, or other persons.",
                "risk_assessment": "Risk assessment indicates no safety impact from component failure. "
                                 "Component operates in non-safety-related functions only."
            },
            "B": {
                "justification": "Component classified as Class B - non-life-supporting with injury possible. "
                              "Failure or malfunction of this component cannot result in death or serious injury, "
                              "but may result in non-serious injury to patients, operators, or other persons.",
                "risk_assessment": "Risk assessment indicates potential for non-serious injury from component failure. "
                                 "Component may affect device functionality but not life-supporting functions."
            },
            "C": {
                "justification": "Component classified as Class C - life-supporting or life-sustaining. "
                              "Failure or malfunction of this component can result in death or serious injury "
                              "to patients, operators, or other persons.",
                "risk_assessment": "Risk assessment indicates potential for death or serious injury from component failure. "
                                 "Component is critical to device safety and requires comprehensive verification."
            }
        }
    
    def _load_verification_requirements(self) -> Dict[str, List[str]]:
        """Load verification requirements by safety class."""
        return {
            "A": [
                "Basic functional testing",
                "Integration testing",
                "Documentation review"
            ],
            "B": [
                "Functional testing of safety-related features",
                "Integration testing",
                "Basic security review",
                "Error handling verification",
                "Documentation review"
            ],
            "C": [
                "Comprehensive testing of all safety-related functions",
                "Security vulnerability assessment",
                "Error handling and fault tolerance verification",
                "Data integrity validation",
                "Failure mode testing",
                "Stress and boundary testing",
                "Code review or static analysis",
                "Supplier quality system verification"
            ]
        }
    
    def _load_documentation_templates(self) -> Dict[str, str]:
        """Load documentation templates."""
        return {
            "soup_list": """
# SOUP Component List

## Component Information
- **Name**: {name}
- **Version**: {version}
- **Supplier**: {supplier}
- **License**: {license}

## Classification
- **Safety Class**: {safety_class}
- **Justification**: {justification}

## Usage
- **Intended Use**: {usage_reason}
- **Safety Justification**: {safety_justification}

## Verification
- **Verification Method**: {verification_method}
- **Known Anomalies**: {anomalies}

## Risk Assessment
{risk_assessment}
""",
            "change_control": """
# SOUP Change Control Record

## Component: {name}
- **Previous Version**: {old_version}
- **New Version**: {new_version}
- **Change Date**: {change_date}

## Impact Analysis
{impact_analysis}

## Verification Required
{verification_requirements}

## Approval Status
- **Status**: {approval_status}
- **Approver**: {approver}
- **Approval Date**: {approval_date}
"""
        }