"""
SOUP (Software of Unknown Provenance) detection service.
Automatically detects SOUP components from project dependency files.
"""

import json
import re
import toml
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from xml.etree import ElementTree as ET

from ..models.soup_models import (
    DetectedSOUPComponent, DetectionMethod, IEC62304SafetyClass
)
from .llm_soup_classifier import LLMSOUPClassifier, SOUPAnalysisContext


class DependencyParser:
    """Base class for dependency file parsers."""
    
    def parse(self, file_path: Path) -> List[DetectedSOUPComponent]:
        """Parse dependency file and return detected components."""
        raise NotImplementedError


class PackageJsonParser(DependencyParser):
    """Parser for package.json files (Node.js/JavaScript)."""
    
    def parse(self, file_path: Path) -> List[DetectedSOUPComponent]:
        """Parse package.json file."""
        components = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Parse dependencies
            for dep_type in ['dependencies', 'devDependencies', 'peerDependencies']:
                if dep_type in data:
                    for name, version in data[dep_type].items():
                        component = DetectedSOUPComponent(
                            name=name,
                            version=self._clean_version(version),
                            source_file=str(file_path),
                            detection_method=DetectionMethod.PACKAGE_JSON,
                            confidence=0.95,
                            package_manager="npm",
                            metadata={
                                "dependency_type": dep_type,
                                "original_version": version
                            }
                        )
                        components.append(component)
            
        except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
            # Log error but don't fail completely
            pass
        
        return components
    
    def _clean_version(self, version: str) -> str:
        """Clean version string by removing prefixes like ^, ~, >=."""
        # Remove common version prefixes
        version = re.sub(r'^[\^~>=<]+', '', version)
        # Extract just the version number
        match = re.match(r'(\d+\.\d+\.\d+)', version)
        return match.group(1) if match else version


class RequirementsTxtParser(DependencyParser):
    """Parser for requirements.txt files (Python)."""
    
    def parse(self, file_path: Path) -> List[DetectedSOUPComponent]:
        """Parse requirements.txt file."""
        components = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Parse requirement line
                component = self._parse_requirement_line(line, file_path)
                if component:
                    components.append(component)
                    
        except FileNotFoundError:
            pass
        
        return components
    
    def _parse_requirement_line(self, line: str, file_path: Path) -> Optional[DetectedSOUPComponent]:
        """Parse a single requirement line."""
        # Handle different requirement formats
        # package==1.0.0, package>=1.0.0, package~=1.0.0, etc.
        match = re.match(r'^([a-zA-Z0-9_-]+)([>=~!<]+)([0-9.]+)', line)
        if match:
            name, operator, version = match.groups()
            return DetectedSOUPComponent(
                name=name,
                version=version,
                source_file=str(file_path),
                detection_method=DetectionMethod.REQUIREMENTS_TXT,
                confidence=0.9,
                package_manager="pip",
                metadata={
                    "operator": operator,
                    "original_line": line
                }
            )
        
        # Handle simple package names without version
        if re.match(r'^[a-zA-Z0-9_-]+$', line):
            return DetectedSOUPComponent(
                name=line,
                version="latest",
                source_file=str(file_path),
                detection_method=DetectionMethod.REQUIREMENTS_TXT,
                confidence=0.7,
                package_manager="pip",
                metadata={
                    "original_line": line,
                    "version_unspecified": True
                }
            )
        
        return None


class CMakeListsParser(DependencyParser):
    """Parser for CMakeLists.txt files (C/C++)."""
    
    def parse(self, file_path: Path) -> List[DetectedSOUPComponent]:
        """Parse CMakeLists.txt file."""
        components = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for find_package commands
            find_package_matches = re.findall(
                r'find_package\s*\(\s*([a-zA-Z0-9_]+)(?:\s+([0-9.]+))?\s*(?:REQUIRED)?\s*\)',
                content, re.IGNORECASE
            )
            
            for match in find_package_matches:
                name = match[0]
                version = match[1] if match[1] else "unknown"
                
                component = DetectedSOUPComponent(
                    name=name,
                    version=version,
                    source_file=str(file_path),
                    detection_method=DetectionMethod.CMAKE_LISTS,
                    confidence=0.8,
                    package_manager="cmake",
                    metadata={
                        "cmake_command": "find_package"
                    }
                )
                components.append(component)
            
            # Look for target_link_libraries with external libraries
            link_lib_matches = re.findall(
                r'target_link_libraries\s*\([^)]*?([a-zA-Z0-9_:]+)',
                content, re.IGNORECASE
            )
            
            for lib_name in link_lib_matches:
                if '::' in lib_name:  # Modern CMake target format
                    component = DetectedSOUPComponent(
                        name=lib_name,
                        version="unknown",
                        source_file=str(file_path),
                        detection_method=DetectionMethod.CMAKE_LISTS,
                        confidence=0.6,
                        package_manager="cmake",
                        metadata={
                            "cmake_command": "target_link_libraries"
                        }
                    )
                    components.append(component)
                    
        except FileNotFoundError:
            pass
        
        return components


class GradleBuildParser(DependencyParser):
    """Parser for build.gradle files (Java/Android)."""
    
    def parse(self, file_path: Path) -> List[DetectedSOUPComponent]:
        """Parse build.gradle file."""
        components = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for dependency declarations
            # implementation 'group:artifact:version'
            # compile 'group:artifact:version'
            dependency_matches = re.findall(
                r'(?:implementation|compile|api|testImplementation)\s+[\'"]([^:]+):([^:]+):([^\'"]+)[\'"]',
                content
            )
            
            for match in dependency_matches:
                group, artifact, version = match
                name = f"{group}:{artifact}"
                
                component = DetectedSOUPComponent(
                    name=name,
                    version=version,
                    source_file=str(file_path),
                    detection_method=DetectionMethod.GRADLE_BUILD,
                    confidence=0.9,
                    package_manager="gradle",
                    metadata={
                        "group": group,
                        "artifact": artifact
                    }
                )
                components.append(component)
                
        except FileNotFoundError:
            pass
        
        return components


class PomXmlParser(DependencyParser):
    """Parser for pom.xml files (Maven/Java)."""
    
    def parse(self, file_path: Path) -> List[DetectedSOUPComponent]:
        """Parse pom.xml file."""
        components = []
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Handle XML namespace
            namespace = {'maven': 'http://maven.apache.org/POM/4.0.0'}
            if root.tag.startswith('{'):
                namespace_uri = root.tag.split('}')[0][1:]
                namespace = {'maven': namespace_uri}
            
            # Find dependencies
            dependencies = root.findall('.//maven:dependency', namespace)
            if not dependencies:  # Try without namespace
                dependencies = root.findall('.//dependency')
            
            for dep in dependencies:
                group_id = self._get_element_text(dep, 'groupId', namespace)
                artifact_id = self._get_element_text(dep, 'artifactId', namespace)
                version = self._get_element_text(dep, 'version', namespace)
                
                if group_id and artifact_id:
                    name = f"{group_id}:{artifact_id}"
                    component = DetectedSOUPComponent(
                        name=name,
                        version=version or "unknown",
                        source_file=str(file_path),
                        detection_method=DetectionMethod.POM_XML,
                        confidence=0.9,
                        package_manager="maven",
                        metadata={
                            "groupId": group_id,
                            "artifactId": artifact_id
                        }
                    )
                    components.append(component)
                    
        except (ET.ParseError, FileNotFoundError):
            pass
        
        return components
    
    def _get_element_text(self, parent, tag, namespace):
        """Get text from XML element with namespace handling."""
        element = parent.find(f'maven:{tag}', namespace)
        if element is None:
            element = parent.find(tag)
        return element.text if element is not None else None


class CargoTomlParser(DependencyParser):
    """Parser for Cargo.toml files (Rust)."""
    
    def parse(self, file_path: Path) -> List[DetectedSOUPComponent]:
        """Parse Cargo.toml file."""
        components = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = toml.load(f)
            
            # Parse dependencies
            for dep_section in ['dependencies', 'dev-dependencies', 'build-dependencies']:
                if dep_section in data:
                    for name, version_info in data[dep_section].items():
                        if isinstance(version_info, str):
                            version = version_info
                        elif isinstance(version_info, dict):
                            version = version_info.get('version', 'unknown')
                        else:
                            version = 'unknown'
                        
                        component = DetectedSOUPComponent(
                            name=name,
                            version=version,
                            source_file=str(file_path),
                            detection_method=DetectionMethod.CARGO_TOML,
                            confidence=0.9,
                            package_manager="cargo",
                            metadata={
                                "dependency_section": dep_section
                            }
                        )
                        components.append(component)
                        
        except (toml.TomlDecodeError, FileNotFoundError):
            pass
        
        return components


class SOUPDetector:
    """Main SOUP detection service."""
    
    def __init__(self, use_llm_classification: bool = True):
        """Initialize SOUP detector with parsers."""
        self.parsers: Dict[str, DependencyParser] = {
            'package.json': PackageJsonParser(),
            'requirements.txt': RequirementsTxtParser(),
            'CMakeLists.txt': CMakeListsParser(),
            'build.gradle': GradleBuildParser(),
            'pom.xml': PomXmlParser(),
            'Cargo.toml': CargoTomlParser(),
        }
        
        # Initialize LLM classifier
        self.use_llm_classification = use_llm_classification
        self.llm_classifier = LLMSOUPClassifier() if use_llm_classification else None
        
        # Fallback safety classification heuristics (used when LLM is unavailable)
        self.safety_classification_rules = {
            # High-risk patterns (Class C)
            'database': IEC62304SafetyClass.CLASS_C,
            'crypto': IEC62304SafetyClass.CLASS_C,
            'security': IEC62304SafetyClass.CLASS_C,
            'network': IEC62304SafetyClass.CLASS_B,
            'http': IEC62304SafetyClass.CLASS_B,
            'ssl': IEC62304SafetyClass.CLASS_C,
            'auth': IEC62304SafetyClass.CLASS_B,
            
            # Medium-risk patterns (Class B)
            'ui': IEC62304SafetyClass.CLASS_B,
            'gui': IEC62304SafetyClass.CLASS_B,
            'parser': IEC62304SafetyClass.CLASS_B,
            'json': IEC62304SafetyClass.CLASS_B,
            'xml': IEC62304SafetyClass.CLASS_B,
            
            # Low-risk patterns (Class A)
            'test': IEC62304SafetyClass.CLASS_A,
            'mock': IEC62304SafetyClass.CLASS_A,
            'debug': IEC62304SafetyClass.CLASS_A,
            'log': IEC62304SafetyClass.CLASS_A,
            'util': IEC62304SafetyClass.CLASS_A,
        }
    
    def detect_soup_components(self, project_path: str) -> List[DetectedSOUPComponent]:
        """
        Detect SOUP components from project dependency files.
        
        Args:
            project_path: Path to the project root directory
            
        Returns:
            List of detected SOUP components
        """
        project_root = Path(project_path)
        all_components = []
        
        # Search for dependency files
        for filename, parser in self.parsers.items():
            dependency_files = list(project_root.rglob(filename))
            
            for file_path in dependency_files:
                components = parser.parse(file_path)
                
                # Add safety classification suggestions
                for component in components:
                    component.suggested_classification = self._suggest_safety_classification(component)
                
                all_components.extend(components)
        
        # Deduplicate and consolidate versions
        deduplicated = self._deduplicate_components(all_components)
        
        return deduplicated
    
    def _suggest_safety_classification(self, component: DetectedSOUPComponent) -> Optional[IEC62304SafetyClass]:
        """
        Suggest IEC 62304 safety classification using LLM analysis or fallback rules.
        
        Args:
            component: Detected SOUP component
            
        Returns:
            Suggested safety classification or None
        """
        if self.use_llm_classification and self.llm_classifier:
            try:
                # Use LLM-based classification
                context = SOUPAnalysisContext(
                    component=component,
                    project_type="medical_device",
                    safety_critical=True
                )
                classification = self.llm_classifier.classify_component(component, context)
                return classification.safety_class
            except Exception:
                # Fall back to rule-based classification if LLM fails
                pass
        
        # Fallback rule-based classification
        name_lower = component.name.lower()
        
        # Check against classification rules
        for pattern, classification in self.safety_classification_rules.items():
            if pattern in name_lower:
                return classification
        
        # Default to Class B for unknown components
        return IEC62304SafetyClass.CLASS_B
    
    def _deduplicate_components(self, components: List[DetectedSOUPComponent]) -> List[DetectedSOUPComponent]:
        """
        Deduplicate components and consolidate version information.
        
        Args:
            components: List of detected components
            
        Returns:
            Deduplicated list of components
        """
        component_map: Dict[str, DetectedSOUPComponent] = {}
        
        for component in components:
            key = component.name
            
            if key in component_map:
                existing = component_map[key]
                
                # Keep the component with higher confidence
                if component.confidence > existing.confidence:
                    component_map[key] = component
                elif component.confidence == existing.confidence:
                    # Merge metadata and source files
                    existing.metadata.update(component.metadata)
                    if component.source_file not in existing.metadata.get('source_files', []):
                        existing.metadata.setdefault('source_files', []).append(component.source_file)
            else:
                component_map[key] = component
        
        return list(component_map.values())
    
    def classify_component(self, component: DetectedSOUPComponent) -> IEC62304SafetyClass:
        """
        Classify a component according to IEC 62304 safety classes.
        
        Args:
            component: Component to classify
            
        Returns:
            IEC 62304 safety classification
        """
        # Use suggested classification if available
        if component.suggested_classification:
            return component.suggested_classification
        
        # Apply classification rules
        suggested = self._suggest_safety_classification(component)
        return suggested or IEC62304SafetyClass.CLASS_B
    
    def assess_safety_impact(self, component: DetectedSOUPComponent) -> Dict[str, Any]:
        """
        Assess the safety impact of a SOUP component.
        
        Args:
            component: Component to assess
            
        Returns:
            Safety impact assessment
        """
        classification = self.classify_component(component)
        
        # Generate assessment based on classification
        if classification == IEC62304SafetyClass.CLASS_C:
            return {
                'impact_level': 'High',
                'failure_modes': [
                    'Component failure could cause death or serious injury',
                    'Malfunction could compromise life-supporting functions',
                    'Security vulnerabilities could endanger patient safety'
                ],
                'verification_requirements': [
                    'Comprehensive testing required',
                    'Code review and static analysis',
                    'Security assessment',
                    'Supplier audit may be required'
                ]
            }
        elif classification == IEC62304SafetyClass.CLASS_B:
            return {
                'impact_level': 'Medium',
                'failure_modes': [
                    'Component failure could cause non-serious injury',
                    'Malfunction could affect device functionality',
                    'Data integrity issues possible'
                ],
                'verification_requirements': [
                    'Functional testing required',
                    'Integration testing',
                    'Basic security review'
                ]
            }
        else:  # CLASS_A
            return {
                'impact_level': 'Low',
                'failure_modes': [
                    'Component failure has no safety impact',
                    'Malfunction affects only non-safety functions'
                ],
                'verification_requirements': [
                    'Basic functional testing',
                    'Documentation review'
                ]
            }
    
    def track_version_changes(self, old_components: List[DetectedSOUPComponent], 
                            new_components: List[DetectedSOUPComponent]) -> List[Dict[str, Any]]:
        """
        Track version changes between component lists.
        
        Args:
            old_components: Previous component list
            new_components: Current component list
            
        Returns:
            List of version changes
        """
        old_map = {comp.name: comp for comp in old_components}
        new_map = {comp.name: comp for comp in new_components}
        
        changes = []
        
        # Check for version changes
        for name, new_comp in new_map.items():
            if name in old_map:
                old_comp = old_map[name]
                if old_comp.version != new_comp.version:
                    changes.append({
                        'component_name': name,
                        'old_version': old_comp.version,
                        'new_version': new_comp.version,
                        'change_type': 'version_update',
                        'impact_assessment_required': True
                    })
        
        # Check for new components
        for name, new_comp in new_map.items():
            if name not in old_map:
                changes.append({
                    'component_name': name,
                    'old_version': None,
                    'new_version': new_comp.version,
                    'change_type': 'added',
                    'impact_assessment_required': True
                })
        
        # Check for removed components
        for name, old_comp in old_map.items():
            if name not in new_map:
                changes.append({
                    'component_name': name,
                    'old_version': old_comp.version,
                    'new_version': None,
                    'change_type': 'removed',
                    'impact_assessment_required': True
                })
        
        return changes
    
    def get_detailed_classification(self, component: DetectedSOUPComponent, 
                                  project_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get detailed LLM-based classification and analysis for a SOUP component.
        
        Args:
            component: Detected SOUP component
            project_context: Optional project context information
            
        Returns:
            Detailed classification and analysis results
        """
        if not self.use_llm_classification or not self.llm_classifier:
            return {
                "error": "LLM classification not available",
                "fallback_classification": self._suggest_safety_classification(component),
                "method": "rule_based"
            }
        
        try:
            # Prepare analysis context
            context = SOUPAnalysisContext(
                component=component,
                project_type=project_context.get("project_type", "medical_device") if project_context else "medical_device",
                safety_critical=project_context.get("safety_critical", True) if project_context else True,
                additional_context=project_context or {}
            )
            
            # Get LLM classification
            classification = self.llm_classifier.classify_component(component, context)
            
            # Get safety impact analysis
            safety_impact = self.llm_classifier.analyze_safety_impact(component, classification)
            
            return {
                "classification": {
                    "safety_class": classification.safety_class.value,
                    "justification": classification.justification,
                    "risk_assessment": classification.risk_assessment,
                    "verification_requirements": classification.verification_requirements,
                    "documentation_requirements": classification.documentation_requirements,
                    "change_control_requirements": classification.change_control_requirements,
                    "metadata": getattr(classification, 'metadata', {})
                },
                "safety_impact": safety_impact,
                "method": "llm_based",
                "component_info": {
                    "name": component.name,
                    "version": component.version,
                    "source_file": component.source_file,
                    "detection_method": component.detection_method.value,
                    "confidence": component.confidence
                }
            }
            
        except Exception as e:
            # Return fallback classification with error info
            return {
                "error": f"LLM classification failed: {str(e)}",
                "fallback_classification": self._suggest_safety_classification(component),
                "method": "rule_based_fallback",
                "component_info": {
                    "name": component.name,
                    "version": component.version,
                    "source_file": component.source_file,
                    "detection_method": component.detection_method.value,
                    "confidence": component.confidence
                }
            }
    
    def batch_classify_components(self, components: List[DetectedSOUPComponent],
                                project_context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Perform batch LLM-based classification of multiple components.
        
        Args:
            components: List of detected SOUP components
            project_context: Optional project context information
            
        Returns:
            List of detailed classification results
        """
        if not self.use_llm_classification or not self.llm_classifier:
            return [
                {
                    "error": "LLM classification not available",
                    "fallback_classification": self._suggest_safety_classification(comp),
                    "method": "rule_based",
                    "component_info": {
                        "name": comp.name,
                        "version": comp.version,
                        "source_file": comp.source_file,
                        "detection_method": comp.detection_method.value,
                        "confidence": comp.confidence
                    }
                }
                for comp in components
            ]
        
        results = []
        for component in components:
            result = self.get_detailed_classification(component, project_context)
            results.append(result)
        
        return results