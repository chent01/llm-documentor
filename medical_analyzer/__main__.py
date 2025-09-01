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


def print_error_with_suggestions(error_type: str, message: str, suggestions: list = None):
    """Print error message with helpful suggestions."""
    print(f"Error: {message}")
    
    if suggestions:
        print("\nSuggestions:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
    
    print()  # Add blank line for readability


def validate_file_access(file_path: Path, operation: str = "read") -> tuple[bool, str]:
    """
    Validate file access and return detailed error information.
    
    Args:
        file_path: Path to validate
        operation: Type of operation ('read', 'write')
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file_path.exists():
        return False, f"File does not exist: {file_path}"
    
    if operation == "read" and not os.access(file_path, os.R_OK):
        return False, f"File is not readable: {file_path}"
    
    if operation == "write" and not os.access(file_path, os.W_OK):
        return False, f"File is not writable: {file_path}"
    
    return True, ""


def validate_directory_access(dir_path: Path, operation: str = "read") -> tuple[bool, str]:
    """
    Validate directory access and return detailed error information.
    
    Args:
        dir_path: Directory path to validate
        operation: Type of operation ('read', 'write')
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not dir_path.exists():
        return False, f"Directory does not exist: {dir_path}"
    
    if not dir_path.is_dir():
        return False, f"Path exists but is not a directory: {dir_path}"
    
    if operation == "read" and not os.access(dir_path, os.R_OK):
        return False, f"Directory is not readable: {dir_path}"
    
    if operation == "write" and not os.access(dir_path, os.W_OK):
        return False, f"Directory is not writable: {dir_path}"
    
    return True, ""


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
        '--init-config',
        action='store_true',
        help='Initialize configuration file and exit'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Medical Software Analysis Tool v1.0.0'
    )
    
    return parser.parse_args()


def handle_init_config() -> int:
    """Handle the --init-config flag to create a default configuration file."""
    try:
        # Create config manager and initialize default config
        config_manager = ConfigManager()
        config_manager.load_default_config()
        
        # Get config directory from environment or use default
        config_dir = os.environ.get("MEDICAL_ANALYZER_CONFIG_DIR")
        if config_dir:
            config_path = Path(config_dir) / "config.json"
        else:
            # Use default config location
            config_path = Path.home() / ".medical_analyzer" / "config.json"
        
        # Check if config file already exists
        if config_path.exists():
            print(f"Configuration file already exists at: {config_path}")
            response = input("Do you want to overwrite it? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("Configuration initialization cancelled.")
                return 0
        
        # Create directory if it doesn't exist
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            print(f"Error: Permission denied creating directory '{config_path.parent}'.")
            print("Please check directory permissions or run with appropriate privileges.")
            return 1
        except Exception as e:
            print(f"Error: Failed to create directory '{config_path.parent}': {e}")
            return 1
        
        # Check if directory is writable
        if not os.access(config_path.parent, os.W_OK):
            print(f"Error: Directory '{config_path.parent}' is not writable.")
            print("Please check directory permissions.")
            return 1
        
        # Save the configuration
        try:
            config_manager.save_config(config_path)
            print(f"Configuration file created successfully at: {config_path}")
            print(f"You can now use --config {config_path} to use this configuration.")
            return 0
        except PermissionError:
            print(f"Error: Permission denied writing to '{config_path}'.")
            print("Please check file permissions.")
            return 1
        except Exception as e:
            print(f"Error: Failed to save configuration file: {e}")
            return 1
        
    except ImportError as e:
        print(f"Error: Failed to import required modules: {e}")
        print("Please ensure all dependencies are installed.")
        return 1
    except Exception as e:
        print(f"Error: Failed to create configuration file: {e}")
        return 1


def initialize_application(args: argparse.Namespace) -> tuple[ConfigManager, AppSettings]:
    """Initialize the application with configuration and settings."""
    # Setup logging
    try:
        log_level = getattr(logging, args.log_level.upper())
        if args.verbose:
            log_level = logging.DEBUG
        
        setup_logging(log_level)
        logger = logging.getLogger(__name__)
        
        logger.info("Initializing Medical Software Analysis Tool")
        
    except Exception as e:
        print(f"Error: Failed to setup logging: {e}")
        sys.exit(1)
    
    # Load configuration
    config_manager = ConfigManager()
    
    if args.config:
        config_path = Path(args.config)
        
        # Validate config file access
        is_valid, error_msg = validate_file_access(config_path, "read")
        if not is_valid:
            logger.error(error_msg)
            print_error_with_suggestions(
                "Configuration File Error",
                error_msg,
                [
                    "Check that the file path is correct",
                    "Verify file permissions (should be readable)",
                    "Use --init-config to create a default configuration file",
                    f"Example: python -m medical_analyzer --init-config"
                ]
            )
            sys.exit(1)
        
        # Try to load the configuration
        try:
            config_manager.load_config(config_path)
            logger.info(f"Successfully loaded configuration from: {config_path}")
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            print_error_with_suggestions(
                "Configuration File Not Found",
                f"Configuration file '{config_path}' was not found",
                [
                    "Check that the file path is correct",
                    "Use --init-config to create a default configuration file"
                ]
            )
            sys.exit(1)
        except PermissionError:
            logger.error(f"Permission denied reading configuration file: {config_path}")
            print_error_with_suggestions(
                "Permission Denied",
                f"Cannot read configuration file '{config_path}'",
                [
                    "Check file permissions (file should be readable)",
                    "Run with appropriate privileges if needed",
                    f"Try: chmod +r {config_path}"
                ]
            )
            sys.exit(1)
        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"Invalid configuration file format: {e}")
            print_error_with_suggestions(
                "Invalid Configuration Format",
                f"Configuration file '{config_path}' contains invalid data: {e}",
                [
                    "Check that the file contains valid JSON",
                    "Verify configuration structure matches expected format",
                    "Use --init-config to create a valid configuration file",
                    "Compare with example configuration files"
                ]
            )
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to load configuration file: {e}")
            print_error_with_suggestions(
                "Configuration Load Error",
                f"Failed to load configuration file '{config_path}': {e}",
                [
                    "Check that the file contains valid JSON configuration",
                    "Verify file is not corrupted",
                    "Use --init-config to create a default configuration file",
                    "Check application logs for more details"
                ]
            )
            sys.exit(1)
    else:
        # Load default configuration
        try:
            config_manager.load_default_config()
            logger.info("Using default configuration")
        except Exception as e:
            logger.error(f"Failed to load default configuration: {e}")
            print(f"Error: Failed to load default configuration: {e}")
            print(f"Try using --init-config to create a configuration file.")
            sys.exit(1)
    
    # Validate project path if provided
    if args.project_path:
        project_path = Path(args.project_path)
        is_valid, error_msg = validate_directory_access(project_path, "read")
        if not is_valid:
            logger.error(error_msg)
            print_error_with_suggestions(
                "Project Path Error",
                error_msg,
                [
                    "Check that the directory path is correct",
                    "Verify directory permissions (should be readable)",
                    "Ensure the path points to a directory, not a file",
                    f"Try: ls -la {project_path.parent} (to check if directory exists)"
                ]
            )
            sys.exit(1)
    
    # Validate output directory if provided
    if args.output_dir:
        output_dir = Path(args.output_dir)
        
        # Check if path exists and is not a directory
        if output_dir.exists() and not output_dir.is_dir():
            logger.error(f"Output path exists but is not a directory: {output_dir}")
            print_error_with_suggestions(
                "Output Directory Error",
                f"Output path '{output_dir}' exists but is not a directory",
                [
                    "Choose a different output directory path",
                    "Remove the existing file if it's not needed",
                    "Use a subdirectory path instead"
                ]
            )
            sys.exit(1)
        
        # Try to create output directory if it doesn't exist
        if not output_dir.exists():
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created output directory: {output_dir}")
            except PermissionError:
                logger.error(f"Permission denied creating output directory: {output_dir}")
                print_error_with_suggestions(
                    "Permission Denied",
                    f"Cannot create output directory '{output_dir}'",
                    [
                        "Check parent directory permissions",
                        "Run with appropriate privileges if needed",
                        "Choose a different output directory location",
                        f"Try: mkdir -p {output_dir} (to test directory creation)"
                    ]
                )
                sys.exit(1)
            except Exception as e:
                logger.error(f"Failed to create output directory: {e}")
                print_error_with_suggestions(
                    "Directory Creation Error",
                    f"Failed to create output directory '{output_dir}': {e}",
                    [
                        "Check that parent directories exist and are writable",
                        "Verify disk space is available",
                        "Choose a different output directory location"
                    ]
                )
                sys.exit(1)
        
        # Check if output directory is writable
        is_valid, error_msg = validate_directory_access(output_dir, "write")
        if not is_valid:
            logger.error(error_msg)
            print_error_with_suggestions(
                "Output Directory Access Error",
                error_msg,
                [
                    "Check directory permissions (should be writable)",
                    "Run with appropriate privileges if needed",
                    "Choose a different output directory location",
                    f"Try: chmod +w {output_dir} (to make directory writable)"
                ]
            )
            sys.exit(1)
    
    # Create application settings
    try:
        app_settings = AppSettings(config_manager)
        
        # Override settings with command line arguments
        if args.project_path:
            app_settings.default_project_path = args.project_path
        
        if args.output_dir:
            app_settings.default_output_dir = args.output_dir
        
        logger.info("Application initialization completed")
        
        return config_manager, app_settings
        
    except Exception as e:
        logger.error(f"Failed to create application settings: {e}")
        print(f"Error: Failed to initialize application settings: {e}")
        sys.exit(1)


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
    
    # Create analysis orchestrator
    from medical_analyzer.services.analysis_orchestrator import AnalysisOrchestrator
    analysis_orchestrator = AnalysisOrchestrator(config_manager, app_settings)
    
    # Create and show main window
    main_window = MainWindow(config_manager, app_settings)
    
    # Connect the analysis_requested signal to the orchestrator
    main_window.analysis_requested.connect(
        lambda path, desc, files: analysis_orchestrator.start_analysis(path, desc, files)
    )
    
    # Connect orchestrator signals to main window for progress updates
    analysis_orchestrator.analysis_started.connect(
        lambda path: logger.info(f"Analysis started for: {path}")
    )
    analysis_orchestrator.analysis_completed.connect(main_window.analysis_completed)
    analysis_orchestrator.analysis_failed.connect(main_window.analysis_failed)
    analysis_orchestrator.progress_updated.connect(
        lambda percentage: main_window.update_stage_progress("Analysis", percentage, "in_progress")
    )
    analysis_orchestrator.stage_started.connect(
        lambda stage: main_window.update_stage_progress(stage, 0, "in_progress")
    )
    analysis_orchestrator.stage_completed.connect(
        lambda stage, results: main_window.update_stage_progress(stage, 100, "completed")
    )
    analysis_orchestrator.stage_failed.connect(
        lambda stage, error: main_window.update_stage_progress(stage, 0, "failed", error_message=error)
    )
    
    # Connect cancellation signal
    main_window.analysis_cancelled.connect(analysis_orchestrator.cancel_analysis)
    
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
        print("Error: Project path is required for headless mode.")
        print("Use --project-path to specify the project directory to analyze.")
        print("Example: python -m medical_analyzer --headless --project-path /path/to/project")
        return 1
    
    try:
        # Import analysis services
        from medical_analyzer.services.ingestion import IngestionService
        from medical_analyzer.parsers.parser_service import ParserService
        from medical_analyzer.services.feature_extractor import FeatureExtractor
        from medical_analyzer.services.hazard_identifier import HazardIdentifier
        from medical_analyzer.tests import TestGenerator
        from medical_analyzer.services.export_service import ExportService
        from medical_analyzer.services.soup_service import SOUPService
        from medical_analyzer.database.schema import DatabaseManager
        from medical_analyzer.llm.backend import LLMBackend
        
        # Initialize services
        db_manager = DatabaseManager(db_path=":memory:")
        
        # Initialize LLM backend using the same approach as AnalysisOrchestrator
        llm_config = config_manager.get_llm_config()
        llm_backend = None
        
        if hasattr(llm_config, 'get_enabled_backends'):
            # New LLMBackendConfig format
            enabled_backends = llm_config.get_enabled_backends()
            for backend_config in enabled_backends:
                try:
                    config_dict = backend_config.config.copy()
                    
                    # Map backend_type to the expected backend key
                    if backend_config.backend_type == 'LocalServerBackend':
                        config_dict['backend'] = 'local_server'
                    elif backend_config.backend_type == 'LlamaCppBackend':
                        config_dict['backend'] = 'llama_cpp'
                    else:
                        config_dict['backend'] = 'fallback'
                    
                    config_dict.setdefault('temperature', llm_config.default_temperature)
                    config_dict.setdefault('max_tokens', llm_config.default_max_tokens)
                    
                    backend = LLMBackend.create_from_config(config_dict)
                    if backend.is_available():
                        llm_backend = backend
                        break
                except Exception:
                    continue
        else:
            # Legacy dict format
            llm_backend = LLMBackend.create_from_config(llm_config)
        
        if llm_backend is None:
            # Fallback to mock backend
            llm_backend = LLMBackend.create_from_config({'backend': 'fallback'})
        
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
        try:
            args = parse_arguments()
        except SystemExit as e:
            # argparse calls sys.exit() for --help, --version, or invalid args
            return e.code
        except Exception as e:
            print(f"Error: Failed to parse command line arguments: {e}")
            return 1
        
        # Handle init-config flag
        if args.init_config:
            return handle_init_config()
        
        # Initialize application
        try:
            config_manager, app_settings = initialize_application(args)
        except SystemExit as e:
            # initialize_application calls sys.exit() for various errors
            return e.code
        except Exception as e:
            print(f"Error: Failed to initialize application: {e}")
            return 1
        
        # Run in appropriate mode
        try:
            if args.headless:
                return run_headless_mode(config_manager, app_settings, args)
            else:
                return run_gui_mode(config_manager, app_settings)
        except Exception as e:
            print(f"Error: Application execution failed: {e}")
            # Try to log the error if logging is set up
            try:
                logger = logging.getLogger(__name__)
                logger.error(f"Application execution failed: {e}")
                import traceback
                logger.debug(f"Full traceback: {traceback.format_exc()}")
            except:
                pass  # Logging might not be set up
            return 1
            
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        print("This is likely a bug. Please report this issue with the full error message.")
        # Try to show traceback in debug scenarios
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
