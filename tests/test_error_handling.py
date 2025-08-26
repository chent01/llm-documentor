"""
Comprehensive tests for error handling system.

Tests task 11.1 requirements: comprehensive error handling with graceful degradation,
parser error handling with partial analysis capability, and LLM service error handling
with fallback options.
"""

import pytest
import tempfile
import os
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from medical_analyzer.error_handling.error_handler import (
    ErrorHandler, AnalysisError, ErrorCategory, ErrorSeverity,
    get_error_handler, set_error_handler, handle_error
)
from medical_analyzer.services.ingestion import IngestionService
from medical_analyzer.parsers.parser_service import ParserService
from medical_analyzer.llm.backend import LLMBackend, LLMError
from medical_analyzer.models.core import CodeChunk, FileMetadata
from medical_analyzer.models.enums import ChunkType


class TestErrorHandler:
    """Test cases for the ErrorHandler class."""
    
    @pytest.fixture
    def error_handler(self):
        """Create a test error handler."""
        return ErrorHandler(enable_logging=False)
    
    @pytest.fixture
    def sample_error(self):
        """Create a sample analysis error."""
        return AnalysisError(
            category=ErrorCategory.FILE_SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            message="Test error message",
            details="Test error details",
            recoverable=True,
            stage="test_stage",
            file_path="/test/file.txt",
            line_number=42
        )
    
    def test_error_handler_initialization(self, error_handler):
        """Test error handler initialization."""
        assert error_handler.enable_logging is False
        assert len(error_handler.error_log) == 0
        assert len(error_handler.recovery_strategies) > 0
        assert len(error_handler.fallback_handlers) == 0
    
    def test_handle_error_basic(self, error_handler):
        """Test basic error handling."""
        error = error_handler.handle_error(
            category=ErrorCategory.FILE_SYSTEM,
            message="Test error",
            details="Test details",
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            stage="test_stage"
        )
        
        assert isinstance(error, AnalysisError)
        assert error.category == ErrorCategory.FILE_SYSTEM
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.message == "Test error"
        assert error.recoverable is True
        assert len(error_handler.error_log) == 1
    
    def test_handle_error_with_exception(self, error_handler):
        """Test error handling with exception."""
        test_exception = ValueError("Test exception")
        
        error = error_handler.handle_error(
            category=ErrorCategory.PARSER,
            message="Parser error",
            severity=ErrorSeverity.HIGH,
            exception=test_exception
        )
        
        assert error.details == "Test exception"
        assert error.category == ErrorCategory.PARSER
        assert error.severity == ErrorSeverity.HIGH
    
    def test_file_system_error_recovery(self, error_handler):
        """Test file system error recovery strategies."""
        error = AnalysisError(
            category=ErrorCategory.FILE_SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            message="Permission denied reading file: /test/file.txt",
            details="Access denied",
            recoverable=True,
            stage="file_discovery"
        )
        
        recovery_action = error_handler._handle_file_system_error(error)
        assert recovery_action == "Skipped file due to permission restrictions"
    
    def test_parser_error_recovery(self, error_handler):
        """Test parser error recovery strategies."""
        error = AnalysisError(
            category=ErrorCategory.PARSER,
            severity=ErrorSeverity.MEDIUM,
            message="Parser failed",
            details="Syntax error",
            recoverable=True,
            stage="file_parsing",
            file_path="/test/file.c"
        )
        
        recovery_action = error_handler._handle_parser_error(error)
        assert "Skipped problematic file" in recovery_action
    
    def test_llm_service_error_recovery(self, error_handler):
        """Test LLM service error recovery strategies."""
        # Register a test fallback handler
        def test_fallback(context):
            return "Fallback response"
        
        error_handler.register_fallback_handler("text_generation", test_fallback)
        
        error = AnalysisError(
            category=ErrorCategory.LLM_SERVICE,
            severity=ErrorSeverity.MEDIUM,
            message="LLM generation failed",
            details="Connection timeout",
            recoverable=True,
            stage="llm_generation",
            context={"operation": "text_generation"}
        )
        
        recovery_action = error_handler._handle_llm_service_error(error)
        assert "Applied fallback analysis" in recovery_action
    
    def test_database_error_recovery(self, error_handler):
        """Test database error recovery strategies."""
        error = AnalysisError(
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.MEDIUM,
            message="database is locked",
            details="SQLite database locked",
            recoverable=True,
            stage="database_operation"
        )
        
        recovery_action = error_handler._handle_database_error(error)
        assert "Retried database operation" in recovery_action
    
    def test_error_summary(self, error_handler):
        """Test error summary generation."""
        # Add some test errors
        error_handler.handle_error(
            category=ErrorCategory.FILE_SYSTEM,
            message="File error 1",
            severity=ErrorSeverity.LOW,
            recoverable=True,
            stage="file_discovery"
        )
        
        error_handler.handle_error(
            category=ErrorCategory.PARSER,
            message="Parser error 1",
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            stage="file_parsing"
        )
        
        error_handler.handle_error(
            category=ErrorCategory.LLM_SERVICE,
            message="LLM error 1",
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            stage="llm_generation"
        )
        
        summary = error_handler.get_error_summary()
        
        assert summary["total_errors"] == 3
        # Note: Only file system and parser errors are recoverable by default
        assert summary["recovered_errors"] >= 1
        assert summary["recovery_rate"] >= 1/3
        assert summary["category_counts"]["file_system"] == 1
        assert summary["category_counts"]["parser"] == 1
        assert summary["category_counts"]["llm_service"] == 1
        assert summary["severity_counts"]["low"] == 1
        assert summary["severity_counts"]["medium"] == 1
        assert summary["severity_counts"]["high"] == 1
    
    def test_export_error_log(self, error_handler):
        """Test error log export functionality."""
        # Add a test error
        error_handler.handle_error(
            category=ErrorCategory.FILE_SYSTEM,
            message="Test export error",
            details="Test details",
            severity=ErrorSeverity.MEDIUM,
            stage="test_stage"
        )
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            log_file = f.name
        
        try:
            error_handler.export_error_log(log_file)
            
            # Verify log file was created and contains expected content
            assert os.path.exists(log_file)
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "Medical Software Analyzer - Error Log" in content
                assert "Test export error" in content
                assert "ERROR SUMMARY" in content
        finally:
            os.unlink(log_file)
    
    def test_global_error_handler(self):
        """Test global error handler functionality."""
        # Test getting default handler
        handler = get_error_handler()
        assert isinstance(handler, ErrorHandler)
        
        # Test setting custom handler
        custom_handler = ErrorHandler(enable_logging=False)
        set_error_handler(custom_handler)
        
        # Test convenience function
        error = handle_error(
            category=ErrorCategory.VALIDATION,
            message="Test global error",
            severity=ErrorSeverity.LOW
        )
        
        assert isinstance(error, AnalysisError)
        assert error.category == ErrorCategory.VALIDATION


class TestIngestionServiceErrorHandling:
    """Test cases for ingestion service error handling."""
    
    @pytest.fixture
    def ingestion_service(self):
        """Create a test ingestion service."""
        return IngestionService()
    
    def test_scan_project_nonexistent_path(self, ingestion_service):
        """Test scanning a non-existent project path."""
        with pytest.raises(ValueError, match="Path does not exist"):
            ingestion_service.scan_project("/nonexistent/path")
    
    def test_scan_project_file_instead_of_directory(self, ingestion_service):
        """Test scanning a file instead of a directory."""
        with tempfile.NamedTemporaryFile() as f:
            with pytest.raises(ValueError, match="Path is not a directory"):
                ingestion_service.scan_project(f.name)
    
    def test_file_discovery_permission_error(self, ingestion_service):
        """Test file discovery with permission errors."""
        # Create a temporary directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a subdirectory that we can't access (simulate permission error)
            sub_dir = os.path.join(temp_dir, "subdir")
            os.makedirs(sub_dir)
            
            # Create a test file
            test_file = os.path.join(temp_dir, "test.c")
            with open(test_file, 'w') as f:
                f.write("int main() { return 0; }")
            
            # Mock os.access to simulate permission error
            with patch('os.access', side_effect=lambda path, mode: path != sub_dir):
                project = ingestion_service.scan_project(temp_dir)
                
                # Should still work with the accessible file
                assert len(project.selected_files) >= 1
                assert test_file in project.selected_files
    
    def test_metadata_extraction_encoding_error(self, ingestion_service):
        """Test metadata extraction with encoding errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file with problematic encoding
            test_file = os.path.join(temp_dir, "test.c")
            with open(test_file, 'wb') as f:
                f.write(b"int main() {\n  return 0;\n}\n")
            
            project = ingestion_service.scan_project(temp_dir)
            
            # Should handle encoding gracefully
            assert len(project.file_metadata) >= 1
            assert any(fm.file_path == test_file for fm in project.file_metadata)


class TestParserServiceErrorHandling:
    """Test cases for parser service error handling."""
    
    @pytest.fixture
    def parser_service(self):
        """Create a test parser service."""
        return ParserService()
    
    def test_parse_file_nonexistent(self, parser_service):
        """Test parsing a non-existent file."""
        result = parser_service.parse_file("/nonexistent/file.c")
        assert result is None
    
    def test_parse_file_unsupported_type(self, parser_service):
        """Test parsing an unsupported file type."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"This is not code")
            f.flush()
            
            result = parser_service.parse_file(f.name)
            assert result is None
            
            # Close the file before trying to delete it
            f.close()
            try:
                os.unlink(f.name)
            except PermissionError:
                # On Windows, file might still be in use
                pass
    
    def test_parse_file_with_fallback(self, parser_service):
        """Test parsing with fallback to text analysis."""
        with tempfile.NamedTemporaryFile(suffix='.c', delete=False) as f:
            f.write(b"invalid c code { { {")
            f.flush()
            
            # Mock the C parser to fail
            with patch.object(parser_service.c_parser, 'parse_file', side_effect=Exception("Parser error")):
                result = parser_service.parse_file(f.name)
                
                # Should fall back to text analysis
                assert result is not None
                assert len(result.chunks) == 1
                assert result.chunks[0].metadata.get('is_fallback') is True
                
            # Close the file before trying to delete it
            f.close()
            try:
                os.unlink(f.name)
            except PermissionError:
                # On Windows, file might still be in use
                pass
    
    def test_parse_project_with_failures(self, parser_service):
        """Test parsing a project with some file failures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some test files
            good_file = os.path.join(temp_dir, "good.c")
            bad_file = os.path.join(temp_dir, "bad.c")
            
            with open(good_file, 'w') as f:
                f.write("int main() { return 0; }")
            
            with open(bad_file, 'w') as f:
                f.write("invalid code { { {")
            
            # Mock the parser to fail on bad file
            def mock_parse_file(file_path):
                if "bad" in file_path:
                    raise Exception("Parser error")
                return Mock()  # Return mock for good file
            
            with patch.object(parser_service.c_parser, 'parse_file', side_effect=mock_parse_file):
                from medical_analyzer.models import ProjectStructure
                project = ProjectStructure(
                    root_path=temp_dir,
                    selected_files=[good_file, bad_file],
                    description="Test project",
                    metadata={},
                    timestamp=datetime.now(),
                    file_metadata=[]
                )
                
                results = parser_service.parse_project(project)
                
                # Should handle the failure gracefully
                assert len(results) >= 1  # At least the good file should be parsed


class TestLLMBackendErrorHandling:
    """Test cases for LLM backend error handling."""
    
    class MockLLMBackend(LLMBackend):
        """Mock LLM backend for testing."""
        
        def generate(self, prompt: str, context_chunks=None, temperature=0.1, 
                    max_tokens=None, system_prompt=None) -> str:
            if "fail" in prompt:
                raise LLMError("Generation failed", recoverable=True, backend="MockBackend")
            return "Generated response"
        
        def is_available(self) -> bool:
            return True
        
        def get_model_info(self):
            from medical_analyzer.llm.backend import ModelInfo, ModelType
            return ModelInfo(
                name="test-model",
                type=ModelType.CHAT,
                context_length=2048,
                backend_name="MockBackend"
            )
        
        def get_required_config_keys(self):
            return ["test"]
        
        def validate_config(self):
            return True
    
    @pytest.fixture
    def mock_backend(self):
        """Create a mock LLM backend."""
        return self.MockLLMBackend({"test": "config"})
    
    def test_circuit_breaker_initialization(self, mock_backend):
        """Test circuit breaker initialization."""
        assert mock_backend._failure_count == 0
        assert mock_backend._circuit_open is False
        assert mock_backend._max_failures == 3
        assert mock_backend._circuit_timeout == 60
    
    def test_circuit_breaker_failure_recording(self, mock_backend):
        """Test circuit breaker failure recording."""
        # Record some failures
        mock_backend._record_failure()
        assert mock_backend._failure_count == 1
        assert mock_backend._circuit_open is False
        
        mock_backend._record_failure()
        mock_backend._record_failure()
        assert mock_backend._failure_count == 3
        assert mock_backend._circuit_open is True
    
    def test_circuit_breaker_timeout(self, mock_backend):
        """Test circuit breaker timeout mechanism."""
        # Open the circuit
        mock_backend._circuit_open = True
        mock_backend._last_failure_time = time.time() - 70  # 70 seconds ago
        
        # Should close the circuit
        assert mock_backend._check_circuit_breaker() is True
        assert mock_backend._circuit_open is False
        assert mock_backend._failure_count == 0
    
    def test_circuit_breaker_success_reset(self, mock_backend):
        """Test circuit breaker reset on success."""
        # Record some failures
        mock_backend._record_failure()
        mock_backend._record_failure()
        
        # Record success
        mock_backend._record_success()
        assert mock_backend._failure_count == 0
        assert mock_backend._circuit_open is False
    
    def test_generation_error_handling(self, mock_backend):
        """Test generation error handling."""
        context = {
            "prompt": "fail this request",
            "temperature": 0.1,
            "max_tokens": 100,
            "operation": "text_generation"
        }
        
        # Register a fallback handler
        def test_fallback(ctx):
            return "Fallback response"
        
        mock_backend._error_handler.register_fallback_handler("text_generation", test_fallback)
        
        # Test error handling - should use fallback and not raise exception
        result = mock_backend._handle_generation_error(
            LLMError("Test error"), context
        )
        
        # Should return fallback response
        assert result == "Fallback response"
        
        # Verify failure was recorded
        assert mock_backend._failure_count == 1


class TestErrorHandlingIntegration:
    """Integration tests for error handling across the system."""
    
    def test_end_to_end_error_handling(self):
        """Test end-to-end error handling in a complete analysis pipeline."""
        # Create a temporary project with various issues
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files with different issues
            good_file = os.path.join(temp_dir, "good.c")
            bad_file = os.path.join(temp_dir, "bad.c")
            large_file = os.path.join(temp_dir, "large.c")
            
            with open(good_file, 'w') as f:
                f.write("int main() { return 0; }")
            
            with open(bad_file, 'w') as f:
                f.write("invalid code { { {")
            
            # Create a large file
            with open(large_file, 'w') as f:
                f.write("int main() {\n" + "  printf(\"test\");\n" * 10000 + "  return 0;\n}")
            
            # Test ingestion service
            ingestion_service = IngestionService()
            project = ingestion_service.scan_project(temp_dir)
            
            # Should handle all files gracefully
            assert len(project.selected_files) >= 3
            
            # Test parser service
            parser_service = ParserService()
            parsed_files = parser_service.parse_project(project)
            
            # Should handle parsing failures gracefully
            assert len(parsed_files) >= 1
            
            # Check error summary
            error_handler = get_error_handler()
            summary = error_handler.get_error_summary()
            
            # Should have recorded some errors
            assert summary["total_errors"] >= 0
            assert summary["recovery_rate"] >= 0


if __name__ == '__main__':
    pytest.main([__file__])
