"""
Parser service orchestrator for code chunking and metadata extraction.
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from .c_parser import CParser, CCodeStructure
from .js_parser import JSParser, JSCodeStructure
from ..models.core import CodeChunk, FileMetadata, CodeReference, ProjectStructure
from ..models.enums import ChunkType
from ..error_handling.error_handler import (
    ErrorCategory, ErrorSeverity, handle_error, 
    get_error_handler, AnalysisError
)


@dataclass
class ParsedFile:
    """Container for parsed file information."""
    file_path: str
    file_metadata: FileMetadata
    code_structure: Any  # CCodeStructure or JSCodeStructure
    chunks: List[CodeChunk]


class ParserService:
    """Orchestrator service for parsing code files and extracting chunks."""
    
    def __init__(self, max_chunk_size: int = 1000):
        """Initialize the parser service.
        
        Args:
            max_chunk_size: Maximum size in characters for code chunks
        """
        self.max_chunk_size = max_chunk_size
        self.c_parser = CParser()
        self.js_parser = JSParser()
        self.supported_extensions = {'.c', '.h', '.js', '.ts', '.jsx', '.tsx'}
    
    def parse_project(self, project_structure: ProjectStructure) -> List[ParsedFile]:
        """Parse all selected files in a project.
        
        Args:
            project_structure: Project structure with selected files
            
        Returns:
            List of parsed file containers
        """
        parsed_files = []
        failed_files = []
        
        for file_path in project_structure.selected_files:
            try:
                parsed_file = self.parse_file(file_path)
                if parsed_file:
                    parsed_files.append(parsed_file)
                else:
                    failed_files.append(file_path)
            except Exception as e:
                # Handle parsing errors with graceful degradation
                error = handle_error(
                    category=ErrorCategory.PARSER,
                    message=f"Failed to parse file: {file_path}",
                    details=str(e),
                    severity=ErrorSeverity.MEDIUM,
                    recoverable=True,
                    stage="file_parsing",
                    file_path=file_path,
                    exception=e
                )
                failed_files.append(file_path)
                continue
        
        # Log summary of parsing results
        if failed_files:
            handle_error(
                category=ErrorCategory.PARSER,
                message=f"Parsing completed with {len(failed_files)} failed files",
                details=f"Failed files: {', '.join(failed_files[:5])}{'...' if len(failed_files) > 5 else ''}",
                severity=ErrorSeverity.LOW,
                recoverable=True,
                stage="file_parsing"
            )
        
        return parsed_files
    
    def parse_file(self, file_path: str) -> Optional[ParsedFile]:
        """Parse a single file and extract code chunks.
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            ParsedFile container or None if parsing failed
        """
        try:
            if not os.path.exists(file_path):
                handle_error(
                    category=ErrorCategory.FILE_SYSTEM,
                    message=f"File not found during parsing: {file_path}",
                    severity=ErrorSeverity.MEDIUM,
                    recoverable=True,
                    stage="file_parsing",
                    file_path=file_path
                )
                return None
            
            # Get file metadata
            file_metadata = self._extract_file_metadata(file_path)
            
            # Determine file type and parse accordingly
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext in {'.c', '.h'}:
                try:
                    code_structure = self.c_parser.parse_file(file_path)
                    chunks = self._extract_c_chunks(code_structure)
                except Exception as e:
                    handle_error(
                        category=ErrorCategory.PARSER,
                        message=f"C parser failed for file: {file_path}",
                        details=str(e),
                        severity=ErrorSeverity.MEDIUM,
                        recoverable=True,
                        stage="c_parsing",
                        file_path=file_path,
                        exception=e
                    )
                    # Fall back to basic text analysis
                    chunks = self._fallback_text_analysis(file_path, file_metadata)
                    code_structure = None
                    
            elif file_ext in {'.js', '.ts', '.jsx', '.tsx'}:
                try:
                    code_structure = self.js_parser.parse_file(file_path)
                    chunks = self._extract_js_chunks(code_structure)
                except Exception as e:
                    handle_error(
                        category=ErrorCategory.PARSER,
                        message=f"JavaScript parser failed for file: {file_path}",
                        details=str(e),
                        severity=ErrorSeverity.MEDIUM,
                        recoverable=True,
                        stage="javascript_parsing",
                        file_path=file_path,
                        exception=e
                    )
                    # Fall back to basic text analysis
                    chunks = self._fallback_text_analysis(file_path, file_metadata)
                    code_structure = None
            else:
                handle_error(
                    category=ErrorCategory.PARSER,
                    message=f"Unsupported file type: {file_ext}",
                    details=f"File: {file_path}",
                    severity=ErrorSeverity.LOW,
                    recoverable=True,
                    stage="file_parsing",
                    file_path=file_path
                )
                return None
            
            # Update file metadata with parsing results
            if code_structure:
                file_metadata.function_count = len(getattr(code_structure, 'functions', []))
            
            return ParsedFile(
                file_path=file_path,
                file_metadata=file_metadata,
                code_structure=code_structure,
                chunks=chunks
            )
            
        except Exception as e:
            handle_error(
                category=ErrorCategory.PARSER,
                message=f"Unexpected error parsing file: {file_path}",
                details=str(e),
                severity=ErrorSeverity.HIGH,
                recoverable=True,
                stage="file_parsing",
                file_path=file_path,
                exception=e
            )
            return None
    
    def _extract_file_metadata(self, file_path: str) -> FileMetadata:
        """Extract metadata from a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            FileMetadata object
        """
        stat = os.stat(file_path)
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Determine file type
        if file_ext in {'.c', '.h'}:
            file_type = 'c'
        elif file_ext in {'.js', '.ts', '.jsx', '.tsx'}:
            file_type = 'javascript'
        else:
            file_type = 'unknown'
        
        # Count lines
        line_count = 0
        encoding = 'utf-8'
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for _ in f)
        except Exception:
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    line_count = sum(1 for _ in f)
                    encoding = 'latin-1'
            except Exception:
                line_count = 0
        
        return FileMetadata(
            file_path=file_path,
            file_size=stat.st_size,
            last_modified=datetime.fromtimestamp(stat.st_mtime),
            file_type=file_type,
            encoding=encoding,
            line_count=line_count,
            function_count=0  # Will be updated after parsing
        )
    
    def _extract_c_chunks(self, code_structure: CCodeStructure) -> List[CodeChunk]:
        """Extract code chunks from C code structure.
        
        Args:
            code_structure: Parsed C code structure
            
        Returns:
            List of code chunks
        """
        chunks = []
        
        if not os.path.exists(code_structure.file_path):
            return chunks
        
        with open(code_structure.file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Create chunks for each function
        for func in code_structure.functions:
            start_idx = max(0, func.start_line - 1)
            end_idx = min(len(lines), func.end_line)
            
            content = ''.join(lines[start_idx:end_idx])
            
            # If function is too large, split it
            if len(content) > self.max_chunk_size:
                sub_chunks = self._split_large_chunk(
                    content, func.name, func.start_line, func.end_line,
                    code_structure.file_path, ChunkType.FUNCTION,
                    {
                        'return_type': func.return_type,
                        'parameters': func.parameters,
                        'is_static': func.is_static,
                        'is_inline': func.is_inline
                    }
                )
                chunks.extend(sub_chunks)
            else:
                chunk = CodeChunk(
                    file_path=code_structure.file_path,
                    start_line=func.start_line,
                    end_line=func.end_line,
                    content=content.strip(),
                    function_name=func.name,
                    chunk_type=ChunkType.FUNCTION,
                    metadata={
                        'return_type': func.return_type,
                        'parameters': func.parameters,
                        'is_static': func.is_static,
                        'is_inline': func.is_inline,
                        'language': 'c'
                    }
                )
                chunks.append(chunk)
        
        # Create chunk for global elements if they exist
        global_chunk = self._create_global_chunk_c(code_structure, lines)
        if global_chunk:
            chunks.append(global_chunk)
        
        return chunks
    
    def _extract_js_chunks(self, code_structure: JSCodeStructure) -> List[CodeChunk]:
        """Extract code chunks from JavaScript code structure.
        
        Args:
            code_structure: Parsed JavaScript code structure
            
        Returns:
            List of code chunks
        """
        chunks = []
        
        if not os.path.exists(code_structure.file_path):
            return chunks
        
        with open(code_structure.file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Create chunks for each function
        for func in code_structure.functions:
            start_idx = max(0, func.start_line - 1)
            end_idx = min(len(lines), func.end_line)
            
            content = ''.join(lines[start_idx:end_idx])
            
            # If function is too large, split it
            if len(content) > self.max_chunk_size:
                sub_chunks = self._split_large_chunk(
                    content, func.name, func.start_line, func.end_line,
                    code_structure.file_path, ChunkType.FUNCTION,
                    {
                        'parameters': func.parameters,
                        'is_async': func.is_async,
                        'is_arrow': func.is_arrow,
                        'is_method': func.is_method,
                        'class_name': func.class_name
                    }
                )
                chunks.extend(sub_chunks)
            else:
                chunk = CodeChunk(
                    file_path=code_structure.file_path,
                    start_line=func.start_line,
                    end_line=func.end_line,
                    content=content.strip(),
                    function_name=func.name,
                    chunk_type=ChunkType.FUNCTION,
                    metadata={
                        'parameters': func.parameters,
                        'is_async': func.is_async,
                        'is_arrow': func.is_arrow,
                        'is_method': func.is_method,
                        'class_name': func.class_name,
                        'language': 'javascript'
                    }
                )
                chunks.append(chunk)
        
        # Create chunks for each class
        for cls in code_structure.classes:
            start_idx = max(0, cls.start_line - 1)
            end_idx = min(len(lines), cls.end_line)
            
            content = ''.join(lines[start_idx:end_idx])
            
            if len(content) > self.max_chunk_size:
                sub_chunks = self._split_large_chunk(
                    content, cls.name, cls.start_line, cls.end_line,
                    code_structure.file_path, ChunkType.CLASS,
                    {
                        'methods': [m.name for m in cls.methods],
                        'properties': cls.properties,
                        'extends': cls.extends
                    }
                )
                chunks.extend(sub_chunks)
            else:
                chunk = CodeChunk(
                    file_path=code_structure.file_path,
                    start_line=cls.start_line,
                    end_line=cls.end_line,
                    content=content.strip(),
                    function_name=cls.name,
                    chunk_type=ChunkType.CLASS,
                    metadata={
                        'methods': [m.name for m in cls.methods],
                        'properties': cls.properties,
                        'extends': cls.extends,
                        'language': 'javascript'
                    }
                )
                chunks.append(chunk)
        
        # Create chunk for global elements if they exist
        global_chunk = self._create_global_chunk_js(code_structure, lines)
        if global_chunk:
            chunks.append(global_chunk)
        
        return chunks
    
    def _split_large_chunk(self, content: str, name: str, start_line: int, end_line: int,
                          file_path: str, chunk_type: ChunkType, 
                          metadata: Dict[str, Any]) -> List[CodeChunk]:
        """Split a large code chunk into smaller pieces.
        
        Args:
            content: The content to split
            name: Name of the function/class
            start_line: Starting line number
            end_line: Ending line number
            file_path: Path to the source file
            chunk_type: Type of chunk
            metadata: Metadata for the chunk
            
        Returns:
            List of smaller code chunks
        """
        chunks = []
        lines = content.split('\n')
        current_chunk_lines = []
        current_size = 0
        chunk_start_line = start_line
        part_number = 1
        
        for i, line in enumerate(lines):
            line_size = len(line) + 1  # +1 for newline
            
            if current_size + line_size > self.max_chunk_size and current_chunk_lines:
                # Create chunk from accumulated lines
                chunk_content = '\n'.join(current_chunk_lines)
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    'is_partial': True,
                    'part_of': name,
                    'part_number': part_number,
                    'total_parts': 'unknown'  # Will be updated after all parts are created
                })
                
                chunk = CodeChunk(
                    file_path=file_path,
                    start_line=chunk_start_line,
                    end_line=chunk_start_line + len(current_chunk_lines) - 1,
                    content=chunk_content,
                    function_name=f"{name}_part_{part_number}",
                    chunk_type=chunk_type,
                    metadata=chunk_metadata
                )
                chunks.append(chunk)
                
                # Start new chunk
                current_chunk_lines = [line]
                current_size = line_size
                chunk_start_line = start_line + i
                part_number += 1
            else:
                current_chunk_lines.append(line)
                current_size += line_size
        
        # Add remaining lines as final chunk
        if current_chunk_lines:
            chunk_content = '\n'.join(current_chunk_lines)
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                'is_partial': True,
                'part_of': name,
                'part_number': part_number,
                'total_parts': part_number
            })
            
            chunk = CodeChunk(
                file_path=file_path,
                start_line=chunk_start_line,
                end_line=chunk_start_line + len(current_chunk_lines) - 1,
                content=chunk_content,
                function_name=f"{name}_part_{part_number}",
                chunk_type=chunk_type,
                metadata=chunk_metadata
            )
            chunks.append(chunk)
        
        # Update total_parts in all chunks
        for chunk in chunks:
            chunk.metadata['total_parts'] = part_number
        
        return chunks
    
    def _create_global_chunk_c(self, code_structure: CCodeStructure, 
                              lines: List[str]) -> Optional[CodeChunk]:
        """Create a global chunk for C code containing includes, defines, etc.
        
        Args:
            code_structure: Parsed C code structure
            lines: Source file lines
            
        Returns:
            CodeChunk for global elements or None
        """
        global_elements = []
        
        # Add includes
        for include in code_structure.includes:
            global_elements.append(include)
        
        # Add defines
        for define in code_structure.defines:
            global_elements.append(f"#define {define['name']} {define['value']}")
        
        # Add struct definitions (simplified representation)
        for struct in code_structure.structs:
            struct_def = f"struct {struct['name']} {{"
            for field in struct.get('fields', []):
                struct_def += f"\n    {field['type']} {field['name']};"
            struct_def += "\n};"
            global_elements.append(struct_def)
        
        # Add enum definitions
        for enum in code_structure.enums:
            enum_def = f"enum {enum['name']} {{"
            if enum.get('values'):
                enum_def += ", ".join(enum['values'])
            enum_def += "};"
            global_elements.append(enum_def)
        
        # Add global variables
        for var in code_structure.global_variables:
            global_elements.append(f"{var['type']} {var['name']};")
        
        if not global_elements:
            return None
        
        content = '\n'.join(global_elements)
        
        return CodeChunk(
            file_path=code_structure.file_path,
            start_line=1,
            end_line=len(lines),
            content=content,
            chunk_type=ChunkType.GLOBAL,
            metadata={
                'includes_count': len(code_structure.includes),
                'defines_count': len(code_structure.defines),
                'structs_count': len(code_structure.structs),
                'enums_count': len(code_structure.enums),
                'global_vars_count': len(code_structure.global_variables),
                'language': 'c'
            }
        )
    
    def _create_global_chunk_js(self, code_structure: JSCodeStructure, 
                               lines: List[str]) -> Optional[CodeChunk]:
        """Create a global chunk for JavaScript code containing imports, exports, etc.
        
        Args:
            code_structure: Parsed JavaScript code structure
            lines: Source file lines
            
        Returns:
            CodeChunk for global elements or None
        """
        global_elements = []
        
        # Add imports
        for imp in code_structure.imports:
            global_elements.append(imp.get('statement', ''))
        
        # Add requires
        for req in code_structure.requires:
            global_elements.append(f"require('{req}')")
        
        # Add exports
        for exp in code_structure.exports:
            global_elements.append(exp.get('statement', ''))
        
        # Add global variables
        for var in code_structure.variables:
            global_elements.append(f"{var['type']} {var['name']}")
        
        if not global_elements:
            return None
        
        content = '\n'.join(filter(None, global_elements))
        
        return CodeChunk(
            file_path=code_structure.file_path,
            start_line=1,
            end_line=len(lines),
            content=content,
            chunk_type=ChunkType.GLOBAL,
            metadata={
                'imports_count': len(code_structure.imports),
                'exports_count': len(code_structure.exports),
                'requires_count': len(code_structure.requires),
                'variables_count': len(code_structure.variables),
                'language': 'javascript'
            }
        )
    
    def extract_code_references(self, chunks: List[CodeChunk]) -> List[CodeReference]:
        """Extract code references from chunks for traceability.
        
        Args:
            chunks: List of code chunks
            
        Returns:
            List of code references
        """
        references = []
        
        for chunk in chunks:
            ref = CodeReference(
                file_path=chunk.file_path,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                function_name=chunk.function_name,
                context=f"{chunk.chunk_type.name}: {chunk.function_name or 'global'}"
            )
            references.append(ref)
        
        return references
    
    def get_chunk_statistics(self, chunks: List[CodeChunk]) -> Dict[str, Any]:
        """Get statistics about the extracted chunks.
        
        Args:
            chunks: List of code chunks
            
        Returns:
            Dictionary with chunk statistics
        """
        stats = {
            'total_chunks': len(chunks),
            'function_chunks': 0,
            'class_chunks': 0,
            'global_chunks': 0,
            'c_chunks': 0,
            'js_chunks': 0,
            'average_chunk_size': 0,
            'max_chunk_size': 0,
            'min_chunk_size': float('inf') if chunks else 0,
            'partial_chunks': 0
        }
        
        total_size = 0
        
        for chunk in chunks:
            chunk_size = len(chunk.content)
            total_size += chunk_size
            
            # Update size statistics
            stats['max_chunk_size'] = max(stats['max_chunk_size'], chunk_size)
            stats['min_chunk_size'] = min(stats['min_chunk_size'], chunk_size)
            
            # Count by type
            if chunk.chunk_type == ChunkType.FUNCTION:
                stats['function_chunks'] += 1
            elif chunk.chunk_type == ChunkType.CLASS:
                stats['class_chunks'] += 1
            elif chunk.chunk_type == ChunkType.GLOBAL:
                stats['global_chunks'] += 1
            
            # Count by language
            language = chunk.metadata.get('language', 'unknown')
            if language == 'c':
                stats['c_chunks'] += 1
            elif language == 'javascript':
                stats['js_chunks'] += 1
            
            # Count partial chunks
            if chunk.metadata.get('is_partial', False):
                stats['partial_chunks'] += 1
        
        if chunks:
            stats['average_chunk_size'] = total_size // len(chunks)
            if stats['min_chunk_size'] == float('inf'):
                stats['min_chunk_size'] = 0
        
        return stats
    
    def _fallback_text_analysis(self, file_path: str, file_metadata: FileMetadata) -> List[CodeChunk]:
        """Perform basic text analysis as fallback when parsing fails.
        
        Args:
            file_path: Path to the file
            file_metadata: File metadata
            
        Returns:
            List of basic code chunks
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Create a single chunk with the entire file content
            chunk = CodeChunk(
                file_path=file_path,
                start_line=1,
                end_line=file_metadata.line_count,
                function_name=None,
                content=content,
                chunk_type=ChunkType.GLOBAL,
                metadata={
                    'language': file_metadata.file_type,
                    'is_fallback': True,
                    'analysis_method': 'text_based'
                }
            )
            
            return [chunk]
            
        except Exception as e:
            handle_error(
                category=ErrorCategory.PARSER,
                message=f"Fallback text analysis failed: {file_path}",
                details=str(e),
                severity=ErrorSeverity.MEDIUM,
                recoverable=True,
                stage="fallback_analysis",
                file_path=file_path,
                exception=e
            )
            return []
    
    def is_supported_file(self, file_path: str) -> bool:
        """Check if a file is supported for parsing.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file is supported, False otherwise
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        return file_ext in self.supported_extensions
    
    def get_supported_extensions(self) -> set:
        """Get the set of supported file extensions.
        
        Returns:
            Set of supported file extensions
        """
        return self.supported_extensions.copy()