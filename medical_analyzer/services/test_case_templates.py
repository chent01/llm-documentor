"""
Test Case Templates and Formatting for Medical Software Analysis.

This module provides comprehensive templates and formatting utilities
for generating professional test case documentation in multiple formats.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import xml.etree.ElementTree as ET
import csv
import io
from pathlib import Path

from ..models.core import Requirement
from ..models.test_models import CaseModel, CaseOutline, CaseStep, CasePriority, CaseCategory


@dataclass
class CaseModelTemplate:
    """Template definition for test case generation."""
    name: str
    category: CaseCategory
    priority: CasePriority
    description_template: str
    preconditions_template: List[str]
    steps_template: List[str]
    expected_results_template: List[str]
    metadata_template: Dict[str, Any]
    
    def apply_to_requirement(self, requirement: Requirement) -> Dict[str, Any]:
        """Apply template to a requirement to generate test case data."""
        return {
            "name": f"Test {requirement.text[:50]}...",
            "description": self.description_template.format(
                requirement_text=requirement.text,
                requirement_id=requirement.id,
                requirement_type=requirement.type.value
            ),
            "category": self.category,
            "priority": self.priority,
            "preconditions": [
                template.format(
                    requirement_text=requirement.text,
                    requirement_id=requirement.id
                ) for template in self.preconditions_template
            ],
            "expected_results": [
                template.format(
                    requirement_text=requirement.text,
                    requirement_id=requirement.id
                ) for template in self.expected_results_template
            ],
            "metadata": {
                **self.metadata_template,
                "template_name": self.name,
                "requirement_type": requirement.type.value
            }
        }


class CaseTemplateManager:
    """Manager for test case templates and formatting."""
    
    def __init__(self):
        self.templates = self._initialize_templates()
        self.formatters = self._initialize_formatters()
    
    def _initialize_templates(self) -> Dict[str, CaseModelTemplate]:
        """Initialize predefined test case templates."""
        templates = {}
        
        # Functional requirement template
        templates["functional"] = CaseModelTemplate(
            name="Functional Test Template",
            category=CaseCategory.FUNCTIONAL,
            priority=CasePriority.HIGH,
            description_template="Verify that the system correctly implements the functional requirement: {requirement_text}",
            preconditions_template=[
                "System is initialized and in operational state",
                "All required dependencies are available and configured",
                "Test environment matches production specifications",
                "User has appropriate permissions for the functionality"
            ],
            steps_template=[
                "Initialize system components and verify readiness",
                "Set up test data and input parameters",
                "Execute the required functionality as specified in {requirement_id}",
                "Capture system outputs and responses",
                "Verify system state after execution"
            ],
            expected_results_template=[
                "System executes the functionality without errors",
                "All outputs match the specified requirements",
                "System maintains stable state throughout execution",
                "Performance meets acceptable thresholds"
            ],
            metadata_template={
                "test_type": "functional",
                "automation_feasible": True,
                "regulatory_impact": "medium"
            }
        )
        
        # Safety requirement template
        templates["safety"] = CaseModelTemplate(
            name="Safety Test Template",
            category=CaseCategory.SAFETY,
            priority=CasePriority.CRITICAL,
            description_template="Verify safety mechanisms and fail-safe behavior for requirement: {requirement_text}",
            preconditions_template=[
                "Safety monitoring systems are active and calibrated",
                "Emergency stop mechanisms are verified functional",
                "Test environment includes safety barriers and monitoring",
                "Safety personnel are present and briefed on procedures"
            ],
            steps_template=[
                "Verify all safety systems are operational",
                "Establish baseline safety parameters",
                "Introduce controlled safety-relevant conditions",
                "Monitor safety system responses and alarms",
                "Verify system enters safe state as required",
                "Test recovery procedures and system restart"
            ],
            expected_results_template=[
                "Safety mechanisms activate within specified time limits",
                "System enters documented safe state without harm",
                "All safety alarms and notifications function correctly",
                "Recovery procedures restore normal operation safely"
            ],
            metadata_template={
                "test_type": "safety_critical",
                "automation_feasible": False,
                "regulatory_impact": "high",
                "safety_classification": "Class C"
            }
        )
        
        # Performance requirement template
        templates["performance"] = CaseModelTemplate(
            name="Performance Test Template",
            category=CaseCategory.PERFORMANCE,
            priority=CasePriority.MEDIUM,
            description_template="Verify performance characteristics and timing requirements for: {requirement_text}",
            preconditions_template=[
                "Performance monitoring tools are configured and calibrated",
                "System is under typical operational load",
                "Baseline performance metrics are established",
                "Test data represents realistic usage patterns"
            ],
            steps_template=[
                "Establish performance baseline measurements",
                "Configure performance monitoring and data collection",
                "Execute performance-critical operations",
                "Measure response times, throughput, and resource usage",
                "Analyze performance data against requirements",
                "Verify performance under various load conditions"
            ],
            expected_results_template=[
                "Response times meet specified performance requirements",
                "System throughput satisfies operational demands",
                "Resource utilization remains within acceptable limits",
                "Performance degrades gracefully under increased load"
            ],
            metadata_template={
                "test_type": "performance",
                "automation_feasible": True,
                "regulatory_impact": "medium",
                "load_testing_required": True
            }
        )
        
        # Usability requirement template
        templates["usability"] = CaseModelTemplate(
            name="Usability Test Template",
            category=CaseCategory.USABILITY,
            priority=CasePriority.MEDIUM,
            description_template="Verify user interface and interaction requirements for: {requirement_text}",
            preconditions_template=[
                "User interface is fully rendered and responsive",
                "Test users represent target user demographics",
                "Usability testing environment is prepared",
                "Screen recording and interaction logging are enabled"
            ],
            steps_template=[
                "Present user interface to test participants",
                "Guide users through typical interaction scenarios",
                "Observe and record user interactions and feedback",
                "Measure task completion times and error rates",
                "Evaluate user satisfaction and ease of use",
                "Document usability issues and improvement suggestions"
            ],
            expected_results_template=[
                "Users can complete tasks within acceptable time limits",
                "Error rates remain below specified thresholds",
                "User satisfaction scores meet target levels",
                "Interface follows established usability guidelines"
            ],
            metadata_template={
                "test_type": "usability",
                "automation_feasible": False,
                "regulatory_impact": "low",
                "user_testing_required": True
            }
        )
        
        # Security requirement template
        templates["security"] = CaseModelTemplate(
            name="Security Test Template",
            category=CaseCategory.SECURITY,
            priority=CasePriority.HIGH,
            description_template="Verify security controls and access restrictions for: {requirement_text}",
            preconditions_template=[
                "Security monitoring and logging systems are active",
                "Test accounts with various permission levels are prepared",
                "Security testing tools are configured and ready",
                "Backup and recovery procedures are verified"
            ],
            steps_template=[
                "Verify authentication mechanisms and access controls",
                "Test authorization for different user roles and permissions",
                "Attempt unauthorized access and privilege escalation",
                "Verify data encryption and secure communication",
                "Test security logging and audit trail functionality",
                "Validate security incident response procedures"
            ],
            expected_results_template=[
                "Authentication mechanisms prevent unauthorized access",
                "Authorization controls enforce proper access restrictions",
                "Security violations are detected and logged appropriately",
                "Data remains protected during transmission and storage"
            ],
            metadata_template={
                "test_type": "security",
                "automation_feasible": True,
                "regulatory_impact": "high",
                "penetration_testing_required": True
            }
        )
        
        # Integration requirement template
        templates["integration"] = CaseModelTemplate(
            name="Integration Test Template",
            category=CaseCategory.INTEGRATION,
            priority=CasePriority.HIGH,
            description_template="Verify system integration and interface requirements for: {requirement_text}",
            preconditions_template=[
                "All integrated systems are operational and accessible",
                "Network connectivity and communication protocols are verified",
                "Integration test data and mock services are prepared",
                "Monitoring tools for inter-system communication are active"
            ],
            steps_template=[
                "Verify connectivity to all integrated systems",
                "Test data exchange and communication protocols",
                "Validate data transformation and mapping accuracy",
                "Test error handling for integration failures",
                "Verify transaction integrity across system boundaries",
                "Test system behavior during integration partner downtime"
            ],
            expected_results_template=[
                "Data flows correctly between integrated systems",
                "Communication protocols function as specified",
                "Error conditions are handled gracefully",
                "System maintains consistency during integration operations"
            ],
            metadata_template={
                "test_type": "integration",
                "automation_feasible": True,
                "regulatory_impact": "medium",
                "external_dependencies": True
            }
        )
        
        return templates
    
    def _initialize_formatters(self) -> Dict[str, Any]:
        """Initialize format-specific formatters."""
        return {
            "text": TextFormatter(),
            "json": JSONFormatter(),
            "xml": XMLFormatter(),
            "csv": CSVFormatter(),
            "html": HTMLFormatter(),
            "markdown": MarkdownFormatter()
        }
    
    def get_template(self, template_name: str) -> Optional[CaseModelTemplate]:
        """Get a test case template by name."""
        return self.templates.get(template_name)
    
    def get_template_for_requirement(self, requirement: Requirement) -> CaseModelTemplate:
        """Get the most appropriate template for a requirement."""
        req_text = requirement.text.lower()
        
        # Safety keywords
        safety_keywords = ["safety", "hazard", "risk", "critical", "fail-safe", "alarm", "emergency"]
        if any(keyword in req_text for keyword in safety_keywords):
            return self.templates["safety"]
        
        # Performance keywords
        performance_keywords = ["performance", "speed", "time", "latency", "throughput", "response"]
        if any(keyword in req_text for keyword in performance_keywords):
            return self.templates["performance"]
        
        # Usability keywords
        usability_keywords = ["user", "interface", "display", "interaction", "usability", "accessible"]
        if any(keyword in req_text for keyword in usability_keywords):
            return self.templates["usability"]
        
        # Security keywords
        security_keywords = ["security", "authentication", "authorization", "encryption", "access"]
        if any(keyword in req_text for keyword in security_keywords):
            return self.templates["security"]
        
        # Integration keywords
        integration_keywords = ["integration", "interface", "communication", "protocol", "api"]
        if any(keyword in req_text for keyword in integration_keywords):
            return self.templates["integration"]
        
        # Default to functional
        return self.templates["functional"]
    
    def format_test_outline(self, test_outline: CaseOutline, format_type: str, **options) -> str:
        """Format test outline using specified formatter."""
        formatter = self.formatters.get(format_type.lower())
        if not formatter:
            raise ValueError(f"Unsupported format type: {format_type}")
        
        return formatter.format(test_outline, **options)
    
    def generate_coverage_report(self, test_outline: CaseOutline, requirements: List[Requirement], format_type: str = "text") -> str:
        """Generate a comprehensive coverage report."""
        coverage_data = self._analyze_coverage(test_outline, requirements)
        
        formatter = self.formatters.get(format_type.lower())
        if not formatter:
            raise ValueError(f"Unsupported format type: {format_type}")
        
        return formatter.format_coverage_report(coverage_data)
    
    def _analyze_coverage(self, test_outline: CaseOutline, requirements: List[Requirement]) -> Dict[str, Any]:
        """Analyze test coverage comprehensively."""
        req_coverage = test_outline.get_coverage_by_requirement()
        category_coverage = test_outline.get_coverage_by_category()
        priority_coverage = test_outline.get_coverage_by_priority()
        
        # Detailed requirement analysis
        covered_reqs = []
        uncovered_reqs = []
        
        for req in requirements:
            test_cases = req_coverage.get(req.id, [])
            if test_cases:
                covered_reqs.append({
                    "requirement": req,
                    "test_cases": test_cases,
                    "test_count": len(test_cases)
                })
            else:
                uncovered_reqs.append(req)
        
        # Quality metrics
        total_steps = sum(len(tc.test_steps) for tc in test_outline.test_cases)
        avg_steps = total_steps / len(test_outline.test_cases) if test_outline.test_cases else 0
        
        tests_with_preconditions = sum(1 for tc in test_outline.test_cases if tc.preconditions)
        precondition_coverage = (tests_with_preconditions / len(test_outline.test_cases) * 100) if test_outline.test_cases else 0
        
        # Risk analysis
        safety_reqs = [req for req in requirements if "safety" in req.text.lower()]
        safety_coverage = sum(1 for req in safety_reqs if req.id in req_coverage)
        safety_coverage_pct = (safety_coverage / len(safety_reqs) * 100) if safety_reqs else 100
        
        return {
            "summary": {
                "total_requirements": len(requirements),
                "covered_requirements": len(covered_reqs),
                "uncovered_requirements": len(uncovered_reqs),
                "coverage_percentage": (len(covered_reqs) / len(requirements) * 100) if requirements else 0,
                "total_test_cases": len(test_outline.test_cases),
                "total_test_steps": total_steps
            },
            "detailed_coverage": {
                "covered": covered_reqs,
                "uncovered": uncovered_reqs
            },
            "distribution": {
                "by_category": category_coverage,
                "by_priority": priority_coverage
            },
            "quality_metrics": {
                "average_steps_per_test": avg_steps,
                "precondition_coverage_percentage": precondition_coverage,
                "safety_coverage_percentage": safety_coverage_pct
            },
            "recommendations": self._generate_recommendations(uncovered_reqs, category_coverage, safety_coverage_pct)
        }
    
    def _generate_recommendations(self, uncovered_reqs: List[Requirement], category_coverage: Dict, safety_coverage_pct: float) -> List[str]:
        """Generate recommendations for improving test coverage."""
        recommendations = []
        
        if uncovered_reqs:
            recommendations.append(f"Create test cases for {len(uncovered_reqs)} uncovered requirements")
            
            # Prioritize safety requirements
            safety_uncovered = [req for req in uncovered_reqs if "safety" in req.text.lower()]
            if safety_uncovered:
                recommendations.append(f"PRIORITY: Address {len(safety_uncovered)} uncovered safety requirements immediately")
        
        if safety_coverage_pct < 100:
            recommendations.append("Ensure 100% test coverage for all safety-critical requirements")
        
        if "performance" not in category_coverage or category_coverage["performance"] < 2:
            recommendations.append("Add performance test cases for critical system operations")
        
        if "security" not in category_coverage or category_coverage["security"] == 0:
            recommendations.append("Include security test cases to verify access controls and data protection")
        
        return recommendations


# Format-specific formatter classes
class TextFormatter:
    """Plain text formatter for test cases."""
    
    def format(self, test_outline: CaseOutline, **options) -> str:
        """Format test outline as plain text."""
        include_metadata = options.get("include_metadata", True)
        include_coverage = options.get("include_coverage", True)
        
        lines = []
        lines.append(f"TEST CASE OUTLINE: {test_outline.project_name}")
        lines.append("=" * 80)
        lines.append(f"Generated: {test_outline.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Total Test Cases: {len(test_outline.test_cases)}")
        lines.append("")
        
        if include_coverage and test_outline.coverage_summary:
            lines.append("COVERAGE SUMMARY")
            lines.append("-" * 40)
            for key, value in test_outline.coverage_summary.items():
                lines.append(f"{key}: {value}")
            lines.append("")
        
        # Test cases
        for i, test_case in enumerate(test_outline.test_cases, 1):
            lines.append(f"TEST CASE {i}: {test_case.name}")
            lines.append("=" * 60)
            lines.append(f"ID: {test_case.id}")
            lines.append(f"Requirement ID: {test_case.requirement_id}")
            lines.append(f"Category: {test_case.category.value.upper()}")
            lines.append(f"Priority: {test_case.priority.value.upper()}")
            if test_case.estimated_duration:
                lines.append(f"Estimated Duration: {test_case.estimated_duration}")
            lines.append("")
            
            lines.append("DESCRIPTION:")
            lines.append(f"  {test_case.description}")
            lines.append("")
            
            if test_case.preconditions:
                lines.append("PRECONDITIONS:")
                for j, precondition in enumerate(test_case.preconditions, 1):
                    lines.append(f"  {j}. {precondition}")
                lines.append("")
            
            lines.append("TEST STEPS:")
            for step in test_case.test_steps:
                lines.append(f"  {step.step_number}. {step.action}")
                lines.append(f"     EXPECTED: {step.expected_result}")
                if step.notes:
                    lines.append(f"     NOTES: {step.notes}")
                lines.append("")
            
            if test_case.expected_results:
                lines.append("OVERALL EXPECTED RESULTS:")
                for j, result in enumerate(test_case.expected_results, 1):
                    lines.append(f"  {j}. {result}")
                lines.append("")
            
            if test_case.test_data_requirements:
                lines.append("TEST DATA REQUIREMENTS:")
                for req in test_case.test_data_requirements:
                    lines.append(f"  - {req}")
                lines.append("")
            
            if test_case.environment_requirements:
                lines.append("ENVIRONMENT REQUIREMENTS:")
                for req in test_case.environment_requirements:
                    lines.append(f"  - {req}")
                lines.append("")
            
            if include_metadata and test_case.metadata:
                lines.append("METADATA:")
                for key, value in test_case.metadata.items():
                    lines.append(f"  {key}: {value}")
                lines.append("")
            
            lines.append("=" * 80)
            lines.append("")
        
        return '\n'.join(lines)
    
    def format_coverage_report(self, coverage_data: Dict[str, Any]) -> str:
        """Format coverage report as plain text."""
        lines = []
        lines.append("TEST COVERAGE REPORT")
        lines.append("=" * 50)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Summary
        summary = coverage_data["summary"]
        lines.append("COVERAGE SUMMARY")
        lines.append("-" * 30)
        lines.append(f"Total Requirements: {summary['total_requirements']}")
        lines.append(f"Covered Requirements: {summary['covered_requirements']}")
        lines.append(f"Uncovered Requirements: {summary['uncovered_requirements']}")
        lines.append(f"Coverage Percentage: {summary['coverage_percentage']:.1f}%")
        lines.append(f"Total Test Cases: {summary['total_test_cases']}")
        lines.append(f"Total Test Steps: {summary['total_test_steps']}")
        lines.append("")
        
        # Quality metrics
        metrics = coverage_data["quality_metrics"]
        lines.append("QUALITY METRICS")
        lines.append("-" * 30)
        lines.append(f"Average Steps per Test: {metrics['average_steps_per_test']:.1f}")
        lines.append(f"Precondition Coverage: {metrics['precondition_coverage_percentage']:.1f}%")
        lines.append(f"Safety Coverage: {metrics['safety_coverage_percentage']:.1f}%")
        lines.append("")
        
        # Recommendations
        recommendations = coverage_data["recommendations"]
        if recommendations:
            lines.append("RECOMMENDATIONS")
            lines.append("-" * 30)
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")
        
        return '\n'.join(lines)


class JSONFormatter:
    """JSON formatter for test cases."""
    
    def format(self, test_outline: CaseOutline, **options) -> str:
        """Format test outline as JSON."""
        data = {
            "project_name": test_outline.project_name,
            "created_at": test_outline.created_at.isoformat(),
            "test_cases": [tc.to_dict() for tc in test_outline.test_cases],
            "coverage_summary": test_outline.coverage_summary,
            "generation_metadata": test_outline.generation_metadata
        }
        
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def format_coverage_report(self, coverage_data: Dict[str, Any]) -> str:
        """Format coverage report as JSON."""
        return json.dumps(coverage_data, indent=2, ensure_ascii=False, default=str)


class XMLFormatter:
    """XML formatter for test cases."""
    
    def format(self, test_outline: CaseOutline, **options) -> str:
        """Format test outline as XML."""
        root = ET.Element("test_outline")
        root.set("project_name", test_outline.project_name)
        root.set("created_at", test_outline.created_at.isoformat())
        
        # Test cases
        test_cases_elem = ET.SubElement(root, "test_cases")
        for test_case in test_outline.test_cases:
            tc_elem = self._test_case_to_xml(test_case)
            test_cases_elem.append(tc_elem)
        
        # Coverage summary
        if test_outline.coverage_summary:
            coverage_elem = ET.SubElement(root, "coverage_summary")
            for key, value in test_outline.coverage_summary.items():
                item_elem = ET.SubElement(coverage_elem, "item")
                item_elem.set("key", str(key))
                item_elem.text = str(value)
        
        return self._prettify_xml(root)
    
    def _test_case_to_xml(self, test_case: CaseModel) -> ET.Element:
        """Convert test case to XML element."""
        tc_elem = ET.Element("test_case")
        tc_elem.set("id", test_case.id)
        tc_elem.set("requirement_id", test_case.requirement_id)
        tc_elem.set("category", test_case.category.value)
        tc_elem.set("priority", test_case.priority.value)
        
        ET.SubElement(tc_elem, "name").text = test_case.name
        ET.SubElement(tc_elem, "description").text = test_case.description
        
        if test_case.estimated_duration:
            ET.SubElement(tc_elem, "estimated_duration").text = test_case.estimated_duration
        
        # Preconditions
        if test_case.preconditions:
            precond_elem = ET.SubElement(tc_elem, "preconditions")
            for precondition in test_case.preconditions:
                ET.SubElement(precond_elem, "precondition").text = precondition
        
        # Test steps
        steps_elem = ET.SubElement(tc_elem, "test_steps")
        for step in test_case.test_steps:
            step_elem = ET.SubElement(steps_elem, "test_step")
            step_elem.set("number", str(step.step_number))
            ET.SubElement(step_elem, "action").text = step.action
            ET.SubElement(step_elem, "expected_result").text = step.expected_result
            if step.notes:
                ET.SubElement(step_elem, "notes").text = step.notes
        
        return tc_elem
    
    def _prettify_xml(self, elem: ET.Element) -> str:
        """Return a pretty-printed XML string."""
        import xml.dom.minidom
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = xml.dom.minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    def format_coverage_report(self, coverage_data: Dict[str, Any]) -> str:
        """Format coverage report as XML."""
        root = ET.Element("coverage_report")
        root.set("generated_at", datetime.now().isoformat())
        
        # Summary
        summary_elem = ET.SubElement(root, "summary")
        for key, value in coverage_data["summary"].items():
            item_elem = ET.SubElement(summary_elem, key)
            item_elem.text = str(value)
        
        return self._prettify_xml(root)


class CSVFormatter:
    """CSV formatter for test cases."""
    
    def format(self, test_outline: CaseOutline, **options) -> str:
        """Format test outline as CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Headers
        headers = [
            "Test Case ID", "Name", "Description", "Requirement ID",
            "Category", "Priority", "Estimated Duration",
            "Preconditions", "Test Steps", "Expected Results",
            "Test Data Requirements", "Environment Requirements"
        ]
        writer.writerow(headers)
        
        # Test cases
        for test_case in test_outline.test_cases:
            row = [
                test_case.id,
                test_case.name,
                test_case.description,
                test_case.requirement_id,
                test_case.category.value,
                test_case.priority.value,
                test_case.estimated_duration or "",
                "; ".join(test_case.preconditions),
                "; ".join([f"Step {s.step_number}: {s.action} -> {s.expected_result}" for s in test_case.test_steps]),
                "; ".join(test_case.expected_results),
                "; ".join(test_case.test_data_requirements),
                "; ".join(test_case.environment_requirements)
            ]
            writer.writerow(row)
        
        return output.getvalue()
    
    def format_coverage_report(self, coverage_data: Dict[str, Any]) -> str:
        """Format coverage report as CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Summary section
        writer.writerow(["Coverage Summary"])
        for key, value in coverage_data["summary"].items():
            writer.writerow([key, value])
        
        writer.writerow([])  # Empty row
        
        # Detailed coverage
        writer.writerow(["Requirement ID", "Coverage Status", "Test Case Count"])
        for item in coverage_data["detailed_coverage"]["covered"]:
            writer.writerow([item["requirement"].id, "Covered", item["test_count"]])
        
        for req in coverage_data["detailed_coverage"]["uncovered"]:
            writer.writerow([req.id, "Not Covered", 0])
        
        return output.getvalue()


class HTMLFormatter:
    """HTML formatter for test cases."""
    
    def format(self, test_outline: CaseOutline, **options) -> str:
        """Format test outline as HTML."""
        html_parts = []
        html_parts.append("<!DOCTYPE html>")
        html_parts.append("<html><head>")
        html_parts.append("<title>Test Case Outline</title>")
        html_parts.append("<style>")
        html_parts.append(self._get_css_styles())
        html_parts.append("</style>")
        html_parts.append("</head><body>")
        
        # Header
        html_parts.append(f"<h1>Test Case Outline: {test_outline.project_name}</h1>")
        html_parts.append(f"<p>Generated: {test_outline.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>")
        html_parts.append(f"<p>Total Test Cases: {len(test_outline.test_cases)}</p>")
        
        # Test cases
        for i, test_case in enumerate(test_outline.test_cases, 1):
            html_parts.append(f"<div class='test-case'>")
            html_parts.append(f"<h2>Test Case {i}: {test_case.name}</h2>")
            html_parts.append(f"<p><strong>ID:</strong> {test_case.id}</p>")
            html_parts.append(f"<p><strong>Requirement ID:</strong> {test_case.requirement_id}</p>")
            html_parts.append(f"<p><strong>Category:</strong> {test_case.category.value}</p>")
            html_parts.append(f"<p><strong>Priority:</strong> {test_case.priority.value}</p>")
            
            html_parts.append(f"<h3>Description</h3>")
            html_parts.append(f"<p>{test_case.description}</p>")
            
            if test_case.preconditions:
                html_parts.append("<h3>Preconditions</h3>")
                html_parts.append("<ul>")
                for precondition in test_case.preconditions:
                    html_parts.append(f"<li>{precondition}</li>")
                html_parts.append("</ul>")
            
            html_parts.append("<h3>Test Steps</h3>")
            html_parts.append("<ol>")
            for step in test_case.test_steps:
                html_parts.append(f"<li>{step.action}<br><em>Expected: {step.expected_result}</em></li>")
            html_parts.append("</ol>")
            
            html_parts.append("</div>")
        
        html_parts.append("</body></html>")
        return '\n'.join(html_parts)
    
    def _get_css_styles(self) -> str:
        """Get CSS styles for HTML formatting."""
        return """
        body { font-family: Arial, sans-serif; margin: 20px; }
        .test-case { border: 1px solid #ccc; margin: 20px 0; padding: 15px; }
        h1 { color: #333; }
        h2 { color: #666; border-bottom: 1px solid #eee; }
        h3 { color: #888; }
        em { color: #666; }
        """
    
    def format_coverage_report(self, coverage_data: Dict[str, Any]) -> str:
        """Format coverage report as HTML."""
        # Implementation similar to format method but for coverage data
        return "<html><body><h1>Coverage Report</h1></body></html>"


class MarkdownFormatter:
    """Markdown formatter for test cases."""
    
    def format(self, test_outline: CaseOutline, **options) -> str:
        """Format test outline as Markdown."""
        lines = []
        lines.append(f"# Test Case Outline: {test_outline.project_name}")
        lines.append("")
        lines.append(f"**Generated:** {test_outline.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Total Test Cases:** {len(test_outline.test_cases)}")
        lines.append("")
        
        for i, test_case in enumerate(test_outline.test_cases, 1):
            lines.append(f"## Test Case {i}: {test_case.name}")
            lines.append("")
            lines.append(f"- **ID:** {test_case.id}")
            lines.append(f"- **Requirement ID:** {test_case.requirement_id}")
            lines.append(f"- **Category:** {test_case.category.value}")
            lines.append(f"- **Priority:** {test_case.priority.value}")
            lines.append("")
            
            lines.append("### Description")
            lines.append(test_case.description)
            lines.append("")
            
            if test_case.preconditions:
                lines.append("### Preconditions")
                for precondition in test_case.preconditions:
                    lines.append(f"- {precondition}")
                lines.append("")
            
            lines.append("### Test Steps")
            for step in test_case.test_steps:
                lines.append(f"{step.step_number}. {step.action}")
                lines.append(f"   - **Expected:** {step.expected_result}")
            lines.append("")
        
        return '\n'.join(lines)
    
    def format_coverage_report(self, coverage_data: Dict[str, Any]) -> str:
        """Format coverage report as Markdown."""
        lines = []
        lines.append("# Test Coverage Report")
        lines.append("")
        
        summary = coverage_data["summary"]
        lines.append("## Summary")
        lines.append(f"- Total Requirements: {summary['total_requirements']}")
        lines.append(f"- Covered Requirements: {summary['covered_requirements']}")
        lines.append(f"- Coverage Percentage: {summary['coverage_percentage']:.1f}%")
        lines.append("")
        
        return '\n'.join(lines)
