"""
Core data models for the Medical Software Analysis Tool.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from .enums import (
    ChunkType, FeatureCategory, RequirementType, 
    Severity, Probability, RiskLevel
)


@dataclass
class FileMetadata:
    """Metadata for analyzed files."""
    file_path: str
    file_size: int
    last_modified: datetime
    file_type: str  # 'c' or 'javascript'
    encoding: str = 'utf-8'
    line_count: int = 0
    function_count: int = 0
    
    def validate(self) -> List[str]:
        """
        Validate the FileMetadata instance.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Validate file_path
        if not self.file_path:
            errors.append("file_path cannot be empty")
        elif not isinstance(self.file_path, str):
            errors.append("file_path must be a string")
        
        # Validate file_size
        if not isinstance(self.file_size, int):
            errors.append("file_size must be an integer")
        elif self.file_size < 0:
            errors.append("file_size cannot be negative")
        
        # Validate last_modified
        if not isinstance(self.last_modified, datetime):
            errors.append("last_modified must be a datetime instance")
        
        # Validate file_type
        if not self.file_type:
            errors.append("file_type cannot be empty")
        elif self.file_type not in ['c', 'javascript']:
            errors.append("file_type must be 'c' or 'javascript'")
        
        # Validate encoding
        if not isinstance(self.encoding, str):
            errors.append("encoding must be a string")
        elif not self.encoding:
            errors.append("encoding cannot be empty")
        
        # Validate line_count
        if not isinstance(self.line_count, int):
            errors.append("line_count must be an integer")
        elif self.line_count < 0:
            errors.append("line_count cannot be negative")
        
        # Validate function_count
        if not isinstance(self.function_count, int):
            errors.append("function_count must be an integer")
        elif self.function_count < 0:
            errors.append("function_count cannot be negative")
        
        return errors
    
    def is_valid(self) -> bool:
        """
        Check if the FileMetadata instance is valid.
        
        Returns:
            True if valid, False otherwise
        """
        return len(self.validate()) == 0


@dataclass
class CodeReference:
    """Reference to specific code location."""
    file_path: str
    start_line: int
    end_line: int
    function_name: Optional[str] = None
    context: Optional[str] = None


@dataclass
class ProjectStructure:
    """Structure representing an analyzed project."""
    root_path: str
    selected_files: List[str]
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    file_metadata: List[FileMetadata] = field(default_factory=list)
    
    def validate(self) -> List[str]:
        """
        Validate the ProjectStructure instance.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Validate root_path
        if not self.root_path:
            errors.append("root_path cannot be empty")
        elif not isinstance(self.root_path, str):
            errors.append("root_path must be a string")
        
        # Validate selected_files
        if not isinstance(self.selected_files, list):
            errors.append("selected_files must be a list")
        else:
            for i, file_path in enumerate(self.selected_files):
                if not isinstance(file_path, str):
                    errors.append(f"selected_files[{i}] must be a string")
                elif not file_path:
                    errors.append(f"selected_files[{i}] cannot be empty")
        
        # Validate description
        if not isinstance(self.description, str):
            errors.append("description must be a string")
        
        # Validate metadata
        if not isinstance(self.metadata, dict):
            errors.append("metadata must be a dictionary")
        
        # Validate timestamp
        if not isinstance(self.timestamp, datetime):
            errors.append("timestamp must be a datetime instance")
        
        # Validate file_metadata
        if not isinstance(self.file_metadata, list):
            errors.append("file_metadata must be a list")
        else:
            for i, metadata in enumerate(self.file_metadata):
                if not isinstance(metadata, FileMetadata):
                    errors.append(f"file_metadata[{i}] must be a FileMetadata instance")
                else:
                    # Validate individual FileMetadata
                    metadata_errors = metadata.validate()
                    for error in metadata_errors:
                        errors.append(f"file_metadata[{i}]: {error}")
        
        # Cross-validation: file_metadata should match selected_files
        count_mismatch = len(self.file_metadata) != len(self.selected_files)
        if count_mismatch:
            errors.append(
                f"file_metadata count ({len(self.file_metadata)}) "
                f"does not match selected_files count ({len(self.selected_files)})"
            )
        
        # Check path correspondence regardless of count mismatch
        # Only do path validation if all file_metadata items are valid FileMetadata instances
        # and all selected_files are strings
        valid_metadata = [fm for fm in self.file_metadata if isinstance(fm, FileMetadata)]
        valid_selected_files = [f for f in self.selected_files if isinstance(f, str)]
        
        if (len(valid_metadata) == len(self.file_metadata) and 
            len(valid_selected_files) == len(self.selected_files)):
            # Check that each file_metadata corresponds to a selected file
            metadata_paths = {fm.file_path for fm in valid_metadata}
            selected_paths = set(valid_selected_files)
            
            missing_metadata = selected_paths - metadata_paths
            if missing_metadata:
                errors.append(f"Missing file metadata for: {', '.join(missing_metadata)}")
            
            extra_metadata = metadata_paths - selected_paths
            if extra_metadata:
                errors.append(f"Extra file metadata for: {', '.join(extra_metadata)}")
        
        return errors
    
    def is_valid(self) -> bool:
        """
        Check if the ProjectStructure instance is valid.
        
        Returns:
            True if valid, False otherwise
        """
        return len(self.validate()) == 0


@dataclass
class CodeChunk:
    """Chunk of code for LLM analysis."""
    file_path: str
    start_line: int
    end_line: int
    content: str
    function_name: Optional[str] = None
    chunk_type: ChunkType = ChunkType.FUNCTION
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class Feature:
    """Identified software feature."""
    id: str
    description: str
    confidence: float
    evidence: List[CodeReference] = field(default_factory=list)
    category: FeatureCategory = FeatureCategory.DATA_PROCESSING
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass  
class Requirement:
    """Software or user requirement."""
    id: str
    type: RequirementType
    text: str
    acceptance_criteria: List[str] = field(default_factory=list)
    derived_from: List[str] = field(default_factory=list)  # Feature IDs or parent requirement IDs
    code_references: List[CodeReference] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskItem:
    """Risk register item per ISO 14971."""
    id: str
    hazard: str
    cause: str
    effect: str
    severity: Severity
    probability: Probability
    risk_level: RiskLevel
    mitigation: str
    verification: str
    related_requirements: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Additional ISO 14971 specific fields
    risk_control_measures: List[str] = field(default_factory=list)
    residual_risk_severity: Optional[Severity] = None
    residual_risk_probability: Optional[Probability] = None
    residual_risk_level: Optional[RiskLevel] = None
    risk_acceptability: Optional[str] = None  # "Acceptable", "Not Acceptable"
    risk_control_effectiveness: Optional[float] = None  # 0.0 to 1.0
    post_market_surveillance: Optional[str] = None
    risk_benefit_analysis: Optional[str] = None


@dataclass
class SOUPComponent:
    """Software of Unknown Provenance (SOUP) component."""
    id: str
    name: str
    version: str
    usage_reason: str
    safety_justification: str
    supplier: Optional[str] = None
    license: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    installation_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    criticality_level: Optional[str] = None  # "High", "Medium", "Low"
    verification_method: Optional[str] = None
    anomaly_list: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> List[str]:
        """
        Validate the SOUPComponent instance.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Validate required fields
        if not self.id:
            errors.append("id cannot be empty")
        elif not isinstance(self.id, str):
            errors.append("id must be a string")
        
        if not self.name:
            errors.append("name cannot be empty")
        elif not isinstance(self.name, str):
            errors.append("name must be a string")
        
        if not self.version:
            errors.append("version cannot be empty")
        elif not isinstance(self.version, str):
            errors.append("version must be a string")
        
        if not self.usage_reason:
            errors.append("usage_reason cannot be empty")
        elif not isinstance(self.usage_reason, str):
            errors.append("usage_reason must be a string")
        
        if not self.safety_justification:
            errors.append("safety_justification cannot be empty")
        elif not isinstance(self.safety_justification, str):
            errors.append("safety_justification must be a string")
        
        # Validate optional string fields
        for field_name in ['supplier', 'license', 'website', 'description', 'criticality_level', 'verification_method']:
            field_value = getattr(self, field_name)
            if field_value is not None and not isinstance(field_value, str):
                errors.append(f"{field_name} must be a string or None")
        
        # Validate datetime fields
        for field_name in ['installation_date', 'last_updated']:
            field_value = getattr(self, field_name)
            if field_value is not None and not isinstance(field_value, datetime):
                errors.append(f"{field_name} must be a datetime instance or None")
        
        # Validate criticality_level values
        if self.criticality_level is not None and self.criticality_level not in ["High", "Medium", "Low"]:
            errors.append("criticality_level must be 'High', 'Medium', 'Low', or None")
        
        # Validate anomaly_list
        if not isinstance(self.anomaly_list, list):
            errors.append("anomaly_list must be a list")
        else:
            for i, anomaly in enumerate(self.anomaly_list):
                if not isinstance(anomaly, str):
                    errors.append(f"anomaly_list[{i}] must be a string")
        
        # Validate metadata
        if not isinstance(self.metadata, dict):
            errors.append("metadata must be a dictionary")
        
        return errors
    
    def is_valid(self) -> bool:
        """
        Check if the SOUPComponent instance is valid.
        
        Returns:
            True if valid, False otherwise
        """
        return len(self.validate()) == 0


@dataclass
class TraceabilityLink:
    """Link between different analysis artifacts."""
    id: str
    source_type: str  # 'code', 'feature', 'requirement', 'risk'
    source_id: str
    target_type: str
    target_id: str
    link_type: str  # 'implements', 'derives_from', 'mitigates', etc.
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)