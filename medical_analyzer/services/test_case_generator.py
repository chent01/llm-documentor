"""
Test Case Generation Service for Medical Software Analysis.

This service generates exportable test case outlines based on requirements,
providing structured test templates that can be exported in multiple formats
for use in external test projects.
"""

from typing import List, Dict, Any, Optional
import json
import xml.etree.ElementTree as ET
import csv
import io

from ..models.core import Requirement
from ..llm.operation_configs import get_operation_params
from ..models.test_models import CaseModel, CaseOutline, CaseStep, CasePriority, CaseCategory, CoverageReport
from ..llm.backend import LLMBackend
from .test_case_templates import CaseTemplateManager


class CaseGenerator:
    """Service for generating exportable test case outlines."""
    
    def __init__(self, llm_backend: Optional[LLMBackend] = None):
        """Initialize test case generator.
        
        Args:
            llm_backend: Optional LLM backend for intelligent test generation
        """
        self.llm_backend = llm_backend
        self.template_manager = CaseTemplateManager()
        self.templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize test case templates for different requirement types."""
        return {
            "functional": {
                "category": CaseCategory.FUNCTIONAL,
                "priority": CasePriority.HIGH,
                "template_steps": [
                    "Verify system initialization",
                    "Execute the required functionality",
                    "Validate expected outputs",
                    "Verify system state after execution"
                ]
            },
            "safety": {
                "category": CaseCategory.SAFETY,
                "priority": CasePriority.CRITICAL,
                "template_steps": [
                    "Set up safety-critical conditions",
                    "Trigger safety mechanism",
                    "Verify safety response",
                    "Confirm system enters safe state"
                ]
            },
            "performance": {
                "category": CaseCategory.PERFORMANCE,
                "priority": CasePriority.MEDIUM,
                "template_steps": [
                    "Establish baseline conditions",
                    "Execute performance-critical operation",
                    "Measure performance metrics",
                    "Verify performance requirements are met"
                ]
            },
            "usability": {
                "category": CaseCategory.USABILITY,
                "priority": CasePriority.MEDIUM,
                "template_steps": [
                    "Set up user interface",
                    "Perform user interaction",
                    "Evaluate user experience",
                    "Verify usability requirements"
                ]
            }
        }
    
    def generate_test_cases(self, requirements: List[Requirement]) -> CaseOutline:
        """Generate test cases for a list of requirements.
        
        Args:
            requirements: List of requirements to generate tests for
            
        Returns:
            CaseOutline containing generated test cases
        """
        test_cases = []
        
        for requirement in requirements:
            # Generate test cases for each requirement
            req_test_cases = self._generate_test_cases_for_requirement(requirement)
            test_cases.extend(req_test_cases)
        
        # Generate coverage summary
        coverage_summary = self._generate_coverage_summary(test_cases, requirements)
        
        # Create test outline
        test_outline = CaseOutline(
            project_name="Medical Software Analysis",
            test_cases=test_cases,
            coverage_summary=coverage_summary,
            export_formats=["text", "json", "xml", "csv"],
            generation_metadata={
                "generator_version": "1.0.0",
                "requirements_count": len(requirements),
                "test_cases_count": len(test_cases),
                "llm_backend": self.llm_backend.__class__.__name__ if self.llm_backend else "template_based"
            }
        )
        
        return test_outline
    
    def _generate_test_cases_for_requirement(self, requirement: Requirement) -> List[CaseModel]:
        """Generate test cases for a single requirement.
        
        Args:
            requirement: Requirement to generate tests for
            
        Returns:
            List of test cases for the requirement
        """
        test_cases = []
        
        # Determine test case category based on requirement content
        category = self._determine_test_category(requirement)
        template = self.templates.get(category.value, self.templates["functional"])
        
        # Generate main test case
        main_test_case = self._create_main_test_case(requirement, template)
        test_cases.append(main_test_case)
        
        # Generate edge case test if acceptance criteria exist
        if requirement.acceptance_criteria:
            edge_test_case = self._create_edge_case_test(requirement, template)
            test_cases.append(edge_test_case)
        
        # Generate negative test case for safety-critical requirements
        if category == CaseCategory.SAFETY:
            negative_test_case = self._create_negative_test_case(requirement, template)
            test_cases.append(negative_test_case)
        
        return test_cases
    
    def _determine_test_category(self, requirement: Requirement) -> CaseCategory:
        """Determine appropriate test category for a requirement using template manager.
        
        Args:
            requirement: Requirement to categorize
            
        Returns:
            Appropriate test case category
        """
        template = self.template_manager.get_template_for_requirement(requirement)
        return template.category
    
    def _create_main_test_case(self, requirement: Requirement, template: Dict[str, Any]) -> CaseModel:
        """Create main test case for a requirement using enhanced templates.
        
        Args:
            requirement: Requirement to create test for
            template: Test case template to use (legacy format)
            
        Returns:
            Main test case for the requirement
        """
        test_case_id = f"TC_{requirement.id}_001"
        
        # Use enhanced template system
        enhanced_template = self.template_manager.get_template_for_requirement(requirement)
        template_data = enhanced_template.apply_to_requirement(requirement)
        
        # Generate test steps based on acceptance criteria or template
        test_steps = []
        if requirement.acceptance_criteria:
            test_steps = self._generate_steps_from_criteria(requirement.acceptance_criteria)
        else:
            test_steps = self._generate_steps_from_template(enhanced_template.steps_template)
        
        # Use LLM for intelligent test generation if available
        if self.llm_backend and self.llm_backend.is_available():
            try:
                enhanced_steps = self._enhance_test_steps_with_llm(requirement, test_steps)
                test_steps = enhanced_steps
            except Exception:
                # Fall back to template-based generation
                pass
        
        return CaseModel(
            id=test_case_id,
            name=template_data["name"],
            description=template_data["description"],
            requirement_id=requirement.id,
            preconditions=template_data["preconditions"],
            test_steps=test_steps,
            expected_results=template_data["expected_results"],
            priority=template_data["priority"],
            category=template_data["category"],
            estimated_duration="30 minutes",
            test_data_requirements=["Standard test dataset", "Boundary value test data"],
            environment_requirements=["Test environment", "Monitoring tools"],
            traceability_links=[requirement.id],
            metadata={
                **template_data["metadata"],
                "generation_method": "llm" if self.llm_backend else "template"
            }
        )
    
    def _create_edge_case_test(self, requirement: Requirement, template: Dict[str, Any]) -> CaseModel:
        """Create edge case test for a requirement.
        
        Args:
            requirement: Requirement to create test for
            template: Test case template to use
            
        Returns:
            Edge case test for the requirement
        """
        test_case_id = f"TC_{requirement.id}_002"
        
        edge_steps = [
            CaseStep(1, "Set up boundary conditions", "System accepts boundary inputs"),
            CaseStep(2, "Execute functionality with edge case inputs", "System processes edge cases correctly"),
            CaseStep(3, "Verify system behavior at boundaries", "System maintains correct behavior"),
            CaseStep(4, "Validate error handling for invalid inputs", "System handles errors gracefully")
        ]
        
        return CaseModel(
            id=test_case_id,
            name=f"Edge Case Test {requirement.text[:40]}...",
            description=f"Verify edge case handling for requirement: {requirement.text}",
            requirement_id=requirement.id,
            preconditions=[
                "System is initialized",
                "Edge case test data is prepared",
                "Error monitoring is enabled"
            ],
            test_steps=edge_steps,
            expected_results=[
                "System handles boundary conditions correctly",
                "Error conditions are properly managed",
                "System remains stable under edge conditions"
            ],
            priority=CasePriority.MEDIUM,
            category=template["category"],
            estimated_duration="45 minutes",
            test_data_requirements=["Boundary value data", "Invalid input data"],
            environment_requirements=["Test environment", "Error logging"],
            traceability_links=[requirement.id],
            metadata={
                "test_type": "edge_case",
                "requirement_type": requirement.type.value
            }
        )
    
    def _create_negative_test_case(self, requirement: Requirement, template: Dict[str, Any]) -> CaseModel:
        """Create negative test case for safety-critical requirements.
        
        Args:
            requirement: Requirement to create test for
            template: Test case template to use
            
        Returns:
            Negative test case for the requirement
        """
        test_case_id = f"TC_{requirement.id}_003"
        
        negative_steps = [
            CaseStep(1, "Introduce failure conditions", "Failure conditions are established"),
            CaseStep(2, "Attempt to violate safety requirement", "System detects violation attempt"),
            CaseStep(3, "Verify safety mechanisms activate", "Safety mechanisms respond correctly"),
            CaseStep(4, "Confirm system enters safe state", "System is in documented safe state")
        ]
        
        return CaseModel(
            id=test_case_id,
            name=f"Negative Test {requirement.text[:40]}...",
            description=f"Verify safety mechanisms for requirement: {requirement.text}",
            requirement_id=requirement.id,
            preconditions=[
                "System is in operational state",
                "Safety monitoring is active",
                "Failure simulation capability is available"
            ],
            test_steps=negative_steps,
            expected_results=[
                "Safety violations are detected",
                "Safety mechanisms activate as designed",
                "System enters safe state without harm"
            ],
            priority=CasePriority.CRITICAL,
            category=CaseCategory.SAFETY,
            estimated_duration="60 minutes",
            test_data_requirements=["Failure scenario data", "Safety threshold data"],
            environment_requirements=["Safety test environment", "Failure simulation tools"],
            traceability_links=[requirement.id],
            metadata={
                "test_type": "negative_safety",
                "requirement_type": requirement.type.value
            }
        )
    
    def _generate_steps_from_criteria(self, acceptance_criteria: List[str]) -> List[CaseStep]:
        """Generate test steps from acceptance criteria.
        
        Args:
            acceptance_criteria: List of acceptance criteria
            
        Returns:
            List of test steps based on criteria
        """
        test_steps = []
        
        for i, criterion in enumerate(acceptance_criteria, 1):
            # Parse EARS format criteria (WHEN/IF...THEN...SHALL)
            if "WHEN" in criterion.upper() and "THEN" in criterion.upper():
                parts = criterion.upper().split("THEN")
                condition = parts[0].replace("WHEN", "").strip()
                expected = parts[1].replace("SHALL", "").strip()
                
                action = f"Execute condition: {condition}"
                result = f"Verify: {expected}"
            else:
                action = f"Verify acceptance criterion: {criterion}"
                result = f"Criterion is satisfied: {criterion}"
            
            test_steps.append(CaseStep(
                step_number=i,
                action=action,
                expected_result=result,
                notes=f"Based on acceptance criterion {i}"
            ))
        
        return test_steps
    
    def _generate_steps_from_template(self, template_steps: List[str]) -> List[CaseStep]:
        """Generate test steps from template.
        
        Args:
            template_steps: List of template step descriptions
            
        Returns:
            List of test steps based on template
        """
        test_steps = []
        
        for i, step_desc in enumerate(template_steps, 1):
            test_steps.append(CaseStep(
                step_number=i,
                action=step_desc,
                expected_result=f"Step {i} completes successfully",
                notes="Generated from template"
            ))
        
        return test_steps
    
    def _enhance_test_steps_with_llm(self, requirement: Requirement, base_steps: List[CaseStep]) -> List[CaseStep]:
        """Enhance test steps using LLM for more detailed and specific steps.
        
        Args:
            requirement: Requirement being tested
            base_steps: Base test steps to enhance
            
        Returns:
            Enhanced test steps
        """
        if not self.llm_backend or not self.llm_backend.is_available():
            return base_steps
        
        # Create prompt for LLM to enhance test steps
        prompt = f"""
        Given the following requirement and basic test steps, enhance the test steps to be more specific and detailed for medical software testing:
        
        Requirement: {requirement.text}
        Acceptance Criteria: {'; '.join(requirement.acceptance_criteria)}
        
        Basic Test Steps:
        {chr(10).join([f"{step.step_number}. {step.action} -> {step.expected_result}" for step in base_steps])}
        
        Please provide enhanced test steps that are:
        1. More specific and actionable
        2. Include relevant medical software considerations
        3. Specify clear verification criteria
        4. Include appropriate safety checks
        
        Format as: Step Number. Action -> Expected Result
        """
        
        try:
            params = get_operation_params("test_case_generation")
            response = self.llm_backend.generate(
                prompt=prompt,
                system_prompt="You are a medical software test engineer creating detailed test procedures.",
                **params
            )
            
            # Parse LLM response to extract enhanced steps
            enhanced_steps = self._parse_llm_test_steps(response)
            return enhanced_steps if enhanced_steps else base_steps
            
        except Exception:
            # Fall back to base steps if LLM enhancement fails
            return base_steps
    
    def _parse_llm_test_steps(self, llm_response: str) -> List[CaseStep]:
        """Parse LLM response to extract test steps.
        
        Args:
            llm_response: LLM generated response
            
        Returns:
            List of parsed test steps
        """
        test_steps = []
        lines = llm_response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or not any(char.isdigit() for char in line[:5]):
                continue
            
            # Look for pattern: "Number. Action -> Expected Result"
            if '->' in line:
                parts = line.split('->', 1)
                if len(parts) == 2:
                    action_part = parts[0].strip()
                    result_part = parts[1].strip()
                    
                    # Extract step number
                    step_num = 1
                    if '.' in action_part:
                        num_part = action_part.split('.', 1)[0].strip()
                        try:
                            step_num = int(''.join(filter(str.isdigit, num_part)))
                        except ValueError:
                            step_num = len(test_steps) + 1
                        
                        action = action_part.split('.', 1)[1].strip()
                    else:
                        action = action_part
                    
                    test_steps.append(CaseStep(
                        step_number=step_num,
                        action=action,
                        expected_result=result_part,
                        notes="Enhanced by LLM"
                    ))
        
        return test_steps
    
    def _generate_coverage_summary(self, test_cases: List[CaseModel], requirements: List[Requirement]) -> Dict[str, Any]:
        """Generate coverage summary for test cases.
        
        Args:
            test_cases: Generated test cases
            requirements: Original requirements
            
        Returns:
            Coverage summary dictionary
        """
        # Calculate requirement coverage
        covered_requirements = set(tc.requirement_id for tc in test_cases)
        total_requirements = len(requirements)
        coverage_percentage = (len(covered_requirements) / total_requirements * 100) if total_requirements > 0 else 0
        
        # Calculate category distribution
        category_counts = {}
        for test_case in test_cases:
            category = test_case.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Calculate priority distribution
        priority_counts = {}
        for test_case in test_cases:
            priority = test_case.priority.value
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        return {
            "total_test_cases": len(test_cases),
            "total_requirements": total_requirements,
            "covered_requirements": len(covered_requirements),
            "coverage_percentage": round(coverage_percentage, 2),
            "category_distribution": category_counts,
            "priority_distribution": priority_counts,
            "uncovered_requirements": [req.id for req in requirements if req.id not in covered_requirements]
        }   
 
    def export_test_cases(self, test_data, format_type: str, **options) -> str:
        """Export test cases in specified format using enhanced templates.
        
        Args:
            test_data: Either CaseOutline or List[CaseModel] containing test cases to export
            format_type: Export format ('text', 'json', 'xml', 'csv', 'html', 'markdown')
            **options: Additional formatting options
            
        Returns:
            Exported test cases as string
            
        Raises:
            ValueError: If format_type is not supported
        """
        # Handle both CaseOutline and List[CaseModel] inputs
        if isinstance(test_data, list):
            # Convert list of CaseModel to CaseOutline
            test_outline = CaseOutline(
                project_name="Medical Software Analysis",
                test_cases=test_data,
                coverage_summary={},
                export_formats=["text", "json", "xml", "csv"],
                generation_metadata={"test_cases_count": len(test_data)}
            )
        else:
            test_outline = test_data
        
        try:
            return self.template_manager.format_test_outline(test_outline, format_type, **options)
        except ValueError:
            # Fall back to legacy formatters for backward compatibility
            if format_type.lower() == 'text':
                return self._export_to_text(test_outline)
            elif format_type.lower() == 'json':
                return self._export_to_json(test_outline)
            elif format_type.lower() == 'xml':
                return self._export_to_xml(test_outline)
            elif format_type.lower() == 'csv':
                return self._export_to_csv(test_outline)
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
    
    def _export_to_text(self, test_outline: CaseOutline) -> str:
        """Export test cases to plain text format.
        
        Args:
            test_outline: Test outline to export
            
        Returns:
            Plain text representation of test cases
        """
        lines = []
        lines.append(f"Test Case Outline: {test_outline.project_name}")
        lines.append("=" * 60)
        lines.append(f"Generated: {test_outline.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Total Test Cases: {len(test_outline.test_cases)}")
        lines.append("")
        
        # Coverage summary
        lines.append("Coverage Summary:")
        lines.append("-" * 20)
        for key, value in test_outline.coverage_summary.items():
            lines.append(f"{key}: {value}")
        lines.append("")
        
        # Test cases
        for i, test_case in enumerate(test_outline.test_cases, 1):
            lines.append(f"Test Case {i}: {test_case.name}")
            lines.append("-" * 40)
            lines.append(f"ID: {test_case.id}")
            lines.append(f"Requirement ID: {test_case.requirement_id}")
            lines.append(f"Category: {test_case.category.value}")
            lines.append(f"Priority: {test_case.priority.value}")
            lines.append(f"Estimated Duration: {test_case.estimated_duration}")
            lines.append("")
            
            lines.append("Description:")
            lines.append(f"  {test_case.description}")
            lines.append("")
            
            if test_case.preconditions:
                lines.append("Preconditions:")
                for precondition in test_case.preconditions:
                    lines.append(f"  - {precondition}")
                lines.append("")
            
            lines.append("Test Steps:")
            for step in test_case.test_steps:
                lines.append(f"  {step.step_number}. {step.action}")
                lines.append(f"     Expected: {step.expected_result}")
                if step.notes:
                    lines.append(f"     Notes: {step.notes}")
                lines.append("")
            
            if test_case.expected_results:
                lines.append("Overall Expected Results:")
                for result in test_case.expected_results:
                    lines.append(f"  - {result}")
                lines.append("")
            
            if test_case.test_data_requirements:
                lines.append("Test Data Requirements:")
                for req in test_case.test_data_requirements:
                    lines.append(f"  - {req}")
                lines.append("")
            
            if test_case.environment_requirements:
                lines.append("Environment Requirements:")
                for req in test_case.environment_requirements:
                    lines.append(f"  - {req}")
                lines.append("")
            
            lines.append("=" * 60)
            lines.append("")
        
        return '\n'.join(lines)
    
    def _export_to_json(self, test_outline: CaseOutline) -> str:
        """Export test cases to JSON format.
        
        Args:
            test_outline: Test outline to export
            
        Returns:
            JSON representation of test cases
        """
        export_data = {
            "project_name": test_outline.project_name,
            "created_at": test_outline.created_at.isoformat(),
            "coverage_summary": test_outline.coverage_summary,
            "generation_metadata": test_outline.generation_metadata,
            "test_cases": [test_case.to_dict() for test_case in test_outline.test_cases]
        }
        
        return json.dumps(export_data, indent=2, ensure_ascii=False)
    
    def _export_to_xml(self, test_outline: CaseOutline) -> str:
        """Export test cases to XML format.
        
        Args:
            test_outline: Test outline to export
            
        Returns:
            XML representation of test cases
        """
        root = ET.Element("test_outline")
        root.set("project_name", test_outline.project_name)
        root.set("created_at", test_outline.created_at.isoformat())
        
        # Coverage summary
        coverage_elem = ET.SubElement(root, "coverage_summary")
        for key, value in test_outline.coverage_summary.items():
            item_elem = ET.SubElement(coverage_elem, "item")
            item_elem.set("key", str(key))
            item_elem.text = str(value)
        
        # Test cases
        test_cases_elem = ET.SubElement(root, "test_cases")
        for test_case in test_outline.test_cases:
            tc_elem = ET.SubElement(test_cases_elem, "test_case")
            tc_elem.set("id", test_case.id)
            tc_elem.set("requirement_id", test_case.requirement_id)
            tc_elem.set("category", test_case.category.value)
            tc_elem.set("priority", test_case.priority.value)
            
            # Basic info
            ET.SubElement(tc_elem, "name").text = test_case.name
            ET.SubElement(tc_elem, "description").text = test_case.description
            ET.SubElement(tc_elem, "estimated_duration").text = test_case.estimated_duration or ""
            
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
            
            # Expected results
            if test_case.expected_results:
                results_elem = ET.SubElement(tc_elem, "expected_results")
                for result in test_case.expected_results:
                    ET.SubElement(results_elem, "result").text = result
            
            # Requirements
            if test_case.test_data_requirements:
                data_req_elem = ET.SubElement(tc_elem, "test_data_requirements")
                for req in test_case.test_data_requirements:
                    ET.SubElement(data_req_elem, "requirement").text = req
            
            if test_case.environment_requirements:
                env_req_elem = ET.SubElement(tc_elem, "environment_requirements")
                for req in test_case.environment_requirements:
                    ET.SubElement(env_req_elem, "requirement").text = req
        
        # Convert to string with proper formatting
        import xml.dom.minidom
        rough_string = ET.tostring(root, encoding='unicode')
        reparsed = xml.dom.minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    def _export_to_csv(self, test_outline: CaseOutline) -> str:
        """Export test cases to CSV format.
        
        Args:
            test_outline: Test outline to export
            
        Returns:
            CSV representation of test cases
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        headers = [
            "Test Case ID", "Name", "Description", "Requirement ID", 
            "Category", "Priority", "Estimated Duration",
            "Preconditions", "Test Steps", "Expected Results",
            "Test Data Requirements", "Environment Requirements",
            "Traceability Links", "Created At"
        ]
        writer.writerow(headers)
        
        # Write test cases
        for test_case in test_outline.test_cases:
            # Format complex fields as semicolon-separated strings
            preconditions = "; ".join(test_case.preconditions)
            
            test_steps = "; ".join([
                f"Step {step.step_number}: {step.action} -> {step.expected_result}"
                for step in test_case.test_steps
            ])
            
            expected_results = "; ".join(test_case.expected_results)
            test_data_reqs = "; ".join(test_case.test_data_requirements)
            env_reqs = "; ".join(test_case.environment_requirements)
            traceability = "; ".join(test_case.traceability_links)
            
            row = [
                test_case.id,
                test_case.name,
                test_case.description,
                test_case.requirement_id,
                test_case.category.value,
                test_case.priority.value,
                test_case.estimated_duration or "",
                preconditions,
                test_steps,
                expected_results,
                test_data_reqs,
                env_reqs,
                traceability,
                test_case.created_at.isoformat()
            ]
            writer.writerow(row)
        
        return output.getvalue()
    
    def generate_coverage_report(self, test_data, requirements: List[Requirement] = None) -> Dict[str, Any]:
        """Generate detailed coverage report.
        
        Args:
            test_data: Either CaseOutline or List[CaseModel] to analyze
            requirements: Original requirements list (optional)
            
        Returns:
            Detailed coverage report
        """
        # Handle both CaseOutline and List[CaseModel] inputs
        if isinstance(test_data, list):
            # Convert list of CaseModel to CaseOutline
            test_outline = CaseOutline(
                project_name="Medical Software Analysis",
                test_cases=test_data,
                coverage_summary={},
                export_formats=["text", "json", "xml", "csv"],
                generation_metadata={"test_cases_count": len(test_data)}
            )
        else:
            test_outline = test_data
        
        # If no requirements provided, try to infer from test cases
        if requirements is None:
            # Extract unique requirement IDs from test cases
            req_ids = set()
            for test_case in test_outline.test_cases:
                if hasattr(test_case, 'requirement_id') and test_case.requirement_id:
                    req_ids.add(test_case.requirement_id)
            
            # Create mock requirements for coverage calculation
            from ..models.core import RequirementType
            requirements = []
            for req_id in req_ids:
                # Create a minimal requirement object for coverage calculation
                mock_req = type('MockRequirement', (), {
                    'id': req_id,
                    'text': f'Requirement {req_id}',
                    'type': RequirementType.USER
                })()
                requirements.append(mock_req)
        
        # Requirement coverage analysis
        req_coverage = test_outline.get_coverage_by_requirement() if hasattr(test_outline, 'get_coverage_by_requirement') else {}
        uncovered_reqs = [req for req in requirements if req.id not in req_coverage]
        
        # Gap analysis
        gaps = []
        for req in uncovered_reqs:
            gaps.append({
                "requirement_id": req.id,
                "requirement_text": req.text,
                "requirement_type": req.type.value,
                "gap_type": "no_test_coverage",
                "severity": "high" if "safety" in req.text.lower() else "medium"
            })
        
        # Test case distribution analysis
        category_dist = test_outline.get_coverage_by_category()
        priority_dist = test_outline.get_coverage_by_priority()
        
        # Quality metrics
        total_steps = sum(len(tc.test_steps) for tc in test_outline.test_cases)
        avg_steps_per_test = total_steps / len(test_outline.test_cases) if test_outline.test_cases else 0
        
        tests_with_preconditions = sum(1 for tc in test_outline.test_cases if tc.preconditions)
        precondition_coverage = (tests_with_preconditions / len(test_outline.test_cases) * 100) if test_outline.test_cases else 0
        
        # Create CoverageReport object
        coverage_percentage = round((len(req_coverage) / len(requirements) * 100), 2) if requirements else 0
        
        return CoverageReport(
            total_requirements=len(requirements),
            covered_requirements=len(req_coverage),
            coverage_percentage=coverage_percentage,
            requirement_coverage=req_coverage,
            uncovered_requirements=[req.id for req in uncovered_reqs],
            test_case_count=len(test_outline.test_cases),
            priority_distribution=priority_dist,
            category_distribution=category_dist
        )
    
    def _generate_coverage_recommendations(self, gaps: List[Dict], category_dist: Dict, priority_dist: Dict) -> List[str]:
        """Generate recommendations for improving test coverage.
        
        Args:
            gaps: List of coverage gaps
            category_dist: Category distribution
            priority_dist: Priority distribution
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Gap-based recommendations
        if gaps:
            high_severity_gaps = [gap for gap in gaps if gap["severity"] == "high"]
            if high_severity_gaps:
                recommendations.append(f"Address {len(high_severity_gaps)} high-severity coverage gaps immediately")
            
            recommendations.append(f"Create test cases for {len(gaps)} uncovered requirements")
        
        # Category balance recommendations
        if "safety" not in category_dist or category_dist.get("safety", 0) == 0:
            recommendations.append("Add safety-focused test cases to ensure regulatory compliance")
        
        if "performance" not in category_dist or category_dist.get("performance", 0) < 2:
            recommendations.append("Consider adding performance test cases for critical operations")
        
        # Priority balance recommendations
        critical_tests = priority_dist.get("critical", 0)
        total_tests = sum(priority_dist.values())
        if total_tests > 0 and (critical_tests / total_tests) < 0.2:
            recommendations.append("Increase proportion of critical priority test cases")
        
        if not recommendations:
            recommendations.append("Test coverage appears comprehensive - consider adding edge case scenarios")
        
        return recommendations
    
    def generate_enhanced_coverage_report(self, test_outline: CaseOutline, requirements: List[Requirement], format_type: str = "text") -> str:
        """Generate enhanced coverage report using template manager.
        
        Args:
            test_outline: Test outline to analyze
            requirements: Original requirements list
            format_type: Report format ('text', 'json', 'xml', 'html', 'markdown')
            
        Returns:
            Enhanced coverage report
        """
        return self.template_manager.generate_coverage_report(test_outline, requirements, format_type)
    # Additional methods expected by tests
    
    def validate_test_case(self, test_case: CaseModel) -> List[str]:
        """Validate a test case and return list of validation errors.
        
        Args:
            test_case: Test case to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not test_case.id or not test_case.id.strip():
            errors.append("Test case ID is required")
        
        if not test_case.name or not test_case.name.strip():
            errors.append("Test case name is required")
        
        if not test_case.requirement_id or not test_case.requirement_id.strip():
            errors.append("Requirement ID is required")
        
        if not test_case.test_steps:
            errors.append("Test steps are required")
        
        if not isinstance(test_case.priority, CasePriority):
            errors.append("Invalid priority value")
        
        return errors
    
    def get_template_by_type(self, requirement_type) -> Dict[str, Any]:
        """Get template by requirement type.
        
        Args:
            requirement_type: Type of requirement
            
        Returns:
            Template dictionary
        """
        # Map requirement types to template categories
        if hasattr(requirement_type, 'value'):
            if requirement_type.value == 1:  # USER requirement
                return self.templates["usability"]
            elif requirement_type.value == 2:  # SOFTWARE requirement
                return self.templates["functional"]
        
        return self.templates["functional"]
    
    def generate_test_steps_from_criteria(self, acceptance_criteria: List[str]) -> List[CaseStep]:
        """Generate test steps from acceptance criteria (public method).
        
        Args:
            acceptance_criteria: List of acceptance criteria
            
        Returns:
            List of test steps
        """
        return self._generate_steps_from_criteria(acceptance_criteria)
    
    def organize_tests_by_requirement(self, test_cases: List[CaseModel]) -> Dict[str, List[CaseModel]]:
        """Organize test cases by requirement ID.
        
        Args:
            test_cases: List of test cases to organize
            
        Returns:
            Dictionary mapping requirement IDs to test cases
        """
        organized = {}
        for test_case in test_cases:
            req_id = test_case.requirement_id
            if req_id not in organized:
                organized[req_id] = []
            organized[req_id].append(test_case)
        
        return organized
    
    def generate_test_summary(self, test_cases: List[CaseModel]) -> Dict[str, Any]:
        """Generate summary statistics for test cases.
        
        Args:
            test_cases: List of test cases
            
        Returns:
            Summary statistics
        """
        if not test_cases:
            return {
                "total_tests": 0,
                "by_category": {},
                "by_priority": {},
                "by_requirement": {}
            }
        
        category_counts = {}
        priority_counts = {}
        requirement_counts = {}
        
        for test_case in test_cases:
            # Count by category
            category = test_case.category.value if hasattr(test_case.category, 'value') else str(test_case.category)
            category_counts[category] = category_counts.get(category, 0) + 1
            
            # Count by priority
            priority = test_case.priority.value if hasattr(test_case.priority, 'value') else str(test_case.priority)
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            # Count by requirement
            req_id = test_case.requirement_id
            requirement_counts[req_id] = requirement_counts.get(req_id, 0) + 1
        
        return {
            "total_tests": len(test_cases),
            "by_category": category_counts,
            "by_priority": priority_counts,
            "by_requirement": requirement_counts
        }
    
    def filter_tests_by_priority(self, test_cases: List[CaseModel], priority: str) -> List[CaseModel]:
        """Filter test cases by priority.
        
        Args:
            test_cases: List of test cases to filter
            priority: Priority to filter by
            
        Returns:
            Filtered list of test cases
        """
        filtered = []
        for test_case in test_cases:
            test_priority = test_case.priority.value if hasattr(test_case.priority, 'value') else str(test_case.priority)
            if test_priority.lower() == priority.lower():
                filtered.append(test_case)
        
        return filtered
    
    def filter_tests_by_category(self, test_cases: List[CaseModel], category: str) -> List[CaseModel]:
        """Filter test cases by category.
        
        Args:
            test_cases: List of test cases to filter
            category: Category to filter by
            
        Returns:
            Filtered list of test cases
        """
        filtered = []
        for test_case in test_cases:
            test_category = test_case.category.value if hasattr(test_case.category, 'value') else str(test_case.category)
            if test_category.lower() == category.lower():
                filtered.append(test_case)
        
        return filtered
    
    def update_test_case_metadata(self, test_case: CaseModel, metadata: Dict[str, Any]) -> None:
        """Update test case metadata.
        
        Args:
            test_case: Test case to update
            metadata: Metadata to add/update
        """
        if not hasattr(test_case, 'metadata') or test_case.metadata is None:
            test_case.metadata = {}
        
        test_case.metadata.update(metadata)
    
    def batch_generate_from_requirements(self, requirements: List[Requirement]) -> List[CaseModel]:
        """Generate test cases from multiple requirements in batch.
        
        Args:
            requirements: List of requirements
            
        Returns:
            List of all generated test cases
        """
        test_outline = self.generate_test_cases(requirements)
        return test_outline.test_cases
    
    def load_templates(self) -> Dict[str, Any]:
        """Load available test case templates.
        
        Returns:
            Dictionary of available templates
        """
        return self.templates.copy()
    
    def apply_template(self, requirement: Requirement) -> str:
        """Apply template to requirement.
        
        Args:
            requirement: Requirement to apply template to
            
        Returns:
            Template content as string
        """
        template = self.template_manager.get_template_for_requirement(requirement)
        template_data = template.apply_to_requirement(requirement)
        
        return f"Template for {requirement.id}: {template_data['name']}"
    
    def customize_template(self, requirement_type, template_params: Dict[str, Any]) -> str:
        """Customize template with specific parameters.
        
        Args:
            requirement_type: Type of requirement
            template_params: Parameters for customization
            
        Returns:
            Customized template content
        """
        base_template = self.get_template_by_type(requirement_type)
        
        # Apply customizations
        customized = base_template.copy()
        if 'test_type' in template_params:
            customized['test_type'] = template_params['test_type']
        if 'complexity' in template_params:
            customized['complexity'] = template_params['complexity']
        if 'automation_level' in template_params:
            customized['automation_level'] = template_params['automation_level']
        
        return f"Customized template: {customized}"