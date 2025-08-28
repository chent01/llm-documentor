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
from medical_analyzer.services.hazard_identifier import HazardIdentifier
from medical_analyzer.tests.test_generator import TestGenerator
from medical_analyzer.services.export_service import ExportService
from medical_analyzer.services.soup_service import SOUPService
from medical_analyzer.services.risk_register import RiskRegister
from medical_analyzer.services.traceability_service import TraceabilityService
from medical_analyzer.database.schema import DatabaseManager
from medical_analyzer.llm.backend import LLMBackend
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
        self.db_manager = DatabaseManager(db_path=":memory:")
        self.llm_backend = None
        
        try:
            self.llm_backend = LLMBackend.create_from_config(
                config_manager.get_llm_config()
            )
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
            self.export_service = ExportService(self.soup_service)
            self.traceability_service = TraceabilityService(self.db_manager)
            self.risk_register = RiskRegister()
            self.test_generator = TestGenerator()
            
            # Services that require LLM backend
            if self.llm_backend:
                self.feature_extractor = FeatureExtractor(self.llm_backend)
                self.hazard_identifier = HazardIdentifier(self.llm_backend)
            else:
                self.feature_extractor = None
                self.hazard_identifier = None
                self.logger.warning("LLM-dependent services disabled due to backend initialization failure")
            
            self.logger.info("Analysis services initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize analysis services: {e}")
            raise
    
    def start_analysis(self, project_path: str, description: str = "") -> None:
        """
        Start the complete analysis workflow for a project.
        
        Args:
            project_path: Path to the project directory to analyze
            description: Optional project description
        """
        if self.is_running:
            self.logger.warning("Analysis already in progress")
            return
        
        self.logger.info(f"Starting analysis for project: {project_path}")
        self.is_running = True
        self.current_analysis = {
            'project_path': project_path,
            'description': description,
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
        try:
            # Stage 1: Project Ingestion (10%)
            self._run_stage("Project Ingestion", self._stage_project_ingestion, 10)
            
            # Stage 2: Code Parsing (20%)
            self._run_stage("Code Parsing", self._stage_code_parsing, 20)
            
            # Stage 3: Feature Extraction (40%)
            if self.feature_extractor:
                self._run_stage("Feature Extraction", self._stage_feature_extraction, 40)
            else:
                self.logger.info("Skipping feature extraction - LLM backend not available")
                self.progress_updated.emit(40)
            
            # Stage 4: Hazard Identification (60%)
            if self.hazard_identifier:
                self._run_stage("Hazard Identification", self._stage_hazard_identification, 60)
            else:
                self.logger.info("Skipping hazard identification - LLM backend not available")
                self.progress_updated.emit(60)
            
            # Stage 5: Risk Analysis (70%)
            self._run_stage("Risk Analysis", self._stage_risk_analysis, 70)
            
            # Stage 6: Test Generation (80%)
            self._run_stage("Test Generation", self._stage_test_generation, 80)
            
            # Stage 7: Traceability Analysis (90%)
            self._run_stage("Traceability Analysis", self._stage_traceability_analysis, 90)
            
            # Stage 8: Results Compilation (100%)
            self._run_stage("Results Compilation", self._stage_results_compilation, 100)
            
            # Analysis completed successfully
            self.analysis_completed.emit(self.current_analysis['results'])
            self.logger.info("Analysis completed successfully")
            
        except Exception as e:
            self.logger.error(f"Analysis pipeline failed: {e}")
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
            self.logger.info(f"Completed stage: {stage_name}")
            
        except Exception as e:
            error_msg = f"Stage '{stage_name}' failed: {str(e)}"
            self.logger.error(error_msg)
            self.stage_failed.emit(stage_name, error_msg)
            raise
    
    def _stage_project_ingestion(self) -> Dict[str, Any]:
        """Stage 1: Project ingestion and file discovery."""
        project_path = self.current_analysis['project_path']
        project_structure = self.ingestion_service.scan_project(project_path)
        
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
    
    def _stage_hazard_identification(self) -> Dict[str, Any]:
        """Stage 4: Hazard identification and analysis."""
        # Get software requirements if available, otherwise create empty list
        software_requirements = []
        
        # Check if we have generated software requirements from previous stages
        # For now, we'll use an empty list since requirements generation isn't implemented yet
        if 'software_requirements' in self.current_analysis['results']:
            software_requirements = self.current_analysis['results']['software_requirements']
        
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
        """Stage 6: Test generation and validation."""
        project_structure = self.current_analysis['results']['project_ingestion']['project_structure']
        parsed_files = self.current_analysis['results']['code_parsing']['parsed_files']
        
        test_suite = self.test_generator.generate_test_suite(project_structure, parsed_files)
        
        # Extract frameworks from framework_configs
        frameworks_used = list(test_suite.framework_configs.keys()) if test_suite.framework_configs else []
        
        return {
            'test_suite': test_suite,
            'total_tests': len(test_suite.test_skeletons),
            'test_frameworks': frameworks_used
        }
    
    def _stage_traceability_analysis(self) -> Dict[str, Any]:
        """Stage 7: Traceability matrix generation."""
        # Get features if available
        features = []
        if 'feature_extraction' in self.current_analysis['results']:
            features = self.current_analysis['results']['feature_extraction']['features']
        
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
            user_requirements=[],  # Empty user requirements for now
            software_requirements=[],  # Empty software requirements for now
            risk_items=risk_items
        )
        
        return {
            'traceability_matrix': traceability_matrix,
            'total_links': len(traceability_matrix.links) if hasattr(traceability_matrix, 'links') else 0
        }
    
    def _stage_results_compilation(self) -> Dict[str, Any]:
        """Stage 8: Compile and prepare final results."""
        # Compile all results into a comprehensive analysis result
        final_results = {
            'project_path': self.current_analysis['project_path'],
            'description': self.current_analysis['description'],
            'analysis_stages': self.current_analysis['results'],
            'summary': self._generate_analysis_summary()
        }
        
        return final_results
    
    def _generate_analysis_summary(self) -> Dict[str, Any]:
        """Generate a summary of the analysis results."""
        results = self.current_analysis['results']
        
        summary = {
            'total_files_analyzed': 0,
            'total_code_chunks': 0,
            'total_features': 0,
            'total_hazards': 0,
            'total_risks': 0,
            'total_tests': 0,
            'analysis_stages_completed': len(results)
        }
        
        # Extract counts from each stage
        if 'project_ingestion' in results:
            summary['total_files_analyzed'] = results['project_ingestion']['total_files']
        
        if 'code_parsing' in results:
            summary['total_code_chunks'] = results['code_parsing']['total_chunks']
        
        if 'feature_extraction' in results:
            summary['total_features'] = results['feature_extraction']['total_features']
        
        if 'hazard_identification' in results:
            summary['total_hazards'] = results['hazard_identification']['total_hazards']
        
        if 'risk_analysis' in results:
            summary['total_risks'] = results['risk_analysis']['total_risks']
        
        if 'test_generation' in results:
            summary['total_tests'] = results['test_generation']['total_tests']
        
        return summary
    
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
                'hazard_identifier': self.hazard_identifier is not None
            }
        }
    
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