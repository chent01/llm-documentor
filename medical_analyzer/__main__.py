#!/usr/bin/env python3
"""
Medical Software Analysis Tool - Main Entry Point

This module provides the main entry point for the Medical Software Analysis Tool,
handling application initialization, configuration loading, and UI startup.

Usage:
    python -m medical_analyzer [options]
    python -m medical_analyzer --help
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from typing import Optional

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from medical_analyzer.config.config_manager import ConfigManager
from medical_analyzer.config.app_settings import AppSettings
from medical_analyzer.ui.main_window import MainWindow
from medical_analyzer.error_handling.error_handler import ErrorHandler
from medical_analyzer.utils.logging_setup import setup_logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Medical Software Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m medical_analyzer                    # Launch GUI
  python -m medical_analyzer --config config.json  # Use custom config
  python -m medical_analyzer --verbose          # Enable verbose logging
  python -m medical_analyzer --headless         # Run in headless mode
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run in headless mode (no GUI)'
    )
    
    parser.add_argument(
        '--project-path', '-p',
        type=str,
        help='Path to project directory to analyze'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        help='Output directory for analysis results'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Medical Software Analysis Tool v1.0.0'
    )
    
    return parser.parse_args()


def initialize_application(args: argparse.Namespace) -> tuple[ConfigManager, AppSettings]:
    """Initialize the application with configuration and settings."""
    # Setup logging
    log_level = getattr(logging, args.log_level.upper())
    if args.verbose:
        log_level = logging.DEBUG
    
    setup_logging(log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("Initializing Medical Software Analysis Tool")
    
    # Load configuration
    config_manager = ConfigManager()
    
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            sys.exit(1)
        config_manager.load_config(config_path)
    else:
        # Load default configuration
        config_manager.load_default_config()
    
    # Create application settings
    app_settings = AppSettings(config_manager)
    
    # Override settings with command line arguments
    if args.project_path:
        app_settings.default_project_path = args.project_path
    
    if args.output_dir:
        app_settings.default_output_dir = args.output_dir
    
    logger.info("Application initialization completed")
    
    return config_manager, app_settings


def run_gui_mode(config_manager: ConfigManager, app_settings: AppSettings) -> int:
    """Run the application in GUI mode."""
    logger = logging.getLogger(__name__)
    logger.info("Starting GUI mode")
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Medical Software Analysis Tool")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Medical Software Analysis")
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    main_window = MainWindow(config_manager, app_settings)
    main_window.show()
    
    logger.info("GUI started successfully")
    
    # Run the application
    return app.exec()


def run_headless_mode(config_manager: ConfigManager, app_settings: AppSettings, args: argparse.Namespace) -> int:
    """Run the application in headless mode."""
    logger = logging.getLogger(__name__)
    logger.info("Starting headless mode")
    
    if not args.project_path:
        logger.error("Project path is required for headless mode")
        return 1
    
    try:
        # Import analysis services
        from medical_analyzer.services.ingestion import IngestionService
        from medical_analyzer.parsers.parser_service import ParserService
        from medical_analyzer.services.feature_extractor import FeatureExtractor
        from medical_analyzer.services.hazard_identifier import HazardIdentifier
        from medical_analyzer.tests.test_generator import TestGenerator
        from medical_analyzer.services.export_service import ExportService
        from medical_analyzer.services.soup_service import SOUPService
        from medical_analyzer.database.schema import DatabaseManager
        from medical_analyzer.llm.backend import LLMBackend
        
        # Initialize services
        db_manager = DatabaseManager(db_path=":memory:")
        llm_backend = LLMBackend.create_from_config(config_manager.get_llm_config())
        
        ingestion_service = IngestionService()
        parser_service = ParserService()
        feature_extractor = FeatureExtractor(llm_backend)
        hazard_identifier = HazardIdentifier(llm_backend)
        test_generator = TestGenerator()
        soup_service = SOUPService(db_manager)
        export_service = ExportService(soup_service)
        
        # Run analysis pipeline
        logger.info(f"Analyzing project: {args.project_path}")
        
        # Step 1: Project Ingestion
        project_structure = ingestion_service.scan_project(args.project_path)
        logger.info(f"Found {len(project_structure.selected_files)} files to analyze")
        
        # Step 2: Code Parsing
        parsed_files = parser_service.parse_project(project_structure)
        logger.info(f"Parsed {len(parsed_files)} files")
        
        # Step 3: Feature Extraction
        code_chunks = []
        for parsed_file in parsed_files:
            code_chunks.extend(parsed_file.chunks)
        
        feature_result = feature_extractor.extract_features(code_chunks)
        logger.info(f"Extracted {len(feature_result.features)} features")
        
        # Step 4: Test Generation
        test_suite = test_generator.generate_test_suite(project_structure, parsed_files)
        logger.info(f"Generated {len(test_suite.test_skeletons)} test skeletons")
        
        # Step 5: Export Results
        output_dir = args.output_dir or os.path.join(args.project_path, "analysis_results")
        os.makedirs(output_dir, exist_ok=True)
        
        results = {
            'project_structure': project_structure,
            'features': feature_result.features,
            'user_requirements': [],
            'software_requirements': [],
            'hazards': [],
            'traceability': {'code_to_requirements': {}},
            'tests': {
                'total_tests': len(test_suite.test_skeletons),
                'passed_tests': 0,
                'test_suites': [test_suite]
            }
        }
        
        export_path = export_service.create_comprehensive_export(
            results, output_dir, os.path.basename(args.project_path)
        )
        
        logger.info(f"Analysis completed. Results exported to: {export_path}")
        return 0
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return 1


def main() -> int:
    """Main application entry point."""
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Initialize application
        config_manager, app_settings = initialize_application(args)
        
        # Run in appropriate mode
        if args.headless:
            return run_headless_mode(config_manager, app_settings, args)
        else:
            return run_gui_mode(config_manager, app_settings)
            
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        return 1
    except Exception as e:
        print(f"Application error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
