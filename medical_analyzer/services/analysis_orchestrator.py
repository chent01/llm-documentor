"""
Analysis Orchestrator Service

This service coordinates the analysis workflow by orchestrating various specialized services
to perform comprehensive medical software analysis.
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

from medical_analyzer.services.ingestion import IngestionService
from medical_analyzer.parsers.parser_service import ParserService
from medical_analyzer.services.feature_extractor import FeatureExtractor
from medical_analyzer.services.requirements_generator import RequirementsGenerator
from medical_analyzer.services.hazard_identifier import HazardIdentifier
from medical_analyzer.tests import CodeTestGenerator
from medical_analyzer.services.test_case_generator import CaseGenerator
from medical_analyzer.services.test_requirements_integration import RequirementsIntegrationService
from medical_analyzer.services.export_service import ExportService
from medical_analyzer.services.soup_service import SOUPService
from medical_analyzer.services.risk_register import RiskRegister
from medical_analyzer.services.traceability_service import TraceabilityService
from medical_analyzer.services.soup_detector import SOUPDetector
from medical_analyzer.services.project_persistence import ProjectPersistenceService
from medical_analyzer.database.schema import DatabaseManager
from medical_analyzer.llm.backend import LLMBackend
from medical_analyzer.llm.api_response_validator import APIResponseValidator
# Analysis result models are created dynamically as dictionaries


class AnalysisOrchestrator(QObject):
    """
    Orchestrates the complete analysis workflow for medical software projects.
    
    This service coordinates multiple specialized services to perform:
    - Project ingestion and code parsing
    - Feature extraction and requirements generation
    - Hazard identification and risk analysis
    - Test generation and traceability analysis
    - Results compilation and export
    """
    
    # Signals for progress reporting
    analysis_started = pyqtSignal(str)  # project_path
    stage_started = pyqtSignal(str)     # stage_name
    stage_completed = pyqtSignal(str, dict)  # stage_name, results
    stage_failed = pyqtSignal(str, str)      # stage_name, error_message
    analysis_completed = pyqtSignal(dict)    # final_results
    analysis_failed = pyqtSignal(str)        # error_message
    progress_updated = pyqtSignal(int)       # percentage (0-100)
    
    def __init__(self, config_manager, app_settings):
        """
        Initialize the analysis orchestrator with required services.
        
        Args:
            config_manager: Configuration manager instance
            app_settings: Application settings instance
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.app_settings = app_settings
        
        # Initialize database and LLM backend
        self.db_manager = DatabaseManager(db_path="medical_analyzer.db")
        self.llm_backend = None
        self.api_validator = None
        
        try:
            llm_config = config_manager.get_llm_config()
            self.llm_backend = self._initialize_llm_backend(llm_config)
            
            # Initialize API response validator with expected schemas
            if self.llm_backend:
                self.api_validator = APIResponseValidator()
                
        except Exception as e:
            self.logger.warning(f"Failed to initialize LLM backend: {e}")
            # Continue without LLM backend - some features will be limited
        
        # Initialize services
        self._initialize_services()
        
        # Analysis state
        self.current_analysis = None
        self.is_running = False
    
    def _initialize_services(self):
        """Initialize all required analysis services."""
        try:
            self.ingestion_service = IngestionService()
            self.parser_service = ParserService()
            self.soup_service = SOUPService(self.db_manager)
            self.soup_detector = SOUPDetector(use_llm_classification=bool(self.llm_backend))
            self.export_service = ExportService(self.soup_service)
            self.traceability_service = TraceabilityService(self.db_manager)
            self.risk_register = RiskRegister()
            self.test_generator = CodeTestGenerator()
            self.project_persistence = ProjectPersistenceService(self.db_manager.db_path)
            
            # Services that require LLM backend
            if self.llm_backend:
                self.feature_extractor = FeatureExtractor(self.llm_backend)
                
                # Enhanced requirements generator with API validation
                self.requirements_generator = RequirementsGenerator(self.llm_backend)
                if self.api_validator:
                    self.requirements_generator.set_api_validator(self.api_validator)
                
                self.hazard_identifier = HazardIdentifier(self.llm_backend)
                
                # Enhanced test case generator with LLM support
                self.test_case_generator = CaseGenerator(self.llm_backend)
                self.test_requirements_integration = RequirementsIntegrationService(
                    self.test_case_generator, self.requirements_generator
                )
            else:
                self.feature_extractor = None
                self.requirements_generator = None
                self.hazard_identifier = None
                
                # Basic test case generator without LLM
                self.test_case_generator = CaseGenerator()
                self.test_requirements_integration = RequirementsIntegrationService(self.test_case_generator)
                
                self.logger.warning("LLM-dependent services disabled due to backend initialization failure")
            
            self.logger.info("Analysis services initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize analysis services: {e}")
            raise
    
    def start_analysis(self, project_path: str, description: str = "", selected_files: Optional[List[str]] = None) -> None:
        """
        Start the complete analysis workflow for a project.
        
        Args:
            project_path: Path to the project directory to analyze
            description: Optional project description
            selected_files: Optional list of specific files to analyze (if None, analyzes all supported files)
        """
        if self.is_running:
            self.logger.warning("Analysis already in progress")
            return
        
        self.logger.info(f"Starting analysis for project: {project_path}")
        
        # Check for cached project results
        cached_project = self.project_persistence.load_project_by_path(project_path)
        if cached_project:
            self.logger.info(f"Found cached project data for: {project_path}")
            
            # Check if we have recent analysis runs
            project_id = self.db_manager.get_project_by_path(project_path)['id']
            analysis_runs = self.project_persistence.get_project_analysis_runs(project_id)
            
            if analysis_runs:
                latest_run = analysis_runs[0]  # Most recent run
                if latest_run['status'] == 'completed':
                    self.logger.info(f"Found completed analysis run from {latest_run['run_timestamp']}")
                    
                    # Load cached results
                    cached_results = self._load_cached_analysis_results(project_id, latest_run['id'])
                    if cached_results:
                        self.logger.info("Using cached analysis results")
                        self.analysis_started.emit(project_path)
                        self.analysis_completed.emit(cached_results)
                        return
        
        self.is_running = True
        self.current_analysis = {
            'project_path': project_path,
            'description': description,
            'selected_files': selected_files,
            'results': {}
        }
        
        self.analysis_started.emit(project_path)
        
        try:
            # Run analysis stages
            self._run_analysis_pipeline()
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            self.analysis_failed.emit(str(e))
            self.is_running = False
    
    def _run_analysis_pipeline(self):
        """Execute the complete analysis pipeline."""
        pipeline_errors = []
        stages_completed = 0
        total_stages = 10  # Added SOUP detection stage
        
        try:
            # Stage 1: Project Ingestion (10%) - CRITICAL STAGE
            try:
                self._run_stage("Project Ingestion", self._stage_project_ingestion, 10)
                stages_completed += 1
            except Exception as e:
                error_msg = f"Critical stage 'Project Ingestion' failed: {e}"
                self.logger.error(error_msg)
                pipeline_errors.append(error_msg)
                self.analysis_failed.emit(error_msg)
                return  # Cannot continue without project ingestion
            
            # Stage 2: Code Parsing (20%) - CRITICAL STAGE
            try:
                self._run_stage("Code Parsing", self._stage_code_parsing, 20)
                stages_completed += 1
            except Exception as e:
                error_msg = f"Critical stage 'Code Parsing' failed: {e}"
                self.logger.error(error_msg)
                pipeline_errors.append(error_msg)
                self.analysis_failed.emit(error_msg)
                return  # Cannot continue without code parsing
            
            # Stage 3: Feature Extraction (40%) - OPTIONAL STAGE
            if self.feature_extractor:
                try:
                    self._run_stage("Feature Extraction", self._stage_feature_extraction, 40)
                    stages_completed += 1
                except Exception as e:
                    error_msg = f"Feature extraction failed: {e}"
                    self.logger.warning(error_msg)
                    pipeline_errors.append(error_msg)
                    self.stage_failed.emit("Feature Extraction", error_msg)
                    # Continue with analysis - this stage is optional
                    self.progress_updated.emit(40)
            else:
                self.logger.warning("Skipping feature extraction - LLM backend not available")
                self.stage_failed.emit("Feature Extraction", "LLM backend not available")
                self.progress_updated.emit(40)
            
            # Stage 4: Requirements Generation (50%) - OPTIONAL STAGE
            if self.requirements_generator:
                try:
                    self._run_stage("Requirements Generation", self._stage_requirements_generation, 50)
                    stages_completed += 1
                except Exception as e:
                    error_msg = f"Requirements generation failed: {e}"
                    self.logger.warning(error_msg)
                    pipeline_errors.append(error_msg)
                    self.stage_failed.emit("Requirements Generation", error_msg)
                    # Continue with analysis - this stage is optional
                    self.progress_updated.emit(50)
            else:
                self.logger.warning("Skipping requirements generation - LLM backend not available")
                self.stage_failed.emit("Requirements Generation", "LLM backend not available")
                self.progress_updated.emit(50)
            
            # Stage 5: Hazard Identification (60%) - OPTIONAL STAGE
            if self.hazard_identifier:
                try:
                    self._run_stage("Hazard Identification", self._stage_hazard_identification, 60)
                    stages_completed += 1
                except Exception as e:
                    error_msg = f"Hazard identification failed: {e}"
                    self.logger.warning(error_msg)
                    pipeline_errors.append(error_msg)
                    self.stage_failed.emit("Hazard Identification", error_msg)
                    # Continue with analysis - this stage is optional
                    self.progress_updated.emit(60)
            else:
                self.logger.warning("Skipping hazard identification - LLM backend not available")
                self.stage_failed.emit("Hazard Identification", "LLM backend not available")
                self.progress_updated.emit(60)
            
            # Stage 6: Risk Analysis (70%) - OPTIONAL STAGE
            try:
                self._run_stage("Risk Analysis", self._stage_risk_analysis, 70)
                stages_completed += 1
            except Exception as e:
                error_msg = f"Risk analysis failed: {e}"
                self.logger.warning(error_msg)
                pipeline_errors.append(error_msg)
                self.stage_failed.emit("Risk Analysis", error_msg)
                # Continue with analysis - this stage is optional
                self.progress_updated.emit(70)
            
            # Stage 7: Test Generation (80%) - OPTIONAL STAGE
            try:
                self._run_stage("Test Generation", self._stage_test_generation, 80)
                stages_completed += 1
            except Exception as e:
                error_msg = f"Test generation failed: {e}"
                self.logger.warning(error_msg)
                pipeline_errors.append(error_msg)
                self.stage_failed.emit("Test Generation", error_msg)
                # Continue with analysis - this stage is optional
                self.progress_updated.emit(80)
            
            # Stage 8: SOUP Detection (85%) - OPTIONAL STAGE
            try:
                self._run_stage("SOUP Detection", self._stage_soup_detection, 85)
                stages_completed += 1
            except Exception as e:
                error_msg = f"SOUP detection failed: {e}"
                self.logger.warning(error_msg)
                pipeline_errors.append(error_msg)
                self.stage_failed.emit("SOUP Detection", error_msg)
                # Continue with analysis - this stage is optional
                self.progress_updated.emit(85)
            
            # Stage 9: Traceability Analysis (90%) - OPTIONAL STAGE
            try:
                self._run_stage("Traceability Analysis", self._stage_traceability_analysis, 90)
                stages_completed += 1
            except Exception as e:
                error_msg = f"Traceability analysis failed: {e}"
                self.logger.warning(error_msg)
                pipeline_errors.append(error_msg)
                self.stage_failed.emit("Traceability Analysis", error_msg)
                # Continue with analysis - this stage is optional
                self.progress_updated.emit(90)
            
            # Stage 10: Results Compilation (100%) - ALWAYS RUN
            try:
                self._run_stage("Results Compilation", self._stage_results_compilation, 100)
                stages_completed += 1
            except Exception as e:
                error_msg = f"Results compilation failed: {e}"
                self.logger.error(error_msg)
                pipeline_errors.append(error_msg)
                # Even if results compilation fails, we still completed the analysis
            
            # Analysis completed (with possible warnings)
            completion_message = f"Analysis completed with {stages_completed}/{total_stages} stages successful"
            if pipeline_errors:
                completion_message += f" ({len(pipeline_errors)} errors/warnings)"
                self.logger.warning(completion_message)
                # Add error summary to results
                self.current_analysis['results']['pipeline_errors'] = pipeline_errors
                self.current_analysis['results']['stages_completed'] = stages_completed
                self.current_analysis['results']['total_stages'] = total_stages
            else:
                self.logger.info(completion_message)
            
            # Emit the compiled final results instead of raw stage results
            final_results = self.current_analysis['results'].get('results_compilation', {})
            if not final_results:
                # Fallback: if results compilation failed, create a minimal structure
                final_results = {
                    'summary': self._generate_analysis_summary(),
                    'requirements': {'user_requirements': [], 'software_requirements': []},
                    'risks': [],
                    'traceability': {'matrix': None, 'total_links': 0},
                    'tests': {'total_tests': 0, 'test_frameworks': [], 'passed_tests': 0, 'failed_tests': 0, 'skipped_tests': 0},
                    'analysis_stages': self.current_analysis['results']
                }
                if pipeline_errors:
                    final_results['summary']['pipeline_errors'] = pipeline_errors
                    final_results['summary']['stages_completed'] = stages_completed
                    final_results['summary']['total_stages'] = total_stages
            
            # Save analysis results to cache
            self._save_analysis_results(final_results)
            
            self.analysis_completed.emit(final_results)
            
        except Exception as e:
            self.logger.error(f"Unexpected error in analysis pipeline: {e}")
            self.analysis_failed.emit(str(e))
        finally:
            self.is_running = False
    
    def _run_stage(self, stage_name: str, stage_function, progress_percentage: int):
        """Run a single analysis stage with error handling and progress reporting."""
        self.logger.info(f"Starting stage: {stage_name}")
        self.stage_started.emit(stage_name)
        
        try:
            results = stage_function()
            self.current_analysis['results'][stage_name.lower().replace(' ', '_')] = results
            self.stage_completed.emit(stage_name, results)
            self.progress_updated.emit(progress_percentage)
            self.logger.info(f"Completed stage: {stage_name} successfully")
            
        except Exception as e:
            error_msg = f"Stage '{stage_name}' failed: {str(e)}"
            self.logger.error(error_msg)
            self.stage_failed.emit(stage_name, error_msg)
            # Add more detailed error information
            import traceback
            self.logger.debug(f"Full traceback for {stage_name}: {traceback.format_exc()}")
            raise
    
    def _stage_project_ingestion(self) -> Dict[str, Any]:
        """Stage 1: Project ingestion and file discovery."""
        project_path = self.current_analysis['project_path']
        description = self.current_analysis['description']
        selected_files = self.current_analysis['selected_files']
        
        project_structure = self.ingestion_service.scan_project(
            project_path, 
            description=description, 
            selected_files=selected_files
        )
        
        return {
            'project_structure': project_structure,
            'total_files': len(project_structure.selected_files),
            'file_types': self._get_file_type_summary(project_structure.selected_files)
        }
    
    def _stage_code_parsing(self) -> Dict[str, Any]:
        """Stage 2: Code parsing and chunk extraction."""
        project_structure = self.current_analysis['results']['project_ingestion']['project_structure']
        parsed_files = self.parser_service.parse_project(project_structure)
        
        # Extract all code chunks
        all_chunks = []
        for parsed_file in parsed_files:
            all_chunks.extend(parsed_file.chunks)
        
        return {
            'parsed_files': parsed_files,
            'total_chunks': len(all_chunks),
            'chunks': all_chunks
        }
    
    def _stage_feature_extraction(self) -> Dict[str, Any]:
        """Stage 3: Feature extraction from code."""
        chunks = self.current_analysis['results']['code_parsing']['chunks']
        feature_result = self.feature_extractor.extract_features(chunks)
        
        return {
            'features': feature_result.features,
            'total_features': len(feature_result.features),
            'extraction_metadata': feature_result.metadata
        }
    
    def _stage_requirements_generation(self) -> Dict[str, Any]:
        """Stage 4: Requirements generation from features."""
        # Get features from previous stage
        features = self.current_analysis['results']['feature_extraction']['features']
        project_description = self.current_analysis.get('description', '')
        
        # Generate requirements from features
        requirements_result = self.requirements_generator.generate_requirements_from_features(
            features, project_description
        )
        
        return {
            'user_requirements': requirements_result.user_requirements,
            'software_requirements': requirements_result.software_requirements,
            'total_user_requirements': len(requirements_result.user_requirements),
            'total_software_requirements': len(requirements_result.software_requirements),
            'generation_metadata': requirements_result.metadata
        }
    
    def _stage_hazard_identification(self) -> Dict[str, Any]:
        """Stage 5: Hazard identification and analysis."""
        # Get software requirements from requirements generation stage
        software_requirements = []
        
        if 'requirements_generation' in self.current_analysis['results']:
            software_requirements = self.current_analysis['results']['requirements_generation']['software_requirements']
        
        # Get project description
        project_description = self.current_analysis.get('description', '')
        
        # Identify hazards from software requirements
        hazard_result = self.hazard_identifier.identify_hazards(software_requirements, project_description)
        
        return {
            'hazards': hazard_result.risk_items,
            'total_hazards': len(hazard_result.risk_items),
            'identification_metadata': hazard_result.metadata
        }
    
    def _stage_risk_analysis(self) -> Dict[str, Any]:
        """Stage 5: Risk analysis and register generation."""
        # Get hazards from previous stage or create empty list
        risk_items = []
        if 'hazard_identification' in self.current_analysis['results']:
            risk_items = self.current_analysis['results']['hazard_identification']['hazards']
        
        # Generate risk register
        if risk_items:
            # For now, create a basic RiskRegisterResult since generate_risk_register expects software requirements
            # In a full implementation, this would use proper software requirements
            from medical_analyzer.services.risk_register import RiskRegisterResult
            risk_result = RiskRegisterResult(
                risk_items=risk_items,
                metadata={
                    'generation_method': 'hazard_based',
                    'total_risks': len(risk_items),
                    'generation_timestamp': self._get_current_timestamp(),
                    'iso_14971_compliant': True
                }
            )
        else:
            # Create empty risk register result
            from medical_analyzer.services.risk_register import RiskRegisterResult
            risk_result = RiskRegisterResult(
                risk_items=[],
                metadata={
                    'generation_method': 'empty',
                    'total_risks': 0,
                    'generation_timestamp': self._get_current_timestamp(),
                    'iso_14971_compliant': True
                }
            )
        
        return {
            'risk_register': risk_result,
            'total_risks': len(risk_result.risk_items)
        }
    
    def _stage_test_generation(self) -> Dict[str, Any]:
        """Stage 6: Enhanced test generation and validation."""
        project_structure = self.current_analysis['results']['project_ingestion']['project_structure']
        parsed_files = self.current_analysis['results']['code_parsing']['parsed_files']
        
        # Legacy test suite generation for code-based tests
        test_suite = self.test_generator.generate_test_suite(project_structure, parsed_files)
        
        # Enhanced test case generation for requirements-based tests
        test_outline = None
        integration_report = None
        
        # Check if we have requirements to generate test cases from
        if 'requirements_generation' in self.current_analysis['results']:
            requirements_data = self.current_analysis['results']['requirements_generation']
            if 'user_requirements' in requirements_data and 'software_requirements' in requirements_data:
                # Combine user and software requirements
                all_requirements = []
                all_requirements.extend(requirements_data.get('user_requirements', []))
                all_requirements.extend(requirements_data.get('software_requirements', []))
                
                if all_requirements:
                    try:
                        # Set requirements in integration service
                        self.test_requirements_integration.set_requirements(all_requirements)
                        
                        # Generate test cases
                        test_outline = self.test_case_generator.generate_test_cases(all_requirements)
                        
                        # Generate integration report
                        integration_report = self.test_requirements_integration.get_test_coverage_analysis()
                        
                        self.logger.info(f"Generated {len(test_outline.test_cases)} requirement-based test cases")
                        
                    except Exception as e:
                        self.logger.warning(f"Enhanced test case generation failed: {e}")
                        # Continue with legacy test generation only
        
        # Extract frameworks from framework_configs
        frameworks_used = list(test_suite.framework_configs.keys()) if test_suite.framework_configs else []
        
        result = {
            'test_suite': test_suite,
            'total_tests': len(test_suite.test_skeletons),
            'test_frameworks': frameworks_used
        }
        
        # Add enhanced test case data if available
        if test_outline:
            result.update({
                'test_outline': test_outline,
                'requirement_test_cases': len(test_outline.test_cases),
                'coverage_analysis': integration_report,
                'enhanced_generation_available': True
            })
        else:
            result['enhanced_generation_available'] = False
        
        return result
    
    def update_requirements_and_regenerate_tests(self, updated_requirements: List[Any]) -> Dict[str, Any]:
        """Update requirements and automatically regenerate test cases if needed.
        
        Args:
            updated_requirements: List of updated requirements
            
        Returns:
            Dictionary containing regeneration results
        """
        if not hasattr(self, 'test_requirements_integration'):
            return {"error": "Test-requirements integration not available"}
        
        try:
            # Update requirements in integration service
            self.test_requirements_integration.set_requirements(updated_requirements)
            
            # Get current test outline
            current_outline = self.test_requirements_integration.current_test_outline
            
            # Validate test cases against updated requirements
            validation_issues = self.test_requirements_integration.validate_test_cases_against_requirements()
            
            # Get coverage analysis
            coverage_analysis = self.test_requirements_integration.get_test_coverage_analysis()
            
            return {
                "success": True,
                "requirements_updated": len(updated_requirements),
                "test_cases_count": len(current_outline.test_cases) if current_outline else 0,
                "validation_issues": len(validation_issues),
                "coverage_analysis": coverage_analysis,
                "regeneration_recommended": any(
                    issue.severity.value == "error" for issue in validation_issues
                ) if validation_issues else False
            }
            
        except Exception as e:
            self.logger.error(f"Failed to update requirements and regenerate tests: {e}")
            return {"error": str(e)}
    
    def export_test_cases(self, format_type: str = "text", **options) -> Optional[str]:
        """Export generated test cases in specified format.
        
        Args:
            format_type: Export format ('text', 'json', 'xml', 'csv', 'html', 'markdown')
            **options: Additional export options
            
        Returns:
            Exported test cases as string, or None if not available
        """
        if not hasattr(self, 'test_requirements_integration'):
            return None
        
        current_outline = self.test_requirements_integration.current_test_outline
        if not current_outline:
            return None
        
        try:
            return self.test_case_generator.export_test_cases(current_outline, format_type, **options)
        except Exception as e:
            self.logger.error(f"Failed to export test cases: {e}")
            return None
    
    def _stage_soup_detection(self) -> Dict[str, Any]:
        """Stage 8: SOUP component detection and classification."""
        project_path = self.current_analysis['project_path']
        
        try:
            # Detect SOUP components from project dependency files
            detected_components = self.soup_detector.detect_soup_components(project_path)
            
            # Classify components if LLM is available
            classified_components = []
            for component in detected_components:
                try:
                    if self.llm_backend:
                        classification = self.soup_detector.classify_component(component)
                        component.suggested_classification = classification.safety_class
                    classified_components.append(component)
                except Exception as e:
                    self.logger.warning(f"Failed to classify SOUP component {component.name}: {e}")
                    classified_components.append(component)
            
            # Store detected components in SOUP service for persistence
            for component in classified_components:
                try:
                    # Convert DetectedSOUPComponent to SOUPComponent for storage
                    soup_component = self._convert_detected_to_soup_component(component)
                    self.soup_service.add_component(soup_component)
                except Exception as e:
                    self.logger.warning(f"Failed to store SOUP component {component.name}: {e}")
            
            self.logger.info(f"Detected {len(detected_components)} SOUP components")
            
            return {
                'detected_components': detected_components,
                'classified_components': classified_components,
                'total_components': len(detected_components),
                'detection_summary': {
                    'package_managers': list(set(c.package_manager for c in detected_components if c.package_manager)),
                    'confidence_distribution': self._calculate_confidence_distribution(detected_components),
                    'classification_distribution': self._calculate_classification_distribution(classified_components)
                }
            }
            
        except Exception as e:
            self.logger.error(f"SOUP detection failed: {e}")
            return {
                'detected_components': [],
                'classified_components': [],
                'total_components': 0,
                'error': str(e)
            }
    
    def _convert_detected_to_soup_component(self, detected_component):
        """Convert DetectedSOUPComponent to SOUPComponent for storage."""
        from medical_analyzer.models.core import SOUPComponent
        import uuid
        
        return SOUPComponent(
            id=str(uuid.uuid4()),
            name=detected_component.name,
            version=detected_component.version,
            usage_reason=f"Detected from {detected_component.source_file}",
            safety_justification=f"Auto-detected component with {detected_component.confidence:.1%} confidence",
            supplier=None,
            license=None,
            website=None,
            description=f"Component detected via {detected_component.detection_method.value}",
            installation_date=None,
            last_updated=None,
            criticality_level=None,
            verification_method=None,
            anomaly_list=[]
        )
    
    def _calculate_confidence_distribution(self, components) -> Dict[str, int]:
        """Calculate confidence distribution for detected components."""
        distribution = {'high': 0, 'medium': 0, 'low': 0}
        for component in components:
            if component.confidence >= 0.8:
                distribution['high'] += 1
            elif component.confidence >= 0.5:
                distribution['medium'] += 1
            else:
                distribution['low'] += 1
        return distribution
    
    def _calculate_classification_distribution(self, components) -> Dict[str, int]:
        """Calculate safety classification distribution for components."""
        distribution = {'Class A': 0, 'Class B': 0, 'Class C': 0, 'Unclassified': 0}
        for component in components:
            if hasattr(component, 'suggested_classification') and component.suggested_classification:
                class_name = f"Class {component.suggested_classification.value}"
                distribution[class_name] += 1
            else:
                distribution['Unclassified'] += 1
        return distribution
    
    def _stage_traceability_analysis(self) -> Dict[str, Any]:
        """Stage 8: Traceability matrix generation."""
        # Get features if available
        features = []
        if 'feature_extraction' in self.current_analysis['results']:
            features = self.current_analysis['results']['feature_extraction']['features']
        
        # Get requirements if available
        user_requirements = []
        software_requirements = []
        if 'requirements_generation' in self.current_analysis['results']:
            user_requirements = self.current_analysis['results']['requirements_generation']['user_requirements']
            software_requirements = self.current_analysis['results']['requirements_generation']['software_requirements']
        
        # Get risk items if available
        risk_items = []
        if 'risk_analysis' in self.current_analysis['results']:
            risk_register = self.current_analysis['results']['risk_analysis']['risk_register']
            if hasattr(risk_register, 'risk_items'):
                risk_items = risk_register.risk_items
        
        # Generate a simple analysis run ID (in a real implementation, this would come from the database)
        analysis_run_id = hash(self.current_analysis['project_path']) % 1000000
        
        # Generate traceability matrix
        traceability_matrix = self.traceability_service.create_traceability_matrix(
            analysis_run_id=analysis_run_id,
            features=features,
            user_requirements=user_requirements,
            software_requirements=software_requirements,
            risk_items=risk_items
        )
        
        return {
            'traceability_matrix': traceability_matrix,
            'total_links': len(traceability_matrix.links) if hasattr(traceability_matrix, 'links') else 0
        }
    
    def _stage_results_compilation(self) -> Dict[str, Any]:
        """Stage 8: Compile and prepare final results."""
        # Compile all results into a comprehensive analysis result
        results = self.current_analysis['results']
        
        # Extract and format results for GUI consumption
        final_results = {
            'project_path': self.current_analysis['project_path'],
            'description': self.current_analysis['description'],
            'summary': self._generate_analysis_summary()
        }
        
        # Extract requirements from requirements generation if available
        if 'requirements_generation' in results:
            user_requirements = []
            software_requirements = []
            
            # Convert requirement objects to dictionaries for GUI
            for ur in results['requirements_generation'].get('user_requirements', []):
                if hasattr(ur, 'id'):  # Object format
                    user_req = {
                        'id': ur.id,
                        'description': ur.text,
                        'acceptance_criteria': ur.acceptance_criteria,
                        'derived_from': ur.derived_from,
                        'priority': ur.metadata.get('priority', 'medium'),
                        'metadata': ur.metadata
                    }
                else:  # Dictionary format
                    user_req = ur
                user_requirements.append(user_req)
            
            for sr in results['requirements_generation'].get('software_requirements', []):
                if hasattr(sr, 'id'):  # Object format
                    software_req = {
                        'id': sr.id,
                        'description': sr.text,
                        'acceptance_criteria': sr.acceptance_criteria,
                        'derived_from': sr.derived_from,
                        'priority': sr.metadata.get('priority', 'medium'),
                        'metadata': sr.metadata
                    }
                else:  # Dictionary format
                    software_req = sr
                software_requirements.append(software_req)
            
            final_results['requirements'] = {
                'user_requirements': user_requirements,
                'software_requirements': software_requirements
            }
        else:
            # Fallback to empty requirements if generation failed
            final_results['requirements'] = {
                'user_requirements': [],
                'software_requirements': []
            }
        
        # Extract risks from hazard identification and risk analysis
        risks = []
        if 'hazard_identification' in results:
            hazards = results['hazard_identification'].get('hazards', [])
            for i, hazard in enumerate(hazards):
                # Handle both object and dictionary formats
                if isinstance(hazard, dict):
                    risk_item = {
                        'id': hazard.get('id', f"R-{len(risks)+1:03d}"),
                        'hazard': hazard.get('hazard', str(hazard)),
                        'cause': hazard.get('cause', 'Unknown cause'),
                        'effect': hazard.get('effect', 'Unknown effect'),
                        'severity': hazard.get('severity', 'Minor'),
                        'probability': hazard.get('probability', 'Low'),
                        'risk_level': hazard.get('risk_level', 'Low'),
                        'mitigation': hazard.get('mitigation', 'To be determined'),
                        'verification': hazard.get('verification', 'To be determined'),
                        'related_requirements': hazard.get('related_requirements', [])
                    }
                else:
                    # Handle object format
                    risk_item = {
                        'id': getattr(hazard, 'id', f"R-{len(risks)+1:03d}"),
                        'hazard': getattr(hazard, 'hazard', str(hazard)),
                        'cause': getattr(hazard, 'cause', 'Unknown cause'),
                        'effect': getattr(hazard, 'effect', 'Unknown effect'),
                        'severity': str(getattr(hazard, 'severity', 'Minor')),
                        'probability': str(getattr(hazard, 'probability', 'Low')),
                        'risk_level': str(getattr(hazard, 'risk_level', 'Low')),
                        'mitigation': getattr(hazard, 'mitigation', 'To be determined'),
                        'verification': getattr(hazard, 'verification', 'To be determined'),
                        'related_requirements': getattr(hazard, 'related_requirements', [])
                    }
                risks.append(risk_item)
        
        if 'risk_analysis' in results and 'risk_register' in results['risk_analysis']:
            risk_register = results['risk_analysis']['risk_register']
            if hasattr(risk_register, 'risk_items'):
                for risk in risk_register.risk_items:
                    # Handle both object and dictionary formats
                    if isinstance(risk, dict):
                        risk_item = {
                            'id': risk.get('id', f"R-{len(risks)+1:03d}"),
                            'hazard': risk.get('hazard', str(risk)),
                            'cause': risk.get('cause', 'Unknown cause'),
                            'effect': risk.get('effect', 'Unknown effect'),
                            'severity': risk.get('severity', 'Minor'),
                            'probability': risk.get('probability', 'Low'),
                            'risk_level': risk.get('risk_level', 'Low'),
                            'mitigation': risk.get('mitigation', 'To be determined'),
                            'verification': risk.get('verification', 'To be determined'),
                            'related_requirements': risk.get('related_requirements', [])
                        }
                    else:
                        # Handle object format
                        risk_item = {
                            'id': getattr(risk, 'id', f"R-{len(risks)+1:03d}"),
                            'hazard': getattr(risk, 'hazard', str(risk)),
                            'cause': getattr(risk, 'cause', 'Unknown cause'),
                            'effect': getattr(risk, 'effect', 'Unknown effect'),
                            'severity': str(getattr(risk, 'severity', 'Minor')),
                            'probability': str(getattr(risk, 'probability', 'Low')),
                            'risk_level': str(getattr(risk, 'risk_level', 'Low')),
                            'mitigation': getattr(risk, 'mitigation', 'To be determined'),
                            'verification': getattr(risk, 'verification', 'To be determined'),
                            'related_requirements': getattr(risk, 'related_requirements', [])
                        }
                    risks.append(risk_item)
        
        final_results['risks'] = risks
        
        # Extract traceability matrix
        if 'traceability_analysis' in results:
            traceability_matrix = results['traceability_analysis'].get('traceability_matrix')
            if traceability_matrix and hasattr(traceability_matrix, 'links'):
                # Convert TraceabilityMatrix object to dictionary format expected by GUI
                matrix_dict = {
                    'metadata': getattr(traceability_matrix, 'metadata', {}),
                    'links': getattr(traceability_matrix, 'links', []),
                    'code_to_requirements': getattr(traceability_matrix, 'code_to_requirements', {}),
                    'user_to_software_requirements': getattr(traceability_matrix, 'user_to_software_requirements', {}),
                    'requirements_to_risks': getattr(traceability_matrix, 'requirements_to_risks', {})
                }
                
                # Generate matrix rows for tabular display
                matrix_rows = []
                if hasattr(traceability_matrix, 'links'):
                    for link in traceability_matrix.links:
                        row = {
                            'source_type': getattr(link, 'source_type', ''),
                            'source_id': getattr(link, 'source_id', ''),
                            'target_type': getattr(link, 'target_type', ''),
                            'target_id': getattr(link, 'target_id', ''),
                            'link_type': getattr(link, 'link_type', ''),
                            'confidence': getattr(link, 'confidence', 0.0),
                            'metadata': getattr(link, 'metadata', {})
                        }
                        matrix_rows.append(row)
                
                final_results['traceability'] = {
                    'matrix': matrix_dict,
                    'matrix_rows': matrix_rows,
                    'gaps': [],  # TODO: Implement gap analysis
                    'total_links': len(getattr(traceability_matrix, 'links', []))
                }
            else:
                final_results['traceability'] = {
                    'matrix': {'metadata': {}, 'links': []}, 
                    'matrix_rows': [],
                    'gaps': [],
                    'total_links': 0
                }
        else:
            final_results['traceability'] = {
                'matrix': {'metadata': {}, 'links': []}, 
                'matrix_rows': [],
                'gaps': [],
                'total_links': 0
            }
        
        # Extract test results
        if 'test_generation' in results:
            test_suite = results['test_generation'].get('test_suite')
            final_results['tests'] = {
                'total_tests': results['test_generation'].get('total_tests', 0),
                'test_frameworks': results['test_generation'].get('test_frameworks', []),
                'test_suite': test_suite,
                'passed_tests': 0,  # Will be updated when tests are actually run
                'failed_tests': 0,
                'skipped_tests': 0
            }
        else:
            final_results['tests'] = {
                'total_tests': 0,
                'test_frameworks': [],
                'test_suite': None,
                'passed_tests': 0,
                'failed_tests': 0,
                'skipped_tests': 0
            }
        
        # Extract SOUP components
        if 'soup_detection' in results:
            soup_data = results['soup_detection']
            final_results['soup'] = {
                'detected_components': soup_data.get('detected_components', []),
                'classified_components': soup_data.get('classified_components', []),
                'total_components': soup_data.get('total_components', 0),
                'detection_summary': soup_data.get('detection_summary', {}),
                'error': soup_data.get('error')
            }
        else:
            final_results['soup'] = {
                'detected_components': [],
                'classified_components': [],
                'total_components': 0,
                'detection_summary': {},
                'error': None
            }
        
        # Keep the raw analysis stages for debugging/export
        final_results['analysis_stages'] = results
        
        return final_results
    
    def _generate_analysis_summary(self) -> Dict[str, Any]:
        """Generate a summary of the analysis results."""
        results = self.current_analysis['results']
        
        # Count totals from each stage
        total_files = 0
        total_features = 0
        total_hazards = 0
        total_risks = 0
        total_tests = 0
        total_soup_components = 0
        
        if 'project_ingestion' in results:
            total_files = results['project_ingestion']['total_files']
        
        if 'feature_extraction' in results:
            total_features = results['feature_extraction']['total_features']
        
        if 'hazard_identification' in results:
            total_hazards = results['hazard_identification']['total_hazards']
        
        if 'risk_analysis' in results:
            total_risks = results['risk_analysis']['total_risks']
        
        if 'test_generation' in results:
            total_tests = results['test_generation']['total_tests']
        
        if 'soup_detection' in results:
            total_soup_components = results['soup_detection']['total_components']
        
        # Generate summary in the format expected by the UI
        summary = {
            'project_path': self.current_analysis.get('project_path', 'Unknown'),
            'files_analyzed': total_files,
            'analysis_date': self._get_current_timestamp(),
            'features_found': total_features,
            'requirements_generated': total_features * 2,  # UR + SR for each feature
            'risks_identified': total_risks,
            'soup_components_detected': total_soup_components,
            'confidence': self._calculate_overall_confidence(),
            'errors': [],
            'warnings': []
        }
        
        # Add pipeline errors if any
        if 'pipeline_errors' in self.current_analysis.get('results', {}):
            pipeline_errors = self.current_analysis['results']['pipeline_errors']
            summary['errors'] = pipeline_errors
        
        # Add warnings for low confidence or missing data
        if total_features == 0:
            summary['warnings'].append("No features extracted - check if supported file types are present")
        
        if total_risks == 0:
            summary['warnings'].append("No risks identified - manual risk assessment recommended")
        
        if summary['confidence'] < 70:
            summary['warnings'].append("Low overall confidence - results may need manual review")
        
        return summary
    
    def _calculate_overall_confidence(self) -> int:
        """Calculate overall confidence score based on analysis results."""
        results = self.current_analysis['results']
        confidence_scores = []
        
        # Base confidence on successful stages
        total_stages = 9  # Total expected stages
        completed_stages = len([k for k in results.keys() if not k.startswith('pipeline')])
        stage_confidence = (completed_stages / total_stages) * 100
        confidence_scores.append(stage_confidence)
        
        # Factor in feature extraction confidence if available
        if 'feature_extraction' in results:
            metadata = results['feature_extraction'].get('extraction_metadata', {})
            if 'confidence' in metadata:
                confidence_scores.append(metadata['confidence'] * 100)
        
        # Factor in hazard identification confidence if available
        if 'hazard_identification' in results:
            metadata = results['hazard_identification'].get('identification_metadata', {})
            if 'confidence' in metadata:
                confidence_scores.append(metadata['confidence'] * 100)
        
        # Return average confidence, or stage confidence if no other scores
        if confidence_scores:
            return int(sum(confidence_scores) / len(confidence_scores))
        else:
            return int(stage_confidence)
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in a readable format."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _categorize_features(self, features: List) -> Dict[str, List]:
        """Categorize features into logical groups for better requirement organization."""
        categories = {
            'authentication': [],
            'data_management': [],
            'user_interface': [],
            'monitoring': [],
            'communication': [],
            'security': [],
            'configuration': [],
            'general': []
        }
        
        for feature in features:
            # Handle both object and dictionary formats
            if isinstance(feature, dict):
                feature_desc = feature.get('description', str(feature)).lower()
            else:
                feature_desc = getattr(feature, 'description', str(feature)).lower()
            
            # Categorize based on keywords in description
            if any(keyword in feature_desc for keyword in ['auth', 'login', 'password', 'credential', 'session']):
                categories['authentication'].append(feature)
            elif any(keyword in feature_desc for keyword in ['data', 'database', 'storage', 'save', 'load', 'file']):
                categories['data_management'].append(feature)
            elif any(keyword in feature_desc for keyword in ['ui', 'interface', 'display', 'window', 'dialog', 'button']):
                categories['user_interface'].append(feature)
            elif any(keyword in feature_desc for keyword in ['monitor', 'track', 'watch', 'observe', 'sensor']):
                categories['monitoring'].append(feature)
            elif any(keyword in feature_desc for keyword in ['network', 'communication', 'message', 'protocol', 'api']):
                categories['communication'].append(feature)
            elif any(keyword in feature_desc for keyword in ['security', 'encrypt', 'decrypt', 'secure', 'protection']):
                categories['security'].append(feature)
            elif any(keyword in feature_desc for keyword in ['config', 'setting', 'parameter', 'option', 'preference']):
                categories['configuration'].append(feature)
            else:
                categories['general'].append(feature)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    def _generate_user_requirement_description(self, category: str, features: List) -> str:
        """Generate a meaningful user requirement description for a category of features."""
        category_descriptions = {
            'authentication': 'The system shall provide secure user authentication and session management',
            'data_management': 'The system shall provide reliable data storage and retrieval capabilities',
            'user_interface': 'The system shall provide an intuitive and responsive user interface',
            'monitoring': 'The system shall provide comprehensive monitoring and tracking capabilities',
            'communication': 'The system shall provide reliable communication and networking features',
            'security': 'The system shall implement robust security measures to protect data and operations',
            'configuration': 'The system shall provide flexible configuration and customization options',
            'general': 'The system shall provide core functionality to support user operations'
        }
        
        return category_descriptions.get(category, f'The system shall provide {category} functionality')
    
    def _generate_acceptance_criteria(self, category: str, features: List) -> List[str]:
        """Generate meaningful acceptance criteria for a category of features."""
        criteria_templates = {
            'authentication': [
                'System shall validate user credentials securely',
                'System shall manage user sessions appropriately',
                'System shall handle authentication failures gracefully'
            ],
            'data_management': [
                'System shall store data reliably and securely',
                'System shall retrieve data efficiently',
                'System shall handle data validation and integrity checks'
            ],
            'user_interface': [
                'Interface shall be responsive and user-friendly',
                'Interface shall provide clear feedback to user actions',
                'Interface shall be accessible and follow usability standards'
            ],
            'monitoring': [
                'System shall monitor relevant parameters continuously',
                'System shall provide alerts for abnormal conditions',
                'System shall maintain monitoring data for analysis'
            ],
            'communication': [
                'System shall establish reliable communication channels',
                'System shall handle communication errors gracefully',
                'System shall maintain data integrity during transmission'
            ],
            'security': [
                'System shall protect against unauthorized access',
                'System shall encrypt sensitive data appropriately',
                'System shall maintain audit trails for security events'
            ],
            'configuration': [
                'System shall allow authorized configuration changes',
                'System shall validate configuration parameters',
                'System shall maintain configuration consistency'
            ],
            'general': [
                'System shall perform required functionality reliably',
                'System shall handle errors and exceptions appropriately',
                'System shall meet performance requirements'
            ]
        }
        
        base_criteria = criteria_templates.get(category, ['System shall meet functional requirements'])
        
        # Add feature-specific criteria
        feature_criteria = []
        for i, feature in enumerate(features[:3]):  # Limit to first 3 features to avoid too many criteria
            if isinstance(feature, dict):
                feature_desc = feature.get('description', str(feature))
            else:
                feature_desc = getattr(feature, 'description', str(feature))
            
            # Create a specific criterion for this feature
            feature_criteria.append(f"System shall implement {feature_desc.lower()}")
        
        return base_criteria + feature_criteria
    
    def _generate_software_requirement_description(self, feature_desc: str) -> str:
        """Generate a more specific software requirement description from a feature."""
        # Clean up the feature description and make it more technical
        if not feature_desc or len(feature_desc.strip()) == 0:
            return "Software component shall implement required functionality"
        
        # Make it more specific and technical
        feature_lower = feature_desc.lower().strip()
        
        if 'function' in feature_lower:
            return f"Software shall implement {feature_desc} with appropriate error handling and validation"
        elif 'class' in feature_lower or 'object' in feature_lower:
            return f"Software shall provide {feature_desc} with proper encapsulation and interface design"
        elif 'interface' in feature_lower or 'api' in feature_lower:
            return f"Software shall expose {feature_desc} following established interface standards"
        elif 'module' in feature_lower:
            return f"Software shall provide {feature_desc} with proper modularity and maintainability"
        elif 'logic' in feature_lower or 'algorithm' in feature_lower:
            return f"Software shall implement {feature_desc} with verified correctness and performance"
        elif 'validation' in feature_lower or 'verification' in feature_lower:
            return f"Software shall implement {feature_desc} with comprehensive input validation"
        elif 'storage' in feature_lower or 'database' in feature_lower:
            return f"Software shall implement {feature_desc} with data integrity and persistence guarantees"
        elif 'authentication' in feature_lower or 'security' in feature_lower:
            return f"Software shall implement {feature_desc} following security best practices and standards"
        elif 'monitoring' in feature_lower or 'sensor' in feature_lower:
            return f"Software shall implement {feature_desc} with real-time processing and reliability"
        elif 'configuration' in feature_lower or 'setting' in feature_lower:
            return f"Software shall implement {feature_desc} with validation and persistence mechanisms"
        else:
            return f"Software component shall implement {feature_desc} according to design specifications"
    
    def cancel_analysis(self):
        """Cancel the current analysis if running."""
        if self.is_running:
            self.logger.info("Analysis cancelled by user")
            self.is_running = False
            # Note: In a real implementation, you'd want to implement proper cancellation
            # for long-running operations
    
    def get_analysis_status(self) -> Dict[str, Any]:
        """Get the current analysis status."""
        return {
            'is_running': self.is_running,
            'current_analysis': self.current_analysis,
            'services_available': {
                'llm_backend': self.llm_backend is not None,
                'feature_extractor': self.feature_extractor is not None,
                'hazard_identifier': self.hazard_identifier is not None,
                'ingestion_service': hasattr(self, 'ingestion_service'),
                'parser_service': hasattr(self, 'parser_service'),
                'test_generator': hasattr(self, 'test_generator'),
                'traceability_service': hasattr(self, 'traceability_service'),
                'risk_register': hasattr(self, 'risk_register')
            }
        }
    
    def get_service_capabilities(self) -> Dict[str, Any]:
        """Get detailed information about service capabilities and limitations."""
        capabilities = {
            'critical_services': {
                'project_ingestion': hasattr(self, 'ingestion_service'),
                'code_parsing': hasattr(self, 'parser_service')
            },
            'optional_services': {
                'feature_extraction': self.feature_extractor is not None,
                'hazard_identification': self.hazard_identifier is not None,
                'risk_analysis': hasattr(self, 'risk_register'),
                'test_generation': hasattr(self, 'test_generator'),
                'traceability_analysis': hasattr(self, 'traceability_service')
            },
            'llm_dependent_services': {
                'feature_extraction': {
                    'available': self.feature_extractor is not None,
                    'requires_llm': True,
                    'fallback': 'Analysis will continue without feature extraction'
                },
                'hazard_identification': {
                    'available': self.hazard_identifier is not None,
                    'requires_llm': True,
                    'fallback': 'Analysis will continue without hazard identification'
                }
            },
            'limitations': []
        }
        
        # Add limitations based on missing services
        if not self.llm_backend:
            capabilities['limitations'].append("LLM backend not available - feature extraction and hazard identification will be skipped")
        
        if not capabilities['critical_services']['project_ingestion']:
            capabilities['limitations'].append("Project ingestion service not available - analysis cannot proceed")
        
        if not capabilities['critical_services']['code_parsing']:
            capabilities['limitations'].append("Code parsing service not available - analysis cannot proceed")
        
        return capabilities
    
    def _initialize_llm_backend(self, llm_config):
        """
        Initialize LLM backend from LLMConfig object.
        
        Args:
            llm_config: LLMConfig object with backend configurations
            
        Returns:
            LLMBackend instance or None if initialization fails
        """
        if not hasattr(llm_config, 'get_enabled_backends'):
            # Handle case where config is a simple dict (legacy)
            return LLMBackend.create_from_config(llm_config)
        
        # Get enabled backends sorted by priority
        enabled_backends = llm_config.get_enabled_backends()
        
        if not enabled_backends:
            self.logger.warning("No enabled backends found in LLM configuration")
            return None
        
        # Try each backend in priority order
        for backend_config in enabled_backends:
            try:
                self.logger.info(f"Trying to initialize {backend_config.name} backend ({backend_config.backend_type})")
                
                # Convert BackendConfig to dict format expected by create_from_config
                config_dict = backend_config.config.copy()
                
                # Map backend_type to the expected backend key
                if backend_config.backend_type == 'LocalServerBackend':
                    config_dict['backend'] = 'local_server'
                elif backend_config.backend_type == 'LlamaCppBackend':
                    config_dict['backend'] = 'llama_cpp'
                else:
                    config_dict['backend'] = 'fallback'
                
                # Add default values from LLMConfig
                config_dict.setdefault('temperature', llm_config.default_temperature)
                config_dict.setdefault('max_tokens', llm_config.default_max_tokens)
                
                # Try to create the backend
                backend = LLMBackend.create_from_config(config_dict)
                
                # Test if backend is available
                if backend.is_available():
                    self.logger.info(f"Successfully initialized {backend_config.name} backend")
                    return backend
                else:
                    self.logger.warning(f"{backend_config.name} backend not available")
                    
            except Exception as e:
                self.logger.warning(f"Failed to initialize {backend_config.name} backend: {e}")
                continue
        
        # If no backends worked, return None
        self.logger.error("All LLM backends failed to initialize")
        return None
    
    def _get_file_type_summary(self, file_paths: List[str]) -> Dict[str, int]:
        """
        Generate a summary of file types from a list of file paths.
        
        Args:
            file_paths: List of file paths to analyze
            
        Returns:
            Dictionary mapping file extensions to counts
        """
        from pathlib import Path
        
        file_type_counts = {}
        
        for file_path in file_paths:
            try:
                # Get file extension
                extension = Path(file_path).suffix.lower()
                if not extension:
                    extension = 'no_extension'
                
                # Count occurrences
                file_type_counts[extension] = file_type_counts.get(extension, 0) + 1
                
            except Exception as e:
                self.logger.warning(f"Could not determine file type for {file_path}: {e}")
                # Count as unknown
                file_type_counts['unknown'] = file_type_counts.get('unknown', 0) + 1
        
        return file_type_counts
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat() 
   
    def _load_cached_analysis_results(self, project_id: int, analysis_run_id: int) -> Optional[Dict[str, Any]]:
        """
        Load cached analysis results from the database.
        
        Args:
            project_id: Database ID of the project
            analysis_run_id: Database ID of the analysis run
            
        Returns:
            Cached analysis results or None if not found
        """
        try:
            # Get analysis run metadata
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT metadata, artifacts_path FROM analysis_runs 
                    WHERE id = ? AND project_id = ? AND status = 'completed'
                """, (analysis_run_id, project_id))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                import json
                metadata = json.loads(row['metadata'] or '{}')
                artifacts_path = row['artifacts_path']
                
                # Check if artifacts file exists
                if artifacts_path and Path(artifacts_path).exists():
                    try:
                        with open(artifacts_path, 'r', encoding='utf-8') as f:
                            cached_results = json.load(f)
                        
                        self.logger.info(f"Successfully loaded cached results from {artifacts_path}")
                        return cached_results
                    except Exception as e:
                        self.logger.warning(f"Failed to load artifacts from {artifacts_path}: {e}")
                
                # Fallback: try to reconstruct results from metadata
                if 'final_results' in metadata:
                    self.logger.info("Using cached results from analysis run metadata")
                    return metadata['final_results']
                
                return None
                
        except Exception as e:
            self.logger.error(f"Error loading cached analysis results: {e}")
            return None
    
    def _save_analysis_results(self, final_results: Dict[str, Any]):
        """
        Save analysis results to the database and artifacts file.
        
        Args:
            final_results: Final analysis results to save
        """
        try:
            project_path = self.current_analysis['project_path']
            
            # Save or update project
            project_structure = self.current_analysis['results'].get('project_ingestion', {}).get('project_structure')
            if project_structure:
                project_id = self.project_persistence.save_project(project_structure)
            else:
                # Fallback: create minimal project record
                project_id = self.db_manager.create_project(
                    name=Path(project_path).name,
                    root_path=project_path,
                    description=self.current_analysis.get('description', '')
                )
            
            # Create artifacts directory
            artifacts_dir = Path("analysis_artifacts")
            artifacts_dir.mkdir(exist_ok=True)
            
            # Save results to artifacts file
            artifacts_filename = f"analysis_{project_id}_{self._get_current_timestamp().replace(':', '-')}.json"
            artifacts_path = artifacts_dir / artifacts_filename
            
            with open(artifacts_path, 'w', encoding='utf-8') as f:
                import json
                
                def json_serializer(obj):
                    """Custom JSON serializer to handle complex objects."""
                    if hasattr(obj, '__dict__'):
                        return obj.__dict__
                    elif hasattr(obj, 'isoformat'):  # datetime objects
                        return obj.isoformat()
                    else:
                        return str(obj)
                
                json.dump(final_results, f, indent=2, default=json_serializer)
            
            # Create analysis run record
            analysis_metadata = {
                'final_results': final_results,
                'analysis_stages': self.current_analysis['results'],
                'project_description': self.current_analysis.get('description', ''),
                'selected_files_count': len(self.current_analysis.get('selected_files', [])) if self.current_analysis.get('selected_files') else 0
            }
            
            analysis_run_id = self.project_persistence.create_analysis_run(
                project_id=project_id,
                artifacts_path=str(artifacts_path),
                metadata=analysis_metadata
            )
            
            # Update analysis run status to completed
            self.db_manager.update_analysis_run_status(analysis_run_id, 'completed')
            
            self.logger.info(f"Analysis results saved to database (run_id: {analysis_run_id}) and artifacts file: {artifacts_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save analysis results: {e}")
            # Don't raise exception - analysis completed successfully even if saving failed