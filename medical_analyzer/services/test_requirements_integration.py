"""
Test-Requirements Integration Service for Medical Software Analysis.

This service provides integration between test case generation and the requirements
management system, including automatic test regeneration, validation, and versioning.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import hashlib

from ..models.core import Requirement
from .test_case_generator import TestCaseGenerator
from ..models.test_models import TestOutline, TestCase
from .requirements_generator import RequirementsGenerator


class ChangeType(Enum):
    """Types of requirement changes."""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    UNCHANGED = "unchanged"


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class RequirementChange:
    """Represents a change to a requirement."""
    requirement_id: str
    change_type: ChangeType
    old_requirement: Optional[Requirement] = None
    new_requirement: Optional[Requirement] = None
    change_summary: str = ""
    impact_assessment: Dict[str, Any] = field(default_factory=dict)
    
    def get_change_hash(self) -> str:
        """Generate a hash representing this change."""
        content = f"{self.requirement_id}:{self.change_type.value}"
        if self.new_requirement:
            content += f":{self.new_requirement.text}"
        return hashlib.md5(content.encode()).hexdigest()[:8]


@dataclass
class ValidationIssue:
    """Represents a validation issue between test cases and requirements."""
    test_case_id: str
    requirement_id: str
    severity: ValidationSeverity
    issue_type: str
    description: str
    suggested_action: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestCaseVersion:
    """Represents a version of test cases for a specific requirement set."""
    version_id: str
    requirements_hash: str
    test_outline: TestOutline
    created_at: datetime
    change_summary: List[RequirementChange]
    validation_results: List[ValidationIssue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TestRequirementsIntegration:
    """Service for integrating test generation with requirements management."""
    
    def __init__(self, test_generator: TestCaseGenerator, requirements_generator: Optional[RequirementsGenerator] = None):
        """Initialize the integration service.
        
        Args:
            test_generator: Test case generator instance
            requirements_generator: Optional requirements generator for updates
        """
        self.test_generator = test_generator
        self.requirements_generator = requirements_generator
        self.test_versions: Dict[str, TestCaseVersion] = {}
        self.current_requirements: List[Requirement] = []
        self.current_test_outline: Optional[TestOutline] = None
        
    def set_requirements(self, requirements: List[Requirement]) -> None:
        """Set the current requirements and detect changes.
        
        Args:
            requirements: Updated requirements list
        """
        changes = self._detect_requirement_changes(self.current_requirements, requirements)
        self.current_requirements = requirements
        
        if changes:
            self._handle_requirement_changes(changes)
    
    def _detect_requirement_changes(self, old_requirements: List[Requirement], new_requirements: List[Requirement]) -> List[RequirementChange]:
        """Detect changes between old and new requirements.
        
        Args:
            old_requirements: Previous requirements list
            new_requirements: Updated requirements list
            
        Returns:
            List of detected changes
        """
        changes = []
        
        # Create lookup dictionaries
        old_req_dict = {req.id: req for req in old_requirements}
        new_req_dict = {req.id: req for req in new_requirements}
        
        # Find added requirements
        for req_id, req in new_req_dict.items():
            if req_id not in old_req_dict:
                changes.append(RequirementChange(
                    requirement_id=req_id,
                    change_type=ChangeType.ADDED,
                    new_requirement=req,
                    change_summary=f"New requirement added: {req.text[:50]}..."
                ))
        
        # Find deleted requirements
        for req_id, req in old_req_dict.items():
            if req_id not in new_req_dict:
                changes.append(RequirementChange(
                    requirement_id=req_id,
                    change_type=ChangeType.DELETED,
                    old_requirement=req,
                    change_summary=f"Requirement deleted: {req.text[:50]}..."
                ))
        
        # Find modified requirements
        for req_id in set(old_req_dict.keys()) & set(new_req_dict.keys()):
            old_req = old_req_dict[req_id]
            new_req = new_req_dict[req_id]
            
            if self._requirements_differ(old_req, new_req):
                changes.append(RequirementChange(
                    requirement_id=req_id,
                    change_type=ChangeType.MODIFIED,
                    old_requirement=old_req,
                    new_requirement=new_req,
                    change_summary=self._summarize_requirement_changes(old_req, new_req)
                ))
        
        return changes
    
    def _requirements_differ(self, req1: Requirement, req2: Requirement) -> bool:
        """Check if two requirements are different.
        
        Args:
            req1: First requirement
            req2: Second requirement
            
        Returns:
            True if requirements differ significantly
        """
        # Compare key fields
        if req1.text != req2.text:
            return True
        if req1.acceptance_criteria != req2.acceptance_criteria:
            return True
        if req1.type != req2.type:
            return True
        
        return False
    
    def _summarize_requirement_changes(self, old_req: Requirement, new_req: Requirement) -> str:
        """Summarize changes between two requirements.
        
        Args:
            old_req: Original requirement
            new_req: Updated requirement
            
        Returns:
            Summary of changes
        """
        changes = []
        
        if old_req.text != new_req.text:
            changes.append("text modified")
        
        if old_req.acceptance_criteria != new_req.acceptance_criteria:
            changes.append("acceptance criteria changed")
        
        if old_req.type != new_req.type:
            changes.append(f"type changed from {old_req.type.value} to {new_req.type.value}")
        
        return "; ".join(changes) if changes else "minor changes"
    
    def _handle_requirement_changes(self, changes: List[RequirementChange]) -> None:
        """Handle detected requirement changes.
        
        Args:
            changes: List of requirement changes
        """
        # Assess impact on existing test cases
        impact_assessment = self._assess_test_impact(changes)
        
        # Update change records with impact assessment
        for change in changes:
            change.impact_assessment = impact_assessment.get(change.requirement_id, {})
        
        # Trigger automatic test regeneration if needed
        if self._should_regenerate_tests(changes):
            self.regenerate_tests_for_changes(changes)
    
    def _assess_test_impact(self, changes: List[RequirementChange]) -> Dict[str, Dict[str, Any]]:
        """Assess the impact of requirement changes on existing test cases.
        
        Args:
            changes: List of requirement changes
            
        Returns:
            Impact assessment for each changed requirement
        """
        impact_assessment = {}
        
        if not self.current_test_outline:
            return impact_assessment
        
        for change in changes:
            req_id = change.requirement_id
            affected_tests = [tc for tc in self.current_test_outline.test_cases if tc.requirement_id == req_id]
            
            impact = {
                "affected_test_count": len(affected_tests),
                "affected_test_ids": [tc.id for tc in affected_tests],
                "regeneration_required": False,
                "validation_required": True
            }
            
            if change.change_type == ChangeType.ADDED:
                impact["regeneration_required"] = True
                impact["action"] = "generate_new_tests"
            elif change.change_type == ChangeType.DELETED:
                impact["regeneration_required"] = True
                impact["action"] = "remove_tests"
            elif change.change_type == ChangeType.MODIFIED:
                # Determine if regeneration is needed based on change severity
                if self._is_significant_change(change):
                    impact["regeneration_required"] = True
                    impact["action"] = "regenerate_tests"
                else:
                    impact["action"] = "validate_tests"
            
            impact_assessment[req_id] = impact
        
        return impact_assessment
    
    def _is_significant_change(self, change: RequirementChange) -> bool:
        """Determine if a requirement change is significant enough to require test regeneration.
        
        Args:
            change: Requirement change to assess
            
        Returns:
            True if change is significant
        """
        if not change.old_requirement or not change.new_requirement:
            return True
        
        old_req = change.old_requirement
        new_req = change.new_requirement
        
        # Text changes that affect more than 30% of the content
        if old_req.text != new_req.text:
            old_words = set(old_req.text.lower().split())
            new_words = set(new_req.text.lower().split())
            
            if len(old_words) == 0:
                return True
            
            common_words = old_words & new_words
            change_ratio = 1 - (len(common_words) / len(old_words))
            
            if change_ratio > 0.3:  # More than 30% change
                return True
        
        # Acceptance criteria changes
        if old_req.acceptance_criteria != new_req.acceptance_criteria:
            return True
        
        # Type changes
        if old_req.type != new_req.type:
            return True
        
        return False
    
    def _should_regenerate_tests(self, changes: List[RequirementChange]) -> bool:
        """Determine if tests should be automatically regenerated.
        
        Args:
            changes: List of requirement changes
            
        Returns:
            True if automatic regeneration is recommended
        """
        # Regenerate if there are added requirements
        if any(change.change_type == ChangeType.ADDED for change in changes):
            return True
        
        # Regenerate if there are significant modifications
        significant_changes = [change for change in changes 
                             if change.change_type == ChangeType.MODIFIED and self._is_significant_change(change)]
        
        return len(significant_changes) > 0
    
    def regenerate_tests_for_changes(self, changes: List[RequirementChange]) -> TestOutline:
        """Regenerate test cases for changed requirements.
        
        Args:
            changes: List of requirement changes
            
        Returns:
            Updated test outline
        """
        # Generate new test outline
        new_test_outline = self.test_generator.generate_test_cases(self.current_requirements)
        
        # Create version record
        version_id = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        requirements_hash = self._calculate_requirements_hash(self.current_requirements)
        
        version = TestCaseVersion(
            version_id=version_id,
            requirements_hash=requirements_hash,
            test_outline=new_test_outline,
            created_at=datetime.now(),
            change_summary=changes
        )
        
        self.test_versions[version_id] = version
        self.current_test_outline = new_test_outline
        
        return new_test_outline
    
    def validate_test_cases_against_requirements(self, test_outline: Optional[TestOutline] = None) -> List[ValidationIssue]:
        """Validate test cases against current requirements.
        
        Args:
            test_outline: Test outline to validate (uses current if None)
            
        Returns:
            List of validation issues
        """
        if test_outline is None:
            test_outline = self.current_test_outline
        
        if not test_outline:
            return []
        
        validation_issues = []
        
        # Create requirement lookup
        req_dict = {req.id: req for req in self.current_requirements}
        
        # Validate each test case
        for test_case in test_outline.test_cases:
            issues = self._validate_single_test_case(test_case, req_dict)
            validation_issues.extend(issues)
        
        # Check for missing test coverage
        covered_req_ids = {tc.requirement_id for tc in test_outline.test_cases}
        for req in self.current_requirements:
            if req.id not in covered_req_ids:
                validation_issues.append(ValidationIssue(
                    test_case_id="",
                    requirement_id=req.id,
                    severity=ValidationSeverity.WARNING,
                    issue_type="missing_coverage",
                    description=f"No test cases found for requirement {req.id}",
                    suggested_action="Generate test cases for this requirement"
                ))
        
        return validation_issues
    
    def _validate_single_test_case(self, test_case: TestCase, req_dict: Dict[str, Requirement]) -> List[ValidationIssue]:
        """Validate a single test case against its requirement.
        
        Args:
            test_case: Test case to validate
            req_dict: Dictionary of requirements by ID
            
        Returns:
            List of validation issues for this test case
        """
        issues = []
        
        # Check if requirement exists
        requirement = req_dict.get(test_case.requirement_id)
        if not requirement:
            issues.append(ValidationIssue(
                test_case_id=test_case.id,
                requirement_id=test_case.requirement_id,
                severity=ValidationSeverity.ERROR,
                issue_type="missing_requirement",
                description=f"Test case references non-existent requirement {test_case.requirement_id}",
                suggested_action="Update test case to reference valid requirement or remove test case"
            ))
            return issues
        
        # Validate acceptance criteria coverage
        if requirement.acceptance_criteria:
            issues.extend(self._validate_acceptance_criteria_coverage(test_case, requirement))
        
        # Validate test case completeness
        issues.extend(self._validate_test_case_completeness(test_case))
        
        # Validate test case consistency
        issues.extend(self._validate_test_case_consistency(test_case, requirement))
        
        return issues
    
    def _validate_acceptance_criteria_coverage(self, test_case: TestCase, requirement: Requirement) -> List[ValidationIssue]:
        """Validate that test case covers acceptance criteria.
        
        Args:
            test_case: Test case to validate
            requirement: Associated requirement
            
        Returns:
            List of validation issues
        """
        issues = []
        
        # Simple keyword-based coverage check
        test_content = f"{test_case.description} {' '.join([step.action for step in test_case.test_steps])}"
        test_content_lower = test_content.lower()
        
        uncovered_criteria = []
        for criterion in requirement.acceptance_criteria:
            # Extract key terms from acceptance criteria
            criterion_words = set(criterion.lower().split())
            test_words = set(test_content_lower.split())
            
            # Check for overlap (simple heuristic)
            overlap = len(criterion_words & test_words)
            if overlap < len(criterion_words) * 0.3:  # Less than 30% overlap
                uncovered_criteria.append(criterion)
        
        if uncovered_criteria:
            issues.append(ValidationIssue(
                test_case_id=test_case.id,
                requirement_id=requirement.id,
                severity=ValidationSeverity.WARNING,
                issue_type="incomplete_criteria_coverage",
                description=f"Test case may not fully cover {len(uncovered_criteria)} acceptance criteria",
                suggested_action="Review and enhance test steps to cover all acceptance criteria",
                metadata={"uncovered_criteria": uncovered_criteria}
            ))
        
        return issues
    
    def _validate_test_case_completeness(self, test_case: TestCase) -> List[ValidationIssue]:
        """Validate test case completeness.
        
        Args:
            test_case: Test case to validate
            
        Returns:
            List of validation issues
        """
        issues = []
        
        # Check for missing elements
        if not test_case.test_steps:
            issues.append(ValidationIssue(
                test_case_id=test_case.id,
                requirement_id=test_case.requirement_id,
                severity=ValidationSeverity.ERROR,
                issue_type="missing_test_steps",
                description="Test case has no test steps defined",
                suggested_action="Add detailed test steps to the test case"
            ))
        
        if not test_case.expected_results:
            issues.append(ValidationIssue(
                test_case_id=test_case.id,
                requirement_id=test_case.requirement_id,
                severity=ValidationSeverity.WARNING,
                issue_type="missing_expected_results",
                description="Test case has no expected results defined",
                suggested_action="Define clear expected results for the test case"
            ))
        
        if not test_case.preconditions:
            issues.append(ValidationIssue(
                test_case_id=test_case.id,
                requirement_id=test_case.requirement_id,
                severity=ValidationSeverity.INFO,
                issue_type="missing_preconditions",
                description="Test case has no preconditions defined",
                suggested_action="Consider adding preconditions to improve test clarity"
            ))
        
        return issues
    
    def _validate_test_case_consistency(self, test_case: TestCase, requirement: Requirement) -> List[ValidationIssue]:
        """Validate test case consistency with requirement.
        
        Args:
            test_case: Test case to validate
            requirement: Associated requirement
            
        Returns:
            List of validation issues
        """
        issues = []
        
        # Check category consistency
        expected_category = self.test_generator._determine_test_category(requirement)
        if test_case.category != expected_category:
            issues.append(ValidationIssue(
                test_case_id=test_case.id,
                requirement_id=requirement.id,
                severity=ValidationSeverity.INFO,
                issue_type="category_mismatch",
                description=f"Test case category ({test_case.category.value}) may not match requirement type",
                suggested_action=f"Consider changing category to {expected_category.value}"
            ))
        
        return issues
    
    def _calculate_requirements_hash(self, requirements: List[Requirement]) -> str:
        """Calculate hash for a set of requirements.
        
        Args:
            requirements: List of requirements
            
        Returns:
            Hash string representing the requirements set
        """
        content = ""
        for req in sorted(requirements, key=lambda r: r.id):
            content += f"{req.id}:{req.text}:{':'.join(req.acceptance_criteria)}"
        
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_test_coverage_analysis(self) -> Dict[str, Any]:
        """Get comprehensive test coverage analysis.
        
        Returns:
            Coverage analysis data
        """
        if not self.current_test_outline:
            return {"error": "No test outline available"}
        
        validation_issues = self.validate_test_cases_against_requirements()
        coverage_report = self.test_generator.generate_coverage_report(self.current_test_outline, self.current_requirements)
        
        # Categorize validation issues
        error_count = sum(1 for issue in validation_issues if issue.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for issue in validation_issues if issue.severity == ValidationSeverity.WARNING)
        info_count = sum(1 for issue in validation_issues if issue.severity == ValidationSeverity.INFO)
        
        return {
            "coverage_report": coverage_report,
            "validation_summary": {
                "total_issues": len(validation_issues),
                "errors": error_count,
                "warnings": warning_count,
                "info": info_count
            },
            "validation_issues": [
                {
                    "test_case_id": issue.test_case_id,
                    "requirement_id": issue.requirement_id,
                    "severity": issue.severity.value,
                    "type": issue.issue_type,
                    "description": issue.description,
                    "suggested_action": issue.suggested_action
                }
                for issue in validation_issues
            ],
            "test_versions": list(self.test_versions.keys()),
            "current_version": max(self.test_versions.keys()) if self.test_versions else None
        }
    
    def export_integration_report(self, format_type: str = "text") -> str:
        """Export comprehensive integration report.
        
        Args:
            format_type: Export format
            
        Returns:
            Integration report
        """
        analysis = self.get_test_coverage_analysis()
        
        if format_type.lower() == "json":
            return json.dumps(analysis, indent=2, default=str)
        
        # Text format
        lines = []
        lines.append("TEST-REQUIREMENTS INTEGRATION REPORT")
        lines.append("=" * 50)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Validation summary
        val_summary = analysis["validation_summary"]
        lines.append("VALIDATION SUMMARY")
        lines.append("-" * 20)
        lines.append(f"Total Issues: {val_summary['total_issues']}")
        lines.append(f"Errors: {val_summary['errors']}")
        lines.append(f"Warnings: {val_summary['warnings']}")
        lines.append(f"Info: {val_summary['info']}")
        lines.append("")
        
        # Coverage summary
        if "coverage_report" in analysis:
            coverage = analysis["coverage_report"]["summary"]
            lines.append("COVERAGE SUMMARY")
            lines.append("-" * 20)
            lines.append(f"Requirements Coverage: {coverage['coverage_percentage']:.1f}%")
            lines.append(f"Total Test Cases: {coverage['total_test_cases']}")
            lines.append("")
        
        # Version history
        if analysis["test_versions"]:
            lines.append("VERSION HISTORY")
            lines.append("-" * 20)
            for version in analysis["test_versions"]:
                lines.append(f"- {version}")
            lines.append("")
        
        return '\n'.join(lines)