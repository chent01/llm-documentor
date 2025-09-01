"""
Unit tests for SOUPDetector class.

Tests cover:
- Automatic SOUP component detection
- Multi-format dependency file parsing
- Component classification and confidence scoring
- Version tracking and change detection
- Edge cases and error handling
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, mock_open
from medical_analyzer.services.soup_detector import SOUPDetector
from medical_analyzer.models.soup_models import DetectedSOUPComponent, IEC62304Classification


class TestSOUPDetector:
    """Test suite for SOUPDetector functionality."""
    
    @pytest.fixture
    def detector(self):
        """Create SOUPDetector for testing."""
        return SOUPDetector()
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary project directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create package.json
            package_json = {
                "name": "test-project",
                "version": "1.0.0",
                "dependencies": {
                    "express": "^4.18.0",
                    "lodash": "4.17.21",
                    "moment": "~2.29.0"
                },
                "devDependencies": {
                    "jest": "^29.0.0",
                    "eslint": "8.0.0"
                }
            }
            
            with open(os.path.join(temp_dir, 'package.json'), 'w') as f:
                import json
                json.dump(package_json, f)
            
            # Create requirements.txt
            requirements_txt = """
numpy==1.21.0
pandas>=1.3.0
requests~=2.28.0
flask==2.0.1
# Development dependencies
pytest>=6.0.0
black==21.9b0
"""
            
            with open(os.path.join(temp_dir, 'requirements.txt'), 'w') as f:
                f.write(requirements_txt)
            
            # Create CMakeLists.txt
            cmake_content = """
cmake_minimum_required(VERSION 3.10)
project(TestProject)

find_package(OpenSSL REQUIRED)
find_package(Boost 1.70 REQUIRED COMPONENTS system filesystem)
find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBXML2 REQUIRED libxml-2.0)

target_link_libraries(test_app OpenSSL::SSL OpenSSL::Crypto)
target_link_libraries(test_app ${Boost_LIBRARIES})
"""
            
            with open(os.path.join(temp_dir, 'CMakeLists.txt'), 'w') as f:
                f.write(cmake_content)
            
            yield temp_dir
    
    def test_detector_initialization(self, detector):
        """Test SOUPDetector initialization."""
        assert detector is not None
        assert hasattr(detector, 'parsers')
        assert len(detector.parsers) > 0
        assert 'package.json' in detector.parsers
        assert 'requirements.txt' in detector.parsers
        assert 'CMakeLists.txt' in detector.parsers
    
    def test_detect_soup_components_comprehensive(self, detector, temp_project_dir):
        """Test comprehensive SOUP component detection."""
        components = detector.detect_soup_components(temp_project_dir)
        
        # Should detect components from all dependency files
        assert len(components) > 0
        
        # Check for JavaScript components
        js_components = [c for c in components if c.source_file == 'package.json']
        assert len(js_components) >= 3  # express, lodash, moment (excluding dev deps)
        
        # Check for Python components
        py_components = [c for c in components if c.source_file == 'requirements.txt']
        assert len(py_components) >= 4  # numpy, pandas, requests, flask
        
        # Check for C++ components
        cpp_components = [c for c in components if c.source_file == 'CMakeLists.txt']
        assert len(cpp_components) >= 3  # OpenSSL, Boost, libxml2
    
    def test_parse_package_json(self, detector, temp_project_dir):
        """Test parsing package.json file."""
        package_json_path = os.path.join(temp_project_dir, 'package.json')
        components = detector.parsers['package.json'](package_json_path)
        
        assert len(components) >= 3
        
        # Check express component
        express = next((c for c in components if c.name == 'express'), None)
        assert express is not None
        assert express.version == '^4.18.0'
        assert express.detection_method == 'package.json_dependencies'
        assert express.confidence > 0.8
        
        # Check lodash component
        lodash = next((c for c in components if c.name == 'lodash'), None)
        assert lodash is not None
        assert lodash.version == '4.17.21'
        
        # Should not include dev dependencies by default
        jest = next((c for c in components if c.name == 'jest'), None)
        assert jest is None  # Dev dependencies excluded
    
    def test_parse_package_json_include_dev_deps(self, detector, temp_project_dir):
        """Test parsing package.json including dev dependencies."""
        package_json_path = os.path.join(temp_project_dir, 'package.json')
        components = detector.parsers['package.json'](package_json_path, include_dev=True)
        
        # Should include dev dependencies
        jest = next((c for c in components if c.name == 'jest'), None)
        assert jest is not None
        assert jest.version == '^29.0.0'
        assert 'dev' in jest.metadata.get('dependency_type', '')
    
    def test_parse_requirements_txt(self, detector, temp_project_dir):
        """Test parsing requirements.txt file."""
        requirements_path = os.path.join(temp_project_dir, 'requirements.txt')
        components = detector.parsers['requirements.txt'](requirements_path)
        
        assert len(components) >= 4
        
        # Check numpy component
        numpy = next((c for c in components if c.name == 'numpy'), None)
        assert numpy is not None
        assert numpy.version == '1.21.0'
        assert numpy.detection_method == 'requirements.txt'
        assert numpy.confidence > 0.9  # Exact version = high confidence
        
        # Check pandas component (version range)
        pandas = next((c for c in components if c.name == 'pandas'), None)
        assert pandas is not None
        assert pandas.version == '>=1.3.0'
        assert pandas.confidence < 0.9  # Version range = lower confidence
        
        # Should not include commented dependencies
        pytest_comp = next((c for c in components if c.name == 'pytest'), None)
        assert pytest_comp is None  # Commented out
    
    def test_parse_cmake_lists(self, detector, temp_project_dir):
        """Test parsing CMakeLists.txt file."""
        cmake_path = os.path.join(temp_project_dir, 'CMakeLists.txt')
        components = detector.parsers['CMakeLists.txt'](cmake_path)
        
        assert len(components) >= 3
        
        # Check OpenSSL component
        openssl = next((c for c in components if c.name == 'OpenSSL'), None)
        assert openssl is not None
        assert openssl.detection_method == 'cmake_find_package'
        assert openssl.confidence > 0.7
        
        # Check Boost component
        boost = next((c for c in components if c.name == 'Boost'), None)
        assert boost is not None
        assert '1.70' in boost.version
        assert 'system' in boost.metadata.get('components', [])
        assert 'filesystem' in boost.metadata.get('components', [])
        
        # Check pkg-config component
        libxml2 = next((c for c in components if c.name == 'libxml2'), None)
        assert libxml2 is not None
        assert libxml2.detection_method == 'cmake_pkg_config'
    
    def test_classify_component_safety_class_a(self, detector):
        """Test classification of Class A (non-safety) components."""
        component = DetectedSOUPComponent(
            name="lodash",
            version="4.17.21",
            source_file="package.json",
            detection_method="package.json_dependencies",
            confidence=0.9,
            suggested_classification="A"
        )
        
        classification = detector.classify_component(component)
        
        assert isinstance(classification, IEC62304Classification)
        assert classification.safety_class == "A"
        assert "utility library" in classification.justification.lower()
        assert len(classification.verification_requirements) > 0
    
    def test_classify_component_safety_class_b(self, detector):
        """Test classification of Class B (non-life-threatening) components."""
        component = DetectedSOUPComponent(
            name="express",
            version="4.18.0",
            source_file="package.json",
            detection_method="package.json_dependencies",
            confidence=0.9,
            suggested_classification="B"
        )
        
        classification = detector.classify_component(component)
        
        assert classification.safety_class == "B"
        assert "web server" in classification.justification.lower()
        assert len(classification.verification_requirements) > len(
            detector.classify_component(DetectedSOUPComponent(
                name="lodash", version="1.0.0", source_file="", 
                detection_method="", confidence=0.9, suggested_classification="A"
            )).verification_requirements
        )
    
    def test_classify_component_safety_class_c(self, detector):
        """Test classification of Class C (life-threatening) components."""
        component = DetectedSOUPComponent(
            name="openssl",
            version="1.1.1",
            source_file="CMakeLists.txt",
            detection_method="cmake_find_package",
            confidence=0.9,
            suggested_classification="C"
        )
        
        classification = detector.classify_component(component)
        
        assert classification.safety_class == "C"
        assert "cryptographic" in classification.justification.lower()
        assert len(classification.verification_requirements) > 5  # Extensive verification for Class C
        assert "penetration testing" in str(classification.verification_requirements).lower()
    
    def test_assess_safety_impact_high_risk(self, detector):
        """Test safety impact assessment for high-risk components."""
        component = DetectedSOUPComponent(
            name="medical-device-driver",
            version="2.1.0",
            source_file="requirements.txt",
            detection_method="requirements.txt",
            confidence=0.9,
            suggested_classification="C"
        )
        
        assessment = detector.assess_safety_impact(component)
        
        assert assessment.safety_impact == "high"
        assert len(assessment.failure_modes) > 0
        assert len(assessment.mitigation_measures) > 0
        assert "device malfunction" in str(assessment.failure_modes).lower()
    
    def test_assess_safety_impact_low_risk(self, detector):
        """Test safety impact assessment for low-risk components."""
        component = DetectedSOUPComponent(
            name="moment",
            version="2.29.0",
            source_file="package.json",
            detection_method="package.json_dependencies",
            confidence=0.9,
            suggested_classification="A"
        )
        
        assessment = detector.assess_safety_impact(component)
        
        assert assessment.safety_impact == "low"
        assert len(assessment.failure_modes) < 3  # Fewer failure modes for low-risk
        assert "date formatting" in str(assessment.failure_modes).lower()
    
    def test_track_version_changes_new_component(self, detector):
        """Test tracking version changes with new components."""
        old_components = [
            DetectedSOUPComponent(
                name="express", version="4.17.0", source_file="package.json",
                detection_method="", confidence=0.9, suggested_classification="B"
            )
        ]
        
        new_components = [
            DetectedSOUPComponent(
                name="express", version="4.18.0", source_file="package.json",
                detection_method="", confidence=0.9, suggested_classification="B"
            ),
            DetectedSOUPComponent(
                name="lodash", version="4.17.21", source_file="package.json",
                detection_method="", confidence=0.9, suggested_classification="A"
            )
        ]
        
        changes = detector.track_version_changes(old_components, new_components)
        
        assert len(changes) == 2
        
        # Check version update
        version_change = next((c for c in changes if c.change_type == 'version_update'), None)
        assert version_change is not None
        assert version_change.component_name == 'express'
        assert version_change.old_version == '4.17.0'
        assert version_change.new_version == '4.18.0'
        
        # Check new component
        new_change = next((c for c in changes if c.change_type == 'added'), None)
        assert new_change is not None
        assert new_change.component_name == 'lodash'
    
    def test_track_version_changes_removed_component(self, detector):
        """Test tracking version changes with removed components."""
        old_components = [
            DetectedSOUPComponent(
                name="express", version="4.17.0", source_file="package.json",
                detection_method="", confidence=0.9, suggested_classification="B"
            ),
            DetectedSOUPComponent(
                name="lodash", version="4.17.21", source_file="package.json",
                detection_method="", confidence=0.9, suggested_classification="A"
            )
        ]
        
        new_components = [
            DetectedSOUPComponent(
                name="express", version="4.17.0", source_file="package.json",
                detection_method="", confidence=0.9, suggested_classification="B"
            )
        ]
        
        changes = detector.track_version_changes(old_components, new_components)
        
        assert len(changes) == 1
        
        # Check removed component
        removed_change = changes[0]
        assert removed_change.change_type == 'removed'
        assert removed_change.component_name == 'lodash'
        assert removed_change.old_version == '4.17.21'
        assert removed_change.new_version is None
    
    def test_detect_components_missing_files(self, detector):
        """Test detection when dependency files are missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Empty directory - no dependency files
            components = detector.detect_soup_components(temp_dir)
            
            assert len(components) == 0
    
    def test_detect_components_malformed_json(self, detector):
        """Test detection with malformed package.json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create malformed package.json
            with open(os.path.join(temp_dir, 'package.json'), 'w') as f:
                f.write('{ "name": "test", invalid json }')
            
            components = detector.detect_soup_components(temp_dir)
            
            # Should handle error gracefully and return empty list
            assert len(components) == 0
    
    def test_detect_components_empty_dependencies(self, detector):
        """Test detection with empty dependency sections."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create package.json with empty dependencies
            package_json = {
                "name": "test-project",
                "version": "1.0.0",
                "dependencies": {},
                "devDependencies": {}
            }
            
            with open(os.path.join(temp_dir, 'package.json'), 'w') as f:
                import json
                json.dump(package_json, f)
            
            components = detector.detect_soup_components(temp_dir)
            
            assert len(components) == 0
    
    def test_confidence_scoring_exact_version(self, detector):
        """Test confidence scoring for exact version specifications."""
        # Exact version should have high confidence
        component = detector._create_component(
            name="test-lib",
            version="1.2.3",
            source_file="requirements.txt",
            detection_method="requirements.txt"
        )
        
        assert component.confidence > 0.9
    
    def test_confidence_scoring_version_range(self, detector):
        """Test confidence scoring for version ranges."""
        # Version ranges should have lower confidence
        component = detector._create_component(
            name="test-lib",
            version=">=1.2.0",
            source_file="requirements.txt",
            detection_method="requirements.txt"
        )
        
        assert component.confidence < 0.9
        assert component.confidence > 0.6
    
    def test_confidence_scoring_no_version(self, detector):
        """Test confidence scoring when no version is specified."""
        # No version should have lowest confidence
        component = detector._create_component(
            name="test-lib",
            version="",
            source_file="CMakeLists.txt",
            detection_method="cmake_find_package"
        )
        
        assert component.confidence < 0.6
    
    def test_deduplication_same_component_different_files(self, detector):
        """Test deduplication of same component found in different files."""
        components = [
            DetectedSOUPComponent(
                name="openssl", version="1.1.1", source_file="CMakeLists.txt",
                detection_method="cmake", confidence=0.8, suggested_classification="C"
            ),
            DetectedSOUPComponent(
                name="openssl", version="1.1.1", source_file="requirements.txt",
                detection_method="pip", confidence=0.9, suggested_classification="C"
            )
        ]
        
        deduplicated = detector._deduplicate_components(components)
        
        # Should keep only one, preferring higher confidence
        assert len(deduplicated) == 1
        assert deduplicated[0].confidence == 0.9
        assert deduplicated[0].source_file == "requirements.txt"
    
    def test_version_consolidation_different_versions(self, detector):
        """Test version consolidation when same component has different versions."""
        components = [
            DetectedSOUPComponent(
                name="boost", version="1.70", source_file="CMakeLists.txt",
                detection_method="cmake", confidence=0.8, suggested_classification="B"
            ),
            DetectedSOUPComponent(
                name="boost", version="1.72", source_file="conanfile.txt",
                detection_method="conan", confidence=0.9, suggested_classification="B"
            )
        ]
        
        consolidated = detector._consolidate_versions(components)
        
        # Should flag version conflict
        assert len(consolidated) == 1
        assert "version_conflict" in consolidated[0].metadata
        assert consolidated[0].metadata["version_conflict"] == ["1.70", "1.72"]
    
    def test_get_supported_file_types(self, detector):
        """Test getting list of supported dependency file types."""
        supported_types = detector.get_supported_file_types()
        
        assert 'package.json' in supported_types
        assert 'requirements.txt' in supported_types
        assert 'CMakeLists.txt' in supported_types
        assert 'Pipfile' in supported_types
        assert 'pom.xml' in supported_types
    
    def test_validate_component_data(self, detector):
        """Test validation of component data."""
        valid_component = DetectedSOUPComponent(
            name="valid-lib",
            version="1.0.0",
            source_file="package.json",
            detection_method="package.json_dependencies",
            confidence=0.9,
            suggested_classification="A"
        )
        
        validation_errors = detector.validate_component_data(valid_component)
        assert len(validation_errors) == 0
        
        # Test invalid component
        invalid_component = DetectedSOUPComponent(
            name="",  # Empty name
            version="invalid-version",
            source_file="",  # Empty source file
            detection_method="",
            confidence=1.5,  # Invalid confidence > 1.0
            suggested_classification="X"  # Invalid classification
        )
        
        validation_errors = detector.validate_component_data(invalid_component)
        assert len(validation_errors) > 0
        assert any("empty name" in error.lower() for error in validation_errors)
        assert any("confidence" in error.lower() for error in validation_errors)
        assert any("classification" in error.lower() for error in validation_errors)


class TestSOUPDetectorParsers:
    """Test individual parser functionality."""
    
    @pytest.fixture
    def detector(self):
        """Create SOUPDetector for testing."""
        return SOUPDetector()
    
    def test_parse_pipfile(self, detector):
        """Test parsing Pipfile for Python dependencies."""
        pipfile_content = """
[[source]]
url = "https://pypi.org/simple"
verify_ssl = true
name = "pypi"

[packages]
requests = "*"
django = ">=3.2"
numpy = "==1.21.0"

[dev-packages]
pytest = "*"
black = "==21.9b0"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='Pipfile', delete=False) as f:
            f.write(pipfile_content)
            f.flush()
            
            try:
                components = detector.parsers['Pipfile'](f.name)
                
                assert len(components) >= 3
                
                # Check requests component
                requests_comp = next((c for c in components if c.name == 'requests'), None)
                assert requests_comp is not None
                assert requests_comp.version == '*'
                
                # Check django component
                django_comp = next((c for c in components if c.name == 'django'), None)
                assert django_comp is not None
                assert django_comp.version == '>=3.2'
                
            finally:
                os.unlink(f.name)
    
    def test_parse_pom_xml(self, detector):
        """Test parsing pom.xml for Java dependencies."""
        pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    
    <dependencies>
        <dependency>
            <groupId>org.springframework</groupId>
            <artifactId>spring-core</artifactId>
            <version>5.3.21</version>
        </dependency>
        <dependency>
            <groupId>junit</groupId>
            <artifactId>junit</artifactId>
            <version>4.13.2</version>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.apache.commons</groupId>
            <artifactId>commons-lang3</artifactId>
            <version>3.12.0</version>
        </dependency>
    </dependencies>
</project>"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='pom.xml', delete=False) as f:
            f.write(pom_content)
            f.flush()
            
            try:
                components = detector.parsers['pom.xml'](f.name)
                
                # Should exclude test dependencies by default
                assert len(components) == 2
                
                # Check spring-core component
                spring_comp = next((c for c in components if 'spring-core' in c.name), None)
                assert spring_comp is not None
                assert spring_comp.version == '5.3.21'
                
                # Check commons-lang3 component
                commons_comp = next((c for c in components if 'commons-lang3' in c.name), None)
                assert commons_comp is not None
                assert commons_comp.version == '3.12.0'
                
                # junit should be excluded (test scope)
                junit_comp = next((c for c in components if 'junit' in c.name), None)
                assert junit_comp is None
                
            finally:
                os.unlink(f.name)
    
    def test_parse_gradle_build(self, detector):
        """Test parsing build.gradle for Java/Android dependencies."""
        gradle_content = """
dependencies {
    implementation 'org.springframework:spring-core:5.3.21'
    implementation 'com.google.guava:guava:31.1-jre'
    api 'org.apache.commons:commons-lang3:3.12.0'
    
    testImplementation 'junit:junit:4.13.2'
    testImplementation 'org.mockito:mockito-core:4.6.1'
    
    compileOnly 'org.projectlombok:lombok:1.18.24'
}
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='build.gradle', delete=False) as f:
            f.write(gradle_content)
            f.flush()
            
            try:
                components = detector.parsers['build.gradle'](f.name)
                
                # Should include implementation and api dependencies
                assert len(components) >= 3
                
                # Check spring-core component
                spring_comp = next((c for c in components if 'spring-core' in c.name), None)
                assert spring_comp is not None
                assert spring_comp.version == '5.3.21'
                
                # Check guava component
                guava_comp = next((c for c in components if 'guava' in c.name), None)
                assert guava_comp is not None
                assert guava_comp.version == '31.1-jre'
                
            finally:
                os.unlink(f.name)


class TestSOUPDetectorEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.fixture
    def detector(self):
        """Create SOUPDetector for testing."""
        return SOUPDetector()
    
    def test_detect_with_permission_error(self, detector):
        """Test detection when file access is denied."""
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create a file that will trigger permission error
                test_file = os.path.join(temp_dir, 'package.json')
                with open(test_file, 'w') as f:
                    f.write('{}')
                
                components = detector.detect_soup_components(temp_dir)
                
                # Should handle error gracefully
                assert len(components) == 0
    
    def test_detect_with_corrupted_file(self, detector):
        """Test detection with corrupted dependency files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create corrupted package.json
            with open(os.path.join(temp_dir, 'package.json'), 'wb') as f:
                f.write(b'\x00\x01\x02\x03')  # Binary data
            
            components = detector.detect_soup_components(temp_dir)
            
            # Should handle corruption gracefully
            assert len(components) == 0
    
    def test_detect_with_very_large_file(self, detector):
        """Test detection with very large dependency files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create large package.json with many dependencies
            large_deps = {f"dep{i}": f"^{i}.0.0" for i in range(1000)}
            package_json = {
                "name": "large-project",
                "version": "1.0.0",
                "dependencies": large_deps
            }
            
            with open(os.path.join(temp_dir, 'package.json'), 'w') as f:
                import json
                json.dump(package_json, f)
            
            components = detector.detect_soup_components(temp_dir)
            
            # Should handle large files
            assert len(components) == 1000
    
    def test_detect_with_nested_directories(self, detector):
        """Test detection in projects with nested dependency files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested structure
            frontend_dir = os.path.join(temp_dir, 'frontend')
            backend_dir = os.path.join(temp_dir, 'backend')
            os.makedirs(frontend_dir)
            os.makedirs(backend_dir)
            
            # Frontend package.json
            frontend_deps = {
                "name": "frontend",
                "dependencies": {"react": "^18.0.0", "axios": "^0.27.0"}
            }
            with open(os.path.join(frontend_dir, 'package.json'), 'w') as f:
                import json
                json.dump(frontend_deps, f)
            
            # Backend requirements.txt
            with open(os.path.join(backend_dir, 'requirements.txt'), 'w') as f:
                f.write("flask==2.0.1\nrequests==2.28.0\n")
            
            components = detector.detect_soup_components(temp_dir)
            
            # Should find components from nested files
            assert len(components) >= 4  # react, axios, flask, requests
            
            # Verify components from different directories
            react_comp = next((c for c in components if c.name == 'react'), None)
            assert react_comp is not None
            assert 'frontend' in react_comp.source_file
            
            flask_comp = next((c for c in components if c.name == 'flask'), None)
            assert flask_comp is not None
            assert 'backend' in flask_comp.source_file