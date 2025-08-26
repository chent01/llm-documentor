"""
Result models for analysis services.

This module contains dataclasses that represent the results of various
analysis operations in the medical software analyzer.
"""

from dataclasses import dataclass
from typing import List, Dict, Any

from ..models.core import Feature, Requirement, RiskItem


@dataclass
class FeatureExtractionResult:
    """Result of feature extraction process."""
    features: List[Feature]
    confidence_score: float
    processing_time: float
    chunks_processed: int
    errors: List[str]
    metadata: Dict[str, Any]


@dataclass
class RequirementGenerationResult:
    """Result of User Requirements generation process."""
    requirements: List[Requirement]
    confidence_score: float
    processing_time: float
    features_processed: int
    errors: List[str]
    metadata: Dict[str, Any]


@dataclass
class SoftwareRequirementGenerationResult:
    """Result of Software Requirements generation process."""
    requirements: List[Requirement]
    confidence_score: float
    processing_time: float
    user_requirements_processed: int
    errors: List[str]
    metadata: Dict[str, Any]


@dataclass
class HazardIdentificationResult:
    """Result of hazard identification process."""
    risk_items: List[RiskItem]
    confidence_score: float
    processing_time: float
    requirements_processed: int
    errors: List[str]
    metadata: Dict[str, Any]


@dataclass
class RiskRegisterResult:
    """Result of risk register generation process."""
    risk_items: List[RiskItem]
    confidence_score: float
    processing_time: float
    requirements_processed: int
    errors: List[str]
    metadata: Dict[str, Any]