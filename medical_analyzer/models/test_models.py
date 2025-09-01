"""
Test Case Models for Medical Software Analysis.

This module contains data models for test case generation and management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class CasePriority(Enum):
    """Test case priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CaseCategory(Enum):
    """Test case categories."""
    FUNCTIONAL = "functional"
    SAFETY = "safety"
    PERFORMANCE = "performance"
    USABILITY = "usability"
    SECURITY = "security"
    INTEGRATION = "integration"
    REGRESSION = "regression"


@dataclass
class CaseStep:
    """Individual test step within a test case."""
    step_number: int
    action: str
    expected_result: str
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert test step to dictionary."""
        return {
            "step_number": self.step_number,
            "action": self.action,
            "expected_result": self.expected_result,
            "notes": self.notes
        }


@dataclass
class CaseModel:
    """Test case outline for requirement validation."""
    id: str
    name: str
    description: str
    requirement_id: str
    preconditions: List[str] = field(default_factory=list)
    test_steps: List[CaseStep] = field(default_factory=list)
    expected_results: List[str] = field(default_factory=list)
    priority: CasePriority = CasePriority.MEDIUM
    category: CaseCategory = CaseCategory.FUNCTIONAL
    estimated_duration: Optional[str] = None
    test_data_requirements: List[str] = field(default_factory=list)
    environment_requirements: List[str] = field(default_factory=list)
    traceability_links: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def validate(self) -> List[str]:
        """Validate test case completeness."""
        errors = []
        
        if not self.id:
            errors.append("Test case ID is required")
        if not self.name:
            errors.append("Test case name is required")
        if not self.description:
            errors.append("Test case description is required")
        if not self.requirement_id:
            errors.append("Requirement ID is required")
        if not self.test_steps:
            errors.append("At least one test step is required")
        
        # Validate test steps
        for i, step in enumerate(self.test_steps):
            if not step.action:
                errors.append(f"Test step {i+1}: Action is required")
            if not step.expected_result:
                errors.append(f"Test step {i+1}: Expected result is required")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert test case to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "requirement_id": self.requirement_id,
            "preconditions": self.preconditions,
            "test_steps": [step.to_dict() for step in self.test_steps],
            "expected_results": self.expected_results,
            "priority": self.priority.value,
            "category": self.category.value,
            "estimated_duration": self.estimated_duration,
            "test_data_requirements": self.test_data_requirements,
            "environment_requirements": self.environment_requirements,
            "traceability_links": self.traceability_links,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class CaseOutline:
    """Collection of test cases with coverage analysis."""
    project_name: str
    test_cases: List[CaseModel] = field(default_factory=list)
    coverage_summary: Dict[str, Any] = field(default_factory=dict)
    export_formats: List[str] = field(default_factory=list)
    generation_metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def get_coverage_by_requirement(self) -> Dict[str, List[str]]:
        """Get test case coverage by requirement ID."""
        coverage = {}
        for test_case in self.test_cases:
            req_id = test_case.requirement_id
            if req_id not in coverage:
                coverage[req_id] = []
            coverage[req_id].append(test_case.id)
        return coverage
    
    def get_coverage_by_category(self) -> Dict[str, int]:
        """Get test case count by category."""
        coverage = {}
        for test_case in self.test_cases:
            category = test_case.category.value
            coverage[category] = coverage.get(category, 0) + 1
        return coverage
    
    def get_coverage_by_priority(self) -> Dict[str, int]:
        """Get test case count by priority."""
        coverage = {}
        for test_case in self.test_cases:
            priority = test_case.priority.value
            coverage[priority] = coverage.get(priority, 0) + 1
        return coverage


@dataclass
class CoverageReport:
    """Test coverage analysis report."""
    total_requirements: int = 0
    covered_requirements: int = 0
    coverage_percentage: float = 0.0
    requirement_coverage: Dict[str, List[str]] = field(default_factory=dict)
    uncovered_requirements: List[str] = field(default_factory=list)
    test_case_count: int = 0
    priority_distribution: Dict[str, int] = field(default_factory=dict)
    category_distribution: Dict[str, int] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)
    
    def calculate_coverage_percentage(self) -> float:
        """Calculate coverage percentage."""
        if self.total_requirements == 0:
            return 0.0
        return (self.covered_requirements / self.total_requirements) * 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert coverage report to dictionary."""
        return {
            "total_requirements": self.total_requirements,
            "covered_requirements": self.covered_requirements,
            "coverage_percentage": self.coverage_percentage,
            "requirement_coverage": self.requirement_coverage,
            "uncovered_requirements": self.uncovered_requirements,
            "test_case_count": self.test_case_count,
            "priority_distribution": self.priority_distribution,
            "category_distribution": self.category_distribution,
            "generated_at": self.generated_at.isoformat()
        }