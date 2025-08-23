"""
Data models for the Medical Software Analysis Tool.
"""

from .core import (
    ProjectStructure,
    CodeChunk,
    Feature,
    Requirement,
    RiskItem,
    FileMetadata,
    CodeReference,
    TraceabilityLink
)

from .enums import (
    ChunkType,
    FeatureCategory,
    RequirementType,
    Severity,
    Probability,
    RiskLevel
)

__all__ = [
    'ProjectStructure',
    'CodeChunk', 
    'Feature',
    'Requirement',
    'RiskItem',
    'FileMetadata',
    'CodeReference',
    'TraceabilityLink',
    'ChunkType',
    'FeatureCategory',
    'RequirementType',
    'Severity',
    'Probability',
    'RiskLevel'
]