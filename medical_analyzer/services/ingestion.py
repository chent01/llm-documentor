"""
Project ingestion service for scanning and filtering project files.
"""

import os
import mimetypes
from pathlib import Path
from datetime import datetime
from typing import List, Set, Optional, Dict, Any
from ..models import ProjectStructure, FileMetadata
from ..error_handling.error_handler import (
    ErrorCategory, ErrorSeverity, handle_error, 
    get_error_handler, AnalysisError
)


class IngestionService:
    """Service for project scanning and file filtering."""
    
    # Supported file extensions for C and JavaScript/Electron projects
    SUPPORTED_EXTENSIONS = {
        '.c', '.h',           # C files
        '.js', '.jsx',        # JavaScript files
        '.ts', '.tsx',        # TypeScript files (for Electron)
        '.json'               # Configuration files (package.json, etc.)
    }
    
    # File patterns to exclude
    EXCLUDED_PATTERNS = {
        'node_modules', '.git', '__pycache__', '.vscode', '.idea',
        'build', 'dist', 'out', 'target', '.cache', 'coverage',
        '.nyc_output', 'logs', '*.log', '*.tmp', '*.temp'
    }
    
    def __init__(self):
        """Initialize the ingestion service."""
        pass
    
    def scan_project(self, root_path: str, description: str = "") -> ProjectStructure:
        """
        Scan a project directory and create a ProjectStructure.
        
        Args:
            root_path: Root directory path to scan
            description: Optional project description
            
        Returns:
            ProjectStructure with discovered files
            
        Raises:
            ValueError: If root_path doesn't exist or isn't a directory
        """
        root_path = os.path.abspath(root_path)
        
        try:
            if not os.path.exists(root_path):
                error = handle_error(
                    category=ErrorCategory.FILE_SYSTEM,
                    message=f"Path does not exist: {root_path}",
                    severity=ErrorSeverity.HIGH,
                    recoverable=False,
                    stage="project_scanning"
                )
                raise ValueError(f"Path does not exist: {root_path}")
            
            if not os.path.isdir(root_path):
                error = handle_error(
                    category=ErrorCategory.FILE_SYSTEM,
                    message=f"Path is not a directory: {root_path}",
                    severity=ErrorSeverity.HIGH,
                    recoverable=False,
                    stage="project_scanning"
                )
                raise ValueError(f"Path is not a directory: {root_path}")
            
            # Discover all files in the project
            all_files = self._discover_files(root_path)
            
            # Filter to supported file types
            supported_files = self.filter_files(all_files)
            
            # Generate file metadata with error handling
            file_metadata = []
            failed_files = []
            
            for file_path in supported_files:
                try:
                    metadata = self.get_file_metadata(file_path)
                    file_metadata.append(metadata)
                except Exception as e:
                    # Handle file metadata extraction errors
                    error = handle_error(
                        category=ErrorCategory.FILE_SYSTEM,
                        message=f"Could not get metadata for {file_path}",
                        details=str(e),
                        severity=ErrorSeverity.MEDIUM,
                        recoverable=True,
                        stage="metadata_extraction",
                        file_path=file_path,
                        exception=e
                    )
                    failed_files.append(file_path)
                    continue
            
            # Create project structure
            project_metadata = {
                'total_files_discovered': len(all_files),
                'supported_files_count': len(supported_files),
                'successful_metadata_extraction': len(file_metadata),
                'failed_metadata_extraction': len(failed_files),
                'scan_timestamp': datetime.now().isoformat()
            }
            
            return ProjectStructure(
                root_path=root_path,
                selected_files=supported_files,
                description=description,
                metadata=project_metadata,
                timestamp=datetime.now(),
                file_metadata=file_metadata
            )
            
        except Exception as e:
            # Handle any unexpected errors during project scanning
            handle_error(
                category=ErrorCategory.ANALYSIS_PIPELINE,
                message="Project scanning failed",
                details=str(e),
                severity=ErrorSeverity.CRITICAL,
                recoverable=False,
                stage="project_scanning",
                context={"root_path": root_path},
                exception=e
            )
            raise
    
    def _discover_files(self, root_path: str) -> List[str]:
        """
        Recursively discover all files in a directory.
        
        Args:
            root_path: Root directory to scan
            
        Returns:
            List of absolute file paths
        """
        discovered_files = []
        access_errors = []
        
        try:
            for root, dirs, files in os.walk(root_path):
                # Filter out excluded directories
                dirs[:] = [d for d in dirs if not self._should_exclude_directory(d, root)]
                
                for file in files:
                    if not self._should_exclude_file(file):
                        file_path = os.path.join(root, file)
                        try:
                            # Check if file is accessible
                            if os.access(file_path, os.R_OK):
                                discovered_files.append(file_path)
                            else:
                                access_errors.append(file_path)
                        except (OSError, PermissionError) as e:
                            access_errors.append(file_path)
                            handle_error(
                                category=ErrorCategory.FILE_SYSTEM,
                                message=f"File access error: {file_path}",
                                details=str(e),
                                severity=ErrorSeverity.MEDIUM,
                                recoverable=True,
                                stage="file_discovery",
                                file_path=file_path,
                                exception=e
                            )
        
        except PermissionError as e:
            handle_error(
                category=ErrorCategory.FILE_SYSTEM,
                message=f"Permission denied accessing directory: {root_path}",
                details=str(e),
                severity=ErrorSeverity.HIGH,
                recoverable=True,
                stage="file_discovery",
                file_path=root_path,
                exception=e
            )
        except OSError as e:
            handle_error(
                category=ErrorCategory.FILE_SYSTEM,
                message=f"OS error during file discovery: {root_path}",
                details=str(e),
                severity=ErrorSeverity.MEDIUM,
                recoverable=True,
                stage="file_discovery",
                file_path=root_path,
                exception=e
            )
        
        # Log summary of access errors
        if access_errors:
            handle_error(
                category=ErrorCategory.FILE_SYSTEM,
                message=f"Skipped {len(access_errors)} files due to access restrictions",
                details=f"Files: {', '.join(access_errors[:5])}{'...' if len(access_errors) > 5 else ''}",
                severity=ErrorSeverity.LOW,
                recoverable=True,
                stage="file_discovery"
            )
        
        return discovered_files
    
    def _should_exclude_directory(self, dir_name: str, parent_path: str) -> bool:
        """
        Check if a directory should be excluded from scanning.
        
        Args:
            dir_name: Directory name to check
            parent_path: Parent directory path
            
        Returns:
            True if directory should be excluded
        """
        # Check against excluded patterns
        for pattern in self.EXCLUDED_PATTERNS:
            if pattern in dir_name.lower():
                return True
        
        # Exclude hidden directories (starting with .)
        if dir_name.startswith('.') and dir_name not in {'.kiro'}:
            return True
            
        return False
    
    def _should_exclude_file(self, file_name: str) -> bool:
        """
        Check if a file should be excluded from discovery.
        
        Args:
            file_name: File name to check
            
        Returns:
            True if file should be excluded
        """
        # Exclude temporary and log files
        for pattern in self.EXCLUDED_PATTERNS:
            if pattern.startswith('*.') and file_name.endswith(pattern[1:]):
                return True
        
        # Exclude very large files (>10MB) to avoid memory issues
        return False
    
    def filter_files(self, files: List[str]) -> List[str]:
        """
        Filter files to only include supported file types (C and JavaScript).
        
        Args:
            files: List of file paths to filter
            
        Returns:
            List of supported file paths
        """
        supported_files = []
        
        for file_path in files:
            if self._is_supported_file(file_path):
                supported_files.append(file_path)
        
        return supported_files
    
    def _is_supported_file(self, file_path: str) -> bool:
        """
        Check if a file is a supported type for analysis.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file is supported (C or JavaScript)
        """
        file_ext = Path(file_path).suffix.lower()
        
        # Check against supported extensions
        if file_ext in self.SUPPORTED_EXTENSIONS:
            return True
        
        # Special handling for files without extensions
        if not file_ext:
            # Check if it's a C header or source file by content
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    first_lines = f.read(1024)
                    # Look for C-style includes or JavaScript patterns
                    if '#include' in first_lines or 'function' in first_lines:
                        return True
            except Exception:
                pass
        
        return False
    
    def get_file_metadata(self, file_path: str) -> FileMetadata:
        """
        Extract metadata from a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            FileMetadata object with file information
            
        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file can't be read
        """
        if not os.path.exists(file_path):
            handle_error(
                category=ErrorCategory.FILE_SYSTEM,
                message=f"File not found: {file_path}",
                severity=ErrorSeverity.MEDIUM,
                recoverable=True,
                stage="metadata_extraction",
                file_path=file_path
            )
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            stat_info = os.stat(file_path)
            file_size = stat_info.st_size
            last_modified = datetime.fromtimestamp(stat_info.st_mtime)
            
            # Check for very large files
            if file_size > 10 * 1024 * 1024:  # 10MB
                handle_error(
                    category=ErrorCategory.FILE_SYSTEM,
                    message=f"Large file detected: {file_path} ({file_size} bytes)",
                    details="File size may impact analysis performance",
                    severity=ErrorSeverity.LOW,
                    recoverable=True,
                    stage="metadata_extraction",
                    file_path=file_path
                )
            
            # Determine file type
            file_ext = Path(file_path).suffix.lower()
            if file_ext in {'.c', '.h'}:
                file_type = 'c'
            elif file_ext in {'.js', '.jsx', '.ts', '.tsx'}:
                file_type = 'javascript'
            elif file_ext == '.json':
                file_type = 'json'
            else:
                file_type = 'unknown'
            
            # Count lines and estimate function count
            line_count = 0
            function_count = 0
            encoding = 'utf-8'
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line_count += 1
                        # Simple heuristic for function counting
                        line_stripped = line.strip()
                        if file_type == 'c':
                            if (line_stripped.endswith('{') and 
                                ('(' in line_stripped and ')' in line_stripped) and
                                not line_stripped.startswith('if') and
                                not line_stripped.startswith('for') and
                                not line_stripped.startswith('while')):
                                function_count += 1
                        elif file_type == 'javascript':
                            if ('function ' in line_stripped or 
                                '=>' in line_stripped or
                                line_stripped.startswith('const ') and '=>' in line_stripped):
                                function_count += 1
            except UnicodeDecodeError as e:
                # Try with different encoding
                try:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        line_count = sum(1 for _ in f)
                        encoding = 'latin-1'
                    
                    handle_error(
                        category=ErrorCategory.FILE_SYSTEM,
                        message=f"Encoding issue with file: {file_path}",
                        details=f"Used latin-1 encoding as fallback: {str(e)}",
                        severity=ErrorSeverity.LOW,
                        recoverable=True,
                        stage="metadata_extraction",
                        file_path=file_path,
                        exception=e
                    )
                except Exception as fallback_error:
                    line_count = 0
                    encoding = 'unknown'
                    handle_error(
                        category=ErrorCategory.FILE_SYSTEM,
                        message=f"Failed to read file content: {file_path}",
                        details=f"Both UTF-8 and latin-1 encodings failed: {str(fallback_error)}",
                        severity=ErrorSeverity.MEDIUM,
                        recoverable=True,
                        stage="metadata_extraction",
                        file_path=file_path,
                        exception=fallback_error
                    )
            
            return FileMetadata(
                file_path=file_path,
                file_size=file_size,
                last_modified=last_modified,
                file_type=file_type,
                encoding=encoding,
                line_count=line_count,
                function_count=function_count
            )
            
        except PermissionError as e:
            handle_error(
                category=ErrorCategory.FILE_SYSTEM,
                message=f"Permission denied reading file: {file_path}",
                severity=ErrorSeverity.MEDIUM,
                recoverable=True,
                stage="metadata_extraction",
                file_path=file_path,
                exception=e
            )
            raise PermissionError(f"Permission denied reading file: {file_path}")
        except Exception as e:
            handle_error(
                category=ErrorCategory.FILE_SYSTEM,
                message=f"Error reading file metadata for {file_path}",
                details=str(e),
                severity=ErrorSeverity.MEDIUM,
                recoverable=True,
                stage="metadata_extraction",
                file_path=file_path,
                exception=e
            )
            raise RuntimeError(f"Error reading file metadata for {file_path}: {e}")
    
    def get_project_summary(self, project: ProjectStructure) -> Dict[str, Any]:
        """
        Generate a summary of the project structure.
        
        Args:
            project: ProjectStructure to summarize
            
        Returns:
            Dictionary with project summary statistics
        """
        c_files = [f for f in project.file_metadata if f.file_type == 'c']
        js_files = [f for f in project.file_metadata if f.file_type == 'javascript']
        
        total_lines = sum(f.line_count for f in project.file_metadata)
        total_functions = sum(f.function_count for f in project.file_metadata)
        total_size = sum(f.file_size for f in project.file_metadata)
        
        return {
            'total_files': len(project.selected_files),
            'c_files': len(c_files),
            'javascript_files': len(js_files),
            'total_lines_of_code': total_lines,
            'total_functions': total_functions,
            'total_size_bytes': total_size,
            'project_root': project.root_path,
            'scan_timestamp': project.timestamp.isoformat()
        }