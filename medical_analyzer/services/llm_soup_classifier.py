"""
LLM-based SOUP (Software of Unknown Provenance) classification service.
Replaces keyword-based classification with intelligent LLM analysis.
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..models.soup_models import (
    DetectedSOUPComponent, IEC62304SafetyClass, IEC62304Classification
)
from ..llm.backend import LLMBackend
from ..llm.config import LLMConfig, load_config
from ..llm.operation_configs import get_operation_params
from ..llm.response_handler import get_response_handler, ResponseFormat


@dataclass
class SOUPAnalysisContext:
    """Context information for SOUP component analysis."""
    component: DetectedSOUPComponent
    project_type: Optional[str] = None  # e.g., "medical_device", "web_app", "embedded"
    safety_critical: bool = True
    additional_context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_context is None:
            self.additional_context = {}


class LLMSOUPClassifier:
    """LLM-based SOUP component classifier for IEC 62304 compliance."""
    
    def __init__(self, llm_backend: Optional[LLMBackend] = None, config: Optional[LLMConfig] = None):
        """
        Initialize LLM SOUP classifier.
        
        Args:
            llm_backend: Optional LLM backend instance
            config: Optional LLM configuration
        """
        self.config = config or load_config()
        self.llm_backend = llm_backend
        
        # Classification prompts
        self.classification_prompt_template = """
You are a medical device software safety expert specializing in IEC 62304 compliance.
Your task is to classify SOUP (Software of Unknown Provenance) components according to IEC 62304 safety classes.

IEC 62304 Safety Classes:
- Class A: Software that cannot contribute to a hazardous situation
- Class B: Software that can contribute to a non-life-threatening hazardous situation  
- Class C: Software that can contribute to a life-threatening hazardous situation

Component Information:
Name: {component_name}
Version: {component_version}
Description: {component_description}
License: {component_license}
Package Manager: {package_manager}
Dependencies: {dependencies}
Metadata: {metadata}

Project Context:
Type: {project_type}
Safety Critical: {safety_critical}
Additional Context: {additional_context}

Please analyze this SOUP component and provide:
1. IEC 62304 Safety Classification (A, B, or C)
2. Detailed justification for the classification
3. Risk assessment considering potential failure modes
4. Specific verification requirements
5. Documentation requirements
6. Change control requirements

Respond in JSON format:
{{
    "safety_class": "A|B|C",
    "justification": "detailed explanation of why this classification was chosen",
    "risk_assessment": "analysis of potential risks and failure modes",
    "verification_requirements": ["requirement1", "requirement2", ...],
    "documentation_requirements": ["requirement1", "requirement2", ...],
    "change_control_requirements": ["requirement1", "requirement2", ...],
    "confidence_score": 0.0-1.0,
    "key_risk_factors": ["factor1", "factor2", ...],
    "mitigation_recommendations": ["recommendation1", "recommendation2", ...]
}}
"""

        self.safety_impact_prompt_template = """
You are a medical device software safety expert. Analyze the safety impact of this SOUP component.

Component: {component_name} v{component_version}
Classification: {safety_class}
Description: {component_description}

Analyze the potential safety impact considering:
1. How this component could fail
2. What systems it interacts with
3. Potential cascading failures
4. Patient safety implications
5. Data integrity risks
6. Security vulnerabilities

Respond in JSON format:
{{
    "failure_modes": ["mode1", "mode2", ...],
    "safety_implications": ["implication1", "implication2", ...],
    "affected_systems": ["system1", "system2", ...],
    "severity_assessment": "low|medium|high|critical",
    "probability_assessment": "rare|unlikely|possible|likely|certain",
    "risk_level": "low|medium|high|critical",
    "immediate_actions": ["action1", "action2", ...],
    "monitoring_requirements": ["requirement1", "requirement2", ...]
}}
"""

    def classify_component(self, component: DetectedSOUPComponent, 
                         context: Optional[SOUPAnalysisContext] = None) -> IEC62304Classification:
        """
        Classify a SOUP component using LLM analysis.
        
        Args:
            component: Detected SOUP component to classify
            context: Optional analysis context
            
        Returns:
            IEC 62304 classification with detailed analysis
            
        Raises:
            ValueError: If classification fails or is invalid
        """
        if context is None:
            context = SOUPAnalysisContext(component=component)
        
        # Prepare prompt with component information
        prompt = self._prepare_classification_prompt(component, context)
        
        try:
            # Get LLM backend if not provided
            if self.llm_backend is None:
                self.llm_backend = self._get_available_backend()
            
            # Generate classification using LLM
            params = get_operation_params("soup_classification")
            response = self.llm_backend.generate(
                prompt=prompt,
                system_prompt="You are a medical device software safety expert specializing in IEC 62304 compliance.",
                **params
            )
            
            # Parse LLM response
            classification_data = self._parse_classification_response(response)
            
            # Create IEC62304Classification object
            classification = IEC62304Classification(
                safety_class=IEC62304SafetyClass(classification_data["safety_class"]),
                justification=classification_data["justification"],
                risk_assessment=classification_data["risk_assessment"],
                verification_requirements=classification_data.get("verification_requirements", []),
                documentation_requirements=classification_data.get("documentation_requirements", []),
                change_control_requirements=classification_data.get("change_control_requirements", [])
            )
            
            # Add additional metadata
            classification.metadata = {
                "confidence_score": classification_data.get("confidence_score", 0.8),
                "key_risk_factors": classification_data.get("key_risk_factors", []),
                "mitigation_recommendations": classification_data.get("mitigation_recommendations", []),
                "llm_backend": self.llm_backend.__class__.__name__,
                "analysis_method": "llm_based"
            }
            
            return classification
            
        except Exception as e:
            # Fallback to rule-based classification if LLM fails
            return self._fallback_classification(component, context, str(e))
    
    def analyze_safety_impact(self, component: DetectedSOUPComponent, 
                            classification: IEC62304Classification) -> Dict[str, Any]:
        """
        Analyze detailed safety impact of a SOUP component.
        
        Args:
            component: SOUP component to analyze
            classification: Existing classification
            
        Returns:
            Detailed safety impact analysis
        """
        prompt = self.safety_impact_prompt_template.format(
            component_name=component.name,
            component_version=component.version,
            safety_class=classification.safety_class.value,
            component_description=component.description or "No description available"
        )
        
        try:
            if self.llm_backend is None:
                self.llm_backend = self._get_available_backend()
            
            params = get_operation_params("soup_risk_assessment")
            response = self.llm_backend.generate(
                prompt=prompt,
                system_prompt="You are a medical device safety analyst.",
                **params
            )
            
            return self._parse_safety_impact_response(response)
            
        except Exception as e:
            # Return basic safety impact analysis as fallback
            return self._fallback_safety_impact(component, classification)
    
    def batch_classify_components(self, components: List[DetectedSOUPComponent],
                                context: Optional[SOUPAnalysisContext] = None) -> List[IEC62304Classification]:
        """
        Classify multiple SOUP components efficiently.
        
        Args:
            components: List of components to classify
            context: Optional shared analysis context
            
        Returns:
            List of classifications in the same order as input
        """
        classifications = []
        
        for component in components:
            try:
                classification = self.classify_component(component, context)
                classifications.append(classification)
            except Exception as e:
                # Use fallback for failed classifications
                fallback_classification = self._fallback_classification(component, context, str(e))
                classifications.append(fallback_classification)
        
        return classifications
    
    def _prepare_classification_prompt(self, component: DetectedSOUPComponent, 
                                     context: SOUPAnalysisContext) -> str:
        """Prepare the classification prompt with component data."""
        return self.classification_prompt_template.format(
            component_name=component.name,
            component_version=component.version,
            component_description=component.description or "No description available",
            component_license=component.license or "Unknown",
            package_manager=component.package_manager or "Unknown",
            dependencies=", ".join(component.dependencies) if component.dependencies else "None listed",
            metadata=json.dumps(component.metadata, indent=2) if component.metadata else "{}",
            project_type=context.project_type or "medical_device",
            safety_critical=context.safety_critical,
            additional_context=json.dumps(context.additional_context, indent=2)
        )
    
    def _parse_classification_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM classification response."""
        try:
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                
                # Validate required fields
                if "safety_class" not in data:
                    raise ValueError("Missing safety_class in response")
                
                if data["safety_class"] not in ["A", "B", "C"]:
                    raise ValueError(f"Invalid safety class: {data['safety_class']}")
                
                return data
            else:
                raise ValueError("No valid JSON found in response")
                
        except (json.JSONDecodeError, ValueError) as e:
            # Try to extract safety class from text response
            response_lower = response.lower()
            if "class c" in response_lower or "safety class c" in response_lower:
                safety_class = "C"
            elif "class b" in response_lower or "safety class b" in response_lower:
                safety_class = "B"
            elif "class a" in response_lower or "safety class a" in response_lower:
                safety_class = "A"
            else:
                safety_class = "B"  # Default to medium risk
            
            return {
                "safety_class": safety_class,
                "justification": f"Extracted from LLM response: {response[:200]}...",
                "risk_assessment": "Unable to parse detailed risk assessment from LLM response",
                "verification_requirements": ["Manual review required due to parsing error"],
                "documentation_requirements": ["Document classification rationale"],
                "change_control_requirements": ["Standard change control process"],
                "confidence_score": 0.5
            }
    
    def _parse_safety_impact_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM safety impact response."""
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                raise ValueError("No valid JSON found in response")
                
        except (json.JSONDecodeError, ValueError):
            return {
                "failure_modes": ["Component malfunction", "Integration failure"],
                "safety_implications": ["Potential system degradation"],
                "affected_systems": ["Unknown - requires manual analysis"],
                "severity_assessment": "medium",
                "probability_assessment": "possible",
                "risk_level": "medium",
                "immediate_actions": ["Manual safety review required"],
                "monitoring_requirements": ["Regular component monitoring"]
            }
    
    def _get_available_backend(self) -> LLMBackend:
        """Get an available LLM backend."""
        from ..llm.backend import LLMBackend
        
        # Try to get backend from config
        enabled_backends = self.config.get_enabled_backends()
        
        for backend_config in enabled_backends:
            try:
                backend = LLMBackend.create_from_config(backend_config.config)
                if backend.is_available():
                    return backend
            except Exception:
                continue
        
        # Fallback to mock backend
        from ..llm.backend import FallbackLLMBackend
        return FallbackLLMBackend({})
    
    def _fallback_classification(self, component: DetectedSOUPComponent, 
                               context: Optional[SOUPAnalysisContext], 
                               error_msg: str) -> IEC62304Classification:
        """Provide fallback rule-based classification when LLM fails."""
        # Simple rule-based classification as fallback
        name_lower = component.name.lower()
        
        # High-risk patterns (Class C)
        high_risk_patterns = [
            'crypto', 'security', 'ssl', 'tls', 'auth', 'database', 'sql',
            'network', 'server', 'kernel', 'driver', 'firmware'
        ]
        
        # Medium-risk patterns (Class B)  
        medium_risk_patterns = [
            'ui', 'gui', 'parser', 'json', 'xml', 'http', 'api', 'client',
            'framework', 'library', 'runtime'
        ]
        
        # Determine classification
        if any(pattern in name_lower for pattern in high_risk_patterns):
            safety_class = IEC62304SafetyClass.CLASS_C
            justification = f"Component '{component.name}' contains high-risk patterns. Fallback classification due to LLM error: {error_msg}"
        elif any(pattern in name_lower for pattern in medium_risk_patterns):
            safety_class = IEC62304SafetyClass.CLASS_B
            justification = f"Component '{component.name}' contains medium-risk patterns. Fallback classification due to LLM error: {error_msg}"
        else:
            safety_class = IEC62304SafetyClass.CLASS_B  # Default to medium risk
            justification = f"Default medium-risk classification for '{component.name}'. Fallback classification due to LLM error: {error_msg}"
        
        return IEC62304Classification(
            safety_class=safety_class,
            justification=justification,
            risk_assessment="Automated rule-based assessment - manual review recommended",
            verification_requirements=["Manual safety review required", "LLM analysis failed"],
            documentation_requirements=["Document fallback classification rationale"],
            change_control_requirements=["Standard change control with additional review"]
        )
    
    def _fallback_safety_impact(self, component: DetectedSOUPComponent, 
                              classification: IEC62304Classification) -> Dict[str, Any]:
        """Provide fallback safety impact analysis."""
        if classification.safety_class == IEC62304SafetyClass.CLASS_C:
            return {
                "failure_modes": ["Critical component failure", "Security vulnerability exploitation"],
                "safety_implications": ["Potential patient harm", "Life-threatening malfunction"],
                "affected_systems": ["Safety-critical systems", "Life support functions"],
                "severity_assessment": "critical",
                "probability_assessment": "possible",
                "risk_level": "high",
                "immediate_actions": ["Immediate safety review", "Consider component replacement"],
                "monitoring_requirements": ["Continuous monitoring", "Regular security updates"]
            }
        elif classification.safety_class == IEC62304SafetyClass.CLASS_B:
            return {
                "failure_modes": ["Component malfunction", "Data corruption"],
                "safety_implications": ["Non-life-threatening injury possible", "System degradation"],
                "affected_systems": ["Non-critical systems", "User interface"],
                "severity_assessment": "medium",
                "probability_assessment": "possible",
                "risk_level": "medium",
                "immediate_actions": ["Safety review recommended", "Testing verification"],
                "monitoring_requirements": ["Regular monitoring", "Update tracking"]
            }
        else:  # CLASS_A
            return {
                "failure_modes": ["Minor malfunction", "Performance degradation"],
                "safety_implications": ["No safety impact", "Functionality impact only"],
                "affected_systems": ["Non-safety systems", "Development tools"],
                "severity_assessment": "low",
                "probability_assessment": "possible",
                "risk_level": "low",
                "immediate_actions": ["Standard review process"],
                "monitoring_requirements": ["Basic monitoring", "Version tracking"]
            }