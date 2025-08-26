#!/usr/bin/env python3
"""
Demo script for comprehensive error handling system.
Demonstrates task 11.1 implementation: comprehensive error handling with graceful degradation,
parser error handling with partial analysis capability, and LLM service error handling with fallback options.
"""

import os
import tempfile
import time
from pathlib import Path

from medical_analyzer.services.error_handler import (
    ErrorHandler, ErrorCategory, ErrorSeverity, handle_error, get_error_handler
)
from medical_analyzer.services.ingestion import IngestionService
from medical_analyzer.parsers.parser_service import ParserService
from medical_analyzer.llm.backend import LLMError
from medical_analyzer.models import ProjectStructure


def create_test_project_with_issues():
    """Create a test project with various issues to demonstrate error handling."""
    temp_dir = tempfile.mkdtemp()
    
    print(f"Creating test project in: {temp_dir}")
    
    # Create files with different issues
    files = {
        "good.c": "int main() { return 0; }",
        "bad.c": "invalid c code { { {",
        "large.c": "int main() {\n" + "  printf(\"test\");\n" * 1000 + "  return 0;\n}",
        "permission_test.c": "int test() { return 1; }",
        "encoding_test.c": "int main() { /* Test with special chars: éñç */ return 0; }",
        "unsupported.txt": "This is not a supported file type",
        "good.js": "function test() { console.log('Hello'); }",
        "bad.js": "function test( { console.log('Invalid syntax'",
    }
    
    for filename, content in files.items():
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return temp_dir


def demonstrate_error_handler():
    """Demonstrate the error handler functionality."""
    print("\n" + "="*60)
    print("ERROR HANDLER DEMONSTRATION")
    print("="*60)
    
    # Create error handler
    error_handler = ErrorHandler(enable_logging=False)
    
    # Demonstrate different error categories
    error_categories = [
        (ErrorCategory.FILE_SYSTEM, "Permission denied reading file", "Access denied"),
        (ErrorCategory.PARSER, "Syntax error in C file", "Invalid token"),
        (ErrorCategory.LLM_SERVICE, "LLM generation timeout", "Connection failed"),
        (ErrorCategory.DATABASE, "Database locked", "SQLite database is locked"),
        (ErrorCategory.VALIDATION, "Invalid input data", "Missing required field"),
    ]
    
    for category, message, details in error_categories:
        error = error_handler.handle_error(
            category=category,
            message=message,
            details=details,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            stage="demo_stage"
        )
        print(f"Handled {category.value} error: {error.message}")
        if error.recovery_action:
            print(f"  Recovery: {error.recovery_action}")
    
    # Demonstrate error summary
    summary = error_handler.get_error_summary()
    print(f"\nError Summary:")
    print(f"  Total errors: {summary['total_errors']}")
    print(f"  Recovered errors: {summary['recovered_errors']}")
    print(f"  Recovery rate: {summary['recovery_rate']:.1%}")
    
    return error_handler


def demonstrate_ingestion_error_handling():
    """Demonstrate ingestion service error handling."""
    print("\n" + "="*60)
    print("INGESTION SERVICE ERROR HANDLING")
    print("="*60)
    
    # Create test project
    project_dir = create_test_project_with_issues()
    
    try:
        ingestion_service = IngestionService()
        
        print("Scanning project with various file issues...")
        project = ingestion_service.scan_project(project_dir, "Test project with issues")
        
        print(f"Project scan results:")
        print(f"  Total files discovered: {project.metadata.get('total_files_discovered', 0)}")
        print(f"  Supported files: {project.metadata.get('supported_files_count', 0)}")
        print(f"  Successful metadata extraction: {project.metadata.get('successful_metadata_extraction', 0)}")
        print(f"  Failed metadata extraction: {project.metadata.get('failed_metadata_extraction', 0)}")
        
        print(f"\nSelected files:")
        for file_path in project.selected_files:
            print(f"  - {os.path.basename(file_path)}")
        
        return project
        
    finally:
        # Clean up
        import shutil
        shutil.rmtree(project_dir)


def demonstrate_parser_error_handling():
    """Demonstrate parser service error handling."""
    print("\n" + "="*60)
    print("PARSER SERVICE ERROR HANDLING")
    print("="*60)
    
    # Create test project
    project_dir = create_test_project_with_issues()
    
    try:
        ingestion_service = IngestionService()
        parser_service = ParserService()
        
        # Scan project
        project = ingestion_service.scan_project(project_dir, "Test project for parsing")
        
        print("Parsing files with various issues...")
        parsed_files = parser_service.parse_project(project)
        
        print(f"Parsing results:")
        print(f"  Total files to parse: {len(project.selected_files)}")
        print(f"  Successfully parsed: {len(parsed_files)}")
        print(f"  Failed to parse: {len(project.selected_files) - len(parsed_files)}")
        
        # Show details of parsed files
        for parsed_file in parsed_files:
            print(f"\nParsed: {os.path.basename(parsed_file.file_path)}")
            print(f"  Chunks: {len(parsed_file.chunks)}")
            print(f"  Functions: {parsed_file.file_metadata.function_count}")
            
            # Check for fallback analysis
            for chunk in parsed_file.chunks:
                if chunk.metadata.get('is_fallback'):
                    print(f"  Note: Used fallback text analysis")
                    break
        
        return parsed_files
        
    finally:
        # Clean up
        import shutil
        shutil.rmtree(project_dir)


def demonstrate_llm_error_handling():
    """Demonstrate LLM service error handling."""
    print("\n" + "="*60)
    print("LLM SERVICE ERROR HANDLING")
    print("="*60)
    
    # Create a mock LLM backend with error simulation
    class MockLLMBackend:
        def __init__(self):
            self.failure_count = 0
            self.circuit_open = False
            self.last_failure_time = None
        
        def generate(self, prompt, **kwargs):
            # Simulate different failure scenarios
            if "timeout" in prompt.lower():
                self.failure_count += 1
                raise LLMError("Generation timeout", recoverable=True, backend="MockBackend")
            elif "critical" in prompt.lower():
                raise LLMError("Critical error", recoverable=False, backend="MockBackend")
            elif "circuit" in prompt.lower() and self.failure_count >= 3:
                raise LLMError("Circuit breaker open", recoverable=True, backend="MockBackend")
            else:
                return "Generated response successfully"
    
    # Register fallback handlers
    error_handler = get_error_handler()
    
    def text_generation_fallback(context):
        return "Fallback response: Template-based generation"
    
    def feature_extraction_fallback(context):
        return "Fallback response: Rule-based feature extraction"
    
    error_handler.register_fallback_handler("text_generation", text_generation_fallback)
    error_handler.register_fallback_handler("feature_extraction", feature_extraction_fallback)
    
    # Test different scenarios
    mock_llm = MockLLMBackend()
    
    test_scenarios = [
        ("Normal generation", "Generate some text"),
        ("Timeout error", "Generate text with timeout"),
        ("Critical error", "Generate text with critical error"),
        ("Circuit breaker", "Generate text with circuit breaker"),
    ]
    
    for scenario, prompt in test_scenarios:
        print(f"\nTesting: {scenario}")
        try:
            result = mock_llm.generate(prompt)
            print(f"  Result: {result}")
        except LLMError as e:
            print(f"  Error: {e.message}")
            print(f"  Recoverable: {e.recoverable}")
            
            # Handle the error
            error = error_handler.handle_error(
                category=ErrorCategory.LLM_SERVICE,
                message=f"LLM generation failed: {scenario}",
                details=str(e),
                severity=ErrorSeverity.MEDIUM if e.recoverable else ErrorSeverity.HIGH,
                recoverable=e.recoverable,
                stage="llm_generation",
                context={"operation": "text_generation", "prompt": prompt}
            )
            
            if error.recovery_action:
                print(f"  Recovery: {error.recovery_action}")


def demonstrate_error_recovery_strategies():
    """Demonstrate various error recovery strategies."""
    print("\n" + "="*60)
    print("ERROR RECOVERY STRATEGIES")
    print("="*60)
    
    error_handler = get_error_handler()
    
    # Test file system error recovery
    print("File System Error Recovery:")
    fs_error = error_handler.handle_error(
        category=ErrorCategory.FILE_SYSTEM,
        message="Permission denied reading file: /test/file.txt",
        severity=ErrorSeverity.MEDIUM,
        recoverable=True,
        stage="file_discovery"
    )
    print(f"  Error: {fs_error.message}")
    print(f"  Recovery: {fs_error.recovery_action}")
    
    # Test parser error recovery
    print("\nParser Error Recovery:")
    parser_error = error_handler.handle_error(
        category=ErrorCategory.PARSER,
        message="Parser failed for file: /test/file.c",
        details="Syntax error at line 10",
        severity=ErrorSeverity.MEDIUM,
        recoverable=True,
        stage="file_parsing",
        file_path="/test/file.c"
    )
    print(f"  Error: {parser_error.message}")
    print(f"  Recovery: {parser_error.recovery_action}")
    
    # Test database error recovery
    print("\nDatabase Error Recovery:")
    db_error = error_handler.handle_error(
        category=ErrorCategory.DATABASE,
        message="database is locked",
        details="SQLite database locked by another process",
        severity=ErrorSeverity.MEDIUM,
        recoverable=True,
        stage="database_operation"
    )
    print(f"  Error: {db_error.message}")
    print(f"  Recovery: {db_error.recovery_action}")


def demonstrate_error_logging_and_export():
    """Demonstrate error logging and export functionality."""
    print("\n" + "="*60)
    print("ERROR LOGGING AND EXPORT")
    print("="*60)
    
    # Create error handler with file logging
    log_file = "demo_error_log.txt"
    error_handler = ErrorHandler(enable_logging=True, log_file=log_file)
    
    # Generate some errors
    for i in range(5):
        error_handler.handle_error(
            category=ErrorCategory.FILE_SYSTEM,
            message=f"Demo error {i+1}",
            details=f"Demo error details {i+1}",
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            stage="demo_stage"
        )
    
    # Export error log
    export_file = "demo_error_export.txt"
    error_handler.export_error_log(export_file)
    
    print(f"Error log written to: {log_file}")
    print(f"Error export written to: {export_file}")
    
    # Show summary
    summary = error_handler.get_error_summary()
    print(f"\nError Summary:")
    print(f"  Total errors: {summary['total_errors']}")
    print(f"  Recovered errors: {summary['recovered_errors']}")
    print(f"  Recovery rate: {summary['recovery_rate']:.1%}")
    
    # Clean up
    try:
        # Close the error handler to release file handles
        error_handler.logger.handlers.clear()
        os.remove(log_file)
        os.remove(export_file)
    except (FileNotFoundError, PermissionError):
        # On Windows, file might still be in use
        pass


def main():
    """Main demonstration function."""
    print("Comprehensive Error Handling System Demo")
    print("="*60)
    print("This demo showcases the error handling system implemented for Task 11.1")
    print("Features demonstrated:")
    print("- Centralized error handling with categorization")
    print("- Graceful degradation for file system operations")
    print("- Partial analysis capability for parser errors")
    print("- LLM service error handling with fallback options")
    print("- Circuit breaker pattern for LLM services")
    print("- Error recovery strategies and logging")
    print("- Error summary and export functionality")
    
    try:
        # Run demonstrations
        error_handler = demonstrate_error_handler()
        project = demonstrate_ingestion_error_handling()
        parsed_files = demonstrate_parser_error_handling()
        demonstrate_llm_error_handling()
        demonstrate_error_recovery_strategies()
        demonstrate_error_logging_and_export()
        
        print("\n" + "="*60)
        print("DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("="*60)
        print("The error handling system provides:")
        print("✓ Graceful degradation for various failure scenarios")
        print("✓ Partial analysis capability when some components fail")
        print("✓ Fallback mechanisms for LLM service failures")
        print("✓ Comprehensive error logging and reporting")
        print("✓ Recovery strategies for different error types")
        print("✓ Circuit breaker pattern for preventing cascading failures")
        
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
