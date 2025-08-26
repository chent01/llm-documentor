"""
Hazard identification service.

This module handles the identification of potential hazards from Software Requirements
following ISO 14971 risk management principles for medical device software.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.core import Requirement, RiskItem
from ..models.enums import Severity, Probability, RiskLevel
from ..llm.backend import LLMBackend, LLMError
from ..models.result_models import HazardIdentificationResult
from .llm_response_parser import LLMResponseParser


class HazardIdentifier:
    """Service for identifying hazards from Software Requirements."""
    
    def __init__(self, llm_backend: LLMBackend):
        """
        Initialize the hazard identifier.
        
        Args:
            llm_backend: LLM backend for analysis
        """
        self.llm_backend = llm_backend
        self.risk_counter = 0
        
        # Hazard identification prompts
        self.system_prompt = """You are an expert risk analyst specializing in medical device software safety. Your task is to identify potential hazards from Software Requirements following ISO 14971 risk management principles. Focus on hazards that could lead to harm to patients, users, or other persons.

For each hazard you identify, provide:
1. A clear description of the hazard (what could go wrong)
2. The potential cause of the hazard (why it might occur)
3. The potential effect or harm that could result
4. An initial severity assessment (Catastrophic, Serious, Minor, Negligible)
5. An initial probability assessment (High, Medium, Low, Remote)
6. A confidence score (0.0 to 1.0) based on how certain you are about this hazard

Consider these types of medical device hazards:
- Energy hazards (electrical, thermal, mechanical)
- Biological and chemical hazards
- Environmental hazards
- Hazards related to use or misuse
- Functional failure hazards
- Information/data hazards
- Software malfunction hazards

Respond in JSON format with an array of hazards."""
        
        self.prompt_template = """Identify potential hazards from the following Software Requirements for a medical device:

Project Context: {project_description}

Software Requirements to analyze:
{requirements_list}

For each Software Requirement, identify potential hazards that could occur if:
- The requirement is not properly implemented
- The requirement fails during operation
- The requirement is misused or misunderstood
- The requirement interacts poorly with other system components

Consider the medical device context and potential harm to:
- Patients receiving treatment
- Healthcare providers using the device
- Other persons in the environment
- The device itself (if failure could lead to subsequent harm)

Respond with a JSON array of hazards in this format:
[
  {{
    "hazard": "Clear description of what could go wrong",
    "cause": "Specific cause or failure mode that could lead to this hazard",
    "effect": "Potential harm or consequence that could result",
    "severity": "Catastrophic|Serious|Minor|Negligible",
    "probability": "High|Medium|Low|Remote",
    "confidence": 0.85,
    "related_requirement_id": "SR_XXXX"
  }}
]

Focus on realistic hazards that are relevant to medical device safety. If no clear hazards can be identified for a requirement, omit it from the response. Return an empty array if no hazards are found."""
    
    def identify_hazards(self, software_requirements: List[Requirement], project_description: str = "") -> HazardIdentificationResult:
        """
        Identify potential hazards from Software Requirements.
        
        Args:
            software_requirements: List of Software Requirements to analyze
            project_description: Description of the project context
            
        Returns:
            HazardIdentificationResult with identified hazards and metadata
        """
        start_time = datetime.now()
        all_risk_items = []
        errors = []
        requirements_processed = 0
        
        if not software_requirements:
            return HazardIdentificationResult(
                risk_items=[],
                confidence_score=0.0,
                processing_time=0.0,
                requirements_processed=0,
                errors=[],
                metadata={'total_requirements': 0, 'identification_method': 'none'}
            )
        
        try:
            # Process requirements in batches for better context
            batch_size = 3
            for i in range(0, len(software_requirements), batch_size):
                batch = software_requirements[i:i + batch_size]
                try:
                    risk_items = self._identify_hazards_for_batch(batch, project_description)
                    all_risk_items.extend(risk_items)
                    requirements_processed += len(batch)
                except Exception as e:
                    error_msg = f"Error identifying hazards for batch {i//batch_size + 1}: {str(e)}"
                    errors.append(error_msg)
                    continue
        
        except Exception as e:
            error_msg = f"Error in hazard identification pipeline: {str(e)}"
            errors.append(error_msg)
        
        # Calculate overall confidence score
        if all_risk_items:
            overall_confidence = sum(r.metadata.get('confidence', 0.5) for r in all_risk_items) / len(all_risk_items)
        else:
            overall_confidence = 0.0
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return HazardIdentificationResult(
            risk_items=all_risk_items,
            confidence_score=overall_confidence,
            processing_time=processing_time,
            requirements_processed=requirements_processed,
            errors=errors,
            metadata={
                'total_requirements': len(software_requirements),
                'successful_requirements': requirements_processed,
                'failed_requirements': len(software_requirements) - requirements_processed,
                'hazards_per_requirement': len(all_risk_items) / max(requirements_processed, 1),
                'llm_backend': self.llm_backend.__class__.__name__,
                'identification_method': 'llm'
            }
        )
    
    def _identify_hazards_for_batch(self, requirements: List[Requirement], project_description: str) -> List[RiskItem]:
        """Identify hazards for a batch of Software Requirements."""
        # Prepare requirements list for prompt
        req_list = []
        for req in requirements:
            criteria_text = '; '.join(req.acceptance_criteria[:2])  # Limit criteria for brevity
            req_list.append(f"- {req.id}: {req.text}")
            if criteria_text:
                req_list.append(f"  Acceptance Criteria: {criteria_text}")
        
        req_text = "\n".join(req_list)
        
        prompt = self.prompt_template.format(
            project_description=project_description or "Medical device software project",
            requirements_list=req_text
        )
        
        try:
            # Generate response using LLM
            response = self.llm_backend.generate(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=0.1,
                max_tokens=2000
            )
            
            # Parse JSON response
            hazards_data = LLMResponseParser.parse_json_response(response)
            
            # Convert to RiskItem objects
            risk_items = []
            for hazard_data in hazards_data:
                risk_item = self._create_risk_item_from_data(hazard_data, requirements)
                if risk_item:
                    risk_items.append(risk_item)
            
            return risk_items
            
        except LLMError as e:
            if not e.recoverable:
                raise
            # Try fallback hazard identification for recoverable errors
            return self._fallback_hazard_identification(requirements)
        except Exception as e:
            raise Exception(f"Hazard identification failed: {str(e)}")
    
    def _create_risk_item_from_data(self, hazard_data: Dict[str, Any], requirements: List[Requirement]) -> Optional[RiskItem]:
        """Create a RiskItem object from parsed hazard data."""
        try:
            # Validate required fields
            required_fields = ['hazard', 'cause', 'effect', 'severity', 'probability']
            if not LLMResponseParser.validate_required_fields(hazard_data, required_fields):
                return None
            
            hazard = hazard_data['hazard'].strip()
            cause = hazard_data['cause'].strip()
            effect = hazard_data['effect'].strip()
            
            # Parse severity and probability
            severity = self._parse_severity(hazard_data['severity'])
            probability = self._parse_probability(hazard_data['probability'])
            
            # Calculate risk level
            risk_level = self._calculate_risk_level(severity, probability)
            
            # Parse confidence
            confidence = LLMResponseParser.clamp_confidence(hazard_data.get('confidence', 0.5))
            
            # Find related requirement
            related_req_id = hazard_data.get('related_requirement_id', '')
            related_requirements = []
            for req in requirements:
                if req.id == related_req_id or related_req_id in req.id:
                    related_requirements.append(req.id)
                    break
            
            # If no specific requirement found, relate to all requirements in batch
            if not related_requirements:
                related_requirements = [req.id for req in requirements]
            
            # Generate unique risk ID
            self.risk_counter += 1
            risk_id = f"RISK_{self.risk_counter:04d}"
            
            # Generate mitigation and verification strategies
            mitigation = self._generate_mitigation_strategy(hazard, cause, effect, severity)
            verification = self._generate_verification_method(hazard, mitigation, severity)
            
            return RiskItem(
                id=risk_id,
                hazard=hazard,
                cause=cause,
                effect=effect,
                severity=severity,
                probability=probability,
                risk_level=risk_level,
                mitigation=mitigation,
                verification=verification,
                related_requirements=related_requirements,
                metadata={
                    'confidence': confidence,
                    'identification_method': 'llm',
                    'source_requirements': len(requirements),
                    'risk_score': self._calculate_risk_score(severity, probability)
                }
            )
            
        except (ValueError, KeyError, TypeError):
            return None
    
    def _parse_severity(self, severity_str: str) -> Severity:
        """Parse severity from string."""
        severity_str = severity_str.strip().upper()
        severity_mapping = {
            'CATASTROPHIC': Severity.CATASTROPHIC,
            'SERIOUS': Severity.SERIOUS,
            'MINOR': Severity.MINOR,
            'NEGLIGIBLE': Severity.NEGLIGIBLE
        }
        return severity_mapping.get(severity_str, Severity.MINOR)
    
    def _parse_probability(self, probability_str: str) -> Probability:
        """Parse probability from string."""
        probability_str = probability_str.strip().upper()
        probability_mapping = {
            'HIGH': Probability.HIGH,
            'MEDIUM': Probability.MEDIUM,
            'LOW': Probability.LOW,
            'REMOTE': Probability.REMOTE
        }
        return probability_mapping.get(probability_str, Probability.LOW)
    
    def _calculate_risk_level(self, severity: Severity, probability: Probability) -> RiskLevel:
        """
        Calculate risk level from severity and probability using ISO 14971 risk matrix.
        
        Risk Matrix:
        - Catastrophic + High/Medium = Unacceptable
        - Catastrophic + Low/Remote = Undesirable
        - Serious + High = Unacceptable
        - Serious + Medium = Undesirable
        - Serious + Low/Remote = Acceptable
        - Minor + High/Medium = Undesirable
        - Minor + Low/Remote = Acceptable
        - Negligible + Any = Negligible
        """
        if severity == Severity.NEGLIGIBLE:
            return RiskLevel.NEGLIGIBLE
        
        if severity == Severity.CATASTROPHIC:
            if probability in [Probability.HIGH, Probability.MEDIUM]:
                return RiskLevel.UNACCEPTABLE
            else:
                return RiskLevel.UNDESIRABLE
        
        if severity == Severity.SERIOUS:
            if probability == Probability.HIGH:
                return RiskLevel.UNACCEPTABLE
            elif probability == Probability.MEDIUM:
                return RiskLevel.UNDESIRABLE
            else:
                return RiskLevel.ACCEPTABLE
        
        if severity == Severity.MINOR:
            if probability in [Probability.HIGH, Probability.MEDIUM]:
                return RiskLevel.UNDESIRABLE
            else:
                return RiskLevel.ACCEPTABLE
        
        return RiskLevel.ACCEPTABLE
    
    def _calculate_risk_score(self, severity: Severity, probability: Probability) -> int:
        """Calculate numerical risk score for sorting and analysis."""
        severity_scores = {
            Severity.CATASTROPHIC: 4,
            Severity.SERIOUS: 3,
            Severity.MINOR: 2,
            Severity.NEGLIGIBLE: 1
        }
        
        probability_scores = {
            Probability.HIGH: 4,
            Probability.MEDIUM: 3,
            Probability.LOW: 2,
            Probability.REMOTE: 1
        }
        
        return severity_scores[severity] * probability_scores[probability]
    
    def _generate_mitigation_strategy(self, hazard: str, cause: str, effect: str, severity: Severity) -> str:
        """Generate mitigation strategy based on hazard characteristics."""
        # Template-based mitigation strategies
        if 'software' in hazard.lower() or 'algorithm' in hazard.lower():
            if severity in [Severity.CATASTROPHIC, Severity.SERIOUS]:
                return f"Implement redundant validation and error checking for {cause.lower()}. Add comprehensive testing and code review processes."
            else:
                return f"Add input validation and error handling for {cause.lower()}. Implement appropriate user feedback mechanisms."
        
        if 'data' in hazard.lower() or 'information' in hazard.lower():
            return f"Implement data integrity checks and validation for {cause.lower()}. Add data backup and recovery mechanisms."
        
        if 'user' in hazard.lower() or 'interface' in hazard.lower():
            return f"Improve user interface design and add confirmation dialogs for {cause.lower()}. Provide clear user guidance and training."
        
        if 'communication' in hazard.lower() or 'network' in hazard.lower():
            return f"Implement communication error detection and recovery for {cause.lower()}. Add timeout and retry mechanisms."
        
        # Generic mitigation
        if severity in [Severity.CATASTROPHIC, Severity.SERIOUS]:
            return f"Implement comprehensive safety measures to prevent {cause.lower()}. Add monitoring and automatic shutdown capabilities."
        else:
            return f"Add appropriate controls and monitoring to mitigate {cause.lower()}. Implement user notification and guidance."
    
    def _generate_verification_method(self, hazard: str, mitigation: str, severity: Severity) -> str:
        """Generate verification method for the mitigation strategy."""
        if severity in [Severity.CATASTROPHIC, Severity.SERIOUS]:
            methods = [
                "Comprehensive testing including unit, integration, and system tests",
                "Independent verification and validation (V&V)",
                "Formal code review and static analysis",
                "Risk-based testing with failure mode analysis"
            ]
        else:
            methods = [
                "Unit testing and integration testing",
                "Code review and peer inspection",
                "User acceptance testing",
                "Functional testing and validation"
            ]
        
        # Select appropriate method based on hazard type
        if 'software' in hazard.lower():
            return methods[0] + ". " + methods[2]
        elif 'data' in hazard.lower():
            return methods[0] + ". Data validation testing and integrity checks."
        elif 'user' in hazard.lower():
            return methods[-1] + ". Usability testing and user training validation."
        else:
            return methods[0]
    
    def _fallback_hazard_identification(self, requirements: List[Requirement]) -> List[RiskItem]:
        """Fallback hazard identification using heuristics."""
        risk_items = []
        
        # Heuristic-based hazard identification
        hazard_patterns = [
            {
                'keywords': ['data', 'input', 'validation', 'process'],
                'hazard': 'Incorrect data processing',
                'cause': 'Invalid input data or processing errors',
                'effect': 'Incorrect results leading to potential misdiagnosis or treatment errors',
                'severity': Severity.SERIOUS,
                'probability': Probability.MEDIUM
            },
            {
                'keywords': ['user', 'interface', 'display', 'output'],
                'hazard': 'Misleading user interface',
                'cause': 'Unclear or incorrect information display',
                'effect': 'User confusion leading to incorrect device operation',
                'severity': Severity.MINOR,
                'probability': Probability.LOW
            },
            {
                'keywords': ['communication', 'network', 'connection', 'transfer'],
                'hazard': 'Communication failure',
                'cause': 'Network interruption or data transmission errors',
                'effect': 'Loss of critical information or device malfunction',
                'severity': Severity.SERIOUS,
                'probability': Probability.LOW
            },
            {
                'keywords': ['storage', 'save', 'database', 'file'],
                'hazard': 'Data loss or corruption',
                'cause': 'Storage system failure or data corruption',
                'effect': 'Loss of patient data or treatment history',
                'severity': Severity.SERIOUS,
                'probability': Probability.LOW
            },
            {
                'keywords': ['algorithm', 'calculation', 'compute', 'analysis'],
                'hazard': 'Algorithmic error',
                'cause': 'Incorrect algorithm implementation or calculation errors',
                'effect': 'Incorrect analysis results affecting patient care',
                'severity': Severity.SERIOUS,
                'probability': Probability.MEDIUM
            }
        ]
        
        for req in requirements:
            req_text_lower = req.text.lower()
            
            for pattern in hazard_patterns:
                if any(keyword in req_text_lower for keyword in pattern['keywords']):
                    self.risk_counter += 1
                    risk_id = f"RISK_{self.risk_counter:04d}"
                    
                    risk_level = self._calculate_risk_level(pattern['severity'], pattern['probability'])
                    mitigation = self._generate_mitigation_strategy(
                        pattern['hazard'], pattern['cause'], pattern['effect'], pattern['severity']
                    )
                    verification = self._generate_verification_method(
                        pattern['hazard'], mitigation, pattern['severity']
                    )
                    
                    risk_item = RiskItem(
                        id=risk_id,
                        hazard=pattern['hazard'],
                        cause=pattern['cause'],
                        effect=pattern['effect'],
                        severity=pattern['severity'],
                        probability=pattern['probability'],
                        risk_level=risk_level,
                        mitigation=mitigation,
                        verification=verification,
                        related_requirements=[req.id],
                        metadata={
                            'confidence': 0.3,  # Lower confidence for heuristic-based
                            'identification_method': 'heuristic',
                            'matched_keywords': [kw for kw in pattern['keywords'] if kw in req_text_lower],
                            'source_requirements': 1,
                            'risk_score': self._calculate_risk_score(pattern['severity'], pattern['probability'])
                        }
                    )
                    
                    risk_items.append(risk_item)
                    break  # Only match first pattern per requirement
        
        return risk_items
    
    def get_statistics(self, risk_items: List[RiskItem]) -> Dict[str, Any]:
        """
        Get statistics about identified risks.
        
        Args:
            risk_items: List of identified risk items
            
        Returns:
            Dictionary with risk statistics
        """
        if not risk_items:
            return {
                'total_risks': 0,
                'average_confidence': 0.0,
                'severity_distribution': {},
                'probability_distribution': {},
                'risk_level_distribution': {},
                'high_risk_count': 0,
                'medium_risk_count': 0,
                'low_risk_count': 0
            }
        
        # Calculate confidence statistics
        confidences = [r.metadata.get('confidence', 0.5) for r in risk_items]
        avg_confidence = sum(confidences) / len(confidences)
        
        # Count by severity
        severity_dist = {}
        for risk in risk_items:
            sev_name = risk.severity.value
            severity_dist[sev_name] = severity_dist.get(sev_name, 0) + 1
        
        # Count by probability
        probability_dist = {}
        for risk in risk_items:
            prob_name = risk.probability.value
            probability_dist[prob_name] = probability_dist.get(prob_name, 0) + 1
        
        # Count by risk level
        risk_level_dist = {}
        for risk in risk_items:
            level_name = risk.risk_level.value
            risk_level_dist[level_name] = risk_level_dist.get(level_name, 0) + 1
        
        # Count by risk categories
        high_risk = sum(1 for r in risk_items if r.risk_level in [RiskLevel.UNACCEPTABLE])
        medium_risk = sum(1 for r in risk_items if r.risk_level in [RiskLevel.UNDESIRABLE])
        low_risk = sum(1 for r in risk_items if r.risk_level in [RiskLevel.ACCEPTABLE, RiskLevel.NEGLIGIBLE])
        
        return {
            'total_risks': len(risk_items),
            'average_confidence': avg_confidence,
            'max_confidence': max(confidences),
            'min_confidence': min(confidences),
            'severity_distribution': severity_dist,
            'probability_distribution': probability_dist,
            'risk_level_distribution': risk_level_dist,
            'high_risk_count': high_risk,
            'medium_risk_count': medium_risk,
            'low_risk_count': low_risk,
            'identification_methods': self._count_identification_methods(risk_items),
            'average_risk_score': sum(r.metadata.get('risk_score', 0) for r in risk_items) / len(risk_items)
        }
    
    def _count_identification_methods(self, risk_items: List[RiskItem]) -> Dict[str, int]:
        """Count risks by identification method."""
        methods = {}
        for risk in risk_items:
            method = risk.metadata.get('identification_method', 'unknown')
            methods[method] = methods.get(method, 0) + 1
        return methods
    
    def filter_by_level(self, risk_items: List[RiskItem], min_level: RiskLevel) -> List[RiskItem]:
        """
        Filter risks by minimum risk level.
        
        Args:
            risk_items: List of risk items to filter
            min_level: Minimum risk level to include
            
        Returns:
            Filtered list of risk items
        """
        level_order = {
            RiskLevel.NEGLIGIBLE: 1,
            RiskLevel.ACCEPTABLE: 2,
            RiskLevel.UNDESIRABLE: 3,
            RiskLevel.UNACCEPTABLE: 4
        }
        
        min_order = level_order[min_level]
        return [r for r in risk_items if level_order[r.risk_level] >= min_order]
    
    def group_by_severity(self, risk_items: List[RiskItem]) -> Dict[Severity, List[RiskItem]]:
        """
        Group risks by severity level.
        
        Args:
            risk_items: List of risk items to group
            
        Returns:
            Dictionary mapping severity levels to risk lists
        """
        grouped = {}
        for risk in risk_items:
            severity = risk.severity
            if severity not in grouped:
                grouped[severity] = []
            grouped[severity].append(risk)
        return grouped