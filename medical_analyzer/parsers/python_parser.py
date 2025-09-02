"""
Python code parser for extracting code chunks from Python files.
"""

import ast
import os
from typing import List, Optional
from ..models import CodeChunk


class PythonParser:
    """Parser for Python source files."""
    
    def __init__(self):
        """Initialize the Python parser."""
        pass
    
    def parse_file(self, file_path: str) -> Optional[List[CodeChunk]]:
        """
        Parse a Python file and extract code chunks.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            List of CodeChunk objects or None if parsing failed
        """
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the Python AST
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                # If AST parsing fails, fall back to simple line-based chunking
                return self._parse_with_fallback(file_path, content)
            
            chunks = []
            
            # Extract function and class definitions
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    chunk = self._create_function_chunk(file_path, content, node)
                    if chunk:
                        chunks.append(chunk)
                elif isinstance(node, ast.ClassDef):
                    chunk = self._create_class_chunk(file_path, content, node)
                    if chunk:
                        chunks.append(chunk)
            
            # If no functions or classes found, create a single chunk for the entire file
            if not chunks:
                chunks.append(CodeChunk(
                    file_path=file_path,
                    start_line=1,
                    end_line=len(content.splitlines()),
                    content=content,
                    function_name="module_level",
                    metadata={
                        'language': 'python',
                        'chunk_type': 'module',
                        'parser': 'python_ast'
                    }
                ))
            
            return chunks
            
        except Exception as e:
            # Fallback to simple parsing if AST parsing fails
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return self._parse_with_fallback(file_path, content)
            except Exception:
                return None
    
    def _create_function_chunk(self, file_path: str, content: str, node: ast.FunctionDef) -> Optional[CodeChunk]:
        """Create a code chunk for a function definition."""
        try:
            lines = content.splitlines()
            start_line = node.lineno
            end_line = node.end_lineno if hasattr(node, 'end_lineno') and node.end_lineno else start_line
            
            # Extract the function content
            if end_line <= len(lines):
                function_content = '\n'.join(lines[start_line-1:end_line])
            else:
                function_content = '\n'.join(lines[start_line-1:])
            
            return CodeChunk(
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                content=function_content,
                function_name=node.name,
                metadata={
                    'language': 'python',
                    'chunk_type': 'function',
                    'is_async': isinstance(node, ast.AsyncFunctionDef),
                    'args_count': len(node.args.args),
                    'parser': 'python_ast'
                }
            )
        except Exception:
            return None
    
    def _create_class_chunk(self, file_path: str, content: str, node: ast.ClassDef) -> Optional[CodeChunk]:
        """Create a code chunk for a class definition."""
        try:
            lines = content.splitlines()
            start_line = node.lineno
            end_line = node.end_lineno if hasattr(node, 'end_lineno') and node.end_lineno else start_line
            
            # Extract the class content
            if end_line <= len(lines):
                class_content = '\n'.join(lines[start_line-1:end_line])
            else:
                class_content = '\n'.join(lines[start_line-1:])
            
            # Count methods in the class
            method_count = sum(1 for child in node.body if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)))
            
            return CodeChunk(
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                content=class_content,
                function_name=f"class_{node.name}",
                metadata={
                    'language': 'python',
                    'chunk_type': 'class',
                    'class_name': node.name,
                    'method_count': method_count,
                    'base_classes': [base.id for base in node.bases if isinstance(base, ast.Name)],
                    'parser': 'python_ast'
                }
            )
        except Exception:
            return None
    
    def _parse_with_fallback(self, file_path: str, content: str) -> Optional[List[CodeChunk]]:
        """Fallback parser that creates chunks based on simple heuristics."""
        try:
            lines = content.splitlines()
            chunks = []
            current_chunk_start = 1
            current_chunk_lines = []
            current_function = None
            
            for i, line in enumerate(lines, 1):
                stripped_line = line.strip()
                
                # Detect function or class definitions
                if (stripped_line.startswith('def ') or 
                    stripped_line.startswith('class ') or 
                    stripped_line.startswith('async def ')):
                    
                    # Save previous chunk if it exists
                    if current_chunk_lines:
                        chunk_content = '\n'.join(current_chunk_lines)
                        chunks.append(CodeChunk(
                            file_path=file_path,
                            start_line=current_chunk_start,
                            end_line=i-1,
                            content=chunk_content,
                            function_name=current_function or "module_level",
                            metadata={
                                'language': 'python',
                                'chunk_type': 'fallback',
                                'parser': 'python_fallback'
                            }
                        ))
                    
                    # Start new chunk
                    current_chunk_start = i
                    current_chunk_lines = [line]
                    
                    # Extract function/class name
                    if stripped_line.startswith('def '):
                        current_function = stripped_line.split('def ')[1].split('(')[0].strip()
                    elif stripped_line.startswith('async def '):
                        current_function = stripped_line.split('async def ')[1].split('(')[0].strip()
                    elif stripped_line.startswith('class '):
                        current_function = f"class_{stripped_line.split('class ')[1].split('(')[0].split(':')[0].strip()}"
                else:
                    current_chunk_lines.append(line)
            
            # Add the last chunk
            if current_chunk_lines:
                chunk_content = '\n'.join(current_chunk_lines)
                chunks.append(CodeChunk(
                    file_path=file_path,
                    start_line=current_chunk_start,
                    end_line=len(lines),
                    content=chunk_content,
                    function_name=current_function or "module_level",
                    metadata={
                        'language': 'python',
                        'chunk_type': 'fallback',
                        'parser': 'python_fallback'
                    }
                ))
            
            # If no chunks were created, create one for the entire file
            if not chunks:
                chunks.append(CodeChunk(
                    file_path=file_path,
                    start_line=1,
                    end_line=len(lines),
                    content=content,
                    function_name="module_level",
                    metadata={
                        'language': 'python',
                        'chunk_type': 'module',
                        'parser': 'python_fallback'
                    }
                ))
            
            return chunks
            
        except Exception:
            return None