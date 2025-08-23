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