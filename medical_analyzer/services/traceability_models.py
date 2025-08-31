"""
Shared data models for traceability services.

This module contains data models used across traceability services to avoid circular imports.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional


@dataclass
class TraceabilityMatrix:
    """Complete traceability matrix for an analysis run."""
    analysis_run_id: int
    links: List[Any]  # TraceabilityLink objects
    code_to_requirements: Dict[str, List[str]]  # code_ref_id -> requirement_ids
    user_to_software_requirements: Dict[str, List[str]]  # ur_id -> sr_ids
    requirements_to_risks: Dict[str, List[str]]  # requirement_id -> risk_ids
    metadata: Dict[str, Any]
    created_at: datetime


@dataclass
class TraceabilityGap:
    """Represents a gap in traceability coverage."""
    gap_type: str  # 'orphaned_code', 'orphaned_requirement', 'missing_link', 'weak_link'
    source_type: str
    source_id: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    description: str = ""
    severity: str = "medium"  # 'low', 'medium', 'high'
    recommendation: str = ""


@dataclass
class TraceabilityTableRow:
    """Row in the tabular traceability matrix display."""
    code_reference: str
    file_path: str
    function_name: str
    feature_id: str
    feature_description: str
    user_requirement_id: str
    user_requirement_text: str
    software_requirement_id: str
    software_requirement_text: str
    risk_id: str
    risk_hazard: str
    confidence: float