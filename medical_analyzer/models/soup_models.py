"""
Enhanced SOUP (Software of Unknown Provenance) models for IEC 62304 compliance.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class IEC62304SafetyClass(Enum):
    """IEC 62304 Safety Classification."""
    CLASS_A = "A"  # Non-life-supporting, non-injury possible
    CLASS_B = "B"  # Non-life-supporting, injury possible
    CLASS_C = "C"  # Life-supporting or life-sustaining


class DetectionMethod(Enum):
    """Methods used to detect SOUP components."""
    PACKAGE_JSON = "package.json"
    REQUIREMENTS_TXT = "requirements.txt"
    CMAKE_LISTS = "CMakeLists.txt"
    GRADLE_BUILD = "build.gradle"
    POM_XML = "pom.xml"
    CARGO_TOML = "Cargo.toml"
    GEMFILE = "Gemfile"
    MANUAL = "manual"


@dataclass
class DetectedSOUPComponent:
    """SOUP component detected from project dependency files."""
    name: str
    version: str
    source_file: str
    detection_method: DetectionMethod
    confidence: float  # 0.0 to 1.0
    suggested_classification: Optional[IEC62304SafetyClass] = None
    package_manager: Optional[str] = None
    description: Optional[str] = None
    homepage: Optional[str] = None
    license: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> List[str]:
        """Validate the DetectedSOUPComponent instance."""
        errors = []
        
        if not self.name:
            errors.append("name cannot be empty")
        if not self.version:
            errors.append("version cannot be empty")
        if not self.source_file:
            errors.append("source_file cannot be empty")
        if not isinstance(self.detection_method, DetectionMethod):
            errors.append("detection_method must be a DetectionMethod enum")
        if not (0.0 <= self.confidence <= 1.0):
            errors.append("confidence must be between 0.0 and 1.0")
        if self.suggested_classification and not isinstance(self.suggested_classification, IEC62304SafetyClass):
            errors.append("suggested_classification must be an IEC62304SafetyClass enum or None")
        
        return errors


@dataclass
class IEC62304Classification:
    """IEC 62304 safety classification for SOUP components."""
    safety_class: IEC62304SafetyClass
    justification: str
    risk_assessment: str
    verification_requirements: List[str] = field(default_factory=list)
    documentation_requirements: List[str] = field(default_factory=list)
    change_control_requirements: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def validate(self) -> List[str]:
        """Validate the IEC62304Classification instance."""
        errors = []
        
        if not isinstance(self.safety_class, IEC62304SafetyClass):
            errors.append("safety_class must be an IEC62304SafetyClass enum")
        if not self.justification:
            errors.append("justification cannot be empty")
        if not self.risk_assessment:
            errors.append("risk_assessment cannot be empty")
        
        return errors


@dataclass
class SafetyAssessment:
    """Safety assessment for SOUP components."""
    component_id: str
    safety_impact: str
    failure_modes: List[str] = field(default_factory=list)
    mitigation_measures: List[str] = field(default_factory=list)
    verification_methods: List[str] = field(default_factory=list)
    residual_risks: List[str] = field(default_factory=list)
    assessment_date: datetime = field(default_factory=datetime.now)
    assessor: Optional[str] = None
    
    def validate(self) -> List[str]:
        """Validate the SafetyAssessment instance."""
        errors = []
        
        if not self.component_id:
            errors.append("component_id cannot be empty")
        if not self.safety_impact:
            errors.append("safety_impact cannot be empty")
        
        return errors


@dataclass
class VersionChange:
    """Tracks version changes for SOUP components."""
    component_id: str
    old_version: str
    new_version: str
    change_date: datetime
    impact_analysis: str
    approval_status: str  # "pending", "approved", "rejected"
    approver: Optional[str] = None
    approval_date: Optional[datetime] = None
    change_reason: Optional[str] = None
    
    def validate(self) -> List[str]:
        """Validate the VersionChange instance."""
        errors = []
        
        if not self.component_id:
            errors.append("component_id cannot be empty")
        if not self.old_version:
            errors.append("old_version cannot be empty")
        if not self.new_version:
            errors.append("new_version cannot be empty")
        if not self.impact_analysis:
            errors.append("impact_analysis cannot be empty")
        if self.approval_status not in ["pending", "approved", "rejected"]:
            errors.append("approval_status must be 'pending', 'approved', or 'rejected'")
        
        return errors


@dataclass
class ComplianceValidation:
    """IEC 62304 compliance validation result."""
    component_id: str
    is_compliant: bool
    validation_date: datetime
    missing_requirements: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    validator: Optional[str] = None
    
    def validate(self) -> List[str]:
        """Validate the ComplianceValidation instance."""
        errors = []
        
        if not self.component_id:
            errors.append("component_id cannot be empty")
        if not isinstance(self.is_compliant, bool):
            errors.append("is_compliant must be a boolean")
        
        return errors


@dataclass
class SOUPAuditEntry:
    """Audit trail entry for SOUP component changes."""
    component_id: str
    action: str  # "created", "updated", "deleted", "classified", "assessed"
    timestamp: datetime
    user: str
    details: Dict[str, Any] = field(default_factory=dict)
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    
    def validate(self) -> List[str]:
        """Validate the SOUPAuditEntry instance."""
        errors = []
        
        if not self.component_id:
            errors.append("component_id cannot be empty")
        if not self.action:
            errors.append("action cannot be empty")
        if not self.user:
            errors.append("user cannot be empty")
        
        return errors